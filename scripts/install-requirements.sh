#!/bin/bash

# Script de instalação e atualização de dependências - NIT API
# Usage: ./scripts/install-requirements.sh [local|production|test]

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funções de log
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar se estamos em um virtual environment
check_virtual_env() {
    if [[ -z "$VIRTUAL_ENV" ]]; then
        log_warning "Não detectamos um ambiente virtual ativo!"
        log_info "Recomendamos usar um ambiente virtual:"
        echo "  python -m venv venv"
        echo "  source venv/bin/activate  # Linux/Mac"
        echo "  venv\\Scripts\\activate     # Windows"
        echo ""
        read -p "Continuar mesmo assim? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        log_success "Ambiente virtual detectado: $VIRTUAL_ENV"
    fi
}

# Backup dos requirements atuais
backup_current() {
    local backup_dir="requirements/backup-$(date +%Y%m%d-%H%M%S)"

    if pip freeze > /dev/null 2>&1; then
        log_info "Criando backup dos packages atuais..."
        mkdir -p "$backup_dir"
        pip freeze > "$backup_dir/current-packages.txt"
        log_success "Backup salvo em: $backup_dir/current-packages.txt"
    fi
}

# Instalar requirements específicos
install_requirements() {
    local env_type="$1"
    local req_file=""

    case $env_type in
        "local")
            req_file="requirements/local.txt"
            log_info "Instalando dependências para desenvolvimento local..."
            ;;
        "production")
            req_file="requirements/production.txt"
            log_info "Instalando dependências para produção..."
            ;;
        "test")
            req_file="requirements/test.txt"
            log_info "Instalando dependências para testes..."
            ;;
        *)
            log_error "Ambiente inválido: $env_type"
            log_info "Uso: $0 [local|production|test]"
            exit 1
            ;;
    esac

    if [[ ! -f "$req_file" ]]; then
        log_error "Arquivo não encontrado: $req_file"
        exit 1
    fi

    log_info "Atualizando pip..."
    pip install --upgrade pip

    log_info "Instalando dependências de $req_file..."
    pip install -r "$req_file"

    log_success "Dependências instaladas com sucesso!"
}

# Verificar instalação
verify_installation() {
    log_info "Verificando instalação..."

    # Verificar conflitos
    if pip check > /dev/null 2>&1; then
        log_success "Nenhum conflito de dependências encontrado"
    else
        log_warning "Possíveis conflitos detectados:"
        pip check
    fi

    # Verificar importações principais
    python -c "
import sys
try:
    import tenacity
    print('✅ Tenacity importado com sucesso')

    import requests
    print('✅ Requests importado com sucesso')

    import django
    print('✅ Django importado com sucesso')

    # Verificar se consegue importar nosso retry_service
    try:
        from tools.retry_service import CEPService, api_retry
        print('✅ Retry service importado com sucesso')
    except ImportError as e:
        print(f'⚠️  Retry service não disponível: {e}')

    print('\\n📦 Versões principais:')
    print(f'   Tenacity: {tenacity.__version__}')
    print(f'   Requests: {requests.__version__}')
    print(f'   Django: {django.__version__}')

except ImportError as e:
    print(f'❌ Erro de importação: {e}')
    sys.exit(1)
"

    if [[ $? -eq 0 ]]; then
        log_success "Verificação concluída com sucesso!"
    else
        log_error "Falha na verificação!"
        exit 1
    fi
}

# Mostrar estatísticas
show_stats() {
    log_info "Estatísticas da instalação:"

    local total_packages=$(pip list | wc -l)
    echo "  📦 Total de packages: $((total_packages - 2))"  # -2 para remover header

    local requirements_count=$(cat requirements/*.txt | grep -v "^#" | grep -v "^-r" | grep -v "^$" | wc -l)
    echo "  📋 Requirements definidos: $requirements_count"

    echo "  💾 Espaço usado: $(du -sh $VIRTUAL_ENV 2>/dev/null | cut -f1 || echo 'N/A')"
}

# Função principal
main() {
    echo "🚀 NIT-API - Instalador de Dependências"
    echo "========================================"
    echo

    local env_type="${1:-local}"

    check_virtual_env
    backup_current
    install_requirements "$env_type"
    verify_installation
    show_stats

    echo
    log_success "Instalação concluída! 🎉"
    echo
    log_info "Próximos passos:"
    case $env_type in
        "local")
            echo "  🧪 Executar testes: pytest"
            echo "  🔍 Verificar lint: make lint"
            echo "  📚 Ver docs: mkdocs serve"
            echo "  🔄 Testar retry: python -c 'from tools.retry_service import CEPService; print(\"OK\")'"
            ;;
        "production")
            echo "  🚀 Iniciar servidor: gunicorn nitapi.wsgi"
            echo "  ⚙️  Coletar static: python manage.py collectstatic"
            echo "  🗃️  Executar migrations: python manage.py migrate"
            ;;
        "test")
            echo "  🧪 Executar testes: pytest"
            echo "  📊 Cobertura: pytest --cov"
            echo "  🔍 Lint: flake8"
            echo "  🛡️  Segurança: bandit -r ."
            ;;
    esac
}

# Executar se chamado diretamente
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
