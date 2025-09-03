# Padrão de Retry Exponencial com Tenacity

## 📋 Índice

- [Visão Geral](#🎯-visão-geral)
- [Instalação](#🔧-instalação)
- [Configurações Básicas](#⚙️-configurações-básicas)
- [Padrões de Implementação](#🏗️-padrões-de-implementação)
- [Exemplos Práticos](#💡-exemplos-práticos)
- [Boas Práticas](#🎯-boas-práticas)
- [Integração com Django](#🔧-integração-com-django)

## 🎯 Visão Geral

O **Tenacity** é uma biblioteca Python que implementa retry com backoff exponencial,
permitindo reexecutar operações que podem falhar temporariamente (APIs externas,
conexões de rede, etc.) de forma elegante e configurável.

### Por que usar Tenacity?

- ✅ **Resiliência**: Torna aplicações mais robustas contra falhas temporárias
- ✅ **Configurável**: Múltiplas estratégias de retry e backoff
- ✅ **Observabilidade**: Logs e callbacks detalhados
- ✅ **Performance**: Evita sobrecarregar serviços com retries muito frequentes

## 🔧 Instalação

```bash
# Instalar via pip
pip install tenacity

# Ou adicionar ao requirements
echo "tenacity>=8.0.0" >> requirements/base.txt
```

## ⚙️ Configurações Básicas

### Retry Simples

```python
from tenacity import retry, stop_after_attempt

@retry(stop=stop_after_attempt(3))
def operacao_basica():
    """Reexecuta até 3 tentativas em caso de erro"""
    # Código que pode falhar
    pass
```

### Retry com Backoff Exponencial

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=60)
)
def operacao_com_backoff():
    """
    Retry com backoff exponencial:
    - Tentativa 1: imediata
    - Tentativa 2: 1s
    - Tentativa 3: 2s
    - Tentativa 4: 4s
    - Tentativa 5: 8s
    - Máximo: 60s entre tentativas
    """
    pass
```

### Retry Condicional

```python
from tenacity import retry, retry_if_exception_type, stop_after_attempt
import requests

@retry(
    retry=retry_if_exception_type((requests.RequestException, ConnectionError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=1, max=30)
)
def chamada_api():
    """Só reexecuta para erros de rede, não para 4xx"""
    response = requests.get("https://api.exemplo.com/dados")
    response.raise_for_status()
    return response.json()
```

## 🏗️ Padrões de Implementação

### 1. Classe de Configuração Centralizada

```python
# config/retry_config.py
from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception_type, before_sleep_log
)
import logging

logger = logging.getLogger(__name__)

class RetryConfig:
    """Configurações centralizadas de retry para diferentes cenários"""

    # Para APIs externas
    API_RETRY = {
        'stop': stop_after_attempt(3),
        'wait': wait_exponential(multiplier=2, min=1, max=30),
        'retry': retry_if_exception_type((
            requests.RequestException,
            ConnectionError,
            TimeoutError
        )),
        'before_sleep': before_sleep_log(logger, logging.WARNING)
    }

    # Para operações de banco de dados
    DATABASE_RETRY = {
        'stop': stop_after_attempt(5),
        'wait': wait_exponential(multiplier=1, min=0.5, max=10),
        'retry': retry_if_exception_type((
            OperationalError,
            InterfaceError
        )),
        'before_sleep': before_sleep_log(logger, logging.ERROR)
    }

    # Para uploads de arquivos
    FILE_UPLOAD_RETRY = {
        'stop': stop_after_attempt(3),
        'wait': wait_exponential(multiplier=3, min=2, max=60),
        'retry': retry_if_exception_type((
            ConnectionError,
            TimeoutError,
            OSError
        ))
    }

# Decorators prontos para uso
def api_retry(func):
    return retry(**RetryConfig.API_RETRY)(func)

def database_retry(func):
    return retry(**RetryConfig.DATABASE_RETRY)(func)

def file_retry(func):
    return retry(**RetryConfig.FILE_UPLOAD_RETRY)(func)
```

### 2. Context Manager para Retry

```python
# utils/retry_context.py
from contextlib import contextmanager
from tenacity import Retrying, stop_after_attempt, wait_exponential
import logging

logger = logging.getLogger(__name__)

@contextmanager
def retry_context(
    max_attempts=3,
    backoff_multiplier=2,
    min_wait=1,
    max_wait=60,
    exceptions=(Exception,)
):
    """
    Context manager para retry flexível.

    Example:
        with retry_context(max_attempts=3) as retryer:
            for attempt in retryer:
                with attempt:
                    # Código que pode falhar
                    result = operacao_perigosa()
    """
    retryer = Retrying(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(
            multiplier=backoff_multiplier,
            min=min_wait,
            max=max_wait
        ),
        retry=retry_if_exception_type(exceptions),
        reraise=True
    )

    try:
        yield retryer
    except Exception as e:
        logger.error(f"Todas as tentativas falharam: {e}")
        raise
```

### 3. Classe de Serviço com Retry

```python
# services/external_api_service.py
from typing import Dict, Any, Optional
import requests
from config.retry_config import api_retry
import logging

logger = logging.getLogger(__name__)

class ExternalAPIService:
    """Serviço para chamadas de API externa com retry automático"""

    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()

    @api_retry
    def get_data(self, endpoint: str, params: Optional[Dict] = None) -> Dict[Any, Any]:
        """
        Busca dados da API externa com retry automático.

        Args:
            endpoint: Endpoint da API (ex: '/users/123')
            params: Parâmetros de query opcionais

        Returns:
            Dict com dados da resposta JSON

        Raises:
            requests.RequestException: Após esgotar tentativas
        """
        url = f"{self.base_url}{endpoint}"

        logger.info(f"Chamando API: {url}")

        response = self.session.get(
            url,
            params=params,
            timeout=self.timeout
        )

        # Não faz retry para erros 4xx (client error)
        if 400 <= response.status_code < 500:
            logger.warning(f"Erro do cliente {response.status_code}: {url}")
            response.raise_for_status()

        # Faz retry para 5xx (server error) e problemas de rede
        response.raise_for_status()

        return response.json()

    @api_retry
    def post_data(self, endpoint: str, data: Dict[Any, Any]) -> Dict[Any, Any]:
        """Envia dados para API externa com retry automático"""
        url = f"{self.base_url}{endpoint}"

        logger.info(f"Enviando dados para: {url}")

        response = self.session.post(
            url,
            json=data,
            timeout=self.timeout
        )

        response.raise_for_status()
        return response.json()
```

## 💡 Exemplos Práticos

### 1. Upload para AWS S3

```python
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from config.retry_config import file_retry

class S3Uploader:
    def __init__(self):
        self.s3_client = boto3.client('s3')

    @file_retry
    def upload_file(self, file_path: str, bucket: str, key: str) -> str:
        """
        Upload de arquivo para S3 com retry automático.

        Faz retry apenas para erros transitórios, não para
        erros de autenticação ou permissão.
        """
        try:
            self.s3_client.upload_file(file_path, bucket, key)
            logger.info(f"Arquivo enviado com sucesso: s3://{bucket}/{key}")
            return f"s3://{bucket}/{key}"

        except NoCredentialsError:
            # Não faz retry para erro de credenciais
            logger.error("Credenciais AWS não configuradas")
            raise

        except ClientError as e:
            error_code = e.response['Error']['Code']

            # Não faz retry para erros de permissão
            if error_code in ['AccessDenied', 'InvalidAccessKeyId']:
                logger.error(f"Erro de permissão S3: {error_code}")
                raise

            # Faz retry para outros erros
            logger.warning(f"Erro temporário S3: {error_code}")
            raise
```

### 2. Consulta de API de CEP

```python
from typing import Optional
import requests
from config.retry_config import api_retry

class CEPService:
    """Serviço para consulta de CEP com fallback entre APIs"""

    def __init__(self):
        self.apis = [
            "https://viacep.com.br/ws/{}/json/",
            "https://cep.awesomeapi.com.br/json/{}",
            "https://ws.apicep.com/cep/{}.json"
        ]

    @api_retry
    def consultar_cep(self, cep: str) -> Optional[Dict[str, str]]:
        """
        Consulta CEP com retry e fallback entre múltiplas APIs.

        Args:
            cep: CEP para consulta (apenas números)

        Returns:
            Dict com dados do endereço ou None se não encontrado
        """
        cep_limpo = re.sub(r'\D', '', cep)

        if len(cep_limpo) != 8:
            raise ValueError("CEP deve ter 8 dígitos")

        for api_url in self.apis:
            try:
                url = api_url.format(cep_limpo)
                response = requests.get(url, timeout=10)

                if response.status_code == 200:
                    data = response.json()

                    # Verifica se CEP foi encontrado
                    if not data.get('erro') and data.get('logradouro'):
                        logger.info(f"CEP {cep} encontrado via {url}")
                        return self._normalizar_dados(data)

            except requests.RequestException as e:
                logger.warning(f"Erro na API {url}: {e}")
                continue

        logger.warning(f"CEP {cep} não encontrado em nenhuma API")
        return None

    def _normalizar_dados(self, data: Dict) -> Dict[str, str]:
        """Normaliza dados entre diferentes APIs"""
        return {
            'cep': data.get('cep', ''),
            'logradouro': data.get('logradouro', ''),
            'bairro': data.get('bairro', ''),
            'cidade': data.get('localidade', ''),
            'uf': data.get('uf', ''),
        }
```

### 3. Task Celery com Retry

```python
from celery import Celery
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

logger = logging.getLogger(__name__)

app = Celery('tasks')

@app.task(bind=True)
def processar_dados_externos(self, data_id: int):
    """
    Task Celery que combina retry do Celery com Tenacity
    para maximum controle sobre reexecuções.
    """

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=1, max=60),
        retry=retry_if_exception_type((ConnectionError, TimeoutError))
    )
    def _processar():
        # Lógica de processamento que pode falhar
        api_service = ExternalAPIService("https://api.externa.com")
        dados = api_service.get_data(f"/dados/{data_id}")

        # Processar dados...
        resultado = processar_dados(dados)

        return resultado

    try:
        return _processar()

    except Exception as exc:
        logger.error(f"Falha ao processar dados {data_id}: {exc}")

        # Usar retry do Celery para tentar novamente mais tarde
        raise self.retry(exc=exc, countdown=300, max_retries=3)
```

## 🎯 Boas Práticas

### 1. Configuração de Logs

```python
import logging
from tenacity import before_sleep_log, after_log

logger = logging.getLogger(__name__)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=1, max=30),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    after=after_log(logger, logging.INFO)
)
def operacao_com_logs():
    """
    Configuração completa de logs:
    - before_sleep: Log antes de cada retry
    - after: Log após sucesso ou falha final
    """
    pass
```

### 2. Callbacks Personalizados

```python
def log_retry_attempt(retry_state):
    """Callback personalizado para log de tentativas"""
    attempt_number = retry_state.attempt_number
    if retry_state.outcome.failed:
        exception = retry_state.outcome.exception()
        logger.warning(
            f"Tentativa {attempt_number} falhou: {exception}"
        )

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=60),
    after=log_retry_attempt
)
def operacao_com_callback():
    pass
```

### 3. Métricas e Monitoramento

```python
from typing import Dict
import time

class RetryMetrics:
    """Coleta métricas de retry para monitoramento"""

    def __init__(self):
        self.stats: Dict[str, list] = {}

    def record_attempt(self, operation: str, attempt: int, success: bool, duration: float):
        """Registra tentativa de operação"""
        if operation not in self.stats:
            self.stats[operation] = []

        self.stats[operation].append({
            'attempt': attempt,
            'success': success,
            'duration': duration,
            'timestamp': time.time()
        })

    def get_success_rate(self, operation: str) -> float:
        """Calcula taxa de sucesso de uma operação"""
        if operation not in self.stats:
            return 0.0

        attempts = self.stats[operation]
        successful = sum(1 for a in attempts if a['success'])

        return successful / len(attempts) if attempts else 0.0

# Singleton global
metrics = RetryMetrics()

def with_metrics(operation_name: str):
    """Decorator para coletar métricas de retry"""
    def decorator(func):
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=2, min=1, max=30)
        )
        def wrapper(*args, **kwargs):
            start_time = time.time()
            attempt = 1

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                metrics.record_attempt(
                    operation_name, attempt, True, duration
                )

                return result

            except Exception as e:
                duration = time.time() - start_time

                metrics.record_attempt(
                    operation_name, attempt, False, duration
                )

                raise

        return wrapper
    return decorator
```

## 🔧 Integração com Django

### 1. Middleware de Retry para Views

```python
# middleware/retry_middleware.py
from django.http import JsonResponse
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

logger = logging.getLogger(__name__)

class APIRetryMiddleware:
    """
    Middleware que adiciona retry automático para views de API
    que fazem chamadas externas.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Aplicar retry apenas para endpoints de API
        if request.path.startswith('/api/'):
            return self._handle_with_retry(request)

        return self.get_response(request)

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=0.5, max=5),
        retry=retry_if_exception_type((ConnectionError, TimeoutError))
    )
    def _handle_with_retry(self, request):
        try:
            return self.get_response(request)
        except (ConnectionError, TimeoutError) as e:
            logger.warning(f"Erro de conectividade em {request.path}: {e}")
            raise
        except Exception as e:
            # Não faz retry para outros tipos de erro
            logger.error(f"Erro não recuperável em {request.path}: {e}")
            return JsonResponse(
                {'error': 'Erro interno do servidor'},
                status=500
            )
```

### 2. Management Command com Retry

```python
# management/commands/sync_external_data.py
from django.core.management.base import BaseCommand
from tenacity import retry, stop_after_attempt, wait_exponential
from myapp.services import ExternalAPIService

class Command(BaseCommand):
    help = 'Sincroniza dados de API externa com retry automático'

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=1, max=120)
    )
    def handle(self, *args, **options):
        api_service = ExternalAPIService()

        try:
            dados = api_service.get_data('/dados-importantes')
            self._processar_dados(dados)

            self.stdout.write(
                self.style.SUCCESS('Sincronização concluída com sucesso')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Erro na sincronização: {e}')
            )
            raise

    def _processar_dados(self, dados):
        # Lógica de processamento
        pass
```

### 3. Configuração no Django Settings

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
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/retry.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'tenacity': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
        'config.retry_config': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': True,
        },
    },
}

# Configurações específicas de retry
RETRY_CONFIG = {
    'API_MAX_ATTEMPTS': 3,
    'API_BACKOFF_MULTIPLIER': 2,
    'API_MIN_WAIT': 1,
    'API_MAX_WAIT': 60,
    'DATABASE_MAX_ATTEMPTS': 5,
    'DATABASE_BACKOFF_MULTIPLIER': 1,
    'DATABASE_MIN_WAIT': 0.5,
    'DATABASE_MAX_WAIT': 10,
}
```

## 📊 Checklist de Implementação

### ✅ Configuração Inicial

- [ ] Tenacity instalado e configurado
- [ ] Logs configurados para retry attempts
- [ ] Configurações centralizadas criadas
- [ ] Métricas de monitoramento implementadas

### ✅ Padrões de Retry

- [ ] API externa: 3 tentativas, backoff exponencial
- [ ] Banco de dados: 5 tentativas, backoff linear
- [ ] Upload de arquivos: 3 tentativas, backoff alto
- [ ] Operações críticas: configuração personalizada

### ✅ Tratamento de Erros

- [ ] Retry apenas para erros transitórios
- [ ] Sem retry para erros 4xx (client error)
- [ ] Sem retry para erros de autenticação
- [ ] Logs detalhados de tentativas

### ✅ Monitoramento

- [ ] Métricas de taxa de sucesso
- [ ] Alertas para alta taxa de retry
- [ ] Dashboard de monitoramento
- [ ] Logs centralizados

---

**📝 Nota**: Esta documentação deve ser atualizada conforme novos padrões
de retry são identificados e implementados no projeto.
