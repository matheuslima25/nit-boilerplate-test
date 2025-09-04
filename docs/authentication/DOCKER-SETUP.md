# Docker Setup para Keycloak + Kong

Este documento explica como configurar Keycloak e Kong usando Docker para desenvolvimento.

## Docker Compose Completo

### Arquivo: `keycloak-kong.yml`

```yaml
version: '3.8'

services:
  # Banco de dados para Keycloak
  keycloak-db:
    image: postgres:13
    environment:
      POSTGRES_DB: keycloak
      POSTGRES_USER: keycloak
      POSTGRES_PASSWORD: keycloak
    volumes:
      - keycloak_db_data:/var/lib/postgresql/data
    networks:
      - auth_network

  # Keycloak Server
  keycloak:
    image: quay.io/keycloak/keycloak:22.0
    environment:
      KEYCLOAK_ADMIN: admin
      KEYCLOAK_ADMIN_PASSWORD: admin
      KC_DB: postgres
      KC_DB_URL: jdbc:postgresql://keycloak-db:5432/keycloak
      KC_DB_USERNAME: keycloak
      KC_DB_PASSWORD: keycloak
      KC_HOSTNAME_STRICT: 'false'
      KC_HTTP_ENABLED: 'true'
      KC_HOSTNAME_STRICT_HTTPS: 'false'
    ports:
      - "8080:8080"
    depends_on:
      - keycloak-db
    command: start-dev
    networks:
      - auth_network

  # Banco de dados para Kong
  kong-db:
    image: postgres:13
    environment:
      POSTGRES_DB: kong
      POSTGRES_USER: kong
      POSTGRES_PASSWORD: kong
    volumes:
      - kong_db_data:/var/lib/postgresql/data
    networks:
      - auth_network

  # Kong Migration
  kong-migration:
    image: kong:3.4
    environment:
      KONG_DATABASE: postgres
      KONG_PG_HOST: kong-db
      KONG_PG_DATABASE: kong
      KONG_PG_USER: kong
      KONG_PG_PASSWORD: kong
    command: kong migrations bootstrap
    depends_on:
      - kong-db
    networks:
      - auth_network

  # Kong Gateway
  kong:
    image: kong:3.4
    environment:
      KONG_DATABASE: postgres
      KONG_PG_HOST: kong-db
      KONG_PG_DATABASE: kong
      KONG_PG_USER: kong
      KONG_PG_PASSWORD: kong
      KONG_PROXY_ACCESS_LOG: /dev/stdout
      KONG_ADMIN_ACCESS_LOG: /dev/stdout
      KONG_PROXY_ERROR_LOG: /dev/stderr
      KONG_ADMIN_ERROR_LOG: /dev/stderr
      KONG_ADMIN_LISTEN: 0.0.0.0:8001
      KONG_ADMIN_GUI_URL: http://localhost:8002
    ports:
      - "8000:8000"  # Gateway
      - "8001:8001"  # Admin API
      - "8002:8002"  # Admin GUI
    depends_on:
      - kong-db
      - kong-migration
    networks:
      - auth_network

  # Kong Manager (Interface Web)
  kong-manager:
    image: pantsel/konga:latest
    environment:
      NODE_ENV: development
      KONGA_HOOK_TIMEOUT: 120000
    ports:
      - "1337:1337"
    networks:
      - auth_network

  # Redis para cache
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - auth_network

volumes:
  keycloak_db_data:
  kong_db_data:
  redis_data:

networks:
  auth_network:
    driver: bridge
```

## Scripts de Inicialização

### Script: `setup-auth.sh`

```bash
#!/bin/bash

echo "🚀 Configurando ambiente de autenticação..."

# 1. Subir serviços
echo "📦 Iniciando containers..."
docker-compose -f keycloak-kong.yml up -d

# 2. Aguardar serviços
echo "⏳ Aguardando serviços iniciarem..."
sleep 30

# 3. Verificar Keycloak
echo "🔐 Verificando Keycloak..."
until curl -f http://localhost:8080/realms/master; do
    echo "Aguardando Keycloak..."
    sleep 5
done

# 4. Verificar Kong
echo "🌉 Verificando Kong..."
until curl -f http://localhost:8001/status; do
    echo "Aguardando Kong..."
    sleep 5
done

# 5. Configurar Kong Service
echo "⚙️ Configurando Kong Service..."
curl -i -X POST http://localhost:8001/services/ \
  --data "name=nit-api" \
  --data "url=http://host.docker.internal:8000"

# 6. Configurar Kong Route
echo "🛣️ Configurando Kong Route..."
curl -i -X POST http://localhost:8001/services/nit-api/routes \
  --data "hosts[]=api.local" \
  --data "paths[]=/api/"

# 7. Configurar Rate Limiting
echo "🚦 Configurando Rate Limiting..."
curl -X POST http://localhost:8001/services/nit-api/plugins \
  --data "name=rate-limiting" \
  --data "config.minute=100" \
  --data "config.hour=1000"

echo "✅ Setup completo!"
echo ""
echo "🔗 URLs disponíveis:"
echo "   Keycloak Admin: http://localhost:8080 (admin/admin)"
echo "   Kong Admin API: http://localhost:8001"
echo "   Kong Manager: http://localhost:1337"
echo "   Redis: localhost:6379"
echo ""
echo "📋 Próximos passos:"
echo "   1. Configure realm no Keycloak"
echo "   2. Crie client para sua aplicação"
echo "   3. Configure variáveis de ambiente"
echo "   4. Inicie sua aplicação Django"
```

### Script: `keycloak-setup.sh`

```bash
#!/bin/bash

KEYCLOAK_URL="http://localhost:8080"
ADMIN_USER="admin"
ADMIN_PASS="admin"
REALM_NAME="nit-services"
CLIENT_ID="nit-api"

echo "🔐 Configurando Keycloak..."

# 1. Obter token de admin
echo "🎫 Obtendo token de admin..."
ADMIN_TOKEN=$(curl -s -X POST "$KEYCLOAK_URL/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$ADMIN_USER" \
  -d "password=$ADMIN_PASS" \
  -d "grant_type=password" \
  -d "client_id=admin-cli" | jq -r '.access_token')

if [ "$ADMIN_TOKEN" = "null" ]; then
    echo "❌ Erro ao obter token de admin"
    exit 1
fi

# 2. Criar realm
echo "🏢 Criando realm: $REALM_NAME"
curl -s -X POST "$KEYCLOAK_URL/admin/realms" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"realm\": \"$REALM_NAME\",
    \"enabled\": true,
    \"registrationAllowed\": true,
    \"loginWithEmailAllowed\": true,
    \"duplicateEmailsAllowed\": false
  }"

# 3. Criar client
echo "📱 Criando client: $CLIENT_ID"
curl -s -X POST "$KEYCLOAK_URL/admin/realms/$REALM_NAME/clients" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"clientId\": \"$CLIENT_ID\",
    \"enabled\": true,
    \"publicClient\": false,
    \"serviceAccountsEnabled\": true,
    \"standardFlowEnabled\": true,
    \"directAccessGrantsEnabled\": true,
    \"redirectUris\": [\"*\"],
    \"webOrigins\": [\"*\"]
  }"

# 4. Obter client secret
echo "🔑 Obtendo client secret..."
CLIENT_UUID=$(curl -s -X GET "$KEYCLOAK_URL/admin/realms/$REALM_NAME/clients" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r ".[] | select(.clientId==\"$CLIENT_ID\") | .id")

CLIENT_SECRET=$(curl -s -X GET "$KEYCLOAK_URL/admin/realms/$REALM_NAME/clients/$CLIENT_UUID/client-secret" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r '.value')

# 5. Criar usuário de teste
echo "👤 Criando usuário de teste..."
curl -s -X POST "$KEYCLOAK_URL/admin/realms/$REALM_NAME/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"testuser\",
    \"email\": \"test@example.com\",
    \"firstName\": \"Test\",
    \"lastName\": \"User\",
    \"enabled\": true,
    \"credentials\": [{
      \"type\": \"password\",
      \"value\": \"testpass\",
      \"temporary\": false
    }]
  }"

echo "✅ Keycloak configurado com sucesso!"
echo ""
echo "📋 Informações importantes:"
echo "   Realm: $REALM_NAME"
echo "   Client ID: $CLIENT_ID"
echo "   Client Secret: $CLIENT_SECRET"
echo "   Test User: testuser / testpass"
echo ""
echo "🔧 Adicione ao seu .django:"
echo "KEYCLOAK_SERVER_URL=$KEYCLOAK_URL"
echo "KEYCLOAK_REALM=$REALM_NAME"
echo "KEYCLOAK_CLIENT_ID=$CLIENT_ID"
echo "KEYCLOAK_CLIENT_SECRET=$CLIENT_SECRET"
```

## Arquivo de Ambiente

### `.django.example`

```bash
# Django
DJANGO_SECRET_KEY=sua-secret-key-super-secreta-aqui
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Database
DATABASE_URL=postgres://nit_user:nit_password@localhost:5432/nit_api

# Redis
REDIS_URL=redis://localhost:6379/0

# Keycloak Configuration
KEYCLOAK_SERVER_URL=http://localhost:8080
KEYCLOAK_REALM=nit-services
KEYCLOAK_CLIENT_ID=nit-api
KEYCLOAK_CLIENT_SECRET=cole-o-secret-aqui
KEYCLOAK_ADMIN_USERNAME=admin
KEYCLOAK_ADMIN_PASSWORD=admin

# Kong Configuration
KONG_ADMIN_URL=http://localhost:8001
KONG_GATEWAY_URL=http://localhost:8000
KONG_SERVICE_NAME=nit-api
KONG_ROUTE_NAME=nit-api-route

# Email (opcional)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Storage (opcional)
DEFAULT_FILE_STORAGE=django.core.files.storage.FileSystemStorage
STATICFILES_STORAGE=whitenoise.storage.CompressedManifestStaticFilesStorage
```

## Comandos Úteis

### Docker Management

```bash
# Iniciar apenas Keycloak e Kong
docker-compose -f keycloak-kong.yml up keycloak kong

# Ver logs específicos
docker-compose -f keycloak-kong.yml logs -f keycloak
docker-compose -f keycloak-kong.yml logs -f kong

# Parar e limpar
docker-compose -f keycloak-kong.yml down -v

# Reiniciar serviço específico
docker-compose -f keycloak-kong.yml restart keycloak
```

### Kong API Testing

```bash
# Listar serviços
curl http://localhost:8001/services

# Listar rotas
curl http://localhost:8001/routes

# Listar plugins
curl http://localhost:8001/plugins

# Status do Kong
curl http://localhost:8001/status
```

### Keycloak Testing

```bash
# Testar realm
curl http://localhost:8080/realms/nit-services

# Obter token
curl -X POST \
  'http://localhost:8080/realms/nit-services/protocol/openid-connect/token' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=password' \
  -d 'client_id=nit-api' \
  -d 'client_secret=CLIENT_SECRET' \
  -d 'username=testuser' \
  -d 'password=testpass'
```

## Troubleshooting Docker

### Problemas Comuns

1. **Port já em uso**:
   ```bash
   # Verificar portas
   netstat -tulpn | grep :8080

   # Matar processo
   sudo fuser -k 8080/tcp
   ```

2. **Containers não iniciam**:
   ```bash
   # Ver logs detalhados
   docker-compose -f keycloak-kong.yml logs

   # Verificar recursos
   docker system df
   docker system prune
   ```

3. **Problemas de rede**:
   ```bash
   # Recriar network
   docker network rm keycloak-kong_auth_network
   docker-compose -f keycloak-kong.yml up
   ```

### Performance

```bash
# Limitar recursos se necessário
echo "
services:
  keycloak:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
" >> keycloak-kong.yml
```

---

Este setup Docker facilita o desenvolvimento local e pode ser adaptado para outros ambientes conforme necessário.
