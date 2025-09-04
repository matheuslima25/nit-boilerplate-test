import requests
from django.conf import settings
from health_check.backends import BaseHealthCheckBackend
from health_check.exceptions import HealthCheckException


class KeycloakHealthCheck(BaseHealthCheckBackend):
    """Health check básico para conectividade com Keycloak."""

    critical_service = False

    def check_status(self):
        """Verifica se o Keycloak está acessível."""
        try:
            # Usar endpoint admin que sempre responde (HTTP 302 é sucesso)
            url = f"{settings.KEYCLOAK_SERVER_URL}/admin"
            response = requests.get(url, timeout=5, allow_redirects=False)

            # 302 é um redirect válido = Keycloak funcionando
            if response.status_code not in [200, 302]:
                raise HealthCheckException(
                    f"Keycloak respondeu com status {response.status_code}"
                )

        except requests.exceptions.RequestException as e:
            raise HealthCheckException(
                f"Keycloak não está acessível: {str(e)}"
            )
        except Exception as e:
            raise HealthCheckException(f"Erro ao verificar Keycloak: {str(e)}")

    def identifier(self):
        return "Keycloak"
