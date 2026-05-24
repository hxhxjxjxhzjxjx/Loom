# Lira — деплой на свой VPS через docker-compose

Один контейнер отдаёт и фронт (статика из `web/`), и API (`/v1/...`, `/health`)
на одном порту. БД — локальный SQLite в named volume `lira-data` (выживает
рестарты и обновления образа). Telegram-бот — опционально, отдельным контейнером.

## Требования
- Ubuntu/Debian VPS с Docker 20.10+ и docker compose v2
  (`sudo apt install docker.io docker-compose-plugin -y`).
- Открыт порт 80 (а лучше 80+443 если планируешь HTTPS через nginx/Caddy).
- ~512 MB RAM, 1 vCPU, ~1 GB диска — этого хватит с запасом.

## Установка

```bash
# 1) Скопируй проект на сервер
scp -r lira-deploy/ user@vps:/opt/lira
ssh user@vps
cd /opt/lira

# 2) Заполни переменные окружения
cp .env.docker.example .env
nano .env          # CORS оставь пустым если домен один; для бота — BOT_TOKEN и т.п.

# 3) Собери и подними API (без бота)
docker compose up -d --build

# 4) Проверь
curl http://localhost:8000/health
# {"status":"ok"}
curl -I http://localhost:8000/
# HTTP/1.1 200 OK  ← раздаётся web/index.html
```

Открой `http://IP_СЕРВЕРА:8000` в браузере — приложение работает целиком,
включая чат с Ларой (он проксируется в pollinations.ai, ключа не нужно).

## Telegram-бот (опционально)

Бот живёт во втором сервисе, запускается только если активировать профиль
`bot` — это сделано чтобы случайно не упасть с пустым `BOT_TOKEN`.

```bash
# 1) Заполни в .env как минимум:
#    BOT_TOKEN=...
#    BOT_USERNAME=...
#    ADMIN_CHAT_ID=...
#    RUN_BOT_IN_API=0    # ← важно: иначе двойной getUpdates

# 2) Подними оба сервиса
docker compose --profile bot up -d --build
```

> **Важно:** Telegram-API разрешает только один `getUpdates`-поллер на токен.
> Если бот живёт в отдельном контейнере (профиль `bot`), API не должен
> поллить параллельно — поэтому `RUN_BOT_IN_API=0`. Для одноконтейнерных
> деплоев (Fly.io и т.п.) оставляй `RUN_BOT_IN_API=1` (значение по умолчанию).
> `setup.sh` выставляет переменную автоматически при наличии `BOT_TOKEN`.

Логи бота:
```bash
docker compose logs -f bot
```

## HTTPS

Контейнер слушает HTTP. Для боевого домена поставь перед ним обратный
прокси — самый простой вариант Caddy в один файл:

```caddyfile
# /etc/caddy/Caddyfile
lira.example.ru {
    reverse_proxy 127.0.0.1:8000
}
```

```bash
sudo apt install caddy -y
sudo systemctl reload caddy
```

Caddy сам получит Let's Encrypt сертификат при первом запросе. Если фронт
оставишь на отдельном поддомене, не забудь в `.env`:
```
ALLOWED_ORIGINS=https://app.example.ru
```

## Управление

```bash
# обновление кода (после git pull / новой версии web/)
docker compose build --no-cache && docker compose up -d

# логи
docker compose logs -f api
docker compose logs -f bot         # если бот включён

# стоп/старт
docker compose down                # остановить и удалить контейнеры
docker compose up -d               # поднять обратно (volume не трогается)

# бэкап БД
docker run --rm -v lira_lira-data:/data -v $PWD:/backup alpine \
  tar czf /backup/lira-db-$(date +%F).tgz -C /data app.db

# восстановление БД
docker run --rm -v lira_lira-data:/data -v $PWD:/backup alpine \
  tar xzf /backup/lira-db-2026-05-13.tgz -C /data
```

## Бэкапы

`setup.sh` ставит cron-задачу `/usr/local/bin/lira-backup.sh`, которая каждую
ночь (`03:17`) делает консистентный SQLite-снапшот через `con.backup()` и
кладёт его в `/opt/lira/backups/app.db.<timestamp>.gz`. Хранятся 14 дней,
старые автоматически удаляются. `.env` тоже бэкапится (мало ли потеряешь
платёжные ключи).

```bash
# Запустить вручную сейчас (для проверки):
sudo /usr/local/bin/lira-backup.sh
ls -la /opt/lira/backups/

# Восстановление:
gunzip -k /opt/lira/backups/app.db.20260513-031700.gz
docker compose down
docker cp /opt/lira/backups/app.db.20260513-031700 lira-api:/data/app.db
docker compose up -d
```

> Локальный бэкап не защитит от потери диска VPS. Когда соберёшься в прод —
> добавь шаг `rclone copy` к `lira-backup.sh` для off-site копии в
> Yandex.Object Storage / S3 (бесплатно до 1 GB).

## Аналитика и мониторинг

- **Yandex.Metrika**: счётчик регистрируется бесплатно на
  https://metrika.yandex.ru → создай счётчик → подставь ID в `web/index.html`,
  поиск по `var ID = '00000000'` → замени на свой.
  Параметры выставлены приватные: webvisor выключен, clickmap выключен,
  hash-роуты трекаются (`trackHash`).
- **Sentry**: бесплатный план 5к ошибок/мес. https://sentry.io → создай
  Browser SDK проект → вставь DSN в `web/index.html`, поиск по
  `var DSN = ''` → замени.
- **Uptime Robot** (бесплатно, https://uptimerobot.com): добавь URL
  `https://твой.домен.ru/health`, тип HTTP(s), интервал 5 минут, алерт в
  Telegram через `@uptimerobotbot`. Если упадёт — придёт сообщение.

## Файлы

- `Dockerfile` — образ с Python 3.11, зависимостями из `backend/bot/requirements.txt`, копией `backend/` + `web/` + `main.py`. Запускается uvicorn'ом, слушает порт 8000.
- `docker-compose.yml` — сервис `api` (всегда) и `bot` (по профилю). Общий volume `lira-data` смонтирован в `/data`, туда же по умолчанию пишется SQLite.
- `main.py` — точка входа для uvicorn. Импортирует FastAPI приложение из `backend/api/main.py` и монтирует `web/` как статику.
- `.env.docker.example` — шаблон переменных окружения.

## Что внутри запущено

- `GET /` → отдаёт `web/index.html` (SPA-шелл React Native Web).
- `GET /_expo/static/*` → JS/CSS бандла Expo.
- `GET /health` → `{"status":"ok"}` для мониторинга.
- `POST /v1/lira/chat` → проксирует в pollinations.ai, бесплатно, без ключа.
- Остальные `/v1/...` — подписки, привязка Telegram, заказы боксов и т.п.

Источник истины — `backend/api/main.py`.
