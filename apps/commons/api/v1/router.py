from rest_framework.routers import DefaultRouter

from .viewsets import AddressViewSet

common_router = DefaultRouter()
common_router.register(r"address", AddressViewSet, "address")
