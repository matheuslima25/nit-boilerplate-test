"""Django management command to setup Kong API Gateway services and routes."""
from django.core.management.base import BaseCommand
from django.conf import settings
from nitapi.kong_middleware import KongServiceRegistry


class Command(BaseCommand):
    help = 'Setup Kong API Gateway services and routes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of existing services and routes',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Setting up Kong API Gateway...')
        )

        try:
            if not getattr(settings, 'KONG_ADMIN_URL', ''):
                self.stdout.write(
                    self.style.WARNING(
                        'KONG_ADMIN_URL não configurado. '
                        'Pulando setup do Kong.'
                    )
                )
                return
            # Initialize Kong service registry
            kong_registry = KongServiceRegistry()

            # Setup default services
            kong_registry.setup_default_services()

            # Add rate limiting plugin
            self.setup_rate_limiting(kong_registry)

            # Add authentication plugin
            self.setup_authentication(kong_registry)

            self.stdout.write(
                self.style.SUCCESS(
                    'Kong API Gateway setup completed successfully!'
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error setting up Kong: {e}')
            )
            raise

    def setup_rate_limiting(self, kong_registry):
        """Setup rate limiting plugin for API."""
        try:
            # Configure rate limiting (100 requests per minute)
            plugin_data = {
                'name': 'rate-limiting',
                'config': {
                    'minute': 100,
                    'policy': 'local'
                }
            }

            response = kong_registry.session.post(
                f"{kong_registry.admin_url}/services/nit-api/plugins",
                json=plugin_data
            )

            if response.status_code in [201, 409]:
                self.stdout.write('Rate limiting plugin configured')
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'Rate limiting setup warning: {response.text}'
                    )
                )

        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Rate limiting setup failed: {e}')
            )

    def setup_authentication(self, kong_registry):
        """Setup JWT authentication plugin."""
        try:
            # Configure JWT plugin
            plugin_data = {
                'name': 'jwt',
                'config': {
                    'secret_is_base64': False,
                    'run_on_preflight': True
                }
            }

            response = kong_registry.session.post(
                f"{kong_registry.admin_url}/services/nit-api/plugins",
                json=plugin_data
            )

            if response.status_code in [201, 409]:
                self.stdout.write('JWT authentication plugin configured')
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'JWT setup warning: {response.text}'
                    )
                )

        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'JWT setup failed: {e}')
            )
