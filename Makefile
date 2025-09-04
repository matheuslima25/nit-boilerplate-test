SHELL := /bin/bash

.PHONY: help build start up stop deploy rollback status test test-coverage \
				pre-commit-install pre-commit-all pre-commit-update ruff ruff-check ruff-format \
				quality-check lint-auto lint-check lint-file lint fix check format migrate \
				makemigrations collectstatic createsuperuser checkdeploy logs logs-api logs-worker \
				down-v backup nitapi_db reload-api reload-worker install-deps install-prod \
				install-test deps-check deps-update deps-test-retry

# --- CONFIGURAÇÕES DE VERSIONAMENTO ---
# Lendo a versão do arquivo VERSION. Se não existir, assume 1.0.0.
# Isso torna a versão disponível para todos os comandos do Makefile.
IMAGE_NAME := nitapi-api
CURRENT_VERSION := $(shell cat VERSION 2>/dev/null || echo "1.0.0")

CURRENT_DIR := $(shell pwd)
USER := $(shell whoami)
TIMESTAMP := $(shell date +%Y-%m-%d_%H-%M-%S)

export COMPOSE_CMD := docker compose
# export COMPOSE_CMD := /usr/local/bin/docker-compose
yml := docker-compose.yml

# when running for the first time in new environment you can simply run "make build"
# you will need the build commands only when there are changes in any container
# all build commands usually takes more time than a run command

# Variável para passar a versão manualmente (ex: make deploy V=1.2)
V :=

# --- COMANDOS PRINCIPAIS DE DESENVOLVIMENTO ---

# Mostrar ajuda com todos os comandos disponíveis
help:
	@echo "🚀 NIT API - Comandos Disponíveis:"
	@echo ""
	@echo "📦 DESENVOLVIMENTO:"
	@echo "  build              - Constrói todos os serviços"
	@echo "  start/up           - Inicia todos os containers"
	@echo "  stop               - Para todos os containers"
	@echo "  down-v             - Para containers e remove volumes"
	@echo ""
	@echo "🔧 SERVIÇOS:"
	@echo "  reload-api         - Reconstrói e reinicia apenas a API"
	@echo "  logs               - Mostra logs de todos os serviços"
	@echo "  logs-api           - Mostra logs apenas da API"
	@echo "  logs-worker        - Mostra logs apenas dos workers"
	@echo ""
	@echo "🗄️  BANCO DE DADOS:"
	@echo "  migrate            - Executa migrações"
	@echo "  makemigrations     - Cria novas migrações"
	@echo "  nitapi_db    			- Acessa o banco via psql"
	@echo "  backup             - Cria backup do banco"
	@echo ""
	@echo "🧪 TESTES E QUALIDADE:"
	@echo "  test               - Executa todos os testes"
	@echo "  test-coverage      - Executa testes com cobertura"
	@echo "  ruff               - Linting com correção automática"
	@echo "  ruff-check         - Linting apenas verificação"
	@echo "  ruff-format        - Formatação de código"
	@echo "  quality-check      - Executa todas verificações"
	@echo "  pre-commit-install - Instala hooks do pre-commit"
	@echo "  pre-commit-all     - Executa pre-commit em tudo"
	@echo ""
	@echo "🎯 LINT HÍBRIDO (FUNCIONA EM QUALQUER AMBIENTE):"
	@echo "  lint-auto          - Lint + correções automáticas"
	@echo "  lint-check         - Verificação apenas (sem correção)"
	@echo "  lint-file FILE=... - Processa arquivo específico"
	@echo ""
	@echo "� DEPENDÊNCIAS:"
	@echo "  install-deps       - Instala dependências locais"
	@echo "  install-prod       - Instala dependências de produção"
	@echo "  install-test       - Instala dependências de teste"
	@echo "  deps-check         - Verifica conflitos de dependências"
	@echo "  deps-update        - Atualiza requirements.txt com versões atuais"
	@echo ""
	@echo "�🚀 ALIASES RÁPIDOS:"
	@echo "  lint/fix/format    - Alias para lint-auto"
	@echo "  check              - Alias para lint-check"
	@echo ""
	@echo "🚀 DEPLOY:"
	@echo "  deploy             - Executa deploy"
	@echo "  rollback           - Faz rollback da última versão"
	@echo "  status             - Mostra status dos containers"
	@echo ""
	@echo "🔧 DJANGO:"
	@echo "  collectstatic      - Coleta arquivos estáticos"
	@echo "  createsuperuser    - Cria superusuário"
	@echo "  checkdeploy        - Verifica configuração para deploy"

# Comando padrão quando executar apenas 'make'
.DEFAULT_GOAL := help

# --- COMANDOS PRINCIPAIS DE DESENVOLVIMENTO ---

# Garante que a rede do projeto exista
create-network:
	@docker network ls | grep -q "nitapi" || docker network create nitapi

# Gera um .env na raiz com BASE_URL extraída do ./.envs/.local/.django
prepare-env: create-network
	@if [ ! -f .env ]; then \
		echo "📄 Arquivo .env não encontrado. Criando um novo com valores padrão..."; \
		grep '^BASE_URL=' ./.envs/.local/.django > .env; \
		echo "API_IMAGE_NAME=$(IMAGE_NAME)" >> .env; \
		echo "API_IMAGE_TAG=$(CURRENT_VERSION)" >> .env; \
		echo "✅ Arquivo .env criado com sucesso."; \
	else \
		echo "ℹ️  Arquivo .env já existe. Nenhuma ação foi tomada."; \
	fi

# Constrói ou reconstrói TODOS os serviços, garantindo que a API use a tag de versão correta
build: prepare-env
	@echo "🔧 Construindo/recriando todos os serviços..."
	@echo "   A API usará a imagem: $(IMAGE_NAME):$(CURRENT_VERSION)"
	@export API_IMAGE_NAME=$(IMAGE_NAME); \
	export API_IMAGE_TAG=$(CURRENT_VERSION); \
	$(COMPOSE_CMD) -f $(yml) up --build -d --remove-orphans

# Inicia TODOS os containers, garantindo que a API use a imagem com a versão correta
start: prepare-env
	@echo "🚀 Iniciando todos os containers..."
	@echo "   A API usará a imagem: $(IMAGE_NAME):$(CURRENT_VERSION)"
	@export API_IMAGE_NAME=$(IMAGE_NAME); \
	export API_IMAGE_TAG=$(CURRENT_VERSION); \
	$(COMPOSE_CMD) -f $(yml) up -d

# Alias para start
up: start

# Para TODOS os containers
stop:
	@echo "🛑 Parando todos os containers..."
	@export API_IMAGE_NAME=$(IMAGE_NAME); \
	export API_IMAGE_TAG=$(CURRENT_VERSION); \
	$(COMPOSE_CMD) -f $(yml) down

# Alias para stop
down: stop

# Comando para visualizar o status
status:
	@echo "📦 Container em execução:"
	@docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" | grep nitapi
	@echo "\n🖼️ Imagens da aplicação e backups (ordenado por data):"
	@docker images nitapi-api --format "table {{.Repository}}\t{{.Tag}}\t{{.CreatedAt}}" | sort -k 3 -r

reload-api:
	${COMPOSE_CMD} -f ${yml} up -d --no-deps --build api

# Comando para ver os logs de TODOS os containers em tempo real
logs:
	@echo "📚 Mostrando logs de TODOS os serviços em tempo real... (Pressione Ctrl+C para sair)"
	@$(COMPOSE_CMD) -f $(yml) logs -f

# Comando para ver os logs APENAS da API em tempo real
logs-api:
	@echo "📄 Mostrando logs do container da API em tempo real... (Pressione Ctrl+C para sair)"
	@$(COMPOSE_CMD) -f $(yml) logs -f api

# Command to run the django migrate script
migrate:
	${COMPOSE_CMD} -f ${yml} run --rm api python3 manage.py migrate

# Command to run the django makemigrations script
makemigrations:
	${COMPOSE_CMD} -f ${yml} run --rm api python3 manage.py makemigrations

# Command to run the django collectstatic script
collectstatic:
	${COMPOSE_CMD} -f ${yml} run --rm api python3 manage.py collectstatic --no-input --clear

# Command to run the django createsuperuse script
createsuperuser:
	${COMPOSE_CMD} -f ${yml} run --rm api python3 manage.py createsuperuser

# Command to run the django test script
test:
	${COMPOSE_CMD} -f ${yml} run --rm api python3 manage.py test

# Comando para executar testes com cobertura
test-coverage:
	${COMPOSE_CMD} -f ${yml} run --rm api coverage run --source='.' manage.py test
	${COMPOSE_CMD} -f ${yml} run --rm api coverage report
	${COMPOSE_CMD} -f ${yml} run --rm api coverage html

# Comando para instalar e configurar pre-commit hooks
pre-commit-install:
	pre-commit install

# Comando para executar pre-commit em todos os arquivos
pre-commit-all:
	pre-commit run --all-files

# Comando para atualizar pre-commit hooks
pre-commit-update:
	pre-commit autoupdate

# Command to stop the docker container and remove the named volume
down-v:
	${COMPOSE_CMD} -f ${yml} down -v

# Command to access the db
nitapi_db:
	${COMPOSE_CMD} -f ${yml} exec postgres psql --username=postgres --dbname=nitapi_db

# Criar backup do banco Postgres em ./backups com timestamp
backup:
	@echo "💾 Criando backup do Postgres..."
	@mkdir -p backups
	@if ${COMPOSE_CMD} -f ${yml} ps postgres | grep -q "Up"; then \
		FILE="backups/postgres_$(TIMESTAMP).dump.gz"; \
		echo "→ Gerando arquivo $$FILE"; \
		${COMPOSE_CMD} -f ${yml} exec -T postgres sh -lc 'export PGPASSWORD="$$POSTGRES_PASSWORD"; pg_dump -h localhost -p 5432 -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -F c -b' | gzip > $$FILE && \
		echo "✅ Backup concluído: $$FILE"; \
	else \
		echo "❌ O serviço postgres não está em execução. Inicie com 'make start'"; \
		exit 1; \
	fi

# --- FERRAMENTAS DE QUALIDADE DE CÓDIGO ---
# Ruff: linter e formatter moderno (substitui flake8, isort e black)
ruff:
	${COMPOSE_CMD} -f ${yml} exec api ruff check --fix .

# Ruff check apenas (sem correção automática)
ruff-check:
	${COMPOSE_CMD} -f ${yml} exec api ruff check .

# Ruff format (formatação de código)
ruff-format:
	${COMPOSE_CMD} -f ${yml} exec api ruff format .

# Executar todas as verificações de qualidade
quality-check: ruff-check ruff-format

# --- COMANDOS HÍBRIDOS (FUNCIONAM DENTRO E FORA DO CONTAINER) ---

# Detecta se está no container ou fora e executa o comando apropriado
lint-auto:
	@if [ -f /.dockerenv ]; then \
		echo "🐳 Executando dentro do container..."; \
		ruff check --fix --unsafe-fixes . && ruff format .; \
	elif command -v docker-compose >/dev/null 2>&1 && ${COMPOSE_CMD} -f ${yml} ps api | grep -q "Up"; then \
		echo "🚀 Executando via Docker Compose..."; \
		${COMPOSE_CMD} -f ${yml} exec api ruff check --fix --unsafe-fixes . && \
		${COMPOSE_CMD} -f ${yml} exec api ruff format .; \
	elif [ -f "./venv/bin/ruff" ]; then \
		echo "🐍 Executando no ambiente virtual local..."; \
		./venv/bin/ruff check --fix --unsafe-fixes . && ./venv/bin/ruff format . && ./venv/bin/black . --line-length 79; \
	else \
		echo "❌ Erro: Nenhum ambiente encontrado!"; \
		echo "💡 Instale as dependências ou inicie o container"; \
		exit 1; \
	fi

# Verificação apenas (sem correção) - funciona em qualquer ambiente
lint-check:
	@if [ -f /.dockerenv ]; then \
		echo "🐳 Verificando código dentro do container..."; \
		ruff check .; \
	elif command -v docker-compose >/dev/null 2>&1 && ${COMPOSE_CMD} -f ${yml} ps api | grep -q "Up"; then \
		echo "🚀 Verificando código via Docker Compose..."; \
		${COMPOSE_CMD} -f ${yml} exec api ruff check .; \
	elif [ -f "./venv/bin/ruff" ]; then \
		echo "🐍 Verificando código no ambiente virtual local..."; \
		./venv/bin/ruff check . && ./venv/bin/mypy . --ignore-missing-imports; \
	else \
		echo "❌ Erro: Nenhum ambiente encontrado!"; \
		echo "💡 Instale as dependências ou inicie o container"; \
		exit 1; \
	fi

# Comando para arquivo específico - funciona em qualquer ambiente
lint-file:
	@if [ -z "$(FILE)" ]; then \
		echo "❌ Erro: Especifique o arquivo com FILE=caminho/arquivo.py"; \
		echo "💡 Exemplo: make lint-file FILE=tools/utils.py"; \
		exit 1; \
	fi; \
	if [ -f /.dockerenv ]; then \
		echo "🐳 Processando $(FILE) dentro do container..."; \
		ruff check --fix --unsafe-fixes $(FILE) && ruff format $(FILE); \
	elif command -v docker-compose >/dev/null 2>&1 && ${COMPOSE_CMD} -f ${yml} ps api | grep -q "Up"; then \
		echo "🚀 Processando $(FILE) via Docker Compose..."; \
		${COMPOSE_CMD} -f ${yml} exec api ruff check --fix --unsafe-fixes $(FILE) && \
		${COMPOSE_CMD} -f ${yml} exec api ruff format $(FILE); \
	elif [ -f "./venv/bin/ruff" ]; then \
		echo "🐍 Processando $(FILE) no ambiente virtual local..."; \
		./venv/bin/ruff check --fix --unsafe-fixes $(FILE) && ./venv/bin/ruff format $(FILE) && ./venv/bin/black $(FILE) --line-length 79; \
	else \
		echo "❌ Erro: Nenhum ambiente encontrado!"; \
		echo "💡 Instale as dependências ou inicie o container"; \
		exit 1; \
	fi

# --- COMANDOS DE DEPENDÊNCIAS ---

# Instalar dependências para desenvolvimento local
install-deps:
	@echo "📦 Instalando dependências para desenvolvimento..."
	@./scripts/install-requirements.sh local

# Instalar dependências para produção
install-prod:
	@echo "📦 Instalando dependências para produção..."
	@./scripts/install-requirements.sh production

# Instalar dependências para testes
install-test:
	@echo "📦 Instalando dependências para testes..."
	@./scripts/install-requirements.sh test

# Verificar conflitos de dependências
deps-check:
	@echo "🔍 Verificando conflitos de dependências..."
	@if command -v pip >/dev/null 2>&1; then \
		pip check; \
	elif [ -f "/.dockerenv" ] || [ -n "$$DOCKER_CONTAINER" ]; then \
		${COMPOSE_CMD} -f ${yml} exec api pip check; \
	else \
		echo "❌ Pip não encontrado e não está em container"; \
		exit 1; \
	fi

# Atualizar requirements.txt com versões instaladas
deps-update:
	@echo "📝 Atualizando requirements com versões atuais..."
	@if command -v pip >/dev/null 2>&1; then \
		pip freeze > requirements/current-freeze.txt; \
		echo "✅ Versões atuais salvas em requirements/current-freeze.txt"; \
	elif [ -f "/.dockerenv" ] || [ -n "$$DOCKER_CONTAINER" ]; then \
		${COMPOSE_CMD} -f ${yml} exec api pip freeze > requirements/current-freeze.txt; \
		echo "✅ Versões atuais salvas em requirements/current-freeze.txt"; \
	else \
		echo "❌ Pip não encontrado e não está em container"; \
		exit 1; \
	fi

# Verificar se retry service está funcionando
deps-test-retry:
	@echo "🔄 Testando retry service..."
	@if command -v python >/dev/null 2>&1; then \
		python -c "from tools.retry_service import CEPService, retry_metrics; print('✅ Retry service funcionando!')"; \
	elif [ -f "/.dockerenv" ] || [ -n "$$DOCKER_CONTAINER" ]; then \
		${COMPOSE_CMD} -f ${yml} exec api python -c "from tools.retry_service import CEPService, retry_metrics; print('✅ Retry service funcionando!')"; \
	else \
		echo "❌ Python não encontrado e não está em container"; \
		exit 1; \
	fi

# --- ALIASES PARA CONVENIÊNCIA ---
# Aliases para os comandos mais usados
lint: lint-auto
fix: lint-auto
check: lint-check
format: lint-auto
