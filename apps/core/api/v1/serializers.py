"""Serializers para a aplicação Core usando Django REST Framework.

Este módulo contém os serializers para conversão de dados entre modelos Django
e representações JSON/API. Todos os serializers devem herdar do BaseSerializer
para ter funcionalidades como conversão automática de PKs para UUIDs,
campos readonly automáticos e validações consistentes.
"""

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.commons.api.v1.serializers import BaseSerializer
from apps.core import models


# =============================================================================
# SERIALIZER BÁSICO - DOCUMENT
# =============================================================================


class DocumentSerializer(BaseSerializer):
    """Serializer para visualização completa de documentos.

    Herda todas as funcionalidades do BaseSerializer:
    - Conversão automática de PKs para UUIDs
    - Campos readonly automáticos (created_at, updated_at, etc.)
    - Remove campo pkid da serialização
    - Validações automáticas do model
    """

    class Meta(BaseSerializer.Meta):
        """Configurações do serializer Document."""

        model = models.Document
        fields = "__all__"
        # BaseSerializer já adiciona automaticamente campos readonly:
        # read_only_fields = ["created_at", "updated_at", "deleted_at",
        #                     "created_by", "updated_by", "deleted_by",
        #                     "is_active"]

    def to_representation(self, instance):
        """Customiza a representação dos dados de saída."""
        representation = super().to_representation(instance)

        # Adiciona informações extras
        representation["file_size"] = None
        if instance.file:
            try:
                representation["file_size"] = instance.file.size
                representation["file_name"] = instance.file.name.split("/")[-1]
            except (AttributeError, ValueError):
                pass

        # Formatar categoria para display
        if instance.category:
            category_field = models.Document._meta.get_field("category")
            category_choices = dict(category_field.choices)
            representation["category_display"] = category_choices.get(
                instance.category, instance.category
            )

        return representation


class DocumentCreateSerializer(BaseSerializer):
    """Serializer para criação de documentos com validações específicas."""

    class Meta(BaseSerializer.Meta):
        """Configurações do serializer de criação."""

        model = models.Document
        fields = ["title", "content", "file", "category", "is_published"]

    def validate_title(self, value):
        """Valida o título do documento."""
        if len(value.strip()) < 3:
            raise ValidationError(
                _("O título deve ter pelo menos 3 caracteres.")
            )

        # Verifica se já existe documento com mesmo título
        if models.Document.objects.filter(
            title__iexact=value.strip(), is_active=True
        ).exists():
            raise ValidationError(_("Já existe um documento com este título."))

        return value.strip().title()

    def validate(self, attrs):
        """Validações que envolvem múltiplos campos."""
        # Deve ter conteúdo OU arquivo
        if not attrs.get("content") and not attrs.get("file"):
            raise ValidationError(
                {
                    "content": _(
                        "Documento deve ter conteúdo ou arquivo anexo."
                    ),
                    "file": _("Documento deve ter conteúdo ou arquivo anexo."),
                }
            )

        # Se for publicado, deve ter título e conteúdo
        if attrs.get("is_published", False):
            if not attrs.get("content"):
                raise ValidationError(
                    {"content": _("Documentos publicados devem ter conteúdo.")}
                )

        return attrs


class DocumentUpdateSerializer(BaseSerializer):
    """Serializer para atualização de documentos."""

    class Meta(BaseSerializer.Meta):
        """Configurações do serializer de atualização."""

        model = models.Document
        fields = ["title", "content", "file", "category", "is_published"]

    def validate_title(self, value):
        """Valida título na atualização (exclui instância atual)."""
        if len(value.strip()) < 3:
            raise ValidationError(
                _("O título deve ter pelo menos 3 caracteres.")
            )

        # Verifica duplicatas excluindo a instância atual
        existing = models.Document.objects.filter(
            title__iexact=value.strip(), is_active=True
        )

        if self.instance:
            existing = existing.exclude(id=self.instance.id)

        if existing.exists():
            raise ValidationError(_("Já existe um documento com este título."))

        return value.strip().title()


# =============================================================================
# SERIALIZER COM RELACIONAMENTOS - CATEGORY
# =============================================================================


class CategorySerializer(BaseSerializer):
    """Serializer para categorias com suporte a hierarquia."""

    # Campos customizados para relacionamentos
    parent_name = serializers.CharField(
        source="parent.name",
        read_only=True,
        help_text=_("Nome da categoria pai"),
    )

    children_count = serializers.SerializerMethodField(
        help_text=_("Número de subcategorias")
    )

    articles_count = serializers.SerializerMethodField(
        help_text=_("Número de artigos na categoria")
    )

    class Meta(BaseSerializer.Meta):
        """Configurações do serializer Category."""

        model = models.Category
        fields = "__all__"

    def get_children_count(self, obj):
        """Retorna número de subcategorias."""
        return obj.children.count()

    def get_articles_count(self, obj):
        """Retorna número de artigos da categoria."""
        return obj.articles.count()

    def validate_parent(self, value):
        """Valida categoria pai para evitar loops."""
        if value == self.instance:
            raise ValidationError(
                _("Uma categoria não pode ser pai de si mesma.")
            )

        # Verifica se não cria loop na hierarquia
        current = value
        while current and current.parent:
            if current.parent == self.instance:
                raise ValidationError(
                    _("Esta operação criaria um loop na hierarquia.")
                )
            current = current.parent

        return value


class CategoryTreeSerializer(BaseSerializer):
    """Serializer para estrutura hierárquica de categorias."""

    children = serializers.SerializerMethodField()

    class Meta(BaseSerializer.Meta):
        """Configurações do serializer de árvore."""

        model = models.Category
        fields = ["id", "name", "description", "children"]

    def get_children(self, obj):
        """Retorna subcategorias recursivamente."""
        children = obj.children.all()
        return CategoryTreeSerializer(children, many=True).data


# =============================================================================
# SERIALIZER SIMPLES - TAG
# =============================================================================


class TagSerializer(BaseSerializer):
    """Serializer simples para tags."""

    articles_count = serializers.SerializerMethodField()

    class Meta(BaseSerializer.Meta):
        """Configurações do serializer Tag."""

        model = models.Tag
        fields = "__all__"

    def get_articles_count(self, obj):
        """Retorna número de artigos com esta tag."""
        return obj.articles.count()

    def validate_name(self, value):
        """Valida nome da tag."""
        value = value.strip().lower()

        if len(value) < 2:
            raise ValidationError(
                _("Nome da tag deve ter pelo menos 2 caracteres.")
            )

        # Verifica duplicatas
        existing = models.Tag.objects.filter(
            name__iexact=value, is_active=True
        )
        if self.instance:
            existing = existing.exclude(id=self.instance.id)

        if existing.exists():
            raise ValidationError(_("Já existe uma tag com este nome."))

        return value

    def validate_color(self, value):
        """Valida formato da cor hexadecimal."""
        import re

        if not re.match(r"^#[0-9A-Fa-f]{6}$", value):
            raise ValidationError(
                _("Cor deve estar no formato hexadecimal (#RRGGBB).")
            )

        return value.upper()


# =============================================================================
# SERIALIZER COMPLEXO - ARTICLE
# =============================================================================


class ArticleSerializer(BaseSerializer):
    """Serializer para artigos com relacionamentos M2M."""

    # Relacionamentos expandidos
    category_name = serializers.CharField(
        source="category.name", read_only=True
    )

    tags_detail = TagSerializer(source="tags", many=True, read_only=True)

    # Campos computados
    word_count = serializers.SerializerMethodField()
    reading_time = serializers.SerializerMethodField()

    class Meta(BaseSerializer.Meta):
        """Configurações do serializer Article."""

        model = models.Article
        fields = "__all__"

    def get_word_count(self, obj):
        """Calcula número de palavras do conteúdo."""
        if obj.content:
            return len(obj.content.split())
        return 0

    def get_reading_time(self, obj):
        """Estima tempo de leitura (250 palavras/minuto)."""
        word_count = self.get_word_count(obj)
        minutes = max(1, round(word_count / 250))
        return f"{minutes} min"

    def validate_slug(self, value):
        """Valida slug único."""
        import re

        # Formato do slug
        if not re.match(r"^[a-z0-9-]+$", value):
            raise ValidationError(
                _(
                    "Slug deve conter apenas letras minúsculas, números e "
                    "hífens."
                )
            )

        # Verifica duplicatas
        existing = models.Article.objects.filter(slug=value, is_active=True)
        if self.instance:
            existing = existing.exclude(id=self.instance.id)

        if existing.exists():
            raise ValidationError(_("Já existe um artigo com este slug."))

        return value

    def validate(self, attrs):
        """Validações complexas do artigo."""
        # Se status for PUBLISHED, deve ter published_at
        if attrs.get("status") == "PUBLISHED":
            if not attrs.get("published_at"):
                from django.utils import timezone

                attrs["published_at"] = timezone.now()

        # Se não for PUBLISHED, limpa published_at
        elif attrs.get("status") in ["DRAFT", "ARCHIVED"]:
            attrs["published_at"] = None

        return attrs


class ArticleCreateSerializer(BaseSerializer):
    """Serializer para criação de artigos."""

    class Meta(BaseSerializer.Meta):
        """Configurações do serializer de criação."""

        model = models.Article
        fields = ["title", "slug", "content", "category", "tags", "status"]

    def validate(self, attrs):
        """Gera slug automaticamente se não fornecido."""
        if not attrs.get("slug") and attrs.get("title"):
            from django.utils.text import slugify

            attrs["slug"] = slugify(attrs["title"])

        return super().validate(attrs)


# =============================================================================
# SERIALIZERS ANINHADOS - EXEMPLO
# =============================================================================


class DocumentWithCategorySerializer(BaseSerializer):
    """Serializer de documento com categoria expandida."""

    category = CategorySerializer(read_only=True)

    class Meta(BaseSerializer.Meta):
        """Configurações do serializer aninhado."""

        model = models.Document
        fields = "__all__"


class CategoryWithDocumentsSerializer(BaseSerializer):
    """Serializer de categoria com documentos relacionados."""

    # Relacionamento reverso
    documents = DocumentSerializer(
        source="document_set", many=True, read_only=True
    )

    class Meta(BaseSerializer.Meta):
        """Configurações do serializer com relacionamentos."""

        model = models.Category
        fields = "__all__"


# =============================================================================
# SERIALIZERS PARA AÇÕES ESPECÍFICAS
# =============================================================================


class DocumentPublishSerializer(serializers.Serializer):
    """Serializer para action de publicação de documento."""

    confirm = serializers.BooleanField(
        default=False, help_text=_("Confirma a publicação do documento")
    )

    def validate_confirm(self, value):
        """Valida confirmação."""
        if not value:
            raise ValidationError(_("É necessário confirmar a publicação."))
        return value


class TagBulkCreateSerializer(serializers.Serializer):
    """Serializer para criação em lote de tags."""

    names = serializers.ListField(
        child=serializers.CharField(max_length=50),
        min_length=1,
        max_length=10,
        help_text=_("Lista de nomes de tags a serem criadas"),
    )

    color = serializers.CharField(
        max_length=7,
        default="#007bff",
        help_text=_("Cor padrão para todas as tags"),
    )

    def validate_names(self, value):
        """Valida lista de nomes."""
        cleaned_names = []

        for name in value:
            name = name.strip().lower()
            if len(name) < 2:
                raise ValidationError(
                    _("Todos os nomes devem ter pelo menos 2 caracteres.")
                )

            if name in cleaned_names:
                raise ValidationError(
                    _("Nomes duplicados na lista: {}").format(name)
                )

            # Verifica se já existe
            if models.Tag.objects.filter(
                name__iexact=name, is_active=True
            ).exists():
                raise ValidationError(_("Tag já existe: {}").format(name))

            cleaned_names.append(name)

        return cleaned_names


# =============================================================================
# EXEMPLOS DE USO DO BASESERIALIZER
# =============================================================================

"""
## Como usar o BaseSerializer:

### 1. Serializer básico:
```python
class MyModelSerializer(BaseSerializer):
    class Meta(BaseSerializer.Meta):
        model = models.MyModel
        fields = "__all__"
```

### 2. Campos readonly automáticos:
```python
# BaseSerializer já adiciona automaticamente:
read_only_fields = [
    "created_at", "updated_at", "deleted_at",
    "created_by", "updated_by", "deleted_by",
    "is_active"
]
```

### 3. Conversão automática de PKs:
```python
# PKs são automaticamente convertidas para UUIDs na saída
# Campo 'pkid' é removido automaticamente
# PrimaryKeyRelatedFields usam UUIDs
```

### 4. Campos customizados:
```python
class MySerializer(BaseSerializer):
    # Campo computado
    full_name = serializers.SerializerMethodField()

    # Relacionamento expandido
    category_name = serializers.CharField(
        source="category.name",
        read_only=True
    )

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
```

### 5. Validações customizadas:
```python
def validate_field_name(self, value):
    if not value:
        raise ValidationError("Campo obrigatório")
    return value.strip()

def validate(self, attrs):
    # Validações entre campos
    if attrs.get("start_date") > attrs.get("end_date"):
        raise ValidationError("Data inicial > data final")
    return attrs
```

### 6. to_representation customizado:
```python
def to_representation(self, instance):
    representation = super().to_representation(instance)

    # Adicionar campos extras
    representation["extra_field"] = "extra_value"

    # Modificar campos existentes
    if instance.status == "ACTIVE":
        representation["status_display"] = "Ativo"

    return representation
```

### 7. Serializers aninhados:
```python
class ParentSerializer(BaseSerializer):
    children = ChildSerializer(many=True, read_only=True)

    class Meta(BaseSerializer.Meta):
        model = models.Parent
        fields = "__all__"
```

### 8. Serializers para ações específicas:
```python
class ActionSerializer(serializers.Serializer):
    param1 = serializers.CharField()
    param2 = serializers.IntegerField()

    def validate_param1(self, value):
        return value.strip()
```

### 9. Campos de relacionamento:
```python
# ForeignKey - automaticamente usa UUID
category = serializers.PrimaryKeyRelatedField(
    queryset=Category.objects.all()
)

# ManyToMany - automaticamente usa UUIDs
tags = serializers.PrimaryKeyRelatedField(
    many=True,
    queryset=Tag.objects.all()
)
```

### 10. Performance com select_related:
```python
# No ViewSet, otimize queries:
def get_queryset(self):
    return super().get_queryset().select_related(
        "category", "created_by"
    ).prefetch_related("tags")
```

"""
