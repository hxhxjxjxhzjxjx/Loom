#!/usr/bin/env bash
# Lira — первый пуш в Git-репозиторий.
#
# Использование:
#   bash git-init.sh https://github.com/<ник>/lira.git
#   bash git-init.sh git@github.com:<ник>/lira.git              # по SSH
#   bash git-init.sh https://gitverse.ru/<ник>/lira.git          # российский хостинг
#
# Скрипт идемпотентный: если уже есть .git/ — просто добавит коммит и пушнет.

set -euo pipefail

REMOTE_URL="${1:-}"
if [ -z "$REMOTE_URL" ]; then
  echo "Использование: bash git-init.sh <git-url>" >&2
  echo "Пример:       bash git-init.sh https://github.com/myname/lira.git" >&2
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  echo "!! Git не установлен. Поставь: " >&2
  echo "   Mac:     brew install git    (или скачай с https://git-scm.com)" >&2
  echo "   Linux:   sudo apt install git" >&2
  echo "   Windows: https://git-scm.com/download/win" >&2
  exit 1
fi

# 1. Инициализируем репозиторий (если ещё нет).
if [ ! -d .git ]; then
  echo "==> git init"
  git init -b main
fi

# 2. Базовые настройки коммитера (только если ещё не настроены глобально).
if ! git config user.email >/dev/null; then
  echo "Введи email для git-коммитов:"
  read -r EMAIL
  git config user.email "$EMAIL"
fi
if ! git config user.name >/dev/null; then
  echo "Введи имя для git-коммитов:"
  read -r NAME
  git config user.name "$NAME"
fi

# 3. Сейф-проверка: .env НЕ должен попасть в коммит.
if [ -f .env ]; then
  echo "!! Внимание: рядом лежит .env с реальными секретами."
  echo "   .gitignore его исключает, но проверь дважды перед пушем:"
  echo "   $ git status .env  → должен быть untracked"
fi

# 4. Коммитим всё, что есть.
echo "==> git add ."
git add .

echo "==> git commit"
git commit -m "Initial commit — Lira v2 (legal pages, age gate, security hardening)" || \
  echo "   (нет изменений для коммита — это нормально, если уже коммитили)"

# 5. Настраиваем remote.
if git remote get-url origin >/dev/null 2>&1; then
  echo "==> git remote set-url origin $REMOTE_URL"
  git remote set-url origin "$REMOTE_URL"
else
  echo "==> git remote add origin $REMOTE_URL"
  git remote add origin "$REMOTE_URL"
fi

# 6. Пушим.
echo "==> git push -u origin main"
echo "   (если попросит логин — на GitHub нужен Personal Access Token вместо пароля:"
echo "    https://github.com/settings/tokens → Generate new token → ставь галочку 'repo')"
git push -u origin main

echo
echo "✓ Готово. Код залит в $REMOTE_URL"
