import os

from celery import Celery
from nitapi.settings.base import env

DEBUG = env.bool("DJANGO_DEBUG", False)  # type: ignore

if DEBUG:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nitapi.settings.local")
else:
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE", "nitapi.settings.production"
    )

app = Celery("nitapi")
app.config_from_object("django.conf:settings", namespace="CELERY")

# Descobrir tarefas automaticamente
app.autodiscover_tasks()

# Configurações de resiliência
app.conf.update(
    # Faz o worker tentar se reconectar automaticamente ao broker se não
    # conseguir conectar na primeira tentativa. Impede que o worker falhe
    # imediatamente na inicialização caso o broker ainda esteja subindo.
    broker_connection_retry_on_startup=True,

    # Define o número máximo de tentativas de reconexão ao broker após perder
    # a conexão. Se falhar 5 vezes seguidas, o worker encerra (importante para
    # permitir que o Docker reinicie o container).
    broker_connection_max_retries=5,

    # Define o intervalo (em segundos) de envio dos heartbeats para o broker.
    # Serve para monitorar se a conexão ainda está viva; se o heartbeat não for
    # recebido, a conexão é encerrada.
    broker_heartbeat=60,

    # Tempo máximo (em segundos) que o worker aguarda para tentar estabelecer
    # conexão com o broker. Se o broker não responder dentro desse tempo, é
    # considerado um erro de conexão.
    broker_connection_timeout=30,

    # Faz o Celery reconhecer a tarefa como "confirmada" (ACK) *apenas depois*
    # que ela for totalmente executada. Se o worker cair no meio da execução,
    # a tarefa volta para a fila e não é perdida.
    task_acks_late=True,

    # Se o worker for perdido (crash, conexão morta) durante a execução de uma
    # tarefa, o Celery rejeita a tarefa corretamente. Isso força o broker a
    # reenfileirar a tarefa para outro worker disponível.
    task_reject_on_worker_lost=True,

    # Define o tempo máximo (em segundos) que uma tarefa pode levar para ser
    # executada. Se a tarefa não for concluída dentro desse tempo, ela é
    # interrompida e considerada falha.
    task_time_limit=300,

    # Define o tempo máximo (em segundos) que uma tarefa pode levar para ser
    # executada antes de ser interrompida. Isso é útil para tarefas que podem
    # ser longas, mas ainda precisam ser monitoradas.
    task_soft_time_limit=280,
)
