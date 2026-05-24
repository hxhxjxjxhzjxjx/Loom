#!/usr/bin/env bash
# ===========================================================
# Lira — установщик для Ubuntu 22.04 / 24.04 LTS
# Запускать ОТ root: sudo bash install.sh
#
# Опции через ENV:
#   SKIP_FIREWALL=1   — не ставить UFW и fail2ban (если ты уже их настроил)
# ===========================================================
set -euo pipefail

if [[ "$(id -u)" != "0" ]]; then
  echo "Этот скрипт нужно запускать с sudo. Пример: sudo bash install.sh"
  exit 1
fi

PKG_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR=/opt/lira
WEB_DIR=/var/www/lira
DATA_DIR=/var/lib/lira

echo
echo "==> 1/10  Проверяем .env"
if [[ ! -f "$PKG_DIR/.env" ]]; then
  if [[ ! -f "$PKG_DIR/.env.example" ]]; then
    echo "Не найден ни .env, ни .env.example — сломанная сборка."
    exit 1
  fi
  cp "$PKG_DIR/.env.example" "$PKG_DIR/.env"
  echo
  echo "  Файла .env не было — сделал из .env.example."
  echo "  СЕЙЧАС ОТКРОЙ ЕГО И ВСТАВЬ BOT_TOKEN и ADMIN_CHAT_ID:"
  echo
  echo "      nano $PKG_DIR/.env"
  echo
  echo "  Потом запусти этот скрипт ещё раз."
  exit 1
fi

if ! grep -E '^BOT_TOKEN=.+' "$PKG_DIR/.env" >/dev/null; then
  echo "  В $PKG_DIR/.env поле BOT_TOKEN пустое. Открой и заполни:"
  echo "      nano $PKG_DIR/.env"
  exit 1
fi

echo "==> 2/10  Ставим системные пакеты"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y >/dev/null
apt-get install -y --no-install-recommends \
  python3 python3-venv python3-pip \
  nginx sqlite3 curl ca-certificates unzip >/dev/null

echo "==> 3/10  Создаём пользователя lira и каталоги"
if ! id -u lira >/dev/null 2>&1; then
  useradd --system --create-home --shell /usr/sbin/nologin lira
fi
mkdir -p "$APP_DIR" "$WEB_DIR" "$DATA_DIR"
chown -R lira:lira "$APP_DIR" "$DATA_DIR"
chmod 750 "$DATA_DIR"

echo "==> 4/10  Копируем backend и web"
rm -rf "$APP_DIR/backend"
cp -r "$PKG_DIR/backend" "$APP_DIR/backend"
find "$APP_DIR/backend" -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true

rm -rf "$WEB_DIR"/*
cp -r "$PKG_DIR/web/"* "$WEB_DIR/"
chown -R www-data:www-data "$WEB_DIR"
chmod -R a+rX "$WEB_DIR"

# .env — секреты, читает только пользователь lira
cp "$PKG_DIR/.env" "$APP_DIR/.env"
chown lira:lira "$APP_DIR/.env"
chmod 600 "$APP_DIR/.env"

echo "==> 5/10  Создаём Python venv и ставим зависимости"
if [[ ! -d "$APP_DIR/venv" ]]; then
  python3 -m venv "$APP_DIR/venv"
fi
"$APP_DIR/venv/bin/pip" install --upgrade pip >/dev/null
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/backend/bot/requirements.txt" >/dev/null
chown -R lira:lira "$APP_DIR/venv"

echo "==> 6/10  Ставим systemd-юнит lira-api"
cp "$PKG_DIR/systemd/lira-api.service" /etc/systemd/system/lira-api.service
systemctl daemon-reload
systemctl enable lira-api >/dev/null

echo "==> 7/10  Ставим nginx-конфиг"
cp "$PKG_DIR/nginx/lira.conf" /etc/nginx/sites-available/lira
ln -sf /etc/nginx/sites-available/lira /etc/nginx/sites-enabled/lira
rm -f /etc/nginx/sites-enabled/default
# Скрываем версию nginx глобально (server_tokens off в sites-conf не действует на all-server ошибки)
if ! grep -q "^[[:space:]]*server_tokens off;" /etc/nginx/nginx.conf; then
  sed -i 's|http {|http {\n    server_tokens off;|' /etc/nginx/nginx.conf
fi
nginx -t

if [[ "${SKIP_FIREWALL:-0}" != "1" ]]; then
  echo "==> 8/10  Firewall + fail2ban + auto-updates"
  apt-get install -y --no-install-recommends ufw fail2ban unattended-upgrades >/dev/null

  # UFW: запрет всего входящего, открыты только 22, 80, 443
  ufw --force reset >/dev/null
  ufw default deny incoming >/dev/null
  ufw default allow outgoing >/dev/null
  ufw allow OpenSSH >/dev/null || ufw allow 22/tcp >/dev/null
  ufw allow 80/tcp >/dev/null
  ufw allow 443/tcp >/dev/null
  ufw --force enable >/dev/null

  # fail2ban: банит SSH-брутфорс + nginx-сканеры + нарушения rate-limit
  cp "$PKG_DIR/fail2ban/jail.local" /etc/fail2ban/jail.local
  cp "$PKG_DIR/fail2ban/filter-nginx-limit-req.conf" /etc/fail2ban/filter.d/nginx-limit-req.conf
  systemctl enable --now fail2ban >/dev/null 2>&1 || true
  systemctl restart fail2ban >/dev/null 2>&1 || true

  # unattended-upgrades: автоустановка security-патчей
  cat >/etc/apt/apt.conf.d/20auto-upgrades <<EOF
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF
  dpkg-reconfigure --priority=low unattended-upgrades >/dev/null 2>&1 || true
else
  echo "==> 8/10  SKIP_FIREWALL=1 — пропускаем UFW/fail2ban/auto-updates"
fi

echo "==> 9/10  Запускаем сервисы"
systemctl restart lira-api
systemctl reload nginx || systemctl restart nginx

# DB-файл (если уже создан) ограничиваем правами
if [[ -f "$DATA_DIR/app.db" ]]; then
  chown lira:lira "$DATA_DIR/app.db"
  chmod 600 "$DATA_DIR/app.db"
fi

echo "==> 10/10  Проверка локального API"
sleep 2
if curl -fsS --max-time 5 http://127.0.0.1:8000/v1/lira/status >/dev/null 2>&1; then
  echo "    API отвечает: OK"
else
  echo "    API не отвечает на 127.0.0.1:8000 — посмотри: journalctl -u lira-api -n 50"
fi

IP=$(curl -fsS -4 --max-time 3 ifconfig.io 2>/dev/null || hostname -I | awk '{print $1}')

cat <<EOF

============================================================
  ГОТОВО. Открой в браузере:

      http://${IP}

  Бот: открой своего бота в Telegram, напиши /start.

  Включена защита:
      • Firewall (UFW): открыты только 22/80/443
      • fail2ban: банит брутфорс SSH + nginx-сканеры
      • Rate-limit: чат 30 r/m, оплата 5 r/m на IP
      • Security headers + блокировка плохих ботов
      • Авто-патчи безопасности Ubuntu
      • .env с правами 600, доступен только пользователю lira

  Проверить состояние:
      systemctl status lira-api
      journalctl -u lira-api -f
      sudo fail2ban-client status
      sudo ufw status verbose

  Установить SSL (после покупки домена) — см. README.md §6.

  Дальше рекомендую: см. README.md §10 «Финальная защита SSH»
  (отключить вход по паролю, оставить только ключи).
============================================================

EOF
