from .base import *
from .base import env
import os
from pathlib import Path

DEBUG = False

ALLOWED_HOSTS = []

INTERNAL_IPS = [
    "127.0.0.1",
]

# Configurações de segurança HTTPS
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000  # 1 ano
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Cookies seguros
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# Headers de segurança
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

if env("USE_CACHE", cast=bool):
    """
    Redis Cache
    """

    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": env("CACHE_HOST"),
            "TIMEOUT": 60,
        }
    }

"""
Logging
"""
LOG_ROOT = Path(__file__).resolve().parent.parent / "logs"

LOG_FILE = "/production.log"

LOG_PATH = f'{LOG_ROOT}{LOG_FILE}'

if not os.path.exists(LOG_ROOT):
    os.mkdir(LOG_ROOT)

# Create empty log file
if not os.path.exists(LOG_PATH):
    f = open(LOG_PATH, 'a').close()

LOGGING = {
    "formatters": {
        "verbose": {
            "format": (
                "[{asctime}] {levelname} {module} {process:d} {thread:d} {message}"
            ),
            "style": "{",
        },
    },
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_PATH,
            "maxBytes": 1024 * 1024 * 5,  # 5MB
            "backupCount": 5,
            "formatter": "verbose",
        },
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": [
                "file",
            ],
            "level": "INFO",
            "propagate": True,
        },
    },
}
