# Exemplo de Configuração Completa

Este arquivo mostra uma configuração completa e funcional para diferentes ambientes.

## Desenvolvimento Local

### Arquivo: `.django` (Local)

```bash
# ========================================
# CONFIGURAÇÃO DESENVOLVIMENTO LOCAL
# ========================================

# Django Core
DJANGO_SECRET_KEY=desenvolvimento-secret-key-insegura-apenas-local
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0,api.local

# Database (PostgreSQL Local)
DATABASE_URL=postgres://nit_user:nit_password@localhost:5432/nit_api_dev

# Redis Cache
REDIS_URL=redis://localhost:6379/0

# ========================================
# KEYCLOAK CONFIGURAÇÃO
# ========================================

# Servidor Keycloak (Docker Local)
KEYCLOAK_SERVER_URL=http://localhost:8080
KEYCLOAK_REALM=nit-services-dev
KEYCLOAK_CLIENT_ID=nit-api-dev
KEYCLOAK_CLIENT_SECRET=your-keycloak-client-secret-here

# Credenciais Admin (apenas desenvolvimento)
KEYCLOAK_ADMIN_USERNAME=admin
KEYCLOAK_ADMIN_PASSWORD=admin

# ========================================
# KONG API GATEWAY
# ========================================

# URLs Kong (Docker Local)
KONG_ADMIN_URL=http://localhost:8001
KONG_GATEWAY_URL=http://localhost:8000

# Configuração do Serviço
KONG_SERVICE_NAME=nit-api-dev
KONG_ROUTE_NAME=nit-api-dev-route

# ========================================
# EMAIL (Desenvolvimento)
# ========================================

EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=noreply@nit-dev.local

# ========================================
# STORAGE (Local)
# ========================================

DEFAULT_FILE_STORAGE=django.core.files.storage.FileSystemStorage
STATICFILES_STORAGE=whitenoise.storage.CompressedManifestStaticFilesStorage

# ========================================
# CELERY (Desenvolvimento)
# ========================================

CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/1
CELERY_TASK_ALWAYS_EAGER=False

# ========================================
# LOGGING (Desenvolvimento)
# ========================================

LOG_LEVEL=DEBUG
DJANGO_LOG_LEVEL=INFO
```

## Produção

### Arquivo: `.django` (Produção)

```bash
# ========================================
# CONFIGURAÇÃO PRODUÇÃO
# ========================================

# Django Core
DJANGO_SECRET_KEY=sua-secret-key-super-segura-producao-256-bits
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=api.suaempresa.com,gateway.suaempresa.com

# Database (PostgreSQL Cluster)
DATABASE_URL=postgres://user:pass@postgres-cluster.internal:5432/nit_api_prod

# Redis Cache (Cluster)
REDIS_URL=redis://redis-cluster.internal:6379/0

# ========================================
# KEYCLOAK CONFIGURAÇÃO (PRODUÇÃO)
# ========================================

# Servidor Keycloak (Cluster)
KEYCLOAK_SERVER_URL=https://auth.suaempresa.com
KEYCLOAK_REALM=nit-services
KEYCLOAK_CLIENT_ID=nit-api-production
KEYCLOAK_CLIENT_SECRET=client-secret-super-seguro-producao

# Admin Service Account
KEYCLOAK_ADMIN_USERNAME=service-account-admin
KEYCLOAK_ADMIN_PASSWORD=password-super-segura-admin

# ========================================
# KONG API GATEWAY (PRODUÇÃO)
# ========================================

# URLs Kong (Load Balanced)
KONG_ADMIN_URL=https://kong-admin.internal:8444
KONG_GATEWAY_URL=https://api.suaempresa.com

# Configuração do Serviço
KONG_SERVICE_NAME=nit-api-production
KONG_ROUTE_NAME=nit-api-production

# ========================================
# EMAIL (Produção)
# ========================================

EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.suaempresa.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=noreply@suaempresa.com
EMAIL_HOST_PASSWORD=smtp-password-segura
DEFAULT_FROM_EMAIL=noreply@suaempresa.com

# ========================================
# STORAGE (S3 Produção)
# ========================================

DEFAULT_FILE_STORAGE=storages.backends.s3boto3.S3Boto3Storage
STATICFILES_STORAGE=storages.backends.s3boto3.S3StaticStorage

# AWS S3
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=sua-secret-key-aws
AWS_STORAGE_BUCKET_NAME=nit-api-storage-prod
AWS_S3_REGION_NAME=us-east-1
AWS_S3_CUSTOM_DOMAIN=cdn.suaempresa.com

# ========================================
# CELERY (Produção)
# ========================================

CELERY_BROKER_URL=redis://redis-cluster.internal:6379/1
CELERY_RESULT_BACKEND=redis://redis-cluster.internal:6379/1
CELERY_TASK_ALWAYS_EAGER=False

# Worker Configuration
CELERYD_CONCURRENCY=4
CELERYD_MAX_TASKS_PER_CHILD=1000

# ========================================
# MONITORING & LOGGING
# ========================================

LOG_LEVEL=INFO
DJANGO_LOG_LEVEL=WARNING

# Sentry (Error Tracking)
SENTRY_DSN=https://...@sentry.io/...

# ========================================
# SECURITY (Produção)
# ========================================

SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
SECURE_CONTENT_TYPE_NOSNIFF=True
SECURE_BROWSER_XSS_FILTER=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

## Docker Compose - Desenvolvimento

### Arquivo: `local.yml` (atualizado)

```yaml
version: '3.8'

services:
  django: &django
    build:
      context: .
      dockerfile: ./docker/local/django/Dockerfile
    image: nit_api_local_django
    container_name: nit_api_local_django
    depends_on:
      - postgres
      - redis
    volumes:
      - .:/app:z
    env_file:
      - ./.django
    ports:
      - "8000:8000"
    command: /start
    networks:
      - nit_network

  postgres:
    build:
      context: .
      dockerfile: ./docker/local/postgres/Dockerfile
    image: nit_api_local_postgres
    container_name: nit_api_local_postgres
    volumes:
      - nit_api_local_postgres_data:/var/lib/postgresql/data
      - nit_api_local_postgres_data_backups:/backups
    env_file:
      - ./.django
    networks:
      - nit_network

  redis:
    image: redis:7-alpine
    container_name: nit_api_local_redis
    volumes:
      - nit_api_local_redis_data:/data
    networks:
      - nit_network

  # Keycloak com PostgreSQL
  keycloak-db:
    image: postgres:13
    container_name: nit_api_keycloak_db
    environment:
      POSTGRES_DB: keycloak
      POSTGRES_USER: keycloak
      POSTGRES_PASSWORD: keycloak
    volumes:
      - nit_api_keycloak_db_data:/var/lib/postgresql/data
    networks:
      - nit_network

  keycloak:
    image: quay.io/keycloak/keycloak:22.0
    container_name: nit_api_keycloak
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
      - nit_network

  # Kong com PostgreSQL
  kong-db:
    image: postgres:13
    container_name: nit_api_kong_db
    environment:
      POSTGRES_DB: kong
      POSTGRES_USER: kong
      POSTGRES_PASSWORD: kong
    volumes:
      - nit_api_kong_db_data:/var/lib/postgresql/data
    networks:
      - nit_network

  kong-migration:
    image: kong:3.4
    container_name: nit_api_kong_migration
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
      - nit_network

  kong:
    image: kong:3.4
    container_name: nit_api_kong
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
      - "8001:8001"  # Admin API
      - "8002:8002"  # Admin GUI
    depends_on:
      - kong-db
      - kong-migration
    networks:
      - nit_network

  # Celery Worker
  celeryworker:
    <<: *django
    image: nit_api_local_celeryworker
    container_name: nit_api_local_celeryworker
    depends_on:
      - redis
      - postgres
    ports: []
    command: /start-celeryworker

  # Celery Beat
  celerybeat:
    <<: *django
    image: nit_api_local_celerybeat
    container_name: nit_api_local_celerybeat
    depends_on:
      - redis
      - postgres
    ports: []
    command: /start-celerybeat

volumes:
  nit_api_local_postgres_data:
  nit_api_local_postgres_data_backups:
  nit_api_local_redis_data:
  nit_api_keycloak_db_data:
  nit_api_kong_db_data:

networks:
  nit_network:
    driver: bridge
```

## Configuração nginx (Produção)

### Arquivo: `nginx.conf`

```nginx
upstream django {
    server django:8000;
}

upstream kong {
    server kong:8000;
}

server {
    listen 80;
    server_name api.suaempresa.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.suaempresa.com;

    ssl_certificate /etc/ssl/certs/api.suaempresa.com.crt;
    ssl_certificate_key /etc/ssl/private/api.suaempresa.com.key;

    # SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:...;
    ssl_prefer_server_ciphers off;

    # Security Headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubdomains; preload";

    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

    # API Routes via Kong
    location /api/ {
        limit_req zone=api burst=20 nodelay;

        proxy_pass http://kong;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Admin routes direto para Django
    location /admin/ {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files
    location /static/ {
        alias /app/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Health check
    location /health/ {
        proxy_pass http://django;
        access_log off;
    }
}
```

## Scripts de Deploy

### Script: `deploy.sh`

```bash
#!/bin/bash

set -e

ENVIRONMENT=${1:-staging}
VERSION=$(cat VERSION)

echo "🚀 Iniciando deploy para $ENVIRONMENT..."
echo "📦 Versão: $VERSION"

# 1. Verificações pré-deploy
echo "✅ Executando verificações..."
python scripts/health_check.py

# 2. Build da imagem
echo "🏗️ Construindo imagem Docker..."
docker build -t nit-api:$VERSION .
docker tag nit-api:$VERSION nit-api:latest

# 3. Push para registry
echo "📤 Enviando para registry..."
docker push nit-api:$VERSION
docker push nit-api:latest

# 4. Deploy via Docker Compose
echo "🔄 Atualizando serviços..."
docker-compose -f production.yml pull
docker-compose -f production.yml up -d --no-deps django

# 5. Migrations
echo "🗃️ Executando migrations..."
docker-compose -f production.yml exec django python manage.py migrate

# 6. Collectstatic
echo "📂 Coletando arquivos estáticos..."
docker-compose -f production.yml exec django python manage.py collectstatic --noinput

# 7. Verificação pós-deploy
echo "🔍 Verificando deploy..."
sleep 10
curl -f https://api.suaempresa.com/health/ || {
    echo "❌ Health check falhou!"
    echo "🔄 Fazendo rollback..."
    docker-compose -f production.yml rollback
    exit 1
}

echo "✅ Deploy concluído com sucesso!"
echo "🌐 Aplicação disponível em: https://api.suaempresa.com"
```

## Checklist de Configuração

### Desenvolvimento Local

- [ ] Copiar `.django.example` para `.django`
- [ ] Configurar URLs do Keycloak local
- [ ] Configurar credenciais Kong local
- [ ] Executar `docker-compose -f local.yml up`
- [ ] Executar `python manage.py migrate`
- [ ] Executar `python scripts/health_check.py`
- [ ] Testar autenticação

### Produção

- [ ] Gerar secret key segura
- [ ] Configurar banco PostgreSQL
- [ ] Configurar cluster Redis
- [ ] Configurar Keycloak em cluster
- [ ] Configurar Kong em cluster
- [ ] Configurar SSL/TLS
- [ ] Configurar nginx
- [ ] Configurar monitoramento
- [ ] Configurar backup
- [ ] Testar disaster recovery

---

Esta configuração fornece uma base sólida para diferentes ambientes, desde desenvolvimento local até produção em larga escala.
