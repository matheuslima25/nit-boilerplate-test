"""Configuração da aplicação Commons.

Este módulo configura a aplicação Commons que contém modelos base
e utilitários compartilhados por todas as outras aplicações.
"""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CoreConfig(AppConfig):
    """Configuração da aplicação Commons.

    Esta aplicação contém modelos base e utilitários compartilhados entre
    todas as outras aplicações do sistema. Inclui:

    - BaseModel: Modelo base com soft delete e rastreabilidade
    - Email: Configurações genéricas de templates de e-mail
    - Address: Modelo de endereços padronizado
    - Health Checks: Verificações de saúde para Keycloak e Kong

    Características principais:
    - Soft delete automático em todos os modelos
    - Rastreabilidade completa (criado por, atualizado por, deletado por)
    - Sistema de health checks para monitoramento
    - Templates de e-mail configuráveis
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.commons"
    verbose_name = _("Configurações Comuns")

    def ready(self):
        """Método executado quando a aplicação está pronta.

        Registra automaticamente os health checks customizados para
        monitoramento da saúde dos serviços externos (Keycloak e Kong).

        Os health checks são opcionais e só são registrados se o pacote
        django-health-check estiver disponível.
        """
        try:
            from health_check.plugins import plugin_dir

            # Importa e registra nossos health checks customizados
            from .checks.keycloak import KeycloakHealthCheck
            from .checks.kong import KongHealthCheck

            plugin_dir.register(KeycloakHealthCheck)
            plugin_dir.register(KongHealthCheck)

        except ImportError:
            # health_check não disponível, ignora silenciosamente
            pass
