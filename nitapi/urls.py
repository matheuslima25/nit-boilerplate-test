from django.conf import settings
from django.conf.urls import include
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, re_path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from .router.api import api_urls

urlpatterns = i18n_patterns(
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc"
    ),
    path(
        "api/docs/swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui"
    ),
    re_path(
        "^admin/",
        include("apps.honeypot.urls", namespace="admin_honeypot")
    ),
    path(settings.ADMIN_URL, admin.site.urls),
    path("health/", include("health_check.urls")),
    path("", include("apps.commons.urls")),
    path("tinymce/", include("tinymce.urls")),
    path("i18n/", include("django.conf.urls.i18n")),
    path(
        "api/",
        include((api_urls, "nitapi.router.api.api_urls"), namespace="api")
    ),
    prefix_default_language=False,
)

if settings.DEBUG:
    urlpatterns += [path("__debug__/", include("debug_toolbar.urls"))]

if not settings.USE_S3:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )

urlpatterns += static(
    settings.STATIC_URL, document_root=settings.STATIC_ROOT
)
