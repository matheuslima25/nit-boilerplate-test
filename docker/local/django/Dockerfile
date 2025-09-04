ARG PYTHON_VERSION=3.11-slim
FROM python:${PYTHON_VERSION} AS python

FROM python AS python-build-stage
ARG BUILD_ENVIRONMENT=local

RUN apt-get update && apt-get install --no-install-recommends -y \
   build-essential \
   libpq-dev


COPY ./requirements .

# Instalar dependências
RUN pip wheel --wheel-dir /usr/src/app/wheels \
   -r ${BUILD_ENVIRONMENT}.txt


FROM python AS python-run-stage
ARG BUILD_ENVIRONMENT=local
ARG APP_HOME=/app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV BUILD_ENV=${BUILD_ENVIRONMENT}

WORKDIR ${APP_HOME}

RUN apt-get update && apt-get install --no-install-recommends -y \
   libpq-dev \
   gettext \
   gcc \
   binutils \
   libproj-dev \
   cron \
   curl

COPY --from=python-build-stage /usr/src/app/wheels /wheels/

# Instala as dependências do Django
RUN pip install --no-cache-dir --no-index --find-links=/wheels/ /wheels/* \
   && rm -rf /wheels/

# Copiar os scripts de inicialização
COPY ./docker/local/django/entrypoint /entrypoint
RUN sed -i 's/\r$//g' /entrypoint
RUN chmod +x /entrypoint

COPY ./docker/local/django/start /start
RUN sed -i 's/\r$//g' /start
RUN chmod +x /start

# Copiar o arquivo de crontab (caso necessário)
COPY ./docker/local/django/crontab /etc/cron.d/crontab

# Dá permissões adequadas ao arquivo de crontab
RUN chmod 0644 /etc/cron.d/crontab

# Cria o diretório para armazenar logs do cron
RUN mkdir -p /var/log/cron

# Redireciona a saída padrão do cron para o arquivo de log
RUN touch /var/log/cron.log

# Instala o crontab
RUN crontab /etc/cron.d/crontab
RUN service cron start

COPY . ${APP_HOME}

ENTRYPOINT ["/entrypoint"]

# Executar aplicação como usuário sem privilégios
# Cria o grupo e usuário com UID/GID 1001 (mesmo usado no docker-compose)
RUN groupadd -g 1001 appgroup && useradd -u 1001 -g 1001 -ms /bin/bash appuser
USER appuser
