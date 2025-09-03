"""API ViewSets para a aplicação Core usando Django REST Framework.

Este módulo contém os ViewSets para gerenciamento de APIs da aplicação Core.
Todos os ViewSets devem herdar do BaseModelApiViewSet para ter funcionalidades
como CRUD completo, permissões, logging automático e rastreabilidade.
"""

import logging
from django.db.models import Q, Count
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions
from rest_framework.response import Response

from apps.commons.api.v1.viewsets import (
    BaseModelApiViewSet,
    BaseReadOnlyModelViewSet,
)
from apps.core.api.v1 import serializers
from apps.core import models


logger = logging.getLogger("django")


# =============================================================================
# VIEWSET COMPLETO - DOCUMENT
# =============================================================================


class DocumentViewSet(BaseModelApiViewSet):
    """ViewSet completo para gerenciamento de documentos.

    Herda todas as funcionalidades do BaseModelApiViewSet:
    - create() - POST /documents/
    - list() - GET /documents/
    - retrieve() - GET /documents/{id}/
    - update() - PUT /documents/{id}/
    - partial_update() - PATCH /documents/{id}/
    - destroy() - DELETE /documents/{id}/ (soft delete)

    Funcionalidades automáticas:
    - Rastreabilidade (created_by, updated_by, deleted_by)
    - Logging de operações
    - Permissões Django (DjangoModelPermissions)
    - Autenticação obrigatória
    - Soft delete automático
    - Serializer automático baseado no model
    """

    model = models.Document

    def get_serializer_class(self):
        """Retorna serializer específico baseado na ação."""
        if self.action == "create":
            return serializers.DocumentCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return serializers.DocumentUpdateSerializer
        return serializers.DocumentSerializer

    def get_queryset(self):
        """Customiza queryset com otimizações e filtros."""
        queryset = super().get_queryset()

        # Otimização de queries
        queryset = queryset.select_related("created_by", "updated_by")

        # Filtros via query params
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category=category)

        published_only = self.request.query_params.get("published_only")
        if published_only == "true":
            queryset = queryset.filter(is_published=True)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(content__icontains=search)
            )

        return queryset.order_by("-created_at")

    @action(
        methods=["post"],
        detail=True,
        url_path="publish",
        permission_classes=[IsAuthenticated, DjangoModelPermissions],
    )
    def publish_document(self, request, id=None):
        """Publica um documento específico."""
        document = self.get_object()

        if document.is_published:
            return Response(
                {"error": _("Documento já está publicado.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        document.is_published = True
        document.updated_by = request.user
        document.save()

        return Response(
            {"message": _("Documento publicado com sucesso.")},
            status=status.HTTP_200_OK,
        )

    @action(
        methods=["get"],
        detail=False,
        url_path="published",
        permission_classes=[IsAuthenticated],
    )
    def list_published(self, request):
        """Lista apenas documentos publicados."""
        queryset = self.get_queryset().filter(is_published=True)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(
        methods=["get"],
        detail=False,
        url_path="categories",
        permission_classes=[IsAuthenticated],
    )
    def list_categories(self, request):
        """Lista categorias disponíveis com contadores."""
        categories = (
            models.Document.objects.values("category")
            .annotate(count=Count("id"))
            .order_by("category")
        )

        return Response(
            {
                "categories": [
                    {
                        "name": cat["category"],
                        "count": cat["count"],
                    }
                    for cat in categories
                ]
            }
        )


# =============================================================================
# VIEWSET COM HIERARQUIA - CATEGORY
# =============================================================================


class CategoryViewSet(BaseModelApiViewSet):
    """ViewSet para gerenciamento de categorias com suporte a hierarquia."""

    model = models.Category

    def get_queryset(self):
        """Otimiza queries e permite filtros hierárquicos."""
        queryset = super().get_queryset()

        # Otimização para relacionamentos
        queryset = queryset.select_related("parent").prefetch_related(
            "children"
        )

        # Filtro por categoria pai
        parent_id = self.request.query_params.get("parent")
        if parent_id:
            if parent_id == "null":
                queryset = queryset.filter(parent__isnull=True)
            else:
                queryset = queryset.filter(parent__id=parent_id)

        return queryset.order_by("name")

    @action(
        methods=["get"],
        detail=True,
        url_path="children",
        permission_classes=[IsAuthenticated],
    )
    def list_children(self, request, id=None):
        """Lista subcategorias de uma categoria."""
        parent_category = self.get_object()
        children = parent_category.children.all()

        serializer = self.get_serializer(children, many=True)
        return Response(serializer.data)

    @action(
        methods=["get"],
        detail=False,
        url_path="tree",
        permission_classes=[IsAuthenticated],
    )
    def category_tree(self, request):
        """Retorna árvore hierárquica de categorias."""
        root_categories = self.get_queryset().filter(parent__isnull=True)

        def build_tree(categories):
            tree = []
            for category in categories:
                children = category.children.all()
                tree.append(
                    {
                        "id": category.id,
                        "name": category.name,
                        "description": category.description,
                        "children": build_tree(children) if children else [],
                    }
                )
            return tree

        return Response({"tree": build_tree(root_categories)})


# =============================================================================
# VIEWSET SIMPLES - TAG
# =============================================================================


class TagViewSet(BaseModelApiViewSet):
    """ViewSet simples para gerenciamento de tags."""

    model = models.Tag

    def get_queryset(self):
        """Permite busca por nome."""
        queryset = super().get_queryset()

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(name__icontains=search)

        return queryset.order_by("name")

    @action(
        methods=["get"],
        detail=False,
        url_path="popular",
        permission_classes=[IsAuthenticated],
    )
    def popular_tags(self, request):
        """Lista tags mais utilizadas."""
        tags = (
            models.Tag.objects.annotate(usage_count=Count("articles"))
            .filter(usage_count__gt=0)
            .order_by("-usage_count")[:10]
        )

        serializer = self.get_serializer(tags, many=True)
        return Response(serializer.data)


# =============================================================================
# VIEWSET COMPLEXO - ARTICLE
# =============================================================================


class ArticleViewSet(BaseModelApiViewSet):
    """ViewSet complexo para artigos com relacionamentos M2M."""

    model = models.Article

    def get_queryset(self):
        """Queryset otimizado com múltiplos filtros."""
        queryset = super().get_queryset()

        # Otimizações
        queryset = queryset.select_related(
            "category", "created_by", "updated_by"
        ).prefetch_related("tags")

        # Filtros
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category__id=category)

        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        tags = self.request.query_params.get("tags")
        if tags:
            tag_ids = tags.split(",")
            queryset = queryset.filter(tags__id__in=tag_ids).distinct()

        return queryset.order_by("-created_at")

    @action(
        methods=["post"],
        detail=True,
        url_path="add-tags",
        permission_classes=[IsAuthenticated, DjangoModelPermissions],
    )
    def add_tags(self, request, id=None):
        """Adiciona tags a um artigo."""
        article = self.get_object()
        tag_ids = request.data.get("tag_ids", [])

        if not tag_ids:
            return Response(
                {"error": _("Lista de tags é obrigatória.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tags = models.Tag.objects.filter(id__in=tag_ids)
        article.tags.add(*tags)

        return Response(
            {"message": _("Tags adicionadas com sucesso.")},
            status=status.HTTP_200_OK,
        )

    @action(
        methods=["delete"],
        detail=True,
        url_path="remove-tags",
        permission_classes=[IsAuthenticated, DjangoModelPermissions],
    )
    def remove_tags(self, request, id=None):
        """Remove tags de um artigo."""
        article = self.get_object()
        tag_ids = request.data.get("tag_ids", [])

        if not tag_ids:
            return Response(
                {"error": _("Lista de tags é obrigatória.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tags = models.Tag.objects.filter(id__in=tag_ids)
        article.tags.remove(*tags)

        return Response(
            {"message": _("Tags removidas com sucesso.")},
            status=status.HTTP_200_OK,
        )


# =============================================================================
# VIEWSET SOMENTE LEITURA - EXEMPLO
# =============================================================================


class ReadOnlyDocumentViewSet(BaseReadOnlyModelViewSet):
    """Exemplo de ViewSet somente leitura.

    Herda do BaseReadOnlyModelViewSet que fornece apenas:
    - list() - GET /readonly-documents/
    - retrieve() - GET /readonly-documents/{id}/

    Útil para APIs públicas ou recursos que não devem ser modificados.
    """

    model = models.Document
    permission_classes = [
        IsAuthenticated
    ]  # Apenas autenticação, sem DjangoModelPermissions

    def get_queryset(self):
        """Retorna apenas documentos publicados."""
        return super().get_queryset().filter(is_published=True)


# =============================================================================
# VIEWSET CUSTOMIZADO - EXEMPLO
# =============================================================================

# class CustomDocumentViewSet(BaseModelApiViewSet):
#     """Exemplo de ViewSet com customizações avançadas."""

#     model = models.Document

#     def get_permissions(self):
#         """Permissões customizadas por ação."""
#         if self.action in ["list", "retrieve"]:
#             permission_classes = [IsAuthenticated]
#         else:
#             permission_classes = [IsAuthenticated, DjangoModelPermissions]

#         return [permission() for permission in permission_classes]

#     def perform_create(self, serializer):
#         """Lógica customizada na criação."""
#         # Lógica antes do save
#         instance = serializer.save()
#         # Lógica após o save
#         logger.info(f"Documento criado: {instance.title}")

#     def perform_update(self, serializer):
#         """Lógica customizada na atualização."""
#         old_title = self.get_object().title
#         instance = serializer.save()
#         logger.info(f"Documento atualizado: {old_title} -> {instance.title}")

#     def perform_destroy(self, instance):
#         """Lógica customizada na exclusão (soft delete)."""
#         logger.warning(f"Documento deletado: {instance.title}")
#         super().perform_destroy(instance)


# =============================================================================
# EXEMPLOS DE USO DO BASEMODELAPIVIEWSET
# =============================================================================

"""
## Como usar o BaseModelApiViewSet:

### 1. ViewSet básico:
```python
class MyModelViewSet(BaseModelApiViewSet):
    model = models.MyModel
    # Automaticamente fornece CRUD completo
```

### 2. Permissões automáticas:
```python
# BaseModelApiViewSet inclui por padrão:
permission_classes = [IsAuthenticated, DjangoModelPermissions]
# - IsAuthenticated: Usuário deve estar logado
# - DjangoModelPermissions: Verifica permissões do Django
```

### 3. Serializer automático:
```python
# Automaticamente busca por:
# apps.myapp.api.v1.serializers.MyModelSerializer
# Se não encontrar, usa BaseSerializer

def get_serializer_class(self):
    if self.action == "create":
        return MyModelCreateSerializer
    return MyModelSerializer
```

### 4. Actions customizadas:
```python
@action(methods=["post"], detail=True, url_path="custom-action")
def custom_action(self, request, id=None):
    instance = self.get_object()
    # Lógica customizada
    return Response({"message": "Success"})
```

### 5. Filtros via query params:
```python
def get_queryset(self):
    queryset = super().get_queryset()

    # Filtros automáticos via BaseListApiViewSet
    # ?field_name=value
    # ?field_name__icontains=search
    # ?field_name__gte=date

    # Filtros customizados
    search = self.request.query_params.get("search")
    if search:
        queryset = queryset.filter(name__icontains=search)

    return queryset
```

### 6. Otimização de queries:
```python
def get_queryset(self):
    return super().get_queryset().select_related(
        "category", "created_by"
    ).prefetch_related("tags")
```

### 7. Funcionalidades automáticas:
```python
# Logging automático de operações (LoggingMethodMixin)
# Rastreabilidade automática:
# - created_by no create
# - updated_by no update
# - deleted_by no destroy

# Soft delete automático:
# DELETE /model/{id}/ -> marca is_active=False

# Filtros automáticos:
# Lista apenas objetos com is_active=True
```

### 8. Customização de perform_*:
```python
def perform_create(self, serializer):
    # Lógica antes do save
    serializer.save()
    # Lógica após o save

def perform_update(self, serializer):
    serializer.save()

def perform_destroy(self, instance):
    # Soft delete com rastreabilidade
    super().perform_destroy(instance)
```

### 9. ViewSet somente leitura:
```python
class ReadOnlyViewSet(BaseReadOnlyModelViewSet):
    model = models.MyModel
    # Apenas list() e retrieve()
```

### 10. URLs automáticas:
```python
# No router.py:
router.register(r"documents", DocumentViewSet, "document")

# Gera automaticamente:
# GET /documents/ - list
# POST /documents/ - create
# GET /documents/{id}/ - retrieve
# PUT /documents/{id}/ - update
# PATCH /documents/{id}/ - partial_update
# DELETE /documents/{id}/ - destroy
# + URLs customizadas das @actions
```

"""
