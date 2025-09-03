"""
Health checks simples para Kong.
"""
import requests
from django.conf import settings
from health_check.backends import BaseHealthCheckBackend
from health_check.exceptions import HealthCheckException


class KongHealthCheck(BaseHealthCheckBackend):
    """Health check básico para Kong Gateway."""

    critical_service = False  # Não crítico para não quebrar o sistema

    def check_status(self):
        """Verifica se Kong está acessível."""
        try:
            # Verifica se Kong Admin API responde
            if getattr(settings, "KONG_ADMIN_URL", ""):
                url = f"{settings.KONG_ADMIN_URL}/status"
                response = requests.get(url, timeout=5)

                if response.status_code != 200:
                    raise HealthCheckException(
                        "Kong Admin API não está respondendo"
                    )

            # Se chegou até aqui, Kong está funcionando

        except requests.exceptions.RequestException:
            raise HealthCheckException("Kong não está acessível")
        except HealthCheckException:
            raise  # Re-raise HealthCheckException
        except Exception as e:
            raise HealthCheckException(f"Erro ao verificar Kong: {str(e)}")

    def identifier(self):
        """Identificador único do health check."""
        return "Kong Gateway"
