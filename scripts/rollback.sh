#!/bin/bash
set -e

# Garante que a rede externa do Docker exista antes de qualquer outra coisa.
if ! docker network ls | grep -q "nitapi"; then
    echo "🔧 Rede 'nitapi' não encontrada. Criando..."
    docker network create nitapi
fi

echo "🔙 Iniciando rollback..."

# --- CONFIGURAÇÕES ---
IMAGE_NAME="nitapi-api"
SERVICE_NAME="api"
COMPOSE_FILE="local.yml"
VERSION_FILE="VERSION"

# --- LÓGICA DE ROLLBACK ---

# Lista todas as imagens versionadas, ordenadas da mais antiga para a mais nova
ALL_VERSIONS=$(docker images "${IMAGE_NAME}" --format "{{.Tag}}" | grep '^[0-9]' | sort -V)
IMAGE_COUNT=$(echo "$ALL_VERSIONS" | wc -l)

# Verifica se o rollback é possível (precisamos de pelo menos 2 versões)
if [ "$IMAGE_COUNT" -lt 2 ]; then
    echo "❌ Erro: Não há versões anteriores para realizar o rollback."
    exit 1
fi

# Identifica a versão atual (com problema) e a versão para a qual faremos o rollback
CURRENT_BAD_VERSION=$(echo "$ALL_VERSIONS" | tail -n 1)
ROLLBACK_TO_VERSION=$(echo "$ALL_VERSIONS" | tail -n 2 | head -n 1)

echo "♻️  Versão atual (a ser removida): ${CURRENT_BAD_VERSION}"
echo "♻️  Restaurando para a versão: ${ROLLBACK_TO_VERSION}"

# Exporta as variáveis para o docker-compose usar a versão de rollback
export API_IMAGE_NAME=${IMAGE_NAME}
export API_IMAGE_TAG=${ROLLBACK_TO_VERSION}

# Para e remove os containers da aplicação (api e worker)
echo "🛑 Parando e removendo containers atuais (api, celery-worker)..."
${COMPOSE_CMD} -f "${COMPOSE_FILE}" stop api celery-worker 2>&1
${COMPOSE_CMD} -f "${COMPOSE_FILE}" rm -f api celery-worker 2>&1

# Sobe os containers da aplicação com a imagem da versão de rollback
echo "✨ Subindo containers com a versão ${ROLLBACK_TO_VERSION}..."
${COMPOSE_CMD} -f "${COMPOSE_FILE}" up -d api celery-worker 2>&1

# --- ROTAÇÃO INVERSA ---
# Remove a imagem da versão que deu problema
echo "🗑️  Removendo a imagem da versão com falha: ${IMAGE_NAME}:${CURRENT_BAD_VERSION}"
docker rmi "${IMAGE_NAME}:${CURRENT_BAD_VERSION}" || echo "⚠️  Aviso: não foi possível remover a imagem ${CURRENT_BAD_VERSION}."

# Atualiza o arquivo de versão para refletir o estado atual
echo "📝 Atualizando arquivo VERSION para ${ROLLBACK_TO_VERSION}..."
echo "${ROLLBACK_TO_VERSION}" > "${VERSION_FILE}"

echo "✅ Rollback para a versão ${ROLLBACK_TO_VERSION} concluído com sucesso!"

echo "📝 Atualizando arquivo .env com a versão restaurada: ${ROLLBACK_TO_VERSION}"
ENV_FILE=".env"
if grep -q "^API_IMAGE_TAG=" "$ENV_FILE"; then
    sed -i "s/^API_IMAGE_TAG=.*/API_IMAGE_TAG=${ROLLBACK_TO_VERSION}/" "$ENV_FILE"
else
    echo "API_IMAGE_TAG=${ROLLBACK_TO_VERSION}" >> "$ENV_FILE"
fi

echo "✅ Rollback para a versão ${ROLLBACK_TO_VERSION} concluído com sucesso!"
