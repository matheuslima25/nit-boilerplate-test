#!/bin/bash
set -e

# Garante que a rede externa do Docker exista.
if ! docker network ls | grep -q "nitapi"; then
    echo "🔧 Rede 'nitapi' não encontrada. Criando..."
    docker network create nitapi
fi

# Carrega as variáveis do arquivo .env se ele existir
if [ -f ./.envs/.local/.django ]; then
    echo "📦 Carregando variáveis de ambiente de ./.envs/.local/.django..."
    # O comando set -a exporta automaticamente as variáveis que o source define
    set -a
    source ./.envs/.local/.django
    set +a

    # Gera o .env com BASE_URL para uso no docker-compose.yml
    echo "🔄 Gerando .env na raiz com BASE_URL..."
    grep '^BASE_URL=' ./.envs/.local/.django > .env
fi

# --- CONFIGURAÇÕES ---
IMAGE_NAME="nitapi-api"
SERVICE_NAME="api"
COMPOSE_FILE="local.yml"
MAX_IMAGES=5

# --- LÓGICA DE VERSIONAMENTO ---
VERSION_FILE="VERSION"
if [ ! -f "$VERSION_FILE" ]; then echo "1.0.0" > "$VERSION_FILE"; fi
CURRENT_VERSION=$(cat "$VERSION_FILE")
NEW_VERSION=""
if [ -n "$1" ]; then
    NEW_VERSION="$1.0"
else
    IFS='.' read -r -a version_parts <<< "$CURRENT_VERSION"
    version_parts[2]=$((version_parts[2] + 1))
    NEW_VERSION="${version_parts[0]}.${version_parts[1]}.${version_parts[2]}"
fi

# --- ATUALIZAÇÃO DO ARQUIVO DE VERSÃO ---
echo "$NEW_VERSION" > "$VERSION_FILE"

echo "🚀 Iniciando deploy da versão: $NEW_VERSION (versão anterior: $CURRENT_VERSION)"

# --- BUILD DA NOVA IMAGEM ---
echo "🔧 Construindo a nova imagem: ${IMAGE_NAME}:${NEW_VERSION}..."
docker build --no-cache -f ./docker/local/django/Dockerfile -t "${IMAGE_NAME}:${NEW_VERSION}" . 2>&1

# --- DEPLOY (Substituição do Container) ---
export API_IMAGE_NAME=${IMAGE_NAME}
export API_IMAGE_TAG=${NEW_VERSION}

echo "🛑 Parando e removendo o container antigo ('${SERVICE_NAME}' e 'celery-worker')..."
${COMPOSE_CMD} -f "${COMPOSE_FILE}" stop "${SERVICE_NAME}" celery-worker 2>&1
${COMPOSE_CMD} -f "${COMPOSE_FILE}" rm -f "${SERVICE_NAME}" celery-worker 2>&1

echo "✨ Subindo novo containers com a imagem ${IMAGE_NAME}:${NEW_VERSION} e 2 workers..."
${COMPOSE_CMD} -f "${COMPOSE_FILE}" up -d --scale celery-worker=2 "${SERVICE_NAME}" celery-worker 2>&1

# Adiciona um período de tolerância para os serviços iniciarem antes de verificar.
echo "⏳ Dando 30 segundos para os serviços iniciarem antes de começar a verificação..."
sleep 30

# --- VERIFICAÇÃO DE SAÚDE (HEALTH CHECK) ---
echo "🩺  Aguardando a aplicação ficar saudável..."

# Constrói a URL de health check a partir da variável de ambiente BASE_URL, com um valor padrão
HEALTH_CHECK_URL="${BASE_URL:-http://localhost:8000}/health/"
TIMEOUT_SECONDS=120
INTERVAL_SECONDS=5
ELAPSED_SECONDS=0
IS_HEALTHY=false

# Assume que seu endpoint /health/ retorna um JSON e queremos que todas as chaves tenham o valor "working"
while [ $ELAPSED_SECONDS -lt $TIMEOUT_SECONDS ]; do
    # Usamos -s para modo silencioso, -f para falhar em erros de HTTP (ex: 404, 500)
    # E -H para adicionar o header que pede uma resposta JSON
    if curl -sf -H "Accept: application/json" ${HEALTH_CHECK_URL} | jq -e 'all(.[]; . == "working")' > /dev/null; then
        echo "✅ Aplicação está saudável!"
        IS_HEALTHY=true
        break
    else
        echo "   ...aguardando ${INTERVAL_SECONDS}s..."
        sleep ${INTERVAL_SECONDS}
        ELAPSED_SECONDS=$((ELAPSED_SECONDS + INTERVAL_SECONDS))
    fi
done

if [ "$IS_HEALTHY" = false ]; then
    echo "❌ Erro: A aplicação não ficou saudável após ${TIMEOUT_SECONDS} segundos."
    echo "   Logs do container '${SERVICE_NAME}' com problema:"
    
    # Obtém dinamicamente o ID do container em execução para o serviço especificado
    API_CONTAINER_ID=$(${COMPOSE_CMD} -f "${COMPOSE_FILE}" ps -q "${SERVICE_NAME}")
    
    # Usa o ID do container para buscar os logs, se o ID foi encontrado
    if [ -n "$API_CONTAINER_ID" ]; then
        docker logs "${API_CONTAINER_ID}" --tail 50
    else
        echo "   Não foi possível encontrar um container em execução para o serviço '${SERVICE_NAME}'."
    fi
    
    exit 1
fi

# <<< LÓGICA DE LIMPEZA E ROTAÇÃO DE IMAGENS >>>
echo "🔁 Verificando e rotacionando imagens antigas (mantendo as ${MAX_IMAGES} mais recentes)..."

# Lista todas as imagens da aplicação que têm uma tag de versão numérica.
# 'sort -V' ordena corretamente as versões (ex: 1.9.0 antes de 1.10.0).
ALL_VERSIONED_IMAGES=$(docker images "${IMAGE_NAME}" --format "{{.Repository}}:{{.Tag}}" | grep ':[0-9]' | sort -V)

# Conta o número total de imagens versionadas
NUM_IMAGES=$(echo "$ALL_VERSIONED_IMAGES" | wc -l)
echo "🖼️  Encontradas ${NUM_IMAGES} imagens versionadas. O limite é ${MAX_IMAGES}."

# Se o número de imagens for maior que o limite, removemos as mais antigas
if [ "$NUM_IMAGES" -gt "$MAX_IMAGES" ]; then
    # Calcula quantas imagens precisam ser removidas
    TO_DELETE_COUNT=$((NUM_IMAGES - MAX_IMAGES))
    
    # Seleciona as imagens mais antigas para remover (as primeiras da lista ordenada por versão)
    IMAGES_TO_DELETE=$(echo "$ALL_VERSIONED_IMAGES" | head -n $TO_DELETE_COUNT)
    
    echo "🗑️  Removendo ${TO_DELETE_COUNT} imagem(ns) mais antiga(s)..."
    for image in $IMAGES_TO_DELETE; do
        # Medida de segurança: nunca tentar remover a imagem que acabamos de colocar no ar.
        if [ "$image" != "${IMAGE_NAME}:${NEW_VERSION}" ]; then
            echo "   - Removendo ${image}"
            docker rmi "$image" || echo "   - Aviso: não foi possível remover ${image} (pode estar em uso por um container parado)."
        else
            echo "   - Pulando a remoção da imagem atualmente ativa: ${image}"
        fi
    done
fi

echo "✅ Deploy da versão ${NEW_VERSION} concluído com sucesso!"

echo "📝 Atualizando arquivo .env com a nova versão: ${NEW_VERSION}"
ENV_FILE=".env"
# Garante que a linha API_IMAGE_NAME exista
if ! grep -q "^API_IMAGE_NAME=" "$ENV_FILE"; then
    echo "API_IMAGE_NAME=${IMAGE_NAME}" >> "$ENV_FILE"
fi
# Atualiza a tag da versão. Se a linha não existir, ela é adicionada.
if grep -q "^API_IMAGE_TAG=" "$ENV_FILE"; then
    sed -i "s/^API_IMAGE_TAG=.*/API_IMAGE_TAG=${NEW_VERSION}/" "$ENV_FILE"
else
    echo "API_IMAGE_TAG=${NEW_VERSION}" >> "$ENV_FILE"
fi
