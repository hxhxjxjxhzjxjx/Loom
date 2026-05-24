# Lira

Трекер цикла, прогноз овуляции, чат-ассистент и подписка Lira Box с заботой
каждый месяц. PWA + Telegram-бот + FastAPI backend, упакованные в Docker.

> 🇷🇺 152-ФЗ-готово, юр.документы под РФ, заглушка платёжки для ЮКассы/Тинькофф,
> возрастной gate 16+, безопасность по чек-листу.

---

## Быстрый старт

```bash
git clone https://github.com/hxhxjxjxhzjxjx/Loom.git lira
cd lira
cp .env.docker.example .env
docker compose up -d --build
```

Открой <http://localhost:8000>.

**Альтернативно:** скачай ZIP кнопкой выше (зелёная **Code → Download ZIP**) —
работает без `git`. Дальше — `docker compose up -d --build`.

---

## Что внутри

| Папка / файл | Описание |
|---|---|
| **`web/`** | Фронт (PWA): React Native Web bundle, manifest, иконки, service worker |
| `web/index.html` | HTML-обёртка: возрастной gate, согласие, Метрика/Sentry, ⓘ-модалка с правовой инфой |
| `web/legal/` | 4 юр.страницы (Политика, Оферта, О сервисе, Контакты) + `footer.js` (single source of truth для реквизитов) |
| **`backend/api/`** | FastAPI: `/v1/lira/*`, `/health`, прокси чата в pollinations.ai |
| **`backend/bot/`** | Telegram-бот (aiogram), SQLAlchemy-модели, сервисы |
| `Dockerfile`, `docker-compose.yml` | Контейнеризация |
| `setup.sh` | One-shot инсталлятор на чистый VPS (Docker + Caddy + HTTPS + бэкапы) |
| `install.sh` | Альтернативный инсталлятор: nginx + systemd (без Docker) |
| `update.sh` | Обновление кода через git pull |
| `nginx/`, `systemd/`, `fail2ban/` | Конфиги защиты для не-Docker деплоя |
| **`HANDOVER.md`** | Чек-лист «после ИП» — что заполнить, где, за сколько минут |
| **`DOCKER.md`** | Дока: docker-compose, бэкапы, Yandex.Metrika, Sentry, UptimeRobot |
| **`QUICKSTART.md`** | Короткая инструкция: PC / Git / VPS — 3 пути |
| `README-VPS-FULL.md` | Полный референс продакшн-установки через `install.sh` |

---

## Документация

- 📖 **[QUICKSTART.md](./QUICKSTART.md)** — короткий старт: на ПК, в Git, на VPS.
- 📋 **[HANDOVER.md](./HANDOVER.md)** — чек-лист после регистрации ИП (12 шагов).
- 🐳 **[DOCKER.md](./DOCKER.md)** — деплой через docker-compose, мониторинг, бэкапы.
- 🏭 **[README-VPS-FULL.md](./README-VPS-FULL.md)** — продакшн через nginx + systemd.

---

## Безопасность

Все правки из аудита (rate-limit, CORS, security headers, non-root Docker,
healthcheck, валидация ввода, fail2ban) встроены. Полный отчёт по 9 фиксам —
рядом с этим репозиторием в файле `AUDIT_REPORT.md` (присылается отдельно с
архивами; в репозитории не размещён, чтобы не светить вектора).

---

## Состояние

- ✅ MVP-функционал работает
- ✅ Юр.документы под РФ-юрисдикцию (152-ФЗ, оферта)
- ✅ Заглушка для оплаты — текст и UI готовы, ЮКасса подключается за час
- ✅ Возрастной gate 16+ + согласие на ОПД
- ✅ Yandex.Metrika и Sentry — хуки готовы, нужны ID/DSN
- ✅ Автобэкап БД (cron + sqlite `.backup`, 14 дней ротации)
- 🔲 Подключение реальной платёжки (после регистрации ИП)
- 🔲 Off-site бэкапы (после первых платежей)
- 🔲 Postgres (после ~500 пользователей)

---

## Лицензия

Proprietary — см. [LICENSE](./LICENSE). По вопросам — `support@<домен>.ru`
после регистрации ИП.

---

*Создано совместно с Devin (https://devin.ai).*
