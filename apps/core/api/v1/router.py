"""Configuração de rotas da API para a aplicação Core.

Este módulo configura todas as rotas da API REST usando Django REST Framework.
O DefaultRouter gera automaticamente URLs para operações CRUD e actions
customizadas dos ViewSets, seguindo padrões RESTful.
"""

from rest_framework.routers import DefaultRouter

from apps.core.api.v1 import viewsets


# =============================================================================
# CONFIGURAÇÃO DO ROUTER PRINCIPAL
# =============================================================================

core_router = DefaultRouter()

# Configuração de trailing slash (opcional)
# core_router.trailing_slash = '/?'  # Permite URLs com ou sem barra final


# =============================================================================
# REGISTRO DE VIEWSETS - RECURSOS PRINCIPAIS
# =============================================================================

# Documents - CRUD completo + actions customizadas
core_router.register(
    r"documents", viewsets.DocumentViewSet, basename="document"
)
# URLs geradas:
# GET    /api/v1/core/documents/           - Listar documentos
# POST   /api/v1/core/documents/           - Criar documento
# GET    /api/v1/core/documents/{id}/      - Buscar documento específico
# PUT    /api/v1/core/documents/{id}/      - Atualizar documento completo
# PATCH  /api/v1/core/documents/{id}/      - Atualizar documento parcial
# DELETE /api/v1/core/documents/{id}/      - Soft delete documento
# POST   /api/v1/core/documents/{id}/publish/ - Action customizada
# GET    /api/v1/core/documents/published/    - Action customizada
# GET    /api/v1/core/documents/categories/   - Action customizada

# Categories - Hierarquia e relacionamentos
core_router.register(
    r"categories", viewsets.CategoryViewSet, basename="category"
)
# URLs geradas:
# GET    /api/v1/core/categories/           - Listar categorias
# POST   /api/v1/core/categories/           - Criar categoria
# GET    /api/v1/core/categories/{id}/      - Buscar categoria específica
# PUT    /api/v1/core/categories/{id}/      - Atualizar categoria
# PATCH  /api/v1/core/categories/{id}/      - Atualizar categoria parcial
# DELETE /api/v1/core/categories/{id}/      - Soft delete categoria
# GET    /api/v1/core/categories/{id}/children/ - Action customizada
# GET    /api/v1/core/categories/tree/          - Action customizada

# Tags - Recursos simples
core_router.register(r"tags", viewsets.TagViewSet, basename="tag")
# URLs geradas:
# GET    /api/v1/core/tags/               - Listar tags
# POST   /api/v1/core/tags/               - Criar tag
# GET    /api/v1/core/tags/{id}/          - Buscar tag específica
# PUT    /api/v1/core/tags/{id}/          - Atualizar tag
# PATCH  /api/v1/core/tags/{id}/          - Atualizar tag parcial
# DELETE /api/v1/core/tags/{id}/          - Soft delete tag
# GET    /api/v1/core/tags/popular/       - Action customizada

# Articles - Relacionamentos M2M complexos
core_router.register(r"articles", viewsets.ArticleViewSet, basename="article")
# URLs geradas:
# GET    /api/v1/core/articles/             - Listar artigos
# POST   /api/v1/core/articles/             - Criar artigo
# GET    /api/v1/core/articles/{id}/        - Buscar artigo específico
# PUT    /api/v1/core/articles/{id}/        - Atualizar artigo
# PATCH  /api/v1/core/articles/{id}/        - Atualizar artigo parcial
# DELETE /api/v1/core/articles/{id}/        - Soft delete artigo
# POST   /api/v1/core/articles/{id}/add-tags/    - Action customizada
# DELETE /api/v1/core/articles/{id}/remove-tags/ - Action customizada


# =============================================================================
# VIEWSETS SOMENTE LEITURA
# =============================================================================

# Read-only documents para APIs públicas
core_router.register(
    r"public-documents",
    viewsets.ReadOnlyDocumentViewSet,
    basename="public-document",
)
# URLs geradas:
# GET    /api/v1/core/public-documents/     - Listar documentos públicos
# GET    /api/v1/core/public-documents/{id}/ - Buscar documento público


# =============================================================================
# VIEWSETS CUSTOMIZADOS (EXEMPLOS COMENTADOS)
# =============================================================================

# Exemplo de ViewSet com prefixo customizado
# core_router.register(
#     r"custom-documents",
#     viewsets.CustomDocumentViewSet,
#     basename="custom-document"
# )

# Exemplo de ViewSet aninhado (sub-recursos)
# core_router.register(
#     r"categories/(?P<category_id>[^/.]+)/documents",
#     viewsets.CategoryDocumentsViewSet,
#     basename="category-documents"
# )

# Exemplo de ViewSet com versioning
# core_router.register(
#     r"v2/documents",
#     viewsets.DocumentV2ViewSet,
#     basename="document-v2"
# )


# =============================================================================
# CONFIGURAÇÕES AVANÇADAS DO ROUTER
# =============================================================================

# Personalização das URLs (se necessário)
# urlpatterns = core_router.urls

# Ou para adicionar URLs customizadas junto com as do router:
# from django.urls import path, include
#
# urlpatterns = [
#     # URLs customizadas
#     path('custom-endpoint/', views.custom_view, name='custom-endpoint'),
#
#     # URLs do router
#     path('', include(core_router.urls)),
# ]


# =============================================================================
# FILTROS E QUERY PARAMETERS SUPORTADOS
# =============================================================================

"""
## Filtros automáticos disponíveis:

### Documents:
- GET /documents/?category=POLICY          # Filtrar por categoria
- GET /documents/?published_only=true      # Apenas publicados
- GET /documents/?search=termo             # Busca no título/conteúdo
- GET /documents/?created_at__gte=2023-01-01  # Data de criação
- GET /documents/?is_published=true        # Status de publicação

### Categories:
- GET /categories/?parent=uuid             # Filtrar por categoria pai
- GET /categories/?parent=null             # Apenas categorias raiz
- GET /categories/?search=termo            # Busca no nome

### Tags:
- GET /tags/?search=termo                  # Busca no nome
- GET /tags/?color=#FF0000                 # Filtrar por cor

### Articles:
- GET /articles/?category=uuid             # Filtrar por categoria
- GET /articles/?status=PUBLISHED         # Filtrar por status
- GET /articles/?tags=uuid1,uuid2          # Filtrar por tags
- GET /articles/?search=termo              # Busca no título/conteúdo

## Ordenação padrão:
- Todos os recursos são ordenados por -created_at (mais recentes primeiro)
- Recursos com is_active=False são filtrados automaticamente

## Paginação:
- Todos os endpoints de listagem suportam paginação
- Parâmetros: ?page=1&page_size=20
- Headers de resposta incluem informações de paginação

## Formatos de resposta:
- JSON (padrão): Accept: application/json
- Browsable API: Accept: text/html (para desenvolvimento)
"""


# =============================================================================
# ESTRUTURA DE RESPOSTA PADRÃO
# =============================================================================

"""
## Estrutura das respostas da API:

### Listagem (GET /resource/):
{
    "count": 100,
    "next": "http://api.example.com/resource/?page=2",
    "previous": null,
    "results": [
        {
            "id": "uuid",
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z",
            // ... outros campos
        }
    ]
}

### Objeto único (GET /resource/{id}/):
{
    "id": "uuid",
    "created_at": "2023-01-01T00:00:00Z",
    "updated_at": "2023-01-01T00:00:00Z",
    // ... outros campos
}

### Criação (POST /resource/):
- Status: 201 Created
- Body: objeto criado

### Atualização (PUT/PATCH /resource/{id}/):
- Status: 200 OK
- Body: objeto atualizado

### Exclusão (DELETE /resource/{id}/):
- Status: 204 No Content
- Body: vazio (soft delete aplicado)

### Erros:
{
    "detail": "Mensagem de erro",
    // ou
    "field_name": ["Lista de erros do campo"]
}
"""


# =============================================================================
# EXEMPLOS DE INTEGRAÇÃO
# =============================================================================

"""
## Como usar este router:

### 1. No urls.py principal do projeto:
```python
from django.urls import path, include
from apps.core.api.v1.router import core_router

urlpatterns = [
    path('api/v1/core/', include(core_router.urls)),
]
```

### 2. URLs completas geradas:
- http://localhost:8000/api/v1/core/documents/
- http://localhost:8000/api/v1/core/categories/
- http://localhost:8000/api/v1/core/tags/
- http://localhost:8000/api/v1/core/articles/

### 3. Testando endpoints:
```bash
# Listar documentos
curl -H "Authorization: Bearer <token>" \\
     http://localhost:8000/api/v1/core/documents/

# Criar documento
curl -X POST \\
     -H "Authorization: Bearer <token>" \\
     -H "Content-Type: application/json" \\
     -d '{"title": "Meu Documento", "content": "Conteúdo"}' \\
     http://localhost:8000/api/v1/core/documents/

# Buscar documento específico
curl -H "Authorization: Bearer <token>" \\
     http://localhost:8000/api/v1/core/documents/uuid-aqui/

# Action customizada
curl -X POST \\
     -H "Authorization: Bearer <token>" \\
     http://localhost:8000/api/v1/core/documents/uuid-aqui/publish/
```

### 4. Navegação automática (browsable API):
- Acesse http://localhost:8000/api/v1/core/ no navegador
- Interface interativa para testar endpoints
- Documentação automática dos parâmetros

### 5. Documentação OpenAPI/Swagger:
- URLs são automaticamente documentadas
- Actions customizadas incluídas
- Parâmetros e respostas documentados
"""
