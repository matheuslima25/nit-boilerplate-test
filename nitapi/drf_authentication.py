"""
Django REST Framework authentication classes for Keycloak-only authentication.
"""
import logging
from django.contrib.auth import get_user_model
from django.db import models
from rest_framework import authentication, exceptions
from .authentication import KeycloakAuthentication

logger = logging.getLogger(__name__)
User = get_user_model()


class KeycloakJWTAuthentication(authentication.BaseAuthentication):
    """DRF Authentication class for Keycloak JWT tokens ONLY
    This is the primary and only authentication method for this API.
    """

    def __init__(self):
        super().__init__()
        self.keycloak_auth = KeycloakAuthentication()

    def authenticate(self, request):
        """Authenticate the request and return a two-tuple of (user, token)."""
        auth_header = authentication.get_authorization_header(request)

        if not auth_header:
            return None

        try:
            auth_parts = auth_header.decode('utf-8').split()
        except UnicodeDecodeError:
            msg = 'Invalid token header. Token should be UTF-8 encoded.'
            raise exceptions.AuthenticationFailed(msg)

        if not auth_parts or auth_parts[0].lower() != 'bearer':
            return None

        if len(auth_parts) == 1:
            msg = 'Invalid token header. No credentials provided.'
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth_parts) > 2:
            msg = ('Invalid token header. Token string should not '
                   'contain spaces.')
            raise exceptions.AuthenticationFailed(msg)

        token = auth_parts[1]

        # Authenticate with Keycloak ONLY
        user = self.keycloak_auth.authenticate(request, token=token)

        if user is None:
            raise exceptions.AuthenticationFailed(
                'Invalid or expired Keycloak token.'
            )

        if not user.is_active:
            raise exceptions.AuthenticationFailed('User inactive or deleted.')

        return (user, token)

    def authenticate_header(self, request):
        """Return a string to be used as the value of the `WWW-Authenticate`
        header in a `401 Unauthenticated` response.
        """
        return 'Bearer realm="Keycloak"'


class KongConsumerAuthentication(authentication.BaseAuthentication):
    """Authentication based on Kong consumer headers
    Used when requests come through Kong API Gateway
    This is secondary authentication for service-to-service communication.
    """

    def authenticate(self, request):
        """Authenticate based on Kong consumer headers."""
        consumer_id = request.META.get('HTTP_X_CONSUMER_ID')
        consumer_username = request.META.get('HTTP_X_CONSUMER_USERNAME')
        consumer_custom_id = request.META.get('HTTP_X_CONSUMER_CUSTOM_ID')

        if not consumer_id:
            return None

        # Try to find user by Kong consumer information
        user = None

        # First try by custom_id (which could be user ID)
        if consumer_custom_id:
            try:
                user = User.objects.get(id=consumer_custom_id)
            except (User.DoesNotExist, ValueError):
                pass

        # Then try by username/email
        if not user and consumer_username:
            try:
                user = User.objects.get(
                    models.Q(username=consumer_username) |
                    models.Q(email=consumer_username)
                )
            except User.DoesNotExist:
                pass

        if not user:
            # Create a service user for Kong consumer
            # This should only be used for service-to-service communication
            user = User(
                username=consumer_username or f"kong_consumer_{consumer_id}",
                email=f"{consumer_id}@kong.service",
                is_active=True,
                first_name="Kong",
                last_name="Service User"
            )
            # Don't save to database - temporary user for this request
            logger.info(f"Created temporary Kong service user: {consumer_id}")

        if not user.is_active:
            raise exceptions.AuthenticationFailed('User inactive or deleted.')

        return (user, consumer_id)

    def authenticate_header(self, request):
        """Kong consumer auth doesn't need WWW-Authenticate header."""
        return None
