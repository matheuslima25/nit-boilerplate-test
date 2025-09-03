# Storage Backend Configuration Guide

Este guia explica como configurar e usar os diferentes backends de storage para arquivos públicos e privados no S3.

## Classes de Storage Disponíveis

### 1. StaticStorage (Público)

- **Uso**: Arquivos estáticos públicos (CSS, JS, imagens)
- **ACL**: `public-read`
- **Localização**: `static/`

### 2. PrivateStaticStorage (Privado)

- **Uso**: Arquivos estáticos privados (documentos internos, configs)
- **ACL**: `private`
- **Localização**: `static-private/`
- **Auth**: URLs assinadas com expiração de 1 hora

### 3. PublicMediaStorage (Público)

- **Uso**: Arquivos de media públicos (avatars, logos públicos)
- **ACL**: `public-read`
- **Localização**: `media/`
- **Sobrescrita**: Desabilitada

### 4. PrivateMediaStorage (Privado)

- **Uso**: Arquivos de media privados (documentos, relatórios)
- **ACL**: `private`
- **Localização**: `media-private/`
- **Auth**: URLs assinadas com expiração de 1 hora
- **Sobrescrita**: Desabilitada

## Configuração no Django Settings

### Para usar storage privado por padrão

```python
# settings/base.py ou production.py
if USE_S3:
    # Para arquivos de media privados por padrão
    DEFAULT_FILE_STORAGE = "nitapi.storage_backends.PrivateMediaStorage"

    # Para arquivos estáticos privados
    STATICFILES_STORAGE = "nitapi.storage_backends.PrivateStaticStorage"
```

### Para usar storage público por padrão (atual)

```python
# settings/base.py ou production.py
if USE_S3:
    # Para arquivos de media públicos (configuração atual)
    DEFAULT_FILE_STORAGE = "nitapi.storage_backends.PublicMediaStorage"

    # Para arquivos estáticos públicos
    STATICFILES_STORAGE = "nitapi.storage_backends.StaticStorage"
```

## Uso nos Models

### Exemplo com FileField/ImageField

```python
from django.db import models
from nitapi.storage_backends import (
    PublicMediaStorage,
    PrivateMediaStorage
)

class UserProfile(models.Model):
    # Avatar público (qualquer um pode ver)
    avatar = models.ImageField(
        upload_to='avatars/',
        storage=PublicMediaStorage()
    )

    # Documento privado (só o usuário pode acessar)
    private_document = models.FileField(
        upload_to='documents/private/',
        storage=PrivateMediaStorage()
    )

class Company(models.Model):
    # Logo público
    logo = models.ImageField(
        upload_to='company/logos/',
        storage=PublicMediaStorage()
    )

    # Relatório financeiro privado
    financial_report = models.FileField(
        upload_to='company/reports/',
        storage=PrivateMediaStorage()
    )
```

### Exemplo para upload direto nas views

```python
from django.core.files.storage import get_storage_class
from nitapi.storage_backends import PrivateMediaStorage, PublicMediaStorage

def upload_file(request):
    file = request.FILES['file']

    # Para arquivo público
    public_storage = PublicMediaStorage()
    public_url = public_storage.save(f'uploads/{file.name}', file)

    # Para arquivo privado
    private_storage = PrivateMediaStorage()
    private_path = private_storage.save(f'private/{file.name}', file)

    # Gerar URL assinada para arquivo privado
    private_url = private_storage.url(private_path)

    return JsonResponse({
        'public_url': public_storage.url(public_url),
        'private_url': private_url  # URL com assinatura e expiração
    })
```

## URLs de Acesso

### Arquivos Públicos

- **Direto**: `https://bucket.s3.amazonaws.com/media/file.jpg`
- **Sem autenticação**: Acessível por qualquer pessoa

### Arquivos Privados

- **Assinado**: `https://bucket.s3.amazonaws.com/media-private/file.pdf?AWSAccessKeyId=...&Signature=...&Expires=...`
- **Com autenticação**: Expira em 1 hora por padrão

## Configurações Recomendadas por Ambiente

### Desenvolvimento (local.py)

```python
# Usar storage público para facilitar debugging
DEFAULT_FILE_STORAGE = "nitapi.storage_backends.PublicMediaStorage"
```

### Produção (production.py)

```python
# Usar storage privado por segurança
DEFAULT_FILE_STORAGE = "nitapi.storage_backends.PrivateMediaStorage"

# Configurar expiração de URLs privadas
AWS_QUERYSTRING_EXPIRE = 3600  # 1 hora
```

## Migração de Arquivos Existentes

Para migrar arquivos de público para privado:

```python
# Command de migração
from django.core.management.base import BaseCommand
from nitapi.storage_backends import PublicMediaStorage, PrivateMediaStorage

class Command(BaseCommand):
    def handle(self, *args, **options):
        public_storage = PublicMediaStorage()
        private_storage = PrivateMediaStorage()

        # Migrar arquivos específicos
        for file_path in files_to_migrate:
            content = public_storage.open(file_path)
            private_storage.save(file_path, content)
            public_storage.delete(file_path)
```

## Estrutura de Buckets S3

```bash
meu-bucket/
├── static/              # Arquivos estáticos públicos
│   ├── css/
│   ├── js/
│   └── images/
├── static-private/      # Arquivos estáticos privados
│   ├── admin/
│   └── internal/
├── media/              # Media público
│   ├── avatars/
│   └── logos/
└── media-private/      # Media privado
    ├── documents/
    ├── reports/
    └── uploads/
```
