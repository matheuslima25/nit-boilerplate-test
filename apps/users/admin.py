from apps.commons.admin import BaseAdmin
from apps.users import models
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.db.models import F
from django.utils.translation import gettext_lazy as _


class ProfileInline(admin.StackedInline):
    model = models.Profile
    extra = 0
    max_num = 1
    fk_name = "user"
    readonly_fields = (
        "id", "created_at", "created_by", "updated_at",
        "updated_by", "deleted_at", "deleted_by"
    )
    exclude = ("address",)

    def has_delete_permission(self, request, obj=None):
        return False

    def get_fields(self, request, obj=None):
        fields = super(ProfileInline, self).get_fields(request, obj)
        if not request.user.is_superuser:
            fields = [field for field in fields if field not in [
                "id", "created_at", "created_by", "updated_at", "updated_by",
                "deleted_at", "deleted_by"
            ]]
        return fields


class ClientInline(admin.StackedInline):
    model = models.Client
    extra = 0
    fk_name = "client"
    readonly_fields = (
        "id", "created_at", "created_by", "updated_at",
        "updated_by", "deleted_at", "deleted_by"
    )
    verbose_name = "Cliente Adicional"
    verbose_name_plural = "Clientes Adicionais"

    def get_fields(self, request, obj=None):
        fields = super(ClientInline, self).get_fields(request, obj)
        if not request.user.is_superuser:
            fields = [field for field in fields if field not in [
                "id", "created_at", "created_by", "updated_at",
                "updated_by", "deleted_at", "deleted_by"
            ]]
        return fields


@admin.register(models.User)
class UserAdmin(DjangoUserAdmin, BaseAdmin):
    """Admin para gerenciamento de usuários.

    IMPORTANTE: Usuários são criados e autenticados via Keycloak.
    Este admin é apenas para visualização e edição de dados de usuários
    já existentes. Não é possível criar novos usuários via Django Admin.
    """

    list_display = (
        "profile_name", "cpf_cnpj", "email", "is_active", "is_staff",
        "is_superuser",
    )
    list_filter = ("is_active", "is_staff", "is_superuser",)
    date_hierarchy = "created_at"
    search_fields = (
        "user__name", "client__name", "client__cpf_cnpj",
        "email", "username", "cpf_cnpj",
    )
    ordering = ("user__name", "-created_at")
    inlines = (ProfileInline, ClientInline)
    change_list_template = "admin/change_list.html"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(profile_name=F("user__name"))
        return qs.order_by("profile_name")

    def profile_name(self, obj):
        return obj.get_profile().name if obj.get_profile() else obj.email

    profile_name.admin_order_field = "profile_name"
    profile_name.short_description = "Nome"

    fieldsets = (
        (
            _("Informações Básicas"),
            {
                "fields": (
                    "email",
                    "cpf_cnpj",
                    "rg",
                )
            },
        ),
        (
            _("Grupos e permissões"),
            {
                "fields": (
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            _("Status"),
            {
                "fields": (
                    "status",
                    "is_active",
                    "first_login_accomplished",
                )
            },
        ),
        (
            _("Concessões e Contatos"),
            {
                "fields": (
                    "terms",
                    "receive_emails",
                    "other_emails",
                )
            },
        ),
        (
            _("Keycloak"),
            {
                "fields": (
                    "keycloak_id",
                )
            },
        ),
        (
            _("Sistema"),
            {
                "fields": (
                    "id",
                    "last_login",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    # Remove add_fieldsets - usuários são criados via Keycloak
    add_fieldsets = None

    def has_add_permission(self, request):
        """
        Desabilita a criação de usuários via Django Admin.

        Usuários devem ser criados via Keycloak.
        """
        return False

    def user_profile_name(self, obj):
        return obj.get_profile().name if obj.get_profile() else obj.email

    user_profile_name.short_description = "Nome"

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return list(self.readonly_fields) + [
                "last_login", "id", "date_joined"
            ]
        return self.readonly_fields

    def get_fieldsets(self, request, obj=None):
        fieldsets = super(UserAdmin, self).get_fieldsets(request, obj)
        if not request.user.is_superuser:
            new_fieldsets = []
            for name, data in fieldsets:
                fields = [field for field in data["fields"] if field not in [
                    "is_staff", "is_superuser", "groups",
                    "user_permissions", "id", "status",
                    "first_login_accomplished",
                ]]
                if fields:
                    new_fieldsets.append((name, {"fields": fields}))
            return new_fieldsets
        return fieldsets

    def get_list_filter(self, request):
        if not request.user.is_superuser:
            return ("is_active",)
        return ("is_active", "is_staff", "is_superuser",)

    def get_list_display(self, request):
        if not request.user.is_superuser:
            return ("profile_name", "cpf_cnpj", "email", "is_active",)
        return (
            "profile_name", "cpf_cnpj", "email", "is_active",
            "is_staff", "is_superuser",
        )
