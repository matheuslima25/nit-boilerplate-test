"""Keycloak authentication backend for Django REST Framework."""
import logging
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from django.conf import settings
from keycloak import KeycloakOpenID, KeycloakError
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError

logger = logging.getLogger(__name__)
User = get_user_model()


class KeycloakAuthentication(BaseBackend):
    """Keycloak authentication backend that validates JWT tokens
    and creates/updates users based on token claims.
    """

    def __init__(self):
        self.keycloak_openid = KeycloakOpenID(
            server_url=settings.KEYCLOAK_SERVER_URL,
            client_id=settings.KEYCLOAK_CLIENT_ID,
            realm_name=settings.KEYCLOAK_REALM,
            client_secret_key=getattr(settings, 'KEYCLOAK_CLIENT_SECRET', None)
        )

    def authenticate(self, request, token=None, **kwargs):
        """Authenticate user using Keycloak JWT token."""
        if not token:
            return None

        try:
            # Validate token with Keycloak
            token_info = self.keycloak_openid.introspect(token)

            if not token_info.get('active'):
                logger.warning("Token is not active")
                return None

            # Decode token to get user info
            decoded_token = jwt.decode(
                token,
                options={"verify_signature": False}  # Already verified
            )

            # Extract user information from token
            user_info = {
                'username': decoded_token.get('preferred_username'),
                'email': decoded_token.get('email'),
                'first_name': decoded_token.get('given_name', ''),
                'last_name': decoded_token.get('family_name', ''),
                'keycloak_id': decoded_token.get('sub'),
                'roles': decoded_token.get('realm_access', {}).get('roles', [])
            }

            # Get or create user
            user = self.get_or_create_user(user_info)

            return user

        except KeycloakError as e:
            logger.error(f"Keycloak authentication error: {e}")
            return None
        except (InvalidTokenError, ExpiredSignatureError) as e:
            logger.error(f"JWT token error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected authentication error: {e}")
            return None

    def get_or_create_user(self, user_info):
        """Get existing user or create new one based on Keycloak user info."""
        try:
            # Try to find user by Keycloak ID first
            try:
                user = User.objects.get(keycloak_id=user_info['keycloak_id'])
                # Update user info if needed
                self.update_user(user, user_info)
                return user
            except User.DoesNotExist:
                pass

            # Try to find user by email
            if user_info.get('email'):
                try:
                    user = User.objects.get(email=user_info['email'])
                    # Link existing user to Keycloak
                    user.keycloak_id = user_info['keycloak_id']  # type: ignore
                    self.update_user(user, user_info)
                    return user
                except User.DoesNotExist:
                    pass

            # Create new user
            user_data = {
                'email': user_info.get('email', ''),
                'first_name': user_info.get('first_name', ''),
                'last_name': user_info.get('last_name', ''),
                'keycloak_id': user_info['keycloak_id'],
                'is_active': True,
            }

            # Generate username if not provided
            if not user_info.get('username'):
                email = user_info.get('email', '')
                keycloak_id = user_info['keycloak_id']
                user_data['username'] = email or f"user_{keycloak_id}"
            else:
                user_data['username'] = user_info['username']

            user = User.objects.create_user(**user_data)
            logger.info(f"Created new user from Keycloak: {user.email}")

            return user

        except Exception as e:
            logger.error(f"Error creating/updating user: {e}")
            return None

    def update_user(self, user, user_info):
        """Update user information from Keycloak token."""
        updated = False

        if user.first_name != user_info.get('first_name', ''):
            user.first_name = user_info.get('first_name', '')
            updated = True

        if user.last_name != user_info.get('family_name', ''):
            user.last_name = user_info.get('family_name', '')
            updated = True

        if updated:
            user.save()
            logger.info(f"Updated user info for: {user.email}")

    def get_user(self, user_id):
        """Get user by ID."""
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
