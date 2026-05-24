#!/usr/bin/env bash
# Lira — one-shot installer for a fresh Ubuntu 22.04 / 24.04 VPS
# (Timeweb / Beget / Selectel / любой провайдер).
#
# Запускать ОТ ROOT:
#   sudo bash setup.sh
#
# До запуска: положи рядом lira-vps.tar.gz и (опционально) свой .env.
# Скрипт идемпотентный: можно безопасно перезапускать.

set -euo pipefail

APP_DIR=/opt/lira
ARCHIVE=${ARCHIVE:-lira-vps.tar.gz}
DOMAIN=${DOMAIN:-}   # можно передать так: DOMAIN=lira.ru bash setup.sh

log(){ printf "\n\033[1;32m==> %s\033[0m\n" "$*"; }
err(){ printf "\n\033[1;31m!! %s\033[0m\n" "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || err "Запусти от root: sudo bash setup.sh"

log "1/6  apt update + базовые пакеты"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq ca-certificates curl gnupg lsb-release ufw rsync

if ! command -v docker >/dev/null 2>&1; then
  log "2/6  Установка Docker"
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
else
  log "2/6  Docker уже установлен — пропускаю"
fi

log "3/6  Распаковка приложения в $APP_DIR"
mkdir -p "$APP_DIR"
if [ ! -f "$ARCHIVE" ]; then
  err "Не нашёл архив $ARCHIVE рядом с setup.sh. Скопируй его на сервер и перезапусти."
fi
tar xzf "$ARCHIVE" -C /tmp
SRC_DIR=$(find /tmp -maxdepth 2 -type d -name 'lira-deploy' | head -1)
[ -d "$SRC_DIR" ] || err "В архиве нет папки lira-deploy/"
rsync -a --delete --exclude='.env' --exclude='app.db' "$SRC_DIR/" "$APP_DIR/"

if [ ! -f "$APP_DIR/.env" ]; then
  log "    Создаю .env из шаблона. ОТРЕДАКТИРУЙ: nano $APP_DIR/.env"
  cp "$APP_DIR/.env.docker.example" "$APP_DIR/.env"
fi

log "4/6  Сборка и запуск контейнера (api + опционально bot)"
cd "$APP_DIR"
PROFILE_ARG=""
# When BOT_TOKEN is set, run the bot in a dedicated container AND tell
# the api container NOT to also start an in-process bot poller —
# Telegram allows only one getUpdates per token, so two pollers would
# fight each other and drop updates.
export RUN_BOT_IN_API=1
if grep -E '^BOT_TOKEN=.+' .env >/dev/null 2>&1; then
  log "    BOT_TOKEN найден — запускаю и API, и бота (в отдельном контейнере)"
  PROFILE_ARG="--profile bot"
  export RUN_BOT_IN_API=0
else
  log "    BOT_TOKEN пуст — поднимаю только API (без бота)"
fi
docker compose $PROFILE_ARG up -d --build

log "5/6  Файрвол: открываю 80/443/22"
ufw allow 22/tcp  >/dev/null || true
ufw allow 80/tcp  >/dev/null || true
ufw allow 443/tcp >/dev/null || true
ufw --force enable >/dev/null || true

log "6/6  Caddy reverse proxy"
if ! command -v caddy >/dev/null 2>&1; then
  apt-get install -y -qq debian-keyring debian-archive-keyring apt-transport-https
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
    | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
    > /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -qq
  apt-get install -y -qq caddy
fi

if [ -n "$DOMAIN" ]; then
  log "    Собираю Caddyfile с HTTPS для $DOMAIN"
  cat > /etc/caddy/Caddyfile <<EOF
{
  email admin@$DOMAIN
}

# Canonical host: serves the app over HTTPS with security headers.
$DOMAIN {
  reverse_proxy 127.0.0.1:8000
  encode gzip zstd
  header {
    Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
    X-Content-Type-Options "nosniff"
    X-Frame-Options "SAMEORIGIN"
    Referrer-Policy "strict-origin-when-cross-origin"
    Permissions-Policy "geolocation=(), microphone=(), camera=()"
    # No need to advertise the upstream framework version.
    -Server
  }
  # Cache static assets aggressively (filenames are hashed by Expo).
  @hashedAssets path /_expo/static/* /assets/* /icons/*
  header @hashedAssets Cache-Control "public, max-age=31536000, immutable"
}

# 301 the www variant to the apex so we don't have two canonical URLs.
www.$DOMAIN {
  redir https://$DOMAIN{uri} 301
}
EOF
  systemctl reload caddy || systemctl restart caddy
  log "    Caddy перезагружен. Сертификат Let's Encrypt получится автоматом при первом запросе."
else
  log "    DOMAIN не указан — ставлю HTTP-only прокси на :80 (без HTTPS)"
  cat > /etc/caddy/Caddyfile <<'EOF'
:80 {
  reverse_proxy 127.0.0.1:8000
  encode gzip
}
EOF
  systemctl reload caddy || systemctl restart caddy
  log "    Чтобы включить HTTPS позже: DOMAIN=твой.домен.ru bash setup.sh"
fi

# ─── Backups ────────────────────────────────────────────────────────────
# Nightly snapshot of the SQLite database (and the .env file) into
# /opt/lira/backups/. Keep 14 days. Free, local only. To off-site backups
# (e.g. to Yandex.Object Storage) — add an `rclone copy` step at the end
# of this script once `rclone config` has been set up.
log "7/7  Настройка автобэкапов БД (ежедневно, 14 дней)"
install -d -m 0700 "$APP_DIR/backups"
cat > /usr/local/bin/lira-backup.sh <<'BACKUP_EOF'
#!/usr/bin/env bash
# Nightly Lira backup — runs from cron at 03:17 (see setup.sh).
# Produces ${APP_DIR}/backups/app.db.<timestamp>.gz and env.<timestamp>.
# Keeps the last 14 days only.
set -euo pipefail
APP_DIR=/opt/lira
BACKUP_DIR=$APP_DIR/backups
KEEP_DAYS=14
DATE=$(date +%Y%m%d-%H%M%S)
mkdir -p "$BACKUP_DIR"

# Use sqlite3 Python module inside the api container — it's guaranteed
# present (stdlib). .backup makes a consistent snapshot even while the
# app is writing.
if docker compose -f "$APP_DIR/docker-compose.yml" ps --status=running --services 2>/dev/null | grep -q api; then
  docker compose -f "$APP_DIR/docker-compose.yml" exec -T api python -c '
import sqlite3, os, sys, tempfile
src = "/data/app.db"
if not os.path.exists(src):
    sys.exit(0)
tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db").name
src_con = sqlite3.connect(src)
dst_con = sqlite3.connect(tmp)
src_con.backup(dst_con)
src_con.close(); dst_con.close()
sys.stdout.buffer.write(open(tmp, "rb").read())
os.unlink(tmp)
' > "$BACKUP_DIR/app.db.$DATE" 2>/dev/null || true
fi

# .env also worth backing up — it contains payment provider keys etc.
if [ -f "$APP_DIR/.env" ]; then
  install -m 0600 "$APP_DIR/.env" "$BACKUP_DIR/env.$DATE"
fi

# Skip empty / broken snapshots (e.g. db not yet created).
if [ -s "$BACKUP_DIR/app.db.$DATE" ]; then
  gzip -9 "$BACKUP_DIR/app.db.$DATE"
else
  rm -f "$BACKUP_DIR/app.db.$DATE"
fi

# Retention — delete files older than $KEEP_DAYS days.
find "$BACKUP_DIR" -type f -mtime +"$KEEP_DAYS" -delete 2>/dev/null || true
BACKUP_EOF
chmod 0755 /usr/local/bin/lira-backup.sh

# cron @daily — 03:17 by default (off-peak)
CRON_LINE="17 3 * * * /usr/local/bin/lira-backup.sh >/var/log/lira-backup.log 2>&1"
( crontab -l 2>/dev/null | grep -v 'lira-backup.sh' ; echo "$CRON_LINE" ) | crontab -
log "    Бэкапы каждый день в 03:17, хранятся 14 дней в $APP_DIR/backups"

echo
log "Готово!"
echo "Проверь:"
echo "   curl http://localhost:8000/health"
echo "   docker compose -f $APP_DIR/docker-compose.yml ps"
if [ -n "$DOMAIN" ]; then
  echo "   https://$DOMAIN  ← открой в браузере (проксирует Caddy → docker:8000)"
else
  IP=$(hostname -I | awk '{print $1}')
  echo "   http://$IP/      ← открой в браузере (HTTP-only, проксирует Caddy)"
fi
