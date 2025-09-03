"""Models da aplicação Core.

Este módulo contém os models principais da aplicação Core.
Todos os models devem herdar do BaseModel para ter funcionalidades
como soft delete, timestamps automáticos e rastreabilidade.
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.db.models import Q

from apps.commons.models import BaseModel


# =============================================================================
# EXEMPLO DE MODEL BÁSICO
# =============================================================================


class Document(BaseModel):
    """Model para documentos do sistema.

    Herda todas as funcionalidades do BaseModel:
    - pkid: Chave primária auto-incremento
    - id: UUID único para identificação
    - created_at/updated_at: Timestamps automáticos
    - created_by/updated_by/deleted_by: Rastreabilidade de usuários
    - is_active: Para soft delete
    - objects/all_objects: Managers customizados
    """

    class Meta(BaseModel.Meta):
        """Configurações do modelo Document."""

        verbose_name = _("Documento")
        verbose_name_plural = _("Documentos")
        ordering = ["-created_at"]
        # Para campos únicos com soft delete, use constraints:
        constraints = [
            models.UniqueConstraint(
                fields=["title"],
                condition=Q(is_active=True),
                name="unique_active_document_title",
            )
        ]

    title = models.CharField(
        _("Título"), max_length=255, help_text=_("Título do documento")
    )

    content = models.TextField(
        _("Conteúdo"),
        blank=True,
        null=True,
        help_text=_("Conteúdo do documento"),
    )

    file = models.FileField(
        _("Arquivo"),
        upload_to="documents/%Y/%m/",
        blank=True,
        null=True,
        help_text=_("Arquivo anexo do documento"),
    )

    category = models.CharField(
        _("Categoria"),
        max_length=50,
        choices=[
            ("POLICY", _("Política")),
            ("PROCEDURE", _("Procedimento")),
            ("MANUAL", _("Manual")),
            ("OTHER", _("Outro")),
        ],
        default="OTHER",
    )

    is_published = models.BooleanField(
        _("Publicado"),
        default=False,
        help_text=_("Define se o documento está publicado"),
    )

    def clean(self):
        """Validações customizadas do model."""
        super().clean()

        if self.title and len(self.title) < 3:
            raise ValidationError(
                {"title": _("O título deve ter pelo menos 3 caracteres.")}
            )

    def __str__(self):
        """Representação string do documento."""
        return f"{self.title} (#{self.pkid})"

    def save(self, *args, **kwargs):
        """Override do save para lógicas customizadas."""
        # Executa validações
        self.full_clean()

        # Lógica customizada antes do save
        if not self.content and not self.file:
            self.content = _("Documento sem conteúdo definido.")

        super().save(*args, **kwargs)


# =============================================================================
# EXEMPLO DE MODEL COM RELACIONAMENTOS
# =============================================================================


class Category(BaseModel):
    """Model para categorias."""

    class Meta(BaseModel.Meta):
        """Configurações do modelo Category."""

        verbose_name = _("Categoria")
        verbose_name_plural = _("Categorias")
        ordering = ["name"]

    name = models.CharField(_("Nome"), max_length=100, unique=True)

    description = models.TextField(_("Descrição"), blank=True, null=True)

    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="children",
        verbose_name=_("Categoria pai"),
    )

    def __str__(self):
        """Representação string da categoria."""
        return self.name


class Tag(BaseModel):
    """Model para tags/etiquetas."""

    class Meta(BaseModel.Meta):
        """Configurações do modelo Tag."""

        verbose_name = _("Tag")
        verbose_name_plural = _("Tags")
        ordering = ["name"]

    name = models.CharField(_("Nome"), max_length=50, unique=True)

    color = models.CharField(
        _("Cor"),
        max_length=7,
        default="#007bff",
        help_text=_("Cor em hexadecimal (ex: #007bff)"),
    )

    def __str__(self):
        """Representação string da tag."""
        return self.name


class Article(BaseModel):
    """Model para artigos com relacionamentosMany-to-Many."""

    class Meta(BaseModel.Meta):
        """Configurações do modelo Article."""

        verbose_name = _("Artigo")
        verbose_name_plural = _("Artigos")
        ordering = ["-created_at"]

    title = models.CharField(_("Título"), max_length=255)
    slug = models.SlugField(_("Slug"), max_length=255, unique=True)
    content = models.TextField(_("Conteúdo"))

    # Relacionamentos
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="articles",
        verbose_name=_("Categoria"),
    )

    tags = models.ManyToManyField(
        Tag, blank=True, related_name="articles", verbose_name=_("Tags")
    )

    # Status
    STATUS_CHOICES = [
        ("DRAFT", _("Rascunho")),
        ("PUBLISHED", _("Publicado")),
        ("ARCHIVED", _("Arquivado")),
    ]

    status = models.CharField(
        _("Status"), max_length=20, choices=STATUS_CHOICES, default="DRAFT"
    )

    published_at = models.DateTimeField(
        _("Publicado em"), blank=True, null=True
    )

    def __str__(self):
        """Representação string do artigo."""
        return self.title


# =============================================================================
# EXEMPLOS DE USO DO BASEMODEL
# =============================================================================

"""
## Como usar o BaseModel:

### 1. Criação básica:
```python
# Criar um novo documento
doc = Document.objects.create(
    title="Meu Documento",
    content="Conteúdo do documento",
    created_by=request.user  # Automaticamente rastreado
)

# Acessar campos do BaseModel
print(doc.id)           # UUID único
print(doc.pkid)         # ID auto-incremento
print(doc.created_at)   # Data de criação
print(doc.is_active)    # True por padrão
```

### 2. Soft Delete:
```python
# Soft delete (marca como inativo)
doc.delete(deleted_by=request.user)
print(doc.is_active)  # False

# Hard delete (remove do banco)
doc.hard_delete()
```

### 3. Managers customizados:
```python
# Apenas objetos ativos (padrão)
active_docs = Document.objects.all()

# Todos os objetos (incluindo inativos)
all_docs = Document.all_objects.all()

# Filtros customizados
active_only = Document.objects.active()
inactive_only = Document.objects.inactive()
```

### 4. Constraints para campos únicos:
```python
# No Meta do model:
constraints = [
    models.UniqueConstraint(
        fields=["field_name"],
        condition=Q(is_active=True),
        name="unique_active_field"
    )
]
```

### 5. Relacionamentos:
```python
# ForeignKey
category = Category.objects.create(name="Tecnologia")
article = Article.objects.create(
    title="Meu Artigo",
    category=category,
    created_by=request.user
)

# ManyToMany
tag1 = Tag.objects.create(name="Python")
tag2 = Tag.objects.create(name="Django")
article.tags.add(tag1, tag2)
```

### 6. Validações customizadas:
```python
# Override do método clean()
def clean(self):
    super().clean()
    if self.custom_validation_logic():
        raise ValidationError("Mensagem de erro")
```

### 7. Admin Integration:
```python
# No admin.py, use BaseAdmin:
from apps.commons.admin import BaseAdmin

@admin.register(Document)
class DocumentAdmin(BaseAdmin):
    list_display = ('title', 'category', 'is_published', 'created_at')
    list_filter = ('category', 'is_published')
    search_fields = ('title', 'content')
```

"""
