"""
Development Django settings for ReadAndQues project.
"""

import os

from .base import *

DEBUG = True

ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0").split(",")
    if h.strip()
]

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CSRF_TRUSTED_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000,http://localhost,http://127.0.0.1",
    ).split(",")
    if origin.strip()
]

# Database: SQLite by default in dev, or Postgres if DB_ENGINE specified
if os.getenv("POSTGRES_DB") or os.getenv("DB_NAME") or os.getenv("DB_ENGINE") == "postgresql":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", os.getenv("POSTGRES_DB", "readandques")),
            "USER": os.getenv("DB_USER", os.getenv("POSTGRES_USER", "myuser")),
            "PASSWORD": os.getenv("DB_PASSWORD", os.getenv("POSTGRES_PASSWORD", "mypassword")),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5432"),
            "CONN_MAX_AGE": 600,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Development Cache: Local Memory Cache
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "readandques-dev-cache",
    }
}

# Logging: Console output in development
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "{asctime} [{levelname}] {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
        "readspace": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "service": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
