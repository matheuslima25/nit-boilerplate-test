# Troubleshooting - Keycloak + Kong

Este documento contém soluções para problemas comuns ao usar autenticação Keycloak + Kong.

## Problemas de Autenticação

### 1. Token JWT Inválido

**Sintoma**: `HTTP 401 - Invalid token`

**Causas Possíveis**:

- Token expirado
- Configuração incorreta do cliente Keycloak
- Chave pública incorreta

**Soluções**:

```bash
# 1. Verificar se o token está válido
curl -X POST \
  'https://seu-keycloak.com/realms/seu-realm/protocol/openid-connect/token/introspect' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'token=SEU_TOKEN' \
  -d 'client_id=seu-client' \
  -d 'client_secret=sua-secret'

# 2. Obter novo token
curl -X POST \
  'https://seu-keycloak.com/realms/seu-realm/protocol/openid-connect/token' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=password' \
  -d 'client_id=seu-client' \
  -d 'client_secret=sua-secret' \
  -d 'username=usuario' \
  -d 'password=senha'
```

**Verificações**:

```python
# No Django shell
from nitapi.authentication import KeycloakAuthentication
auth = KeycloakAuthentication()

# Testar conexão
try:
    auth._get_keycloak_admin()
    print("Conexão OK")
except Exception as e:
    print(f"Erro: {e}")
```

### 2. Usuário não Criado Automaticamente

**Sintoma**: Token válido mas usuário não existe no Django

**Solução**:

```python
# Verificar logs
import logging
logging.getLogger('nitapi.authentication').setLevel(logging.DEBUG)

# Forçar criação de usuário
from django.contrib.auth import get_user_model
from nitapi.authentication import KeycloakAuthentication

User = get_user_model()
auth = KeycloakAuthentication()

# Simular autenticação
token = "SEU_TOKEN_AQUI"
user_info = auth._decode_token(token)
user = auth._get_or_create_user(user_info)
print(f"Usuário criado: {user}")
```

### 3. Permissões Insuficientes

**Sintoma**: `HTTP 403 - Permission denied`

**Verificações**:

```python
# Verificar roles do usuário
user = request.user
print(f"User: {user}")
print(f"Is authenticated: {user.is_authenticated}")
print(f"Is staff: {user.is_staff}")
print(f"Is superuser: {user.is_superuser}")
```

**Configurar Roles no Keycloak**:

1. Acesse **Realm Roles**
2. Crie roles necessárias: `admin`, `user`, `manager`
3. Atribua roles aos usuários
4. Configure mappers no cliente

## Problemas Kong

### 1. Kong Gateway Não Responde

**Sintoma**: `Connection refused` ou timeout

**Verificações**:

```bash
# 1. Verificar se Kong está rodando
docker ps | grep kong

# 2. Testar conectividade
curl -i http://kong-admin:8001/status
curl -i http://kong-gateway:8000/

# 3. Verificar logs
docker logs kong-container
```

**Soluções**:

```bash
# Reiniciar Kong
docker-compose restart kong

# Verificar configuração
curl http://kong-admin:8001/services
curl http://kong-admin:8001/routes
```

### 2. Serviço não Registrado

**Sintoma**: `HTTP 404 - no Route matched`

**Verificação**:

```bash
# Listar serviços
curl http://kong-admin:8001/services

# Listar rotas
curl http://kong-admin:8001/routes
```

**Solução**:

```bash
# Registrar serviço
curl -i -X POST http://kong-admin:8001/services/ \
  --data "name=nit-api" \
  --data "url=http://django:8000"

# Criar rota
curl -i -X POST http://kong-admin:8001/services/nit-api/routes \
  --data "hosts[]=api.nit.com" \
  --data "paths[]=/api/"
```

### 3. Rate Limiting Issues

**Sintoma**: `HTTP 429 - API rate limit exceeded`

**Verificação**:

```bash
# Verificar plugins de rate limiting
curl http://kong-admin:8001/plugins | jq '.data[] | select(.name=="rate-limiting")'
```

**Ajustar Limites**:

```bash
# Atualizar rate limiting
curl -X PATCH http://kong-admin:8001/plugins/PLUGIN_ID \
  --data "config.minute=1000" \
  --data "config.hour=10000"
```

## Problemas de Conectividade

### 1. Keycloak Inacessível

**Sintoma**: `ConnectionError` ou `Timeout`

**Verificações**:

```bash
# 1. Ping do servidor
ping seu-keycloak.com

# 2. Testar porta
telnet seu-keycloak.com 443

# 3. Verificar DNS
nslookup seu-keycloak.com

# 4. Testar endpoint
curl -k https://seu-keycloak.com/realms/seu-realm
```

**Soluções**:

```python
# Configurar timeout maior
KEYCLOAK_CONNECTION_TIMEOUT = 30  # segundos

# Usar IP direto (temporário)
KEYCLOAK_SERVER_URL = 'http://192.168.1.100:8080'
```

### 2. Problema de CORS

**Sintoma**: `CORS policy error` no browser

**Solução Django**:

```python
# settings.py
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://seu-frontend.com",
]

CORS_ALLOW_CREDENTIALS = True
```

**Solução Kong**:

```bash
# Plugin CORS no Kong
curl -X POST http://kong-admin:8001/services/nit-api/plugins \
  --data "name=cors" \
  --data "config.origins=http://localhost:3000,https://seu-frontend.com" \
  --data "config.methods=GET,POST,PUT,DELETE,OPTIONS" \
  --data "config.headers=Accept,Accept-Version,Content-Length,Content-MD5,Content-Type,Date,Authorization"
```

## Problemas de Performance

### 1. Autenticação Lenta

**Sintoma**: Requests demoram muito para retornar

**Diagnóstico**:

```python
# Adicionar timing nos logs
import time
import logging

logger = logging.getLogger(__name__)

def authenticate(self, request):
    start_time = time.time()
    result = super().authenticate(request)
    end_time = time.time()
    logger.info(f"Auth took {end_time - start_time:.2f}s")
    return result
```

**Soluções**:

```python
# 1. Cache de tokens
from django.core.cache import cache

def _decode_token(self, token):
    cache_key = f"token_{token[:10]}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result

    result = self._actual_decode(token)
    cache.set(cache_key, result, 300)  # 5 minutos
    return result

# 2. Connection pooling
import requests
session = requests.Session()
```

### 2. Muitas Consultas ao Banco

**Sintoma**: Queries N+1, banco lento

**Diagnóstico**:

```python
# settings.py para debug
LOGGING = {
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',
        },
    },
}
```

**Soluções**:

```python
# Use select_related para foreign keys
User.objects.select_related('profile').get(id=user_id)

# Use prefetch_related para many-to-many
User.objects.prefetch_related('groups').all()

# Cache queries frequentes
from django.core.cache import cache

def get_user_permissions(user_id):
    cache_key = f"user_perms_{user_id}"
    perms = cache.get(cache_key)
    if not perms:
        perms = User.objects.get(id=user_id).get_all_permissions()
        cache.set(cache_key, perms, 3600)
    return perms
```

## Problemas de Configuração

### 1. Variáveis de Ambiente Incorretas

**Verificação**:

```python
# Django shell
from django.conf import settings
print(f"Keycloak URL: {settings.KEYCLOAK_SERVER_URL}")
print(f"Realm: {settings.KEYCLOAK_REALM}")
print(f"Client ID: {settings.KEYCLOAK_CLIENT_ID}")
```

**Arquivo de Debug**:

```python
# debug_config.py
import os
from django.conf import settings

required_vars = [
    'KEYCLOAK_SERVER_URL',
    'KEYCLOAK_REALM',
    'KEYCLOAK_CLIENT_ID',
    'KEYCLOAK_CLIENT_SECRET',
]

for var in required_vars:
    value = getattr(settings, var, None)
    print(f"{var}: {'✓' if value else '✗'} {value}")
```

### 2. SSL/TLS Issues

**Sintoma**: `SSL verification failed`

**Soluções**:

```python
# Para desenvolvimento (NÃO usar em produção)
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

# Ou configurar certificados
KEYCLOAK_SSL_VERIFY = '/path/to/ca-bundle.crt'
```

## Scripts de Diagnóstico

### Script Completo de Health Check

```python
#!/usr/bin/env python
"""
Health check para Keycloak + Kong
"""
import requests
import sys
from django.conf import settings

def check_keycloak():
    try:
        url = f"{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}"
        response = requests.get(url, timeout=10)
        print(f"✓ Keycloak: {response.status_code}")
        return True
    except Exception as e:
        print(f"✗ Keycloak: {e}")
        return False

def check_kong():
    try:
        url = f"{settings.KONG_ADMIN_URL}/status"
        response = requests.get(url, timeout=10)
        print(f"✓ Kong Admin: {response.status_code}")

        url = f"{settings.KONG_GATEWAY_URL}/"
        response = requests.get(url, timeout=10)
        print(f"✓ Kong Gateway: {response.status_code}")
        return True
    except Exception as e:
        print(f"✗ Kong: {e}")
        return False

def check_database():
    try:
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        print("✓ Database: OK")
        return True
    except Exception as e:
        print(f"✗ Database: {e}")
        return False

if __name__ == "__main__":
    checks = [
        check_keycloak(),
        check_kong(),
        check_database(),
    ]

    if all(checks):
        print("\n🎉 Todos os serviços estão funcionando!")
        sys.exit(0)
    else:
        print("\n⚠️  Alguns serviços têm problemas")
        sys.exit(1)
```

### Script de Teste de Token

```bash
#!/bin/bash
# test_token.sh

TOKEN="$1"
if [ -z "$TOKEN" ]; then
    echo "Uso: $0 <token>"
    exit 1
fi

echo "Testando token..."

# Teste 1: Introspect no Keycloak
echo "1. Introspect Keycloak:"
curl -s -X POST \
  "$KEYCLOAK_SERVER_URL/realms/$KEYCLOAK_REALM/protocol/openid-connect/token/introspect" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d "token=$TOKEN" \
  -d "client_id=$KEYCLOAK_CLIENT_ID" \
  -d "client_secret=$KEYCLOAK_CLIENT_SECRET" | jq .

# Teste 2: Uso no Django
echo "2. Teste Django API:"
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/users/me/ | jq .

# Teste 3: Via Kong
echo "3. Teste via Kong:"
curl -s -H "Authorization: Bearer $TOKEN" \
  http://kong-gateway:8000/api/v1/users/me/ | jq .
```

## Logs e Monitoramento

### Configuração de Logs Detalhados

```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'auth_debug.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'nitapi.authentication': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'nitapi.kong_middleware': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
```

---

Para mais informações:

- [Setup Principal](./KEYCLOAK-KONG-SETUP.md)
- [Guia de Migração](./MIGRATION-GUIDE.md)
