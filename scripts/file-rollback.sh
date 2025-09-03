#!/bin/bash
set -e

APP_DIR=""
BACKUP_DIR=""

echo "🚨 A sincronização de arquivos falhou! Iniciando rollback dos arquivos."

# Verifica se a pasta de backup existe antes de tentar o rollback
if [ -d "$BACKUP_DIR" ]; then
    echo "Pasta de backup encontrada. Restaurando de ${BACKUP_DIR}..."
    # Usamos rsync para garantir uma cópia espelhada, limpando arquivos parciais do deploy falho.
    # <<< CORREÇÃO CRÍTICA AQUI >>>
    # Adicionamos as mesmas exclusões do script de backup para proteger as pastas.
    rsync -a --delete \
      --exclude '/nitapi/logs' \
      --exclude '/nitapi/static' \
      --exclude '/nitapi/staticfiles' \
      --exclude '/nitapi/media' \
      --exclude '/.git' \
      --exclude '/.envs' \
      "${BACKUP_DIR}/" "${APP_DIR}/"

    echo "✅ Rollback de arquivos concluído. O estado anterior do código-fonte foi restaurado."
else
    echo "⚠️ Aviso: Nenhuma pasta de backup foi encontrada (${BACKUP_DIR}). Não foi possível reverter os arquivos."
    # Falha o job para deixar claro que a recuperação não foi possível
    exit 1
fi
