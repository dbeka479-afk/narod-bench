#!/usr/bin/env bash
# Сборка на Render: зависимости, статика, таблицы в базе.
set -o errexit
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input
# Администратор для удаления мусора из топа (/admin/). Создаётся один раз, если заданы переменные
# DJANGO_SUPERUSER_USERNAME и DJANGO_SUPERUSER_PASSWORD (и DJANGO_SUPERUSER_EMAIL).
if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ]; then
  python manage.py createsuperuser --no-input || true
fi
