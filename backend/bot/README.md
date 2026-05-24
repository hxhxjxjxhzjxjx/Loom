# FlowCare Telegram Bot

Backend service for the **Flow** menstrual-cycle tracker app: sells the
monthly "care box" subscription, runs a deep questionnaire to learn the
customer, generates an activation code for the mobile app, and helps an
operator assemble personalised boxes every cycle.

## Architecture

```
bot/
├── main.py             # aiogram entrypoint + APScheduler
├── config.py           # pydantic-settings, env-driven
├── db.py               # SQLAlchemy async engine + session
├── states.py           # FSM states for the questionnaire
├── handlers/           # aiogram routers
│   ├── start.py        # /start, /help, /cancel, welcome screen
│   ├── onboarding.py   # 7-step questionnaire FSM
│   ├── payment.py      # tariff selection + Telegram Payments + code issuing
│   └── cabinet.py      # /mybox, edit profile, pause
├── keyboards/          # inline keyboard builders
├── models/             # SQLAlchemy ORM (User, Profile, Subscription,
│                       #   ActivationCode, CatalogItem, Order, DeliveryHistory)
├── services/           # repositories + business logic
│   ├── users.py
│   ├── subscriptions.py
│   ├── codes.py        # 8-char unique code generation + redeem
│   ├── catalog.py      # ~30-item seeded catalog
│   ├── recommender.py  # filter by allergies/season/history → box list
│   └── payments.py     # Telegram Payments invoice + post-pay finalisation
├── scheduler.py        # APScheduler daily job (T-5 days from cycle)
└── migrations/         # Alembic
api/
├── main.py             # FastAPI: POST /v1/activate {code} → tariff/expires
└── Dockerfile
```

The bot and the API share the same SQLAlchemy models and database — the
bot writes activation codes, the API redeems them on behalf of the
mobile app.

## Setup

### 1. Create the bot

1. Open [@BotFather](https://t.me/BotFather), `/newbot`, choose name & username.
2. Copy the `BOT_TOKEN`.
3. (Optional, for real payments) `/mybots` → choose bot → **Payments**
   → connect a YooMoney provider; copy the `PAYMENT_PROVIDER_TOKEN`.

### 2. Find your admin chat ID

Forward any message to [@userinfobot](https://t.me/userinfobot). It will
reply with your numeric chat ID. Optionally create a separate chat for
box-assembly tasks and use its ID as `ASSEMBLY_CHAT_ID`.

### 3. Configure environment

```bash
cd bot
cp .env.example .env
# edit BOT_TOKEN, ADMIN_CHAT_ID, PAYMENT_PROVIDER_TOKEN
```

### 4. Run with Docker Compose (recommended)

From the repo root:

```bash
docker compose up -d --build
docker compose logs -f bot
```

This launches:
- `postgres` (Postgres 16, port 5432)
- `bot` — the aiogram bot, polling Telegram
- `api` — FastAPI on port 8000

### 5. Run locally without Docker (SQLite)

```bash
cd bot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd ..
python -m bot.main          # questionnaire bot
# in another terminal:
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

## Activation flow

1. Customer runs `/start`, taps **Начать настройку бокса**.
2. Bot walks through 7 steps:
   - Basic profile (name, age, city, cycle stats)
   - Hygiene preferences (pads + tampons by brand, cup, period panties)
   - Allergies & sensitive skin
   - Lifestyle (diet, goal, joys, novelty, dislikes)
   - Deep preferences (favourite season, calming, occupation, hobbies)
   - Delivery address
   - Tariff (Basic 999₽ / VIP 1999₽) + Telegram Payments
3. After successful payment the bot generates a unique 8-char activation
   code (e.g. `K7M3X2QY`) and DMs it to the customer.
4. Customer pastes the code into the **Подписка** tab in the Lira app.
   The app calls `POST /v1/activate {code}` against the FastAPI service.
   The service redeems the code and returns `{valid, tariff, expires}`,
   which the app stores locally and uses to flip the subscription banner.

## Personal cabinet

- `/mybox` — current tariff, valid-through date, predicted next ship
  date, and the contents of the previous box (after shipping).
- "✏️ Изменить профиль" — re-runs the questionnaire (overwrites answers).
- "⏸ Поставить на паузу" — DMs the admin chat with a pause request.

## Box assembly job

`scheduler.py` runs daily at 09:00 UTC and checks every active
subscription. For each user whose next ship date is *today*
(`anchor_date + cycle_length − BOX_LEAD_DAYS`), it:

1. Calls `services.recommender.build_box(user, profile, tariff)`.
2. Filters the catalog by allergies, sensitivity, diet, current season.
3. Avoids items shipped in the last 3 boxes (novelty bonus).
4. Picks one item per slot (tariff-specific composition).
5. DMs the assembly chat with the list, formatted for the operator.
6. Records the planned shipment in `delivery_history` (status=`planned`).

## Database

PostgreSQL in Docker; SQLite (via `aiosqlite`) for local dev. Tables:

- `users` (Telegram-side)
- `profiles` (questionnaire answers + delivery address)
- `subscriptions` (tariff, dates, status, payment_id)
- `activation_codes` (unique code → subscription mapping)
- `catalog_items` (SKU, name, brand, category, price, tags, allergens)
- `orders` (one per payment, snapshot of the deal)
- `delivery_history` (per shipment items)

### Migrations

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

`bot.main.init_db` calls `Base.metadata.create_all` on startup, which
keeps SQLite dev mode hassle-free; in production rely on Alembic.

## API contract

```
POST /v1/activate
Content-Type: application/json

{
  "code": "K7M3X2QY",
  "device_id": "optional-device-uuid"
}

→ 200 { "valid": true, "tariff": "vip", "expires": "2026-06-02",
        "redeemed_at": "2026-05-03T08:42:46.413195" }
→ 200 { "valid": false }   // unknown / expired / already-claimed-by-other-device

GET /health → 200 {"status":"ok"}
```

## Deployment

A simple production setup on a VPS:

```bash
# 1. Clone
git clone https://github.com/sorordgsh-bot/NewRepo.git flowcare && cd flowcare

# 2. Configure
cp bot/.env.example bot/.env && nano bot/.env

# 3. Run
docker compose up -d --build

# 4. Tail logs
docker compose logs -f bot
docker compose logs -f api

# 5. Update later
git pull && docker compose up -d --build
```

Reverse-proxy `api.your-domain.com` → `api:8000` with a TLS terminator
(Caddy / nginx) and configure the Lira app's `extra.activationApiUrl`
in `app.json` (or `app.config.ts`) accordingly.
