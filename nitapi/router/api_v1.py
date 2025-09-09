from django.conf.urls import include
from django.urls import path

from apps.commons.api.v1.router import common_router
from apps.users.api.v1.router import user_router
from apps.core.api.v1.router import core_router

api_v1_urls = [
    path(
        "common/",
        include((common_router.urls, "common"), namespace="common")
    ),
    path("core/", include((core_router.urls, "core"), namespace="core")),
    path("user/", include((user_router.urls, "user"), namespace="user")),
]
