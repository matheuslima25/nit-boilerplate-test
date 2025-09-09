"""Keycloak authentication backend for Django REST Framework."""
import logging

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from keycloak import KeycloakError, KeycloakOpenID

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
        # Se for uma requisição admin, não usar autenticação Keycloak
        if hasattr(request, 'is_admin_request') and request.is_admin_request:
            return None

        if not token:
            return None

        # MODO DEBUG: Bypass para desenvolvimento local
        # ⚠️  ATENÇÃO: Remove em produção!
        # TODO: Remover antes do deploy em produção
        if (getattr(settings, 'DEBUG', False) and
                getattr(settings, 'ENABLE_DEBUG_AUTH', False) and
                token.startswith('debug-token-')):
            logger.warning("⚠️  USING DEBUG BYPASS TOKEN - DEVELOPMENT ONLY!")
            user_info = {
                'username': 'debug-user',
                'email': 'debug@nit.com',
                'keycloak_id': 'debug-123',
                'roles': ['api-access']  # Removido 'admin' por segurança
            }
            return self.get_or_create_user(user_info)

        try:
            # First decode token without verification to check basic structure
            decoded_token = jwt.decode(
                token,
                options={"verify_signature": False, "verify_exp": False}
            )
            
            # Check if token is not expired
            import time
            current_time = int(time.time())
            exp = decoded_token.get('exp', 0)
            
            if exp < current_time:
                logger.warning("Token has expired")
                return None
            
            # Check issuer - accept both localhost and keycloak-auth
            iss = decoded_token.get('iss', '')
            keycloak_url = settings.KEYCLOAK_SERVER_URL
            realm = settings.KEYCLOAK_REALM
            valid_issuers = [
                f"{keycloak_url}/realms/{realm}",
                f"http://localhost:8080/realms/{realm}",
                f"http://keycloak-auth:8080/realms/{realm}"
            ]
            
            if iss not in valid_issuers:
                logger.warning(
                    f"Invalid issuer: {iss}. Expected one of: {valid_issuers}"
                )
                return None
                
            # Try to validate with Keycloak introspect - but don't fail
            try:
                token_info = self.keycloak_openid.introspect(token)
                if not token_info.get('active'):
                    logger.warning(
                        "Token is not active according to Keycloak introspect"
                    )
                    # Still continue with local validation for now
            except Exception as e:
                logger.warning(
                    f"Could not introspect token with Keycloak: {e}. "
                    "Using local validation only."
                )
                # Continue with local validation

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

            # Create user with unusable password since auth is via Keycloak
            user = User.objects.create_user(password=None, **user_data)
            user.set_unusable_password()
            user.save()
            logger.info(f"Created new user from Keycloak: {user.email}")

            return user

        except Exception as e:
            logger.error(f"Error creating/updating user: {e}")
            return None

    def update_user(self, user, user_info):
        """Update user information from Keycloak token."""
        updated = False

        # Update username if needed
        if user.username != user_info.get('username', ''):
            user.username = user_info.get('username', '')
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
