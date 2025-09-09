from .base import *
from .base import env
import os

DEBUG = True

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS += ["debug_toolbar"]

MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE

INTERNAL_IPS = [
    "127.0.0.1",
]

if env("USE_CACHE", cast=bool):
    """
    Local Memory Cache
    Default cache TIMEOUT is five minute (If is none, the cache never expires)
    For more about cache, visit:
    https://docs.djangoproject.com/en/5.2/topics/cache/
    """

    # CACHES = {
    #     'default': {
    #         'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    #         'LOCATION': 'unique-snowflake',
    #         'TIMEOUT': 60
    #     }
    # }

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

LOG_FILE = "/local.log"

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
                "[{asctime}] {levelname} {module} {process:d} "
                "{thread:d} {message}"
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

DEFAULT_EXCEPTION_REPORTER_FILTER = "tools.helpers.CustomExceptionFilter"
