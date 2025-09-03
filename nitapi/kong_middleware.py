"""Kong API Gateway middleware for Django."""
import logging
import requests
from django.http import JsonResponse
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class KongMiddleware(MiddlewareMixin):
    """Middleware to interact with Kong API Gateway
    Handles rate limiting, authentication verification, and request routing.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.kong_admin_url = getattr(settings, 'KONG_ADMIN_URL', None)
        self.kong_proxy_url = getattr(settings, 'KONG_PROXY_URL', None)
        super().__init__(get_response)

    def process_request(self, request):
        """Process incoming request through Kong gateway logic."""
        # Skip Kong processing for admin and static files
        if self.should_skip_kong(request):
            return None

        # Extract Kong headers if present
        consumer_id = request.META.get('HTTP_X_CONSUMER_ID')
        consumer_username = request.META.get('HTTP_X_CONSUMER_USERNAME')
        consumer_custom_id = request.META.get('HTTP_X_CONSUMER_CUSTOM_ID')

        # Add Kong information to request for use in views
        request.kong_consumer = {
            'id': consumer_id,
            'username': consumer_username,
            'custom_id': consumer_custom_id,
        }

        # Log Kong consumer information
        if consumer_id:
            logger.info(
                f"Request from Kong consumer: {consumer_username} "
                f"(ID: {consumer_id})"
            )

        return None

    def process_response(self, request, response):
        """Process response and add Kong-related headers."""
        # Add custom headers for Kong tracking
        if hasattr(request, 'kong_consumer'):
            consumer = request.kong_consumer
            if consumer.get('id'):
                response['X-Kong-Consumer-ID'] = consumer['id']
                response['X-Kong-Consumer-Username'] = consumer.get(
                    'username', ''
                )

        # Add API version header
        response['X-API-Version'] = getattr(settings, 'API_VERSION', '1.0')

        return response

    def should_skip_kong(self, request):
        """Check if request should skip Kong processing."""
        skip_paths = [
            '/admin/',
            '/static/',
            '/media/',
            '/health/',
            '/docs/',
            '/schema/',
        ]

        return any(request.path.startswith(path) for path in skip_paths)


class KongRateLimitMiddleware(MiddlewareMixin):
    """Custom rate limiting middleware that respects Kong rate limits."""

    def process_request(self, request):
        """Check rate limiting headers from Kong."""
        # Check if rate limit headers are present (set by Kong)
        rate_limit_remaining = request.META.get('HTTP_X_RATELIMIT_REMAINING')
        rate_limit_limit = request.META.get('HTTP_X_RATELIMIT_LIMIT')

        if rate_limit_remaining is not None:
            try:
                remaining = int(rate_limit_remaining)
                if remaining <= 0:
                    return JsonResponse({
                        'error': 'Rate limit exceeded',
                        'message': 'Too many requests. Try again later.',
                        'limit': rate_limit_limit,
                        'remaining': remaining
                    }, status=429)
            except ValueError:
                pass

        return None


class KongServiceRegistry:
    """Utility class to register and manage services in Kong."""

    def __init__(self):
        self.admin_url = settings.KONG_ADMIN_URL
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json'
        })

    def register_service(self, name, url, path=None):
        """Register a service in Kong."""
        try:
            service_data = {
                'name': name,
                'url': url,
            }

            if path:
                service_data['path'] = path

            response = self.session.post(
                f"{self.admin_url}/services",
                json=service_data
            )

            if response.status_code == 201:
                logger.info(
                    f"Service '{name}' registered successfully in Kong"
                )
                return response.json()
            elif response.status_code == 409:
                logger.info(f"Service '{name}' already exists in Kong")
                return self.get_service(name)
            else:
                logger.error(
                    f"Failed to register service '{name}': "
                    f"{response.status_code} - {response.text}"
                )
                return None

        except requests.RequestException as e:
            logger.error(f"Error registering service '{name}' in Kong: {e}")
            return None

    def create_route(self, service_name, paths, methods=None):
        """Create a route for a service in Kong."""
        try:
            route_data = {
                'paths': paths if isinstance(paths, list) else [paths],
                'service': {'name': service_name}
            }

            if methods:
                route_data['methods'] = (
                    methods if isinstance(methods, list) else [methods]
                )

            response = self.session.post(
                f"{self.admin_url}/routes",
                json=route_data
            )

            if response.status_code == 201:
                logger.info(f"Route created for service '{service_name}'")
                return response.json()
            else:
                logger.error(
                    f"Failed to create route for '{service_name}': "
                    f"{response.status_code} - {response.text}"
                )
                return None

        except requests.RequestException as e:
            logger.error(f"Error creating route for '{service_name}': {e}")
            return None

    def get_service(self, name):
        """Get service information from Kong."""
        try:
            response = self.session.get(f"{self.admin_url}/services/{name}")
            if response.status_code == 200:
                return response.json()
            return None
        except requests.RequestException:
            return None

    def setup_default_services(self):
        """Setup default services and routes for the Django application."""
        # Register main API service
        self.register_service(
            name='nit-api',
            url=getattr(settings, 'BASE_URL', 'http://localhost:8000')
        )

        # Create routes for API endpoints
        self.create_route(
            service_name='nit-api',
            paths=['/api'],
            methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
        )

        logger.info("Default Kong services and routes setup completed")
