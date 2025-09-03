#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

export CELERY_BROKER_URL="pyamqp://${RABBITMQ_DEFAULT_USER}:${RABBITMQ_DEFAULT_PASS}@rabbitmq//"

echo "Iniciando Flower com broker: $CELERY_BROKER_URL"
echo "Acesso: http://${FLOWER_USER}:${FLOWER_PASSWORD}@flower:5555"

exec celery --broker="$CELERY_BROKER_URL" flower \
    --port=5555 \
    --basic_auth="${FLOWER_USER}:${FLOWER_PASSWORD}"