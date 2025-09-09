"""
Middleware para separar autenticação entre Admin Django e API REST.
"""
import logging

logger = logging.getLogger(__name__)


class AdminAuthenticationMiddleware:
    """
    Middleware que garante que apenas o Django Admin use autenticação
    tradicional. As rotas da API continuam usando autenticação Keycloak.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Identifica se é uma requisição para o admin
        path = request.path_info

        # Rotas que devem usar autenticação Django tradicional
        admin_paths = [
            '/pt-br/secret/',  # Admin URL configurada
            '/secret/',        # Admin URL sem prefixo de idioma
            '/admin/',         # Admin padrão (se existir)
        ]

        # Verifica se é uma rota admin
        is_admin_request = any(
            path.startswith(admin_path)
            for admin_path in admin_paths
        )

        if is_admin_request:
            # Para requisições admin, remove headers de autenticação API
            # para forçar uso da autenticação tradicional Django
            request.META.pop('HTTP_AUTHORIZATION', None)
            request.META.pop('HTTP_X_CONSUMER_ID', None)
            request.META.pop('HTTP_X_CONSUMER_USERNAME', None)
            request.META.pop('HTTP_X_CONSUMER_CUSTOM_ID', None)

            # Marca a requisição como admin
            request.is_admin_request = True

            logger.debug(f"Admin request detected: {path}")
        else:
            request.is_admin_request = False

        response = self.get_response(request)
        return response
