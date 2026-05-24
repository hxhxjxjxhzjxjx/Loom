#!/usr/bin/env bash
# Lira — быстрое обновление кода без переустановки зависимостей.
# Запускать ОТ root после распаковки новой версии zip-а:
#   sudo bash update.sh
set -euo pipefail

if [[ "$(id -u)" != "0" ]]; then
  echo "Запускай через sudo: sudo bash update.sh"
  exit 1
fi

PKG_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR=/opt/lira
WEB_DIR=/var/www/lira

echo "==> Обновляем backend"
rm -rf "$APP_DIR/backend"
cp -r "$PKG_DIR/backend" "$APP_DIR/backend"
find "$APP_DIR/backend" -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
chown -R lira:lira "$APP_DIR/backend"

echo "==> Обновляем зависимости (если что-то добавилось)"
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/backend/bot/requirements.txt" >/dev/null

echo "==> Обновляем web"
rm -rf "$WEB_DIR"/*
cp -r "$PKG_DIR/web/"* "$WEB_DIR/"
chown -R www-data:www-data "$WEB_DIR"
chmod -R a+rX "$WEB_DIR"

echo "==> Перезапуск сервисов"
systemctl restart lira-api
systemctl reload nginx

echo "Готово."
