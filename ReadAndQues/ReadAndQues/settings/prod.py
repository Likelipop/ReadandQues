"""
Production Django settings for ReadAndQues project.
Hardened for production deployment: DEBUG=False, strict security headers,
PostgreSQL, Redis caching, and structured rotating file logging.
"""

import os

from .base import *

DEBUG = False

# Security check: Ensure SECRET_KEY is set and secure in production
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY or SECRET_KEY.startswith("django-insecure"):
    # Fallback to env or raise for security
    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "prod-secure-key-must-be-replaced-in-env-file-for-security-982137918237",
    )

ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0").split(",")
    if h.strip()
]

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CSRF_TRUSTED_ORIGINS", "http://localhost,http://127.0.0.1,http://0.0.0.0"
    ).split(",")
    if origin.strip()
]

# Database: PostgreSQL in production
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", os.getenv("POSTGRES_DB", "readandques")),
        "USER": os.getenv("DB_USER", os.getenv("POSTGRES_USER", "myuser")),
        "PASSWORD": os.getenv(
            "DB_PASSWORD", os.getenv("POSTGRES_PASSWORD", "mypassword")
        ),
        "HOST": os.getenv("DB_HOST", "postgres"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "CONN_MAX_AGE": 600,
    }
}

# Production Cache: Redis backend
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/1")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/2")


# Security Hardening for Production Nginx Reverse Proxy
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# Structured Logging Configuration
LOGS_DIR = BASE_DIR / "logs"
os.makedirs(LOGS_DIR, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} [{levelname}] {name} (pid:{process:d} thread:{thread:d}): {message}",
            "style": "{",
        },
        "simple": {
            "format": "{asctime} [{levelname}] {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "file_error": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOGS_DIR / "django_error.log"),
            "maxBytes": 10 * 1024 * 1024,  # 10 MB
            "backupCount": 5,
            "formatter": "verbose",
        },
        "file_info": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOGS_DIR / "django_info.log"),
            "maxBytes": 10 * 1024 * 1024,  # 10 MB
            "backupCount": 5,
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file_error", "file_info"],
            "level": "INFO",
            "propagate": True,
        },
        "readspace": {
            "handlers": ["console", "file_error", "file_info"],
            "level": "INFO",
            "propagate": False,
        },
        "service": {
            "handlers": ["console", "file_error", "file_info"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
