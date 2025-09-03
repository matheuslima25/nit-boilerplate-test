"""Modelos base e utilitários comuns do sistema.

Este módulo contém modelos base que são utilizados por todas as outras
aplicações do sistema, fornecendo funcionalidades padrão como soft delete,
rastreabilidade, configurações de e-mail e endereços.
"""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import QuerySet
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from tinymce import models as tinymce_models

from apps.commons.constants import CommonConstants


class BaseModelQuerySet(QuerySet):
    """QuerySet customizado para BaseModel.

    Fornece métodos adicionais para trabalhar com soft delete e filtragem
    de registros ativos/inativos.
    """

    def delete(self):
        """Soft delete em todos os objetos do queryset."""
        [x.delete() for x in self]

    def hard_delete(self):
        """Delete permanente em todos os objetos do queryset."""
        [x.hard_delete() for x in self]

    def active(self):
        """Filtra apenas registros ativos (is_active=True)."""
        return self.filter(is_active=True)

    def inactive(self):
        """Filtra apenas registros inativos (is_active=False)."""
        return self.filter(is_active=False)


class BaseModelManager(models.Manager):
    """Manager customizado para BaseModel.

    Este manager implementa funcionalidades específicas para trabalhar com
    soft delete, fornecendo métodos para filtrar apenas registros ativos
    por padrão e permitir acesso a todos os registros quando necessário.

    Características:
    - Por padrão, filtra apenas registros ativos (is_active=True)
    - Fornece método all_objects() para acessar todos os registros
    - Implementa hard_delete() para remoção permanente
    """

    use_for_related_fields = True

    def __init__(self, *args, **kwargs):
        """Inicializa o manager.

        Args:
            *args: Argumentos posicionais para o manager base
            **kwargs: Argumentos nomeados, incluindo:
                active_only (bool): Se True, filtra apenas registros ativos.
                                  Padrão: True

        """
        self.active_only = kwargs.pop("active_only", True)
        super(BaseModelManager, self).__init__(*args, **kwargs)

    def all_objects(self):
        """Retorna um queryset com todos os objetos, incluindo inativos.

        Returns:
            BaseModelQuerySet: Queryset com todos os registros

        """
        return BaseModelQuerySet(self.model)

    def get_queryset(self):
        """Override do método get_queryset para implementar soft delete.

        Returns:
            BaseModelQuerySet: Queryset filtrado por registros ativos
                              (se active_only=True) ou todos os registros

        """
        if self.active_only:
            return BaseModelQuerySet(self.model).filter(is_active=True)
        return BaseModelQuerySet(self.model)

    def hard_delete(self):
        """Remove permanentemente todos os registros do queryset."""
        self.get_queryset().hard_delete()


class BaseModel(models.Model):
    """Modelo base com soft delete e rastreabilidade completa.

    Este modelo fornece funcionalidades comuns a todos os modelos do sistema:
    - Soft delete: registros são marcados como inativos em vez de removidos
    - Rastreabilidade: tracking de criação, atualização e remoção
    - UUID: identificador único além da chave primária sequencial
    - Timestamps automáticos

    Para campos únicos, adicione no modelo que herda desta classe:

    class Meta:
        ...
        constraints = [
            models.UniqueConstraint(
                fields=["field"],
                condition=Q(is_active=True),
                name="_unique"
            )
        ]

    Troque "field" pelos nomes dos campos que devem ser únicos,
    depois execute makemigrations/migrate.

    Managers disponíveis:
    - objects: apenas registros ativos (padrão)
    - all_objects: todos os registros (incluindo inativos)
    """

    class Meta:
        """Configuração do modelo base."""

        ordering = ("-created_at",)
        abstract = True

    # Chave primária sequencial para performance
    pkid = models.BigAutoField(primary_key=True, editable=False)

    # UUID para identificação externa
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    # Campos de rastreabilidade de criação
    created_at = models.DateTimeField(
        _("Criado em"), auto_now_add=True, null=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Criado por"),
        on_delete=models.DO_NOTHING,
        related_name="%(class)s_creator",
        null=True,
    )

    # Campos de rastreabilidade de atualização
    updated_at = models.DateTimeField(_("Atualizado em"), auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Atualizado por"),
        on_delete=models.DO_NOTHING,
        related_name="%(class)s_updator",
        null=True,
    )

    # Campos de rastreabilidade de remoção (soft delete)
    deleted_at = models.DateTimeField(_("Deletado em"), null=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Deletado por"),
        on_delete=models.DO_NOTHING,
        related_name="%(class)s_remover",
        null=True,
    )

    # Flag de soft delete
    is_active = models.BooleanField(
        editable=False, default=True, verbose_name=_("Está ativo?")
    )

    # Managers para controle de soft delete
    objects = BaseModelManager()  # Apenas registros ativos
    all_objects = BaseModelManager(active_only=False)  # Todos os registros

    def delete(self, **kwargs):
        """Implementa soft delete em vez de remoção física.

        Marca o registro como inativo (is_active=False) e registra
        informações de rastreabilidade da remoção.

        Args:
            **kwargs: Argumentos nomeados incluindo:
                deleted_by: Usuário que solicitou a remoção
                deleted_at: Timestamp da remoção

        """
        self.is_active = False
        if "deleted_by" in kwargs:
            self.deleted_by = kwargs["deleted_by"]
        if "deleted_at" in kwargs:
            self.deleted_at = kwargs["deleted_at"]
        self.save()
        # Nota: Relacionamentos em cascata devem ser tratados por signals

    def hard_delete(self, **kwargs):
        """Remove o registro permanentemente do banco de dados.

        Use com cuidado! Esta operação não pode ser desfeita.
        """
        super(BaseModel, self).delete(**kwargs)


class Email(BaseModel):
    """Modelo para configuração de templates de e-mail genéricos.

    Este modelo centraliza a configuração de templates de e-mail utilizados
    pelo sistema. Permite personalização de assuntos e conteúdos HTML
    para diferentes tipos de notificações.

    Características:
    - Singleton: apenas uma instância pode existir
    - Templates HTML com suporte a variáveis
    - Configuração centralizada de todos os e-mails do sistema
    - Herda soft delete e rastreabilidade do BaseModel

    Variáveis disponíveis nos templates:
    - {{ nome }}: Nome do usuário
    - {{ email }}: E-mail do usuário
    - {{ link }}: Link de ação (quando aplicável)
    - {{ site_name }}: Nome do site/sistema
    - {{ data }}: Data atual
    """

    class Meta(BaseModel.Meta):
        """Configuração do modelo Email."""

        verbose_name = _("Configuração de E-mail")
        verbose_name_plural = _("Configurações de E-mail")
        select_on_save = True

    # Template genérico para notificações
    notification_subject = models.CharField(
        _("Notificação (assunto)"),
        max_length=255,
        default=_("Nova notificação"),
        help_text=_("Assunto padrão para notificações gerais"),
    )
    notification_template = tinymce_models.HTMLField(
        _("Notificação (template)"),
        blank=True,
        null=True,
        help_text=_(
            "Template HTML para notificações gerais. "
            "Variáveis: {{ nome }}, {{ email }}, {{ mensagem }}, "
            "{{ site_name }}"
        ),
    )

    def clean(self):
        """Valida que apenas uma instância pode existir (Singleton)."""
        if not self.pk and Email.objects.exists():
            raise ValidationError(
                "Só pode haver uma configuração de e-mail no sistema."
            )

    def __str__(self):
        """Representação em string do modelo Email."""
        return f"Configurações de E-mail #{self.pkid}"

    @classmethod
    def get_instance(cls):
        """Retorna a única instância de configuração de e-mail.

        Returns:
            Email: Instância de configuração ou None se não existir

        """
        return cls.objects.first()

    def get_welcome_context(self, user, extra_context=None):
        """Prepara o contexto para o template de boas-vindas.

        Args:
            user: Usuário para o qual o e-mail será enviado
            extra_context: Contexto adicional opcional

        Returns:
            dict: Contexto para renderização do template

        """
        context = {
            "nome": getattr(user, "first_name", str(user)),
            "email": getattr(user, "email", ""),
            "site_name": "Sistema",
            "data": timezone.now().strftime("%d/%m/%Y"),
        }
        if extra_context:
            context.update(extra_context)
        return context


class Address(BaseModel):
    """Modelo para endereços padronizado para uso em todo o sistema.

    Este modelo fornece uma estrutura comum para armazenamento de endereços,
    principalmente focado no padrão brasileiro, mas com flexibilidade para
    outros países.

    Características:
    - Campos opcionais para máxima flexibilidade
    - Choices para estados brasileiros
    - Herda soft delete e rastreabilidade do BaseModel
    - Formatação automática de CEP

    Uso recomendado:
    - Como ForeignKey em outros modelos quando precisar de endereço
    - Para armazenar endereços de usuários, empresas, etc.
    """

    class Meta:
        """Configuração do modelo Address."""

        verbose_name = _("Endereço")
        verbose_name_plural = _("Endereços")
        ordering = ["-created_at"]

    # Logradouro e identificação
    street = models.CharField(_("Rua"), max_length=255, null=True, blank=True)
    district = models.CharField(
        _("Bairro"), max_length=255, null=True, blank=True
    )
    number = models.CharField(
        _("Número"), max_length=255, null=True, blank=True
    )
    complement = models.CharField(
        _("Complemento"), max_length=255, null=True, blank=True
    )

    # Localização
    city = models.CharField(_("Cidade"), max_length=255, null=True, blank=True)
    state = models.CharField(
        _("Estado"),
        max_length=255,
        null=True,
        blank=True,
        choices=CommonConstants.BRAZIL_STATES,
    )
    country = models.CharField(
        _("País"), max_length=255, null=True, blank=True
    )
    cep = models.CharField(_("CEP"), max_length=9, null=True, blank=True)

    def __str__(self):
        """Representação em string do endereço.

        Returns:
            str: Representação formatada do endereço

        """
        if self.street and self.city:
            return f"{self.street}, {self.number or 'S/N'} - {self.city}"
        return f"Endereço #{self.pkid}"

    def get_full_address(self):
        """Retorna o endereço completo formatado.

        Returns:
            str: Endereço completo em uma linha

        """
        parts = []

        if self.street:
            street_part = self.street
            if self.number:
                street_part += f", {self.number}"
            if self.complement:
                street_part += f" - {self.complement}"
            parts.append(street_part)

        if self.district:
            parts.append(self.district)

        if self.city:
            city_part = self.city
            if self.state:
                city_part += f" - {self.state}"
            parts.append(city_part)

        if self.cep:
            parts.append(f"CEP: {self.cep}")

        return ", ".join(parts) if parts else "Endereço não informado"

    def clean(self):
        """Validação customizada do modelo.

        Raises:
            ValidationError: Se CEP não estiver no formato correto

        """
        super().clean()

        # Validação simples de CEP brasileiro
        if self.cep:
            # Remove caracteres não numéricos
            cep_clean = "".join(filter(str.isdigit, self.cep))
            if len(cep_clean) == 8:
                # Formata CEP como XXXXX-XXX
                self.cep = f"{cep_clean[:5]}-{cep_clean[5:]}"
            elif len(cep_clean) != 0:
                raise ValidationError({"cep": _("CEP deve ter 8 dígitos.")})
