"""Administração da aplicação Commons.

Este módulo define as classes de administração para os modelos da aplicação
Commons, incluindo configurações personalizadas para BaseAdmin, LogEntry,
Email e Address com funcionalidades específicas de rastreabilidade e
soft delete.
"""

from django.conf import settings
from django.contrib import admin
from django.contrib.admin.models import DELETION, LogEntry
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from django.utils.html import escape
from django.utils.safestring import mark_safe

from apps.commons import models


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    """Administração para LogEntry (logs de auditoria do Django Admin).

    Fornece uma interface readonly para visualização dos logs de auditoria
    do Django Admin, permitindo rastreamento de todas as operações realizadas
    pelos usuários no painel administrativo.
    """

    date_hierarchy = "action_time"

    list_filter = ["user", "content_type", "action_flag"]

    search_fields = ["object_repr", "change_message"]

    list_display = [
        "action_time",
        "user",
        "content_type",
        "object_link",
        "action_flag",
    ]

    def has_add_permission(self, request):
        """Impede criação manual de logs."""
        return False

    def has_change_permission(self, request, obj=None):
        """Impede edição de logs existentes."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Impede remoção de logs."""
        return False

    def has_view_permission(self, request, obj=None):
        """Permite visualização apenas para superusuários."""
        return request.user.is_superuser

    def object_link(self, obj):
        """Cria link para o objeto relacionado ao log.

        Returns:
            str: HTML com link para o objeto ou texto simples se deletado

        """
        try:
            if obj.action_flag == DELETION:
                link = escape(obj.object_repr)
            else:
                ct = obj.content_type
                link = '<a href="%s">%s</a>' % (
                    reverse(
                        "admin:%s_%s_change" % (ct.app_label, ct.model),
                        args=[obj.object_id],
                    ),
                    escape(obj.object_repr),
                )
            return mark_safe(link)
        except NoReverseMatch:
            return ""

    object_link.admin_order_field = "object_repr"
    object_link.short_description = "Objeto"


class BaseAdmin(admin.ModelAdmin):
    """Classe base de administração para modelos que herdam de BaseModel.

    Implementa funcionalidades específicas para trabalhar com soft delete
    e rastreabilidade automática, sobrescrevendo comportamentos padrão
    do Django Admin para compatibilidade com BaseModel.

    Características:
    - Campos de rastreabilidade como readonly
    - Save automático com usuário de criação/atualização
    - Soft delete em vez de remoção física
    - Ocultação de campos readonly em formulários de criação
    """

    readonly_fields = (
        "id",
        "created_at",
        "created_by",
        "updated_at",
        "updated_by",
        "deleted_at",
        "deleted_by",
    )

    def save_model(self, request, obj, form, change):
        """Override do save para rastreabilidade automática.

        Identifica o usuário que fez a requisição e atualiza campos
        de rastreabilidade dependendo se é criação ou atualização.

        Args:
            request: Requisição Django com usuário associado
            obj: Objeto sendo criado/atualizado
            form: Formulário utilizado (não usado diretamente)
            change: Info sobre mudanças (não usado diretamente)

        """
        if obj.pk is None:
            # Novo objeto - define usuário de criação
            obj.created_by = request.user
        else:
            # Objeto existente - atualiza campos de modificação
            obj.updated_at = timezone.now()
            obj.updated_by = request.user

        super().save_model(request, obj, form, change)

    def delete_queryset(self, request, queryset):
        """Override do delete queryset para soft delete em lote.

        Chama o método delete override para cada modelo no queryset,
        implementando soft delete em vez de remoção física.

        Args:
            request: Requisição Django com usuário associado
            queryset: Queryset com objetos a serem removidos

        """
        for model in queryset:
            kwargs = {"deleted_by": request.user, "deleted_at": timezone.now()}
            model.delete(**kwargs)

    def delete_model(self, request, obj):
        """Override do delete model para soft delete individual.

        Chama o método delete override do modelo implementando
        soft delete em vez de remoção física.

        Args:
            request: Requisição Django com usuário associado
            obj: Instância do modelo a ser removida

        """
        kwargs = {"deleted_by": request.user, "deleted_at": timezone.now()}
        obj.delete(**kwargs)

    def get_fields(self, request, obj=None):
        """Override para ocultar campos readonly em formulários de criação.

        Remove campos readonly quando criando novo objeto para
        melhorar UX do formulário.

        Args:
            request: Requisição Django
            obj: Objeto sendo editado (None para criação)

        Returns:
            list: Lista de campos a serem exibidos

        """
        if obj:
            # Objeto existente - mostra todos os campos
            return super(BaseAdmin, self).get_fields(request, obj)

        # Novo objeto - remove campos readonly
        all_fields = super(BaseAdmin, self).get_fields(request, obj)
        return [
            field for field in all_fields if field not in self.readonly_fields
        ]


@admin.register(models.Email)
class EmailAdmin(BaseAdmin):
    """Administração para o modelo Email (configurações de templates).

    Implementa padrão Singleton permitindo apenas uma instância ativa.
    Fornece interface para configuração de templates de e-mail do sistema.
    """

    list_display = (
        "id",
        "notification_subject",
        "created_at",
        "is_active",
    )

    list_filter = ("is_active", "created_at")

    search_fields = (
        "notification_subject",
    )

    fieldsets = (
        ("Informações Gerais", {"fields": ("id", "is_active")}),
        (
            "Templates de Notificação",
            {
                "fields": ("notification_subject", "notification_template"),
                "classes": ("collapse",),
            },
        ),
        (
            "Rastreabilidade",
            {
                "fields": (
                    "created_at",
                    "created_by",
                    "updated_at",
                    "updated_by",
                    "deleted_at",
                    "deleted_by",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def has_add_permission(self, request):
        """Implementa padrão Singleton - permite apenas uma instância.

        Returns:
            bool: False se já existe uma configuração ativa

        """
        email_exists = models.Email.objects.filter(is_active=True).exists()
        return not email_exists

    def has_delete_permission(self, request, obj=None):
        """Permite soft delete apenas para superusuários.

        Returns:
            bool: True apenas para superusuários

        """
        return request.user.is_superuser

    def get_queryset(self, request):
        """Mostra apenas registros ativos por padrão.

        Returns:
            QuerySet: Registros ativos ou todos para superusuários

        """
        if request.user.is_superuser:
            return models.Email.all_objects.all()
        return super().get_queryset(request)

    def save_model(self, request, obj, form, change):
        """Override do save com validação de Singleton."""
        if not change and models.Email.objects.filter(is_active=True).exists():
            from django.contrib import messages

            messages.error(
                request,
                "Só pode haver uma configuração de e-mail ativa no sistema.",
            )
            return
        super().save_model(request, obj, form, change)


@admin.register(models.Address)
class AddressAdmin(BaseAdmin):
    """Administração para o modelo Address.

    Fornece interface de visualização para endereços com funcionalidades
    restritas - apenas visualização e edição limitada, sem criação ou
    remoção direta pelo admin.
    """

    list_display = (
        "id",
        "street",
        "number",
        "district",
        "city",
        "state",
        "cep",
        "created_at",
        "is_active",
    )

    list_filter = ("state", "city", "is_active", "created_at")

    search_fields = (
        "street",
        "district",
        "city",
        "cep",
        "number",
        "complement",
    )

    # Adiciona CEP como readonly além dos campos base
    def get_readonly_fields(self, request, obj=None):
        """Adiciona CEP aos campos readonly."""
        base_fields = list(self.readonly_fields)
        base_fields.append("cep")
        return tuple(base_fields)

    fieldsets = (
        ("Informações Básicas", {"fields": ("id", "is_active")}),
        (
            "Endereço",
            {
                "fields": (
                    "street",
                    "number",
                    "complement",
                    "district",
                    "city",
                    "state",
                    "country",
                    "cep",
                )
            },
        ),
        (
            "Rastreabilidade",
            {
                "fields": (
                    "created_at",
                    "created_by",
                    "updated_at",
                    "updated_by",
                    "deleted_at",
                    "deleted_by",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def has_add_permission(self, request):
        """Desabilita criação direta de endereços pelo admin.

        Endereços devem ser criados através de outros modelos
        ou via API/interface específica.

        Returns:
            bool: False para todos os usuários

        """
        return False

    def has_change_permission(self, request, obj=None):
        """Permite edição apenas para staff e superusuários.

        Returns:
            bool: True para staff/superusuários

        """
        return request.user.is_superuser or request.user.is_staff

    def has_delete_permission(self, request, obj=None):
        """Desabilita remoção direta de endereços pelo admin.

        Returns:
            bool: False para todos os usuários

        """
        return False

    def get_queryset(self, request):
        """Mostra todos os registros para superusuários.

        Returns:
            QuerySet: Todos os registros para superusuários,
                    apenas ativos para outros usuários

        """
        if request.user.is_superuser:
            return models.Address.all_objects.all()
        return super().get_queryset(request)

    def get_full_address(self, obj):
        """Exibe endereço completo formatado.

        Returns:
            str: Endereço completo formatado

        """
        return obj.get_full_address()

    get_full_address.short_description = "Endereço Completo"


# Configurações globais do Django Admin
admin.site.site_title = getattr(settings, "PROJECT_TITLE", "Administração")
admin.site.site_header = getattr(
    settings, "PROJECT_TITLE", "Painel Administrativo"
)
admin.site.index_title = "Bem-vindo ao painel administrativo"
