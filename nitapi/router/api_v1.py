from django.conf.urls import include
from django.urls import path

from apps.commons.api.v1.router import core_router
from apps.core.api.v1.router import core_router
from apps.users.api.v1.router import urlpatterns as user_urlpatterns
from apps.users.api.v1.router import user_router

api_v1_urls = [
    path("common/", include((core_router.urls, "common"), namespace="common")),
    path("core/", include((core_router.urls, "core"), namespace="core")),
    path("user/", include((user_urlpatterns, "user"), namespace="user")),
]
