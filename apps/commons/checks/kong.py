import requests
from django.conf import settings
from health_check.backends import BaseHealthCheckBackend
from health_check.exceptions import HealthCheckException


class KongHealthCheck(BaseHealthCheckBackend):
    """Health check para Kong Gateway - apenas on-demand."""

    critical_service = False
    # Desabilita execução automática - apenas manual
    run_check = False

    def check_status(self):
        """Verifica se Kong está acessível."""
        try:
            # Usar Kong Admin API diretamente
            url = f"{settings.KONG_ADMIN_URL}/status"
            response = requests.get(url, timeout=5)

            if response.status_code != 200:
                raise HealthCheckException(
                    (
                        f"Kong Admin API respondeu com status "
                        f"{response.status_code}"
                    )
                )

            # Verificar se resposta contém dados válidos
            data = response.json()
            if not data.get("server"):
                raise HealthCheckException("Kong retornou dados inválidos")

        except requests.exceptions.RequestException as e:
            raise HealthCheckException(f"Kong não está acessível: {str(e)}")
        except Exception as e:
            raise HealthCheckException(f"Erro ao verificar Kong: {str(e)}")

    def identifier(self):
        return "Kong Gateway"
