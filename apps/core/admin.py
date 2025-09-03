"""Configurações do Django Admin para a aplicação Core.

Este módulo contém as configurações do admin para os models da aplicação Core.
Todos os admins devem herdar do BaseAdmin para ter funcionalidades como
rastreabilidade automática, soft delete e comportamentos customizados.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.db.models import Count
from django.utils.translation import gettext_lazy as _

from apps.commons.admin import BaseAdmin
from apps.core import models


# =============================================================================
# ADMIN BÁSICO - DOCUMENT
# =============================================================================


@admin.register(models.Document)
class DocumentAdmin(BaseAdmin):
    """Admin para o model Document.

    Herda todas as funcionalidades do BaseAdmin:
    - Rastreabilidade automática (created_by, updated_by, deleted_by)
    - Soft delete com informações de quem deletou
    - Campos readonly apropriados
    - Override de save_model para capturar usuário
    """

    list_display = (
        "title",
        "category",
        "is_published",
        "file_link",
        "created_at",
        "created_by",
    )

    list_filter = (
        "category",
        "is_published",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "title",
        "content",
        "category",
    )

    list_editable = ("is_published",)

    fieldsets = (
        (
            _("Informações Básicas"),
            {"fields": ("title", "category", "is_published")},
        ),
        (
            _("Conteúdo"),
            {"fields": ("content", "file"), "classes": ("collapse",)},
        ),
        (
            _("Rastreabilidade"),
            {
                "fields": (
                    "id",
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

    readonly_fields = tuple(BaseAdmin.readonly_fields) + ("file_link",)

    def file_link(self, obj):
        """Exibe link para download do arquivo."""
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank">📄 Download</a>', obj.file.url
            )
        return "—"

    file_link.short_description = _("Arquivo")

    def get_queryset(self, request):
        """Otimiza queries incluindo relacionamentos."""
        return (
            super()
            .get_queryset(request)
            .select_related("created_by", "updated_by")
        )


# =============================================================================
# ADMIN COM INLINES - CATEGORY
# =============================================================================


class CategoryInline(admin.TabularInline):
    """Inline para subcategorias."""

    model = models.Category
    fk_name = "parent"
    extra = 0
    fields = ("name", "description")


@admin.register(models.Category)
class CategoryAdmin(BaseAdmin):
    """Admin para categorias com suporte a hierarquia."""

    list_display = (
        "name",
        "parent",
        "children_count",
        "articles_count",
        "created_at",
    )

    list_filter = (
        "parent",
        "created_at",
    )

    search_fields = ("name", "description")

    inlines = [CategoryInline]

    fieldsets = (
        (
            _("Informações da Categoria"),
            {"fields": ("name", "description", "parent")},
        ),
        (
            _("Rastreabilidade"),
            {
                "fields": (
                    "id",
                    "created_at",
                    "created_by",
                    "updated_at",
                    "updated_by",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def children_count(self, obj):
        """Conta subcategorias."""
        count = obj.children.count()
        if count > 0:
            url = reverse("admin:core_category_changelist")
            return format_html(
                '<a href="{}?parent__id__exact={}">{} filho(s)</a>',
                url,
                obj.id,
                count,
            )
        return "0"

    children_count.short_description = _("Subcategorias")

    def articles_count(self, obj):
        """Conta artigos da categoria."""
        count = obj.articles.count()
        if count > 0:
            url = reverse("admin:core_article_changelist")
            return format_html(
                '<a href="{}?category__id__exact={}">{} artigo(s)</a>',
                url,
                obj.id,
                count,
            )
        return "0"

    articles_count.short_description = _("Artigos")

    def get_queryset(self, request):
        """Otimiza queries com contadores."""
        return (
            super()
            .get_queryset(request)
            .annotate(
                children_count=Count("children"),
                articles_count=Count("articles"),
            )
            .select_related("parent")
        )


# =============================================================================
# ADMIN SIMPLES - TAG
# =============================================================================


@admin.register(models.Tag)
class TagAdmin(BaseAdmin):
    """Admin simples para tags."""

    list_display = ("name", "color_preview", "articles_count", "created_at")
    list_filter = ("created_at",)
    search_fields = ("name",)

    fields = ("name", "color")

    def color_preview(self, obj):
        """Exibe preview da cor."""
        return format_html(
            '<div style="width: 20px; height: 20px; background-color: {}; '
            'border: 1px solid #ddd; border-radius: 3px;"></div>',
            obj.color,
        )

    color_preview.short_description = _("Cor")

    def articles_count(self, obj):
        """Conta artigos com esta tag."""
        return obj.articles.count()

    articles_count.short_description = _("Artigos")


# =============================================================================
# ADMIN COMPLEXO - ARTICLE
# =============================================================================


@admin.register(models.Article)
class ArticleAdmin(BaseAdmin):
    """Admin complexo para artigos com relacionamentos M2M."""

    list_display = (
        "title",
        "category",
        "status",
        "tags_list",
        "published_at",
        "created_at",
    )

    list_filter = (
        "status",
        "category",
        "tags",
        "published_at",
        "created_at",
    )

    search_fields = ("title", "content", "slug")

    list_editable = ("status",)

    prepopulated_fields = {"slug": ("title",)}

    filter_horizontal = ("tags",)

    fieldsets = (
        (_("Conteúdo"), {"fields": ("title", "slug", "content")}),
        (_("Classificação"), {"fields": ("category", "tags", "status")}),
        (
            _("Publicação"),
            {"fields": ("published_at",), "classes": ("collapse",)},
        ),
        (
            _("Rastreabilidade"),
            {
                "fields": (
                    "id",
                    "created_at",
                    "created_by",
                    "updated_at",
                    "updated_by",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    actions = ["mark_as_published", "mark_as_draft"]

    def tags_list(self, obj):
        """Exibe lista de tags coloridas."""
        tags = obj.tags.all()
        if not tags:
            return "—"

        tag_html = []
        for tag in tags:
            tag_html.append(
                f'<span style="background-color: {tag.color}; '
                f"color: white; padding: 2px 6px; border-radius: 3px; "
                f'font-size: 11px; margin-right: 3px;">{tag.name}</span>'
            )
        return mark_safe("".join(tag_html))

    tags_list.short_description = _("Tags")

    def mark_as_published(self, request, queryset):
        """Publica artigos selecionados."""
        from django.utils import timezone

        updated = queryset.update(
            status="PUBLISHED", published_at=timezone.now()
        )
        self.message_user(
            request, f"{updated} artigo(s) publicado(s) com sucesso."
        )

    mark_as_published.short_description = _("Marcar como publicado")

    def mark_as_draft(self, request, queryset):
        """Marca artigos como rascunho."""
        updated = queryset.update(status="DRAFT")
        self.message_user(
            request, f"{updated} artigo(s) marcado(s) como rascunho."
        )

    mark_as_draft.short_description = _("Marcar como rascunho")

    def get_queryset(self, request):
        """Otimiza queries."""
        return (
            super()
            .get_queryset(request)
            .select_related("category", "created_by")
            .prefetch_related("tags")
        )


# =============================================================================
# ADMIN SOMENTE LEITURA - EXEMPLO
# =============================================================================

# @admin.register(models.ReadOnlyModel)
# class ReadOnlyAdmin(BaseAdmin):
#     """Exemplo de admin somente leitura."""

#     list_display = ("name", "created_at", "created_by")
#     list_filter = ("created_at",)
#     search_fields = ("name",)

#     def has_add_permission(self, request):
#         """Remove permissão de adicionar."""
#         return False

#     def has_change_permission(self, request, obj=None):
#         """Permite apenas visualização."""
#         return request.user.is_superuser

#     def has_delete_permission(self, request, obj=None):
#         """Remove permissão de deletar."""
#         return False


# =============================================================================
# EXEMPLOS DE USO DO BASEADMIN
# =============================================================================

"""
## Como usar o BaseAdmin:

### 1. Admin básico:
```python
@admin.register(models.MyModel)
class MyModelAdmin(BaseAdmin):
    list_display = ("name", "created_at", "created_by")
    list_filter = ("created_at", "is_active")
    search_fields = ("name",)
```

### 2. Campos readonly automáticos:
```python
# BaseAdmin já inclui estes campos como readonly:
readonly_fields = (
    "id", "created_at", "created_by",
    "updated_at", "updated_by",
    "deleted_at", "deleted_by"
)
```

### 3. Fieldsets organizados:
```python
fieldsets = (
    (_("Dados Principais"), {
        "fields": ("name", "description")
    }),
    (_("Rastreabilidade"), {
        "fields": BaseAdmin.readonly_fields,
        "classes": ("collapse",)
    }),
)
```

### 4. Métodos customizados para display:
```python
def custom_field(self, obj):
    return format_html('<strong>{}</strong>', obj.name)
custom_field.short_description = _("Nome Formatado")
```

### 5. Actions customizadas:
```python
def custom_action(self, request, queryset):
    # Lógica da action
    updated = queryset.update(status="ACTIVE")
    self.message_user(request, f"{updated} items atualizados.")
custom_action.short_description = _("Ativar itens")

actions = ["custom_action"]
```

### 6. Permissões customizadas:
```python
def has_add_permission(self, request):
    return request.user.is_superuser

def has_change_permission(self, request, obj=None):
    return request.user.is_staff

def has_delete_permission(self, request, obj=None):
    return False  # Bloqueia delete
```

### 7. Otimização de queries:
```python
def get_queryset(self, request):
    return super().get_queryset(request).select_related(
        "category", "created_by"
    ).prefetch_related("tags")
```

### 8. Inlines para relacionamentos:
```python
class RelatedInline(admin.TabularInline):
    model = RelatedModel
    extra = 1

class MainAdmin(BaseAdmin):
    inlines = [RelatedInline]
```

### 9. Filtros horizontais para M2M:
```python
filter_horizontal = ("tags", "categories")
```

### 10. Prepopulated fields:
```python
prepopulated_fields = {"slug": ("title",)}
```

"""
