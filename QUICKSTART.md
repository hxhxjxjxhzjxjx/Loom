# Lira — быстрый старт

Этот архив — **полный исходный код** приложения: фронт (PWA), бэкенд
(FastAPI), Telegram-бот, конфиги Docker / nginx / Caddy, юр.документы,
скрипты деплоя и автобэкапы. Достаточно одного из путей ниже.

---

## A) Запустить локально на ПК (Mac / Linux / Windows-WSL)

Требуется только Docker Desktop (бесплатно: https://docs.docker.com/desktop/).

```bash
cd lira-deploy
cp .env.docker.example .env       # оставь как есть, бот не запустится
docker compose up -d --build
```

Откроется на http://localhost:8000.

Чтобы остановить:
```bash
docker compose down
```

---

## B) Положить в свой Git-репозиторий

### Через GitHub Desktop / VS Code (двойной клик)
1. Распакуй архив в любую папку (например, `Documents/lira`).
2. Открой папку в **GitHub Desktop**: меню «File → Add Local Repository».
3. Нажми «Create repository» / «Publish repository».
4. GitHub Desktop сам сделает commit + push.

### Через скрипт (Mac / Linux / WSL)
```bash
cd lira-deploy
bash git-init.sh https://github.com/<ник>/lira.git
```
Скрипт:
- инициализирует git,
- делает первый коммит со всем кодом,
- пушит в указанный репозиторий.

**Внимание:** перед пушем убедись, что `.env` НЕ зайдёт в репозиторий —
`.gitignore` его уже исключает. Не коммить токены и пароли.

### На Gitverse.ru (российский гит-хостинг)
Точно так же — просто замени `github.com` на `gitverse.ru/<ник>/lira.git`.

---

## C) Развернуть на VPS (продакшн)

См. [DOCKER.md](./DOCKER.md) и [README.md](./README.md). В двух командах:
```bash
scp lira-vps.tar.gz root@IP:/root/
ssh root@IP "cd /root && tar xzf lira-vps.tar.gz && cd lira-deploy && DOMAIN=твой.домен.ru bash setup.sh"
```

---

## D) Что внутри архива

| Папка / файл | Что это |
|---|---|
| `web/` | Фронт (PWA): React Native Web bundle, манифест, иконки, service worker |
| `web/index.html` | HTML-обёртка с возрастным gate, Метрикой/Sentry, ⓘ-модалкой |
| `web/legal/` | 4 юр.страницы (Политика, Оферта, О сервисе, Контакты) + `footer.js` с реквизитами |
| `backend/api/` | FastAPI: `/v1/lira/*`, `/health`, прокси чата в pollinations.ai |
| `backend/bot/` | Telegram-бот (aiogram), модели SQLAlchemy, сервисы |
| `Dockerfile`, `docker-compose.yml` | Контейнеризация |
| `setup.sh` | One-shot инсталлятор на чистый VPS (Docker + Caddy + HTTPS + бэкапы) |
| `install.sh` | Альтернативный инсталлятор: nginx + systemd (без Docker) |
| `update.sh` | Обновление кода через git pull |
| `nginx/`, `systemd/`, `fail2ban/` | Конфиги защиты (на случай если не Docker, а installl.sh) |
| `HANDOVER.md` | **Чек-лист после ИП** — что заполнить, где, за сколько минут |
| `DOCKER.md` | Глубокая дока по docker-compose, бэкапам, Метрике, Sentry |
| `README.md` | Полный референс по продакшн-установке через install.sh |

---

## E) Что ОБЯЗАТЕЛЬНО заполнить перед запуском в коммерческий бой

Все TODO-маркеры найдёшь так:
```bash
grep -rn "TODO\|PLACEHOLDER\|00000000\|770000000000" .
```

Список (полная версия — в [HANDOVER.md](./HANDOVER.md)):

1. **`web/legal/footer.js`** — реквизиты ИП (1 файл, 6 строк).
2. **`web/index.html`** — Yandex.Metrika ID + Sentry DSN (2 строки).
3. **`.env` на сервере** — `BOT_TOKEN`, `BOT_USERNAME`, `ADMIN_CHAT_ID`.
4. (Когда подключишь ЮКассу) — попроси добавить интеграцию в
   `backend/api/main.py` функция `create_payment_link()`.

---

## F) Поддержка

- **Документация:** `DOCKER.md` (Docker-путь), `README.md` (nginx-путь),
  `HANDOVER.md` (продакшн-чек-лист).
- **Аудит безопасности:** `AUDIT_REPORT.md` рядом с архивом.
- **Возникли вопросы по коду** — есть смысл сразу спросить разработчика
  (меня), пока всё в голове.
