from django.urls import path

from .views import index, keycloak_status, kong_status, system_status

urlpatterns = [
    path("", index, name="index"),
    # Endpoints de status on-demand
    path("status/", system_status, name="system_status"),
    path("status/keycloak/", keycloak_status, name="keycloak_status"),
    path("status/kong/", kong_status, name="kong_status"),
]
