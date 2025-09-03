FROM python:3.11-slim

RUN pip install flower

COPY ./docker/local/flower/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
