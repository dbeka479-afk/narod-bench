"""Разбор DATABASE_URL с понятными ошибками.

На Render адрес базы вставляют руками, и легко скопировать не то: ссылку на страницу Neon (https://…),
команду «psql '…'» или строку в кавычках. Здесь строка подключения вытаскивается из обёрток, а если
вставлено что-то другое — сборка останавливается с объяснением по-русски. Пароль в текст ошибки не попадает."""
import re

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

HELP = ("Где взять: Neon → ваш проект → кнопка Connect → Connection string (строка начинается с postgresql://). "
        "Вставьте её в Render → сервис narod-bench → Environment → DATABASE_URL → Save, rebuild, and deploy.")
OK_SCHEMES = {"postgres", "postgresql", "pgsql", "sqlite"}


def clean_url(raw):
    s = (raw or "").strip()
    m = re.search(r"postgres(?:ql)?://[^\s'\"]+", s)  # из «psql '…'», кавычек и пробелов
    return m.group(0) if m else s.strip("'\"").strip()


def config(raw, default, required=False):
    url = clean_url(raw)
    if not url:
        if required:
            raise ImproperlyConfigured("DATABASE_URL не задан — без него замеры будут стираться при каждом "
                                       "перезапуске сервера. " + HELP)
        url = default
    scheme = url.split("://", 1)[0].lower() if "://" in url else ""
    if scheme not in OK_SCHEMES:
        start = f"«{scheme}://»" if scheme else "не со схемы адреса"
        raise ImproperlyConfigured(f"DATABASE_URL должен начинаться с postgresql://, а сейчас начинается {start}. "
                                   "Похоже, вставлена ссылка на страницу, а не строка подключения к базе. " + HELP)
    return dj_database_url.parse(url, conn_max_age=600, conn_health_checks=True)
