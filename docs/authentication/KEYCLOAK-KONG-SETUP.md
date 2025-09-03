# Configuração de Autenticação Keycloak + Kong API Gateway

Este documento descreve como configurar e usar este projeto Django para autenticação agnóstica com Keycloak e gerenciamento via Kong API Gateway.

## Arquitetura de Autenticação

O sistema utiliza uma arquitetura de autenticação completamente agnóstica:

```
Cliente → Kong API Gateway → Django API → Keycloak
```

### Componentes

1. **Keycloak**: Servidor de autenticação e autorização
2. **Kong API Gateway**: Gateway de API com rate limiting e service discovery
3. **Django API**: API backend com autenticação baseada em JWT

## Configuração do Ambiente

### 1. Variáveis de Ambiente Obrigatórias

Crie um arquivo `.django` com as seguintes variáveis:

```bash
# Configurações Keycloak
KEYCLOAK_SERVER_URL=https://seu-keycloak.com
KEYCLOAK_REALM=seu-realm
KEYCLOAK_CLIENT_ID=seu-client-id
KEYCLOAK_CLIENT_SECRET=sua-client-secret
KEYCLOAK_ADMIN_USERNAME=admin
KEYCLOAK_ADMIN_PASSWORD=admin-password

# Configurações Kong
KONG_ADMIN_URL=http://kong-admin:8001
KONG_GATEWAY_URL=http://kong-gateway:8000
KONG_SERVICE_NAME=nit-api
KONG_ROUTE_NAME=nit-api-route

# Configurações Django (mantenha as existentes)
DJANGO_SECRET_KEY=sua-secret-key
DJANGO_DEBUG=True
DATABASE_URL=postgres://user:pass@host:port/db
REDIS_URL=redis://localhost:6379/0
```

### 2. Configuração do Keycloak

#### 2.1. Criar um Realm

1. Acesse o Admin Console do Keycloak
2. Crie um novo realm (ex: `nit-services`)
3. Configure as seguintes opções:
   - **Login**: Habilitado
   - **Registration**: Conforme necessário
   - **Email as Username**: Recomendado

#### 2.2. Criar um Client

1. Vá para **Clients** → **Create**
2. Configure:
   - **Client ID**: `nit-api`
   - **Client Protocol**: `openid-connect`
   - **Access Type**: `confidential`
   - **Valid Redirect URIs**: `*` (ou específico para produção)
   - **Web Origins**: `*` (ou específico para produção)

3. Na aba **Credentials**, copie o **Secret**

#### 2.3. Configurar Scopes

1. Vá para **Client Scopes**
2. Crie scopes customizados se necessário:
   - `api:read`
   - `api:write`
   - `api:admin`

### 3. Configuração do Kong

#### 3.1. Serviço Base

```bash
# Criar serviço no Kong
curl -i -X POST http://kong-admin:8001/services/ \
  --data "name=nit-api" \
  --data "url=http://django:8000"

# Criar rota
curl -i -X POST http://kong-admin:8001/services/nit-api/routes \
  --data "hosts[]=api.nit.com" \
  --data "paths[]=/api/"
```

#### 3.2. Plugin JWT (Opcional)

Se quiser validação JWT no Kong:

```bash
curl -X POST http://kong-admin:8001/services/nit-api/plugins \
  --data "name=jwt" \
  --data "config.uri_param_names=jwt" \
  --data "config.cookie_names=jwt"
```

#### 3.3. Rate Limiting

```bash
curl -X POST http://kong-admin:8001/services/nit-api/plugins \
  --data "name=rate-limiting" \
  --data "config.minute=100" \
  --data "config.hour=1000"
```

## Fluxo de Autenticação

### 1. Obter Token do Keycloak

```bash
curl -X POST \
  'https://seu-keycloak.com/realms/nit-services/protocol/openid-connect/token' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=password' \
  -d 'client_id=nit-api' \
  -d 'client_secret=sua-client-secret' \
  -d 'username=usuario@email.com' \
  -d 'password=senha123'
```

### 2. Usar Token nas Requisições

```bash
curl -X GET \
  'http://kong-gateway:8000/api/v1/users/me/' \
  -H 'Authorization: Bearer SEU_JWT_TOKEN'
```

## Classes de Autenticação Disponíveis

### 1. KeycloakJWTAuthentication

Autenticação principal via JWT do Keycloak.

```python
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from nitapi.drf_authentication import KeycloakJWTAuthentication

@api_view(['GET'])
@authentication_classes([KeycloakJWTAuthentication])
@permission_classes([IsAuthenticated])
def protected_view(request):
    # Acesso apenas com JWT válido do Keycloak
    return Response({'user': request.user.username})
```

### 2. KongConsumerAuthentication

Para endpoints que precisam de informações do Kong Consumer.

```python
from nitapi.drf_authentication import KongConsumerAuthentication

@api_view(['GET'])
@authentication_classes([KongConsumerAuthentication])
def kong_protected_view(request):
    # Acesso via Kong Consumer
    return Response({'consumer': request.user.username})
```

## Middleware Kong

O projeto inclui middleware para integração automática com Kong:

```python
MIDDLEWARE = [
    # ... outros middlewares
    'nitapi.kong_middleware.KongMiddleware',
    'nitapi.kong_middleware.KongRateLimitMiddleware',
]
```

### Headers Kong Suportados

- `X-Consumer-ID`: ID do consumer no Kong
- `X-Consumer-Username`: Username do consumer
- `X-RateLimit-Limit`: Limite de rate limiting
- `X-RateLimit-Remaining`: Requests restantes

## Testando a Configuração

### 1. Teste de Saúde

```bash
curl http://localhost:8000/health/
```

### 2. Teste de Autenticação

```bash
# Sem token (deve retornar 401)
curl http://localhost:8000/api/v1/users/me/

# Com token válido
curl -H "Authorization: Bearer SEU_TOKEN" \
     http://localhost:8000/api/v1/users/me/
```

### 3. Teste Kong Integration

```bash
# Com headers Kong
curl -H "Authorization: Bearer SEU_TOKEN" \
     -H "X-Consumer-Username: test-consumer" \
     http://localhost:8000/api/v1/users/me/
```

## Modelos de Dados

### User Model Estendido

O modelo User foi estendido para suportar Keycloak:

```python
class User(AbstractUser):
    keycloak_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    # ... outros campos
```

### Sincronização de Usuários

Os usuários são automaticamente criados/atualizados durante a autenticação:

1. JWT é validado no Keycloak
2. Informações do usuário são extraídas
3. User é criado/atualizado no Django
4. Keycloak ID é armazenado para referência

## Troubleshooting

### Problemas Comuns

1. **Token Inválido**
   - Verificar se o token não expirou
   - Confirmar configurações do cliente Keycloak
   - Validar variáveis de ambiente

2. **Erro de Conexão Keycloak**
   - Verificar URL do servidor
   - Confirmar conectividade de rede
   - Validar credenciais admin

3. **Kong não responde**
   - Verificar se Kong está rodando
   - Confirmar configuração de serviços
   - Validar URLs de admin e gateway

### Logs de Debug

Para habilitar logs detalhados:

```python
LOGGING = {
    'loggers': {
        'nitapi.authentication': {
            'level': 'DEBUG',
        },
        'nitapi.kong_middleware': {
            'level': 'DEBUG',
        },
    }
}
```

## Próximos Passos

1. Configurar ambiente de produção
2. Implementar refresh tokens
3. Adicionar métricas e monitoramento
4. Configurar backup e disaster recovery
5. Implementar CI/CD pipelines

---

Para mais informações técnicas, consulte:
- [Padrões de Configuração](./patterns/SETUP.md)
- [Documentação de Segurança](./sql/SECURITY.md)
- [Guia de Storage](./storage/README.md)
