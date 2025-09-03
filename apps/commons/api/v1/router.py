from rest_framework.routers import DefaultRouter

from .viewsets import *

core_router = DefaultRouter()
core_router.register(r"address", AddressViewSet, "address")
