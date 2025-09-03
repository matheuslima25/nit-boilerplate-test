from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

__all__ = ["AdminHoneypotConfig"]


class AdminHoneypotConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.honeypot"
    verbose_name = _("Segurança")

    def ready(self):
        pass
