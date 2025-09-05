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

        Configura health checks para execução apenas on-demand.
        """
        self._register_health_checks()

    def _register_health_checks(self):
        """
        Health checks configurados para execução on-demand.
        
        Em vez de polling automático, os health checks agora funcionam
        apenas quando solicitados através dos endpoints REST.
        """
        # Health checks automáticos desabilitados
        # Use endpoints /commons/status/ para verificações on-demand
        pass
