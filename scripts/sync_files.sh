#!/bin/bash
set -e

# Define os diretórios como variáveis para clareza
APP_DIR=""
BACKUP_DIR=""
TEMP_DIR=""

echo "Iniciando processo de backup da versão atual em ${BACKUP_DIR}..."

# Verifica se o diretório de backup antigo já existe
if [ -d "$BACKUP_DIR" ]; then
    echo "Backup antigo encontrado. Removendo ${BACKUP_DIR}..."
    rm -rf "$BACKUP_DIR"
else
    echo "Nenhum backup antigo encontrado. Prosseguindo..."
fi

# Cria um novo backup da pasta de produção atual
echo "Criando novo backup da pasta ${APP_DIR}..."
rsync -a --delete \
  --exclude '/nitapi/logs' \
  --exclude '/nitapi/static' \
  --exclude '/nitapi/staticfiles' \
  --exclude '/nitapi/media' \
  --exclude '/.git' \
  --exclude '/.envs' \
  "${APP_DIR}/" "${BACKUP_DIR}/"
echo "✅ Backup concluído com sucesso em ${BACKUP_DIR}"

# Sincroniza os arquivos da pasta temporária para a pasta de produção
echo "Sincronizando novos arquivos de ${TEMP_DIR} para ${APP_DIR}..."
rsync -avz --delete \
  --exclude '.git/' \
  --exclude '.envs/' \
  --exclude 'nitapi/logs/' \
  --exclude 'nitapi/static/' \
  --exclude 'nitapi/staticfiles/' \
  --exclude 'nitapi/media/' \
  "${TEMP_DIR}/" "${APP_DIR}/"

echo "✅ Sincronização de arquivos concluída com sucesso."
