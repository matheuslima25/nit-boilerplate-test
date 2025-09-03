
# NIT API

API moderna baseada em Django REST Framework, com autenticação Keycloak + Kong API Gateway, suporte a mensageria via Celery + RabbitMQ, health checks integrados, infraestrutura conteinerizada e documentação interativa.

## 🏗️ Arquitetura

Este projeto utiliza uma arquitetura moderna baseada em:

- **Django 5.0.1** + **Django REST Framework 3.15.1** - Backend robusto
- **Keycloak** - Gerenciamento de identidade e autenticação
- **Kong API Gateway** - Gateway, rate limiting e roteamento
- **PostgreSQL** - Banco de dados principal
- **Redis** - Cache e sessions
- **Celery + RabbitMQ** - Processamento assíncrono
- **Docker** - Conteinerização completa

## 🔐 Sistema de Autenticação

### Keycloak + Kong Integration

Este projeto implementa autenticação moderna usando:

1. **Keycloak** como Identity Provider (IdP)
   - Gerenciamento centralizado de usuários
   - JWT tokens seguros
   - Single Sign-On (SSO)
   - Realms e clients configuráveis

2. **Kong API Gateway** como proxy
   - Rate limiting inteligente
   - Validação de JWT tokens
   - Roteamento de APIs
   - Middleware personalizado

### Fluxo de Autenticação

```bash
Cliente → Kong Gateway → Keycloak (validação) → Django API
```

**Características:**

- ✅ Tokens JWT assinados pelo Keycloak
- ✅ Validação automática no Kong
- ✅ Rate limiting por usuário/endpoint
- ✅ Health checks integrados
- ✅ Middleware Django para contexto adicional

---

## 🧱 Estrutura do Projeto

```bash
nit-api/
├── apps/                        # Aplicações Django
├── nitapi/                      # Core do projeto
│   ├── settings/                # Configurações por ambiente
│   ├── router/                  # Rotas principais
│   ├── static/ & staticfiles/   # Arquivos estáticos
│   ├── media/ & mediafiles/     # Arquivos de mídia
│   ├── logs/                    # Logs da aplicação
│   ├── celery.py                # Configuração do Celery
│   ├── asgi.py / wsgi.py        # Entry points ASGI/WSGI
│   ├── storage_backends.py      # Armazenamento customizado
│   └── urls.py                  # Rotas principais
├── docker/                      # Dockerfiles e configurações
├── .envs/                       # Variáveis de ambiente
├── tools/                       # Scripts utilitários
├── scripts/                     # Scripts de auxílio para o deploy automatizado
├── manage.py                    # Comando de gerenciamento
├── Makefile                     # Comandos úteis com `make`
├── postman_collection.json      # Coleção para testes
└── README.md                    # Este arquivo
```

---

## 🚀 Requisitos

- [Docker Engine](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- [GNU Make](https://www.gnu.org/software/make/)

---

## ▶️ Comandos Úteis

### Ver todos os comandos disponíveis

```bash
make help
# ou simplesmente
make
```

### Inicializar o projeto

```bash
make build
make up
```

### Rebuild de imagem + reload

```bash
make reload-api
make reload-worker
```

### Testes e Qualidade de Código

```bash
# Executar todos os testes
make test

# Executar testes com cobertura
make test-coverage

# Configurar pre-commit hooks
make pre-commit-install

# Executar verificações de qualidade
make pre-commit-all

# Atualizar hooks
make pre-commit-update

# Linting moderno com Ruff (substitui flake8)
make ruff

# Verificação sem correção automática
make ruff-check

# Formatação de código com Ruff
make ruff-format

# Executar todas verificações de uma vez
make quality-check
```

### Acessar o Admin do Django

- URL: [http://localhost:8000](http://localhost:8000)
- Login: `admin@nit.com.br`
- Senha: `NIT@123`

---

## 🏥 Health Checks

O sistema inclui health checks integrados usando Django Health Check framework.

### Verificação Rápida

```bash
# Usando o script integrado
python scripts/health_check.py

# Ou via curl
curl http://localhost:8000/health/
```

### Health Checks Disponíveis

**Serviços Básicos:**

- ✅ **Database** - Conectividade PostgreSQL
- ✅ **Cache** - Redis funcionando
- ✅ **Storage** - Sistema de arquivos
- ✅ **Migrations** - Estado das migrações
- ✅ **Memory/Disk** - Recursos do sistema

**Serviços Integrados:**

- 🔑 **Keycloak** - Conectividade e configuração do realm
- 🌉 **Kong Admin** - API administrativa do Kong
- 🌉 **Kong Gateway** - Gateway funcionando
- 🌉 **Kong Service** - Serviços registrados

### Interpretando os Resultados

```bash
# ✅ Verde = Funcionando
# ⚠️  Amarelo = Disponível mas com avisos (ex: serviços externos offline)
# ❌ Vermelho = Erro crítico

# Status HTTP:
# 200 = Todos os serviços OK
# 500 = Alguns serviços externos indisponíveis (normal em desenvolvimento)
```

### Monitoramento em Produção

```bash
# Health check endpoint para monitoramento externo
GET /health/

# Para integração com ferramentas como Kubernetes, Docker Swarm, etc.
```

---

## 🔐 Autenticação

A autenticação é feita via JWT, com endpoints padrão do Simple JWT. O token pode ser usado nos headers com `Authorization: Bearer <token>`.

---

## 📚 Documentação da API

- Swagger: [http://localhost:8000/api/schema/](http://localhost:8000/api/schema/)
- CoreAPI: [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/)

---

## 💌 Coleção Postman

Importe o arquivo [`postman_collection.json`](postman_collection.json) no Postman para testar os endpoints rapidamente.

---

## 🛠 Funcionalidades

- Django 5+ com DRF
- Suporte a múltiplos ambientes (`local.py`, `production.py`)
- Celery + RabbitMQ com monitoramento de tarefas
- Configuração de storage customizado
- Gerador automático de logs
- Deploy automatizado via `deploy.sh`, com criação de imagens de backup
- Integração com GitHub Actions (`.github/workflows/main.yml`)

---

## 🧪 Testes

A aplicação possui uma suíte completa de testes automatizados que garantem a qualidade e confiabilidade do código.

### Como executar os testes

**Executar todos os testes:**

```bash
make test
```

**Executar testes com cobertura:**

```bash
make test-coverage
```

**Executar testes de um app específico:**

```bash
# Usando Docker
docker-compose exec api python manage.py test apps.users

# Localmente (com ambiente configurado)
python manage.py test apps.users
```

**Executar um teste específico:**

```bash
# Usando Docker
docker-compose exec api python manage.py test apps.users.tests.test_models.UserModelTest.test_create_user

# Localmente
python manage.py test apps.users.tests.test_models.UserModelTest.test_create_user
```

### Onde os testes são executados

#### 1. **Desenvolvimento Local**

- Executados pelo desenvolvedor antes de cada commit
- Via comandos `make test` ou `python manage.py test`
- Cobertura mínima exigida: 80%

#### 2. **Pre-commit Hooks**

- Executados automaticamente antes de cada commit via **pre-commit**
- Incluem validações de:
  - **Black**: formatação de código
  - **isort**: ordenação de imports
  - **Ruff**: linting moderno (substitui flake8) - verificação de estilo, bugs e qualidade
  - **MyPy**: verificação de tipos
  - Hooks básicos: trailing whitespace, YAML, JSON, etc.

**Instalação e configuração:**

```bash
# Instalar pre-commit (primeira vez)
pip install pre-commit
# ou via apt no Ubuntu/Debian
sudo apt install pre-commit

# Instalar hooks no repositório
make pre-commit-install
# ou diretamente
pre-commit install

# Executar manualmente em todos os arquivos
make pre-commit-all
# ou diretamente
pre-commit run --all-files

# Atualizar hooks para versões mais recentes
make pre-commit-update
# ou diretamente
pre-commit autoupdate
```

#### 3. **GitHub Actions (CI/CD Pipeline)**

- **Trigger**: A cada `push` na branch `main`
- **Localização**: `.github/workflows/main.yml`
- **Fluxo**:
  1. **CI - Integração Contínua**:
     - Configuração do ambiente Python
     - Instalação de dependências
     - **Execução da suíte completa de testes** (`python manage.py test`)
     - ✅ **Deploy só prossegue se todos os testes passarem**

  2. **Build & Deploy**:
     - Construção da imagem Docker
     - Push para Docker Hub
     - Deploy automático na VPS

#### 4. **Ambiente de Produção**

- Testes de fumaça (smoke tests) após deploy
- Verificação de health checks
- Monitoramento contínuo via logs

### Configuração de Cobertura

A cobertura de testes é configurada no `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["nitapi", "apps"]
omit = [
    "*/migrations/*",
    "*/tests/*",
    "*/apps.py",
    "*/__init__.py",
    "manage.py",
    "*/settings/*",
    # ... outros arquivos excluídos
]

[tool.coverage.report]
show_missing = true
fail_under = 80  # Falha se cobertura < 80%
```

### Estrutura de Testes

```bash
apps/
├── users/
│   └── tests/
│       ├── __init__.py
│       ├── test_models.py
│       ├── test_views.py
│       ├── test_api.py
│       └── test_utils.py
├── core/
│   └── tests/
└── commons/
    └── tests/
```

**Importante**: Os testes são uma barreira obrigatória no pipeline. O deploy **não acontece** se algum teste falhar, garantindo que apenas código testado e funcional chegue à produção.

---

## 📦 Deploy

Configure as variáveis no `production.yml` ou `local.yml` e execute:

```bash
make deploy
```

---

## 🔁 Pipeline de Deploy (GitHub Actions)

A aplicação conta com uma pipeline automatizada no GitHub Actions, definida no arquivo [`.github/workflows/main.yml`](.github/workflows/main.yml).

O fluxo é acionado a cada `push` na branch `main` e segue as melhores práticas para deployments baseados em contêineres.

### Etapas da pipeline

1. **Trigger automático**: a pipeline roda a cada `push` na branch `main`.

2. **CI - Testes de Integração Contínua**
   - O ambiente Python é configurado e as dependências são instaladas.
   - A suíte de testes do Django (`manage.py test`) é executada para garantir a integridade e a qualidade do novo código. O deploy só prossegue se todos os testes passarem.

3. **Build & Push - Criação do Artefato Docker**
   - Após a aprovação nos testes, o pipeline constrói uma nova imagem Docker da aplicação.
   - A imagem é "tagueada" com um identificador único (como o hash do commit) e também com a tag `latest`.
   - Em seguida, a nova imagem é enviada (push) para o **Docker Hub**, servindo como um registro de versões imutáveis da aplicação.

4. **Estágio de Deploy na VPS Hostinger**:
   - A Action se conecta de forma segura à instância na Hostinger via SSH.
   - Uma vez conectado, o pipeline executa os seguintes comandos no servidor:
     - `docker-compose pull`: Baixa a imagem mais recente (a que acabamos de enviar com a tag `latest`) do Docker Hub.
     - `docker-compose up -d --force-recreate`: Reinicia o contêiner da aplicação, substituindo a versão antiga pela nova de forma transparente e aplicando as novas mudanças.
     - **Migrações e Comandos Adicionais**: Opcionalmente, o script de deploy também executa comandos essenciais, como migrações de banco de dados (`python manage.py migrate`) e coleta de arquivos estáticos, para garantir que a infraestrutura esteja sincronizada com o código.
     - **Limpeza**: Para otimizar o espaço em disco, imagens Docker antigas e não utilizadas são removidas do servidor.

A lógica de health check já está implementada no próprio `deploy.sh`, garantindo que a aplicação esteja funcional após o deploy.

---

Feito com ❤️ pela **NIT Team**
