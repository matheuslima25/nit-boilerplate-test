import os
from pathlib import Path

import environ
from corsheaders.defaults import default_headers
from django.utils.translation import gettext_lazy as _

env = environ.Env()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
APPS_DIR = ROOT_DIR / "apps"

# Carregamento contextual do .env (antes de ler variáveis com env())
_dj_settings_module = os.environ.get("DJANGO_SETTINGS_MODULE", "")
_environment = os.environ.get("ENVIRONMENT", "").lower()
if (
    "production" in _dj_settings_module
    or _environment in ("prod", "production")
):
    _ENV_PATH = ROOT_DIR / ".envs" / ".production" / ".django"
else:
    _ENV_PATH = ROOT_DIR / ".envs" / ".local" / ".django"
environ.Env.read_env(str(_ENV_PATH))

SECRET_KEY = env("DJANGO_SECRET_KEY")

DEBUG = env.bool("DJANGO_DEBUG", False)  # type: ignore

ALLOWED_HOSTS = ["*"]

BASE_URL = env("BASE_URL")

LOCAL_APPS = [
    "apps.users",
    "apps.commons",
    "apps.core",
    "apps.honeypot",
]

THIRD_PARTY_APPS = [
    # Django Rest Framework
    "rest_framework",
    "rest_framework.authtoken",
    "drf_spectacular",
    "corsheaders",
    "django_filters",
    "tinymce",
    # Admin
    "admin_interface",
    "colorfield",
    "django_admin_inline_paginator",
    # Import/Export
    "import_export",
    # Others
    "django_extensions",
    "django_crontab",
]

HEALTH_CHECK_APPS = [
    "health_check",
    "health_check.db",
    "health_check.cache",
    "health_check.storage",
    "health_check.contrib.migrations",
    "health_check.contrib.psutil",
    "health_check.contrib.redis",
]

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

INSTALLED_APPS = (
    LOCAL_APPS
    + THIRD_PARTY_APPS
    + DJANGO_APPS
    + HEALTH_CHECK_APPS
)

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "nitapi.kong_middleware.KongMiddleware",
    "nitapi.kong_middleware.KongRateLimitMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    # Middleware personalizado para separar autenticação admin/API
    "nitapi.admin_middleware.AdminAuthenticationMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.locale.LocaleMiddleware",
]

ROOT_URLCONF = "nitapi.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [str(APPS_DIR / "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "nitapi.wsgi.application"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "nitapi.drf_authentication.KeycloakJWTAuthentication",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": (
        "rest_framework.pagination.PageNumberPagination"
    ),
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    "TEST_REQUEST_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
    "EXCEPTION_HANDLER": "apps.commons.api.v1.exceptions.exception_handler",
    "NON_FIELD_ERRORS_KEY": "error",
    "PAGE_SIZE": 10,
    "DATE_INPUT_FORMATS": ("%d/%m/%Y",),
    "COERCE_DECIMAL_TO_STRING": False,
}

VERSION_FILE = ROOT_DIR / "VERSION"

try:
    with open(VERSION_FILE) as f:
        API_VERSION = f.read().strip()
except FileNotFoundError:
    API_VERSION = "1.0.0"

SPECTACULAR_SETTINGS = {
    "TITLE": "NIT API",
    "DESCRIPTION": "API docs and endpoints for NIT API.",
    "VERSION": API_VERSION,
    "DISABLE_WARN_ON_IGNORED_VIEWS": True
}

DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["ATOMIC_REQUESTS"] = True
DATABASES["default"]["ENGINE"] = "django.db.backends.postgresql"

# Schema específico para isolamento de dados entre diferentes APIs
DATABASE_SCHEMA = env("DATABASE_SCHEMA", default="public")
DATABASES["default"]["OPTIONS"] = {
    "options": f"-c search_path={DATABASE_SCHEMA},public"
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

AUTHENTICATION_BACKENDS = [
    # Django admin usa autenticação tradicional
    "django.contrib.auth.backends.ModelBackend",
    # API usa autenticação Keycloak
    "nitapi.authentication.KeycloakAuthentication",
]

AUTH_USER_MODEL = "users.User"

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]

# Permitir métodos específicos
CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]

CORS_URLS_REGEX = r"^(/api/v1/.*|/media/.*)$"

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://172.19.0.3",  # Docker
]

CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^http://localhost:\d+$",
    r"^http://172\.\d+\.\d+\.\d+(:\d+)?$",  # Permite qualquer IP do Docker
]

CORS_ALLOW_HEADERS = list(default_headers) + [
    "x-msw-request-id",
    "authorization",
    "content-type",
    "x-requested-with",
]

CORS_EXPOSE_HEADERS = ["Content-Type", "X-CSRFToken"]

CSRF_TRUSTED_ORIGINS = [
    "https://*.ngrok-free.app",
    "https://*.nit.com.br",
]

LANGUAGES = (("pt-br", _("Português")), ("en", _("English")))

LANGUAGE_CODE = "pt-br"

TIME_ZONE = "America/Recife"

USE_TZ = True

USE_I18N = True

USE_L10N = True

SITE_ID = 1

ADMIN_URL = "secret/"

# For report CRITICAL errors
ADMINS = (
    ("Matheus", "josemedeiros1@fiponline.edu.br"),
)

MANAGERS = ADMINS

LOCALE_PATHS = (os.path.join(BASE_DIR, "locale"),)

# S3 Configs
USE_S3 = env("USE_S3", cast=bool)

if USE_S3:
    # AWS settings
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"
    AWS_REGION = env("AWS_REGION")

    # S3 public media settings
    PUBLIC_MEDIA_LOCATION = "media"
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{PUBLIC_MEDIA_LOCATION}/"
    DEFAULT_FILE_STORAGE = "nitapi.storage_backends.PublicMediaStorage"

    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None
    AWS_S3_OBJECT_PARAMETERS = {
        "CacheControl": "max-age=86400",
    }
else:
    MEDIA_URL = "/mediafiles/"
    MEDIA_ROOT = os.path.join(BASE_DIR, "mediafiles")

STATIC_URL = "/staticfiles/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

PROJECT_TITLE = "NIT API"

SITE_URL = env("SITE_URL")
SITE_NAME = "NIT API"

# Admin
X_FRAME_OPTIONS = "SAMEORIGIN"
SILENCED_SYSTEM_CHECKS = ["security.W019"]

# Cache Configuration
API_CACHE_TIMEOUT = 3600  # 1 hour default cache timeout

FIXTURE_DIRS = [
    os.path.join(BASE_DIR, "fixtures"),
]

HONEYPOT_URL = "/admin"

CRONJOBS = [
    # ("*/3 * * * *", "apps.app_name.utils.file.function"),
]

DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000
DATA_UPLOAD_MAX_NUMBER_FILES = 1000
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Default timeout for requests
DEFAULT_TIMEOUT = env("DEFAULT_TIMEOUT", cast=int)

# Django Health Check
REDIS_URL = env("CACHE_HOST")

# Keycloak Configuration for Agnostic Authentication
# Required for auth
KEYCLOAK_SERVER_URL = env('KEYCLOAK_SERVER_URL')
KEYCLOAK_REALM = env('KEYCLOAK_REALM')
KEYCLOAK_CLIENT_ID = env('KEYCLOAK_CLIENT_ID')
# SECRET opcional para clientes públicos; None quando ausente
KEYCLOAK_CLIENT_SECRET = os.environ.get('KEYCLOAK_CLIENT_SECRET')
# Optional (admin API only) — não obrigatório para autenticação básica
# Ler via os.environ para manter opcionalidade sem afetar tipagem
KEYCLOAK_ADMIN_USERNAME = os.environ.get('KEYCLOAK_ADMIN_USERNAME', '')
KEYCLOAK_ADMIN_PASSWORD = os.environ.get('KEYCLOAK_ADMIN_PASSWORD', '')

# Kong API Gateway Configuration (opcional)
# Admin URL é útil para health checks e comandos de setup; torne opcional
KONG_ADMIN_URL = os.environ.get('KONG_ADMIN_URL', '')
KONG_GATEWAY_URL = os.environ.get('KONG_GATEWAY_URL', '')
# Nomes padrão (não exigir em env)
KONG_SERVICE_NAME = 'nit-api'
KONG_ROUTE_NAME = 'nit-api-route'
