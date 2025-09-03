from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.commons.models import BaseModel


class LoginAttempt(BaseModel):
    class Meta(BaseModel.Meta):
        verbose_name = _(u"Tentativa de login")
        verbose_name_plural = _(u"Tentativas de login")
        ordering = ("-timestamp",)

    username = models.CharField(
        _(u"Username"),
        max_length=255,
        blank=True,
        null=True
    )
    ip_address = models.GenericIPAddressField(
        _(u"IP address"),
        protocol='both',
        blank=True,
        null=True
    )
    session_key = models.CharField(
        _(u"Session key"),
        max_length=50,
        blank=True,
        null=True
    )
    user_agent = models.TextField(_(u"user-agent"), blank=True, null=True)
    timestamp = models.DateTimeField(_(u"Timestamp"), auto_now_add=True)
    path = models.TextField(_(u"Path"), blank=True, null=True)

    def __str__(self):
        return self.username
