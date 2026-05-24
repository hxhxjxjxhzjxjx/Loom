# Lira — установка на свой VPS (v2, продакшн)

Самодостаточный комплект: **веб-приложение (с PWA) + Telegram-бот + API**
для разворачивания на собственном сервере Ubuntu, с базовой защитой
от ботов/сканеров и автоматическими патчами безопасности.

> **TL;DR.** Купи VPS → SSH → `sudo bash install.sh` → открой `http://IP-сервера`.

---

## 1. Что нужно купить

**VPS** (виртуальный сервер) **Ubuntu 22.04 LTS** или **24.04 LTS**.
Минимум: **1 vCPU, 1 ГБ RAM, 10 ГБ диск.** ~200–400 ₽/мес.

| Провайдер | Сайт | Примерная цена |
|-----------|----------------------------------------------|----------------|
| Timeweb Cloud | https://timeweb.cloud/services/cloud-server | ~200 ₽/мес |
| Beget VPS | https://beget.com/ru/services/vps | ~250 ₽/мес |
| REG.RU VPS | https://www.reg.ru/vps/ | ~290 ₽/мес |
| Selectel | https://selectel.ru/services/cloud/servers/ | ~300 ₽/мес |

При заказе выбирай **Ubuntu 22.04 LTS** (или 24.04 LTS), без панели управления.
Тебе дадут **IP-адрес и пароль root** (или ssh-ключ).

---

## 2. Что нужно подготовить в Telegram

### 2.1 BOT_TOKEN

1. Открой [@BotFather](https://t.me/BotFather) → `/newbot` → имя → username (`*_bot`).
2. Скопируй токен `7400000000:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` → `BOT_TOKEN`.
3. Username бота без `@` → `BOT_USERNAME` (например, `myshop_bot`).

### 2.2 ADMIN_CHAT_ID

1. Открой [@userinfobot](https://t.me/userinfobot) → `/start`.
2. Запиши число → `ADMIN_CHAT_ID` (твой Telegram-ID).

### 2.3 (опционально) PAYMENT_PROVIDER_TOKEN

Нужен для приёма **реальных** платежей через Telegram-инвойсы. Без него
работает только демо-режим («Я оплатила (тест)»). Возьми у @BotFather →
Bot Settings → Payments.

---

## 3. Установка (5 команд)

### 3.1 Подключись к серверу

```bash
ssh root@IP-сервера
```

### 3.2 Загрузи zip

С компьютера (Mac/Linux):
```bash
scp lira-deploy.zip root@IP-сервера:/root/
```
Windows → **WinSCP** или drag-and-drop через Termius.

### 3.3 Распакуй

```bash
cd /root
apt-get update && apt-get install -y unzip
unzip lira-deploy.zip
cd lira-deploy
```

### 3.4 Заполни `.env`

```bash
cp .env.example .env
nano .env
```

Минимально вписать:
- `BOT_TOKEN=…` (от @BotFather)
- `BOT_USERNAME=…` (без @)
- `ADMIN_CHAT_ID=…` (от @userinfobot)

`Ctrl+O` → `Enter` (сохранить) → `Ctrl+X` (выйти).

### 3.5 Запусти установщик

```bash
sudo bash install.sh
```

Скрипт сам:

- поставит python3, nginx, sqlite, **ufw, fail2ban, unattended-upgrades**;
- создаст системного пользователя `lira` без shell;
- скопирует backend в `/opt/lira/backend`, веб в `/var/www/lira`;
- создаст Python venv и поставит зависимости;
- зарегистрирует systemd-юнит `lira-api` с песочницей;
- настроит nginx с **rate-limit, security headers, защитой от ботов**;
- настроит **UFW** (открыты только 22/80/443);
- настроит **fail2ban** (банит брутфорс SSH и сканеры);
- включит **авто-обновления** security-патчей Ubuntu;
- проверит, что API отвечает.

Открой `http://IP-сервера` в браузере. Готово.

---

## 4. Что защищено «из коробки» (v2)

| Слой | Защита |
|------|--------|
| Сеть | UFW — только 22 (SSH), 80 (HTTP), 443 (HTTPS) |
| SSH | fail2ban — бан на 1 час после 5 ошибочных логинов за 10 мин |
| HTTP | server_tokens off — не светим версию nginx |
| HTTP | Security headers: CSP, X-Frame-Options DENY, X-Content-Type-Options, Referrer-Policy, Permissions-Policy |
| HTTP | Rate-limit: `/v1/lira/chat` 30 r/min/IP, `/v1/lira/{subscription,onboarding,cycle-update}` 5 r/min/IP |
| HTTP | Блокировка scanner User-Agents (sqlmap, nikto, nmap, masscan, …) и популярных путей атак (`/wp-admin`, `/.env`, `/.git`, `phpmyadmin`, …) — отвечаем 444 |
| HTTP | fail2ban на nginx-сканеры и нарушителей rate-limit — бан на 6 часов |
| Файлы | `.env` 0600, читает только пользователь `lira` |
| Файлы | `/var/lib/lira/app.db` 0600, доступен только пользователю `lira` |
| Процесс | API в systemd-песочнице: ProtectSystem=strict, NoNewPrivileges, без capabilities, без write-execute памяти, фильтрация syscall |
| Процесс | API слушает только 127.0.0.1, снаружи недоступен напрямую |
| ОС | unattended-upgrades — авто-патчинг CVE Ubuntu |
| PWA | Service Worker кэширует только GET-статику; API никогда не кешируется |

---

## 5. Что НЕ защищено и что стоит сделать руками

1. **Демо-оплата.** Пока `PAYMENT_PROVIDER_TOKEN` не задан в `.env`,
   любой может через UI нажать «Я оплатила (тест)» и получить запись о
   подписке. Это нормально для тестов, но **до реального запуска**
   обязательно подключи реального провайдера (ЮKassa, Тинькофф) через
   @BotFather → Payments. Тогда оплата проходит только при реальном
   списании с карты.
2. **HTTPS.** Стартуешь на IP — это HTTP. Все данные клиентов (анкеты,
   адрес) идут в открытом виде. **Перед тем как звать клиентов** — купи
   домен и подключи SSL (раздел 6). Это бесплатно, ~5 минут.
3. **SSH-пароли.** Брутфорс через fail2ban мы блокируем, но самый
   надёжный вариант — отключить вход по паролю целиком и использовать
   только SSH-ключ. См. раздел 10.
4. **Бэкапы.** Раз в неделю-месяц скачивай `/var/lib/lira/app.db` к себе
   на компьютер. Команда:
   ```bash
   scp root@IP-сервера:/var/lib/lira/app.db ~/lira-backup-$(date +%F).db
   ```
5. **Мониторинг.** Если сервер упадёт, ты узнаешь от клиентов. Для
   простого мониторинга — добавь uptimerobot.com (бесплатно, шлёт письмо
   при недоступности).

---

## 6. HTTPS / SSL (после покупки домена)

1. Купи домен (`lira.ru` или какой нравится).
2. В DNS у регистратора добавь A-запись: `lira.ru → IP-сервера`,
   и ещё одну: `www.lira.ru → IP-сервера`. Подожди 10-15 минут.
3. На сервере:

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d твой-домен.ru -d www.твой-домен.ru \
  --redirect --hsts --staple-ocsp --email твой@email.com --agree-tos --no-eff-email
```

Certbot сам:
- перепишет `/etc/nginx/sites-available/lira` под HTTPS;
- включит редирект `http → https`;
- добавит HSTS-заголовок;
- настроит автообновление сертификата (каждые 60 дней).

Открой `https://твой-домен.ru` — должен быть зелёный замочек.
Проверить уровень защиты: https://www.ssllabs.com/ssltest/

---

## 7. PWA — установка на главный экран

Когда ты дашь клиенту ссылку, она открывается как обычный сайт.
Чтобы это выглядело как «приложение» — в браузере:

- **iPhone (Safari):** Поделиться → «На экран Домой».
- **Android (Chrome):** ⋮ → «Установить приложение» (или «Добавить на главный экран»).

Иконка попадёт на рабочий стол, при запуске откроется полноэкранно без
адресной строки. Работает и после потери связи (показывает последний
просмотренный экран).

---

## 8. Проверка и логи

```bash
# Состояние сервисов
systemctl status lira-api      # API + бот
systemctl status nginx
sudo ufw status verbose        # firewall
sudo fail2ban-client status    # fail2ban jails

# Живые логи
journalctl -u lira-api -f
tail -f /var/log/nginx/lira.access.log
tail -f /var/log/nginx/lira.error.log

# Кого fail2ban сейчас банит
sudo fail2ban-client status sshd
sudo fail2ban-client status nginx-botsearch

# Локальный API-чек
curl http://127.0.0.1:8000/v1/lira/status
```

---

## 9. Обновление кода (новый zip)

```bash
cd /root
unzip -o lira-deploy-new.zip
cd lira-deploy
sudo bash update.sh
```

`update.sh` не трогает `.env`, firewall и сертификаты.

---

## 10. Финальная защита SSH (рекомендуется)

После того как убедишься, что всё работает — переключись на SSH-ключ
вместо пароля. Это убирает 99% попыток брутфорса.

**На своём компьютере** (если ключа ещё нет):
```bash
ssh-keygen -t ed25519 -C "lira-admin"
# Enter, Enter, Enter (без passphrase или с ним — на твоё усмотрение)
```

Загрузи публичный ключ на сервер:
```bash
ssh-copy-id root@IP-сервера
# или вручную: scp ~/.ssh/id_ed25519.pub root@IP-сервера:/root/.ssh/authorized_keys
```

Проверь, что вход по ключу работает:
```bash
ssh root@IP-сервера     # должен пустить без пароля
```

Только после этого отключи вход по паролю:
```bash
ssh root@IP-сервера
sudo sed -i 's|^#*PasswordAuthentication.*|PasswordAuthentication no|' /etc/ssh/sshd_config
sudo sed -i 's|^#*PermitRootLogin.*|PermitRootLogin prohibit-password|' /etc/ssh/sshd_config
sudo systemctl reload ssh
```

---

## 11. Структура файлов на сервере

```
/opt/lira/
  ├── backend/        # код бота + API (Python)
  ├── venv/           # виртуальное окружение Python
  └── .env            # секреты (0600, только lira)

/var/www/lira/        # статика веб-приложения
  ├── index.html
  ├── manifest.webmanifest
  ├── sw.js           # service worker (PWA)
  ├── icons/
  └── _expo/          # минифицированный JS-бандл

/var/lib/lira/app.db                       # база SQLite (0600, только lira)
/etc/systemd/system/lira-api.service       # systemd-юнит
/etc/nginx/sites-available/lira            # nginx
/etc/fail2ban/jail.local                   # fail2ban
/etc/fail2ban/filter.d/nginx-limit-req.conf
```

---

## 12. Если что-то пошло не так

**Бот не отвечает.** Скорее всего пустой `BOT_TOKEN` или забанило fail2ban:
```bash
journalctl -u lira-api -n 80
sudo fail2ban-client status sshd
sudo ufw status
```

**Чат с Лирой пишет «недоступен».** Pollinations.ai периодически тупит.
```bash
curl http://127.0.0.1:8000/v1/lira/status   # должно вернуть online:true
curl -X POST http://127.0.0.1:8000/v1/lira/chat \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"hi"}]}'
```

**Случайно забанил себя.** С ssh-консоли провайдера (web-консоль в
панели хостинга):
```bash
sudo fail2ban-client unban 'TWOJ-IP'
# или
sudo iptables -F
```

**Удалить всё:**
```bash
sudo systemctl disable --now lira-api fail2ban
sudo rm /etc/systemd/system/lira-api.service
sudo rm /etc/nginx/sites-enabled/lira /etc/nginx/sites-available/lira
sudo systemctl reload nginx
sudo rm -rf /opt/lira /var/www/lira /var/lib/lira
sudo userdel lira
sudo ufw --force disable
```

---

Если что — пришли вывод `journalctl -u lira-api -n 80` и `sudo ufw status verbose`. Разберёмся.
