"""
Health check simples para Keycloak.
"""
import requests
from django.conf import settings
from health_check.backends import BaseHealthCheckBackend
from health_check.exceptions import HealthCheckException


class KeycloakHealthCheck(BaseHealthCheckBackend):
    """Health check básico para conectividade com Keycloak."""

    critical_service = False  # Não crítico para não quebrar o sistema

    def check_status(self):
        """Verifica se o Keycloak está acessível."""
        try:
            # Verifica apenas se o Keycloak responde
            url = f"{settings.KEYCLOAK_SERVER_URL}/health"
            response = requests.get(url, timeout=5)

            if response.status_code != 200:
                raise HealthCheckException("Keycloak não está respondendo")

        except requests.exceptions.RequestException:
            raise HealthCheckException("Keycloak não está acessível")
        except HealthCheckException:
            raise  # Re-raise HealthCheckException
        except Exception as e:
            raise HealthCheckException(f"Erro ao verificar Keycloak: {str(e)}")

    def identifier(self):
        """Identificador único do health check."""
        return "Keycloak"
