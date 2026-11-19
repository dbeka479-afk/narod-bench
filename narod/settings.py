"""Настройки проекта «Народный бенчмарк».

Локально всё работает без настроек (SQLite, DEBUG). На Render настройки берутся из переменных окружения:
  SECRET_KEY    — секретный ключ Django (Render создаёт сам, см. render.yaml)
  DATABASE_URL  — адрес базы Postgres (Neon): postgresql://user:pass@host/db?sslmode=require
  DEBUG         — "1", чтобы видеть подробные ошибки (на открытом сайте не включать)
Бесплатный Render стирает диск при перезапуске, поэтому замеры хранятся во внешней базе."""
import os
from pathlib import Path

from . import dburl

BASE_DIR = Path(__file__).resolve().parent.parent
RENDER_HOST = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "")
ON_SERVER = bool(RENDER_HOST or os.environ.get("DATABASE_URL"))

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-narod-bench-not-for-production")
DEBUG = os.environ.get("DEBUG", "0" if ON_SERVER else "1") == "1"

EXTRA_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "").split(",") if h.strip()]  # свой домен
ALLOWED_HOSTS = ["127.0.0.1", "localhost", ".onrender.com"] + EXTRA_HOSTS
if RENDER_HOST:
    ALLOWED_HOSTS.append(RENDER_HOST)
if DEBUG:
    ALLOWED_HOSTS.append("*")  # локально — открывать с телефона по адресу компьютера
CSRF_TRUSTED_ORIGINS = ["https://*.onrender.com"] + [f"https://{h}" for h in EXTRA_HOSTS]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "bench",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "narod.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "bench.context.assets",
            ],
        },
    },
]

WSGI_APPLICATION = "narod.wsgi.application"

DATABASES = {
    # на Render (там всегда есть переменная RENDER) база обязательна, локально — SQLite
    "default": dburl.config(os.environ.get("DATABASE_URL"), default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
                            required=bool(os.environ.get("RENDER"))),
}
if DATABASES["default"]["ENGINE"].endswith("sqlite3"):
    DATABASES["default"].setdefault("OPTIONS", {})["timeout"] = 20

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

LANGUAGE_CODE = "ru"
TIME_ZONE = "Asia/Almaty"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
DATA_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
}
