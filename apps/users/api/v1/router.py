from rest_framework.routers import DefaultRouter

from .viewsets import ProfileViewSet, UserOnboardingViewSet, UserViewSet

user_router = DefaultRouter()

# User actions
user_router.register(r"user", UserViewSet, "user")
user_router.register(r"profile", ProfileViewSet, "profile")
user_router.register(r"", UserOnboardingViewSet, "user-onboarding")
