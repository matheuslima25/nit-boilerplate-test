#!/bin/bash
set -e

# Define o limite aceitável de uso do disco
THRESHOLD=90

echo "Verificando espaço em disco no filesystem raiz (/). Limite: ${THRESHOLD}%"

CURRENT_USAGE=$(df --output=pcent / | tail -n 1 | tr -d ' %')

echo "Uso atual do disco: ${CURRENT_USAGE}%"

if [ "$CURRENT_USAGE" -gt "$THRESHOLD" ]; then
  echo "##[error]Espaço em disco crítico! Uso em ${CURRENT_USAGE}%, que é maior que o limite de ${THRESHOLD}%. Abortando o deploy."
  exit 1
fi

echo "✅ Espaço em disco está OK."