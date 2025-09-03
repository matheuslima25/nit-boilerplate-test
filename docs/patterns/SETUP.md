# Configuração do Tenacity para o Projeto NIT-API

## 📋 Instalação

Adicione o Tenacity ao arquivo de requirements:

```bash
# requirements/base.txt
tenacity>=8.0.0
```

## ⚙️ Configuração no Django Settings

```python
# settings/base.py

# Configuração de logging para Tenacity
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'retry_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'nitapi/logs/retry.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'tenacity': {
            'handlers': ['retry_file'],
            'level': 'INFO',
            'propagate': True,
        },
        'tools.retry_service': {
            'handlers': ['retry_file'],
            'level': 'WARNING',
            'propagate': True,
        },
    },
}

# Configurações específicas de retry para o projeto
RETRY_CONFIG = {
    # APIs externas (CEP, pagamento, etc.)
    'API_MAX_ATTEMPTS': 3,
    'API_BACKOFF_MULTIPLIER': 2,
    'API_MIN_WAIT': 1,
    'API_MAX_WAIT': 30,

    # Operações de banco de dados
    'DATABASE_MAX_ATTEMPTS': 5,
    'DATABASE_BACKOFF_MULTIPLIER': 1,
    'DATABASE_MIN_WAIT': 0.5,
    'DATABASE_MAX_WAIT': 10,

    # Upload de arquivos
    'FILE_MAX_ATTEMPTS': 3,
    'FILE_BACKOFF_MULTIPLIER': 3,
    'FILE_MIN_WAIT': 2,
    'FILE_MAX_WAIT': 60,
}
```

## 🚀 Como Usar no Projeto

### 1. Importar o Serviço

```python
from tools.retry_service import (
    api_retry, database_retry, file_retry,
    CEPService, ExternalAPIClient, retry_metrics
)
```

### 2. Usar Decorators

```python
# Para chamadas de API externa
@api_retry
def consultar_api_externa():
    response = requests.get("https://api.externa.com/dados")
    return response.json()

# Para operações de banco críticas
@database_retry
def executar_query_complexa():
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM tabela_grande WHERE condicao_complexa")
        return cursor.fetchall()

# Para upload de arquivos
@file_retry
def upload_documento(arquivo):
    # Upload para S3 ou storage
    return storage.save(arquivo.name, arquivo)
```

### 3. Usar Classes de Serviço

```python
# Consulta de CEP
cep_service = CEPService()
endereco = cep_service.consultar("01310-100")

# API externa
api_client = ExternalAPIClient("https://api.pagamento.com")
dados = api_client.get("/transacoes/123")

# Queries com retry
from tools.retry_service import DatabaseQueryExecutor
db_executor = DatabaseQueryExecutor()
resultados = db_executor.execute_raw_query(
    "SELECT * FROM contracts WHERE status = %s",
    ["active"]
)
```

## 📊 Monitoramento

### Ver Métricas de Retry

```python
from tools.retry_service import retry_metrics

# Resumo geral
print(retry_metrics.get_summary())

# Taxa de sucesso específica
success_rate = retry_metrics.get_success_rate('consulta_cep')
print(f"Taxa de sucesso CEP: {success_rate:.2%}")

# Tentativas médias
avg_attempts = retry_metrics.get_avg_attempts('consulta_cep')
print(f"Tentativas médias: {avg_attempts:.1f}")
```

### Management Command para Monitoramento

```python
# management/commands/retry_stats.py
from django.core.management.base import BaseCommand
from tools.retry_service import retry_metrics

class Command(BaseCommand):
    help = 'Exibe estatísticas de retry do sistema'

    def handle(self, *args, **options):
        stats = retry_metrics.get_summary()

        self.stdout.write("📊 Estatísticas de Retry\n")

        for operation, data in stats.items():
            self.stdout.write(f"\n🔄 {operation}")
            self.stdout.write(f"  Total de chamadas: {data['total_calls']}")
            self.stdout.write(f"  Taxa de sucesso: {data['success_rate']:.2%}")
            self.stdout.write(f"  Tentativas médias: {data['avg_attempts']:.1f}")
            self.stdout.write(f"  Últimas 24h: {data['last_24h']}")
```

## 🔧 Personalização

### Configuração Customizada

```python
from tenacity import retry, stop_after_attempt, wait_exponential

# Retry customizado para operação específica
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=0.5, max=5),
    retry=retry_if_exception_type(SpecificException)
)
def operacao_especial():
    # Lógica específica
    pass
```

### Callback Personalizado

```python
def log_retry_personalizado(retry_state):
    """Log personalizado para debugging"""
    if retry_state.outcome.failed:
        exception = retry_state.outcome.exception()
        print(f"Tentativa {retry_state.attempt_number} falhou: {exception}")

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=1, max=30),
    after=log_retry_personalizado
)
def funcao_com_log_custom():
    pass
```

## ⚠️ Importante

### Quando NÃO usar retry

- ❌ Erros de validação de dados
- ❌ Erros de autenticação/autorização
- ❌ Erros 4xx (client errors)
- ❌ Operações não idempotentes críticas

### Quando usar retry

- ✅ Falhas de rede temporárias
- ✅ Timeouts de conexão
- ✅ Erros 5xx (server errors)
- ✅ Deadlocks de banco temporários
- ✅ Problemas de conectividade

## 📝 Exemplos de Integração

### Views Django

```python
from django.http import JsonResponse
from tools.retry_service import CEPService, api_retry

class EnderecoViewSet(ViewSet):

    def buscar_cep(self, request, cep):
        """Endpoint para consulta de CEP com retry automático"""
        try:
            cep_service = CEPService()
            endereco = cep_service.consultar(cep)

            if endereco:
                return JsonResponse(endereco)
            else:
                return JsonResponse(
                    {'error': 'CEP não encontrado'},
                    status=404
                )

        except ValueError as e:
            return JsonResponse(
                {'error': str(e)},
                status=400
            )
        except Exception as e:
            return JsonResponse(
                {'error': 'Erro interno do servidor'},
                status=500
            )
```

### Tasks Celery

```python
from celery import Celery
from tools.retry_service import api_retry, ExternalAPIClient

app = Celery('nit_tasks')

@app.task
@api_retry
def sincronizar_dados_externos(data_id):
    """Task para sincronizar dados com API externa"""
    api_client = ExternalAPIClient("https://api.fornecedor.com")

    dados = api_client.get(f"/dados/{data_id}")

    # Processar e salvar dados...
    return f"Dados {data_id} sincronizados com sucesso"
```

---

**📝 Nota**: Para mais detalhes, consulte a documentação completa em
`docs/patterns/tenacity-retry.md`
