"""Exemplo prático de implementação do padrão Tenacity no projeto NIT-API.

Este módulo demonstra como implementar retry exponencial para diferentes
cenários comuns no projeto, seguindo as melhores práticas documentadas.
"""

import logging
import time
from typing import Dict, Any, Optional, List
from functools import wraps

import requests
from django.db import OperationalError, InterfaceError
from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception_type, before_sleep_log, after_log
)

logger = logging.getLogger(__name__)


class RetryConfig:
    """Configurações centralizadas de retry para diferentes cenários
    do projeto.

    Baseado na documentação docs/patterns/tenacity-retry.md
    """

    # Configuração para APIs externas (CEP, pagamento, etc.)
    API_EXTERNAL = {
        'stop': stop_after_attempt(3),
        'wait': wait_exponential(multiplier=2, min=1, max=30),
        'retry': retry_if_exception_type((
            requests.RequestException,
            ConnectionError,
            TimeoutError
        )),
        'before_sleep': before_sleep_log(logger, logging.WARNING),
        'after': after_log(logger, logging.INFO)
    }

    # Configuração para operações de banco de dados
    DATABASE = {
        'stop': stop_after_attempt(5),
        'wait': wait_exponential(multiplier=1, min=0.5, max=10),
        'retry': retry_if_exception_type((
            OperationalError,
            InterfaceError
        )),
        'before_sleep': before_sleep_log(logger, logging.ERROR)
    }

    # Configuração para uploads de arquivos
    FILE_UPLOAD = {
        'stop': stop_after_attempt(3),
        'wait': wait_exponential(multiplier=3, min=2, max=60),
        'retry': retry_if_exception_type((
            ConnectionError,
            TimeoutError,
            OSError
        ))
    }


# Decorators prontos para uso no projeto
def api_retry(func):
    """Decorator para chamadas de API externa com retry automático.

    Uso:
        @api_retry
        def buscar_cep(cep: str):
            response = requests.get(f"https://viacep.com.br/ws/{cep}/json/")
            return response.json()
    """
    return retry(**RetryConfig.API_EXTERNAL)(func)


def database_retry(func):
    """Decorator para operações de banco com retry automático.

    Uso:
        @database_retry
        def executar_query_complexa():
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM tabela_grande")
                return cursor.fetchall()
    """
    return retry(**RetryConfig.DATABASE)(func)


def file_retry(func):
    """Decorator para uploads de arquivo com retry automático.

    Uso:
        @file_retry
        def upload_para_s3(arquivo):
            s3_client.upload_file(arquivo, bucket, key)
    """
    return retry(**RetryConfig.FILE_UPLOAD)(func)


class CEPService:
    """Serviço para consulta de CEP com retry e fallback entre APIs.

    Implementa o padrão de retry exponencial para múltiplas APIs
    de CEP, garantindo alta disponibilidade.
    """

    def __init__(self):
        self.apis = [
            "https://viacep.com.br/ws/{}/json/",
            "https://cep.awesomeapi.com.br/json/{}",
            "https://ws.apicep.com/cep/{}.json"
        ]
        self.timeout = 10

    @api_retry
    def consultar(self, cep: str) -> Optional[Dict[str, str]]:
        """Consulta CEP com retry automático e fallback entre APIs.

        Args:
            cep: CEP para consulta (com ou sem formatação)

        Returns:
            Dict com dados do endereço ou None se não encontrado

        Raises:
            ValueError: Se CEP tem formato inválido
            requests.RequestException: Se todas as tentativas falharam

        """
        import re

        # Limpar CEP
        cep_limpo = re.sub(r'\D', '', cep)

        if len(cep_limpo) != 8:
            raise ValueError("CEP deve ter 8 dígitos")

        # Tentar cada API em sequência
        for api_url in self.apis:
            try:
                url = api_url.format(cep_limpo)
                logger.info(f"Consultando CEP {cep} via {url}")

                response = requests.get(url, timeout=self.timeout)

                if response.status_code == 200:
                    data = response.json()

                    # Verificar se CEP foi encontrado
                    if not data.get('erro') and data.get('logradouro'):
                        logger.info(f"CEP {cep} encontrado via {url}")
                        return self._normalizar_dados(data)

            except requests.RequestException as e:
                logger.warning(f"Erro na API {url}: {e}")
                # Continua para próxima API
                continue

        logger.warning(f"CEP {cep} não encontrado em nenhuma API")
        return None

    def _normalizar_dados(self, data: Dict) -> Dict[str, str]:
        """Normaliza dados entre diferentes APIs de CEP."""
        return {
            'cep': data.get('cep', ''),
            'logradouro': data.get('logradouro', ''),
            'bairro': data.get('bairro', ''),
            'cidade': data.get('localidade', data.get('city', '')),
            'uf': data.get('uf', data.get('state', '')),
        }


class ExternalAPIClient:
    """Cliente genérico para APIs externas com retry configurável.

    Fornece interface padronizada para chamadas HTTP com
    retry automático e logging detalhado.
    """

    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()

        # Headers padrão
        self.session.headers.update({
            'User-Agent': 'NIT-API/v1',
            'Accept': 'application/json'
        })

    @api_retry
    def get(
        self,
        endpoint: str,
        params: Optional[Dict] = None
    ) -> Dict[Any, Any]:
        """GET request com retry automático.

        Args:
            endpoint: Endpoint da API (ex: '/users/123')
            params: Parâmetros de query opcionais

        Returns:
            Dict com resposta JSON

        """
        url = f"{self.base_url}{endpoint}"

        logger.info(f"GET {url} params={params}")

        response = self.session.get(
            url,
            params=params,
            timeout=self.timeout
        )

        # Não faz retry para erros 4xx (client error)
        if 400 <= response.status_code < 500:
            logger.warning(f"Client error {response.status_code}: {url}")
            response.raise_for_status()

        # Faz retry para 5xx (server error)
        response.raise_for_status()

        return response.json()

    @api_retry
    def post(self, endpoint: str, data: Dict[Any, Any]) -> Dict[Any, Any]:
        """POST request com retry automático."""
        url = f"{self.base_url}{endpoint}"

        logger.info(f"POST {url}")

        response = self.session.post(
            url,
            json=data,
            timeout=self.timeout
        )

        # Mesma lógica de retry do GET
        if 400 <= response.status_code < 500:
            logger.warning(f"Client error {response.status_code}: {url}")
            response.raise_for_status()

        response.raise_for_status()
        return response.json()


class DatabaseQueryExecutor:
    """Executor de queries SQL com retry para operações críticas.

    Usado para queries que podem falhar por problemas transitórios
    de conectividade ou concorrência no banco.
    """

    @database_retry
    def execute_raw_query(
        self,
        query: str,
        params: Optional[List] = None
    ) -> List[Dict[str, Any]]:
        """Executa query SQL raw com retry automático.

        Args:
            query: Query SQL a ser executada
            params: Parâmetros para a query

        Returns:
            Lista de dicts com resultados

        """
        from django.db import connection

        logger.info(f"Executando query: {query[:100]}...")

        with connection.cursor() as cursor:
            cursor.execute(query, params or [])

            if cursor.description:
                columns = [col[0] for col in cursor.description]
                results = [
                    dict(zip(columns, row, strict=False))
                    for row in cursor.fetchall()
                ]

                logger.info(
                    f"Query executada com sucesso. "
                    f"{len(results)} resultados"
                )
                return results
            else:
                affected_rows = cursor.rowcount
                logger.info(
                    f"Query executada. "
                    f"{affected_rows} linhas afetadas"
                )
                return []

    @database_retry
    def execute_bulk_operation(self, operation_func):
        """Executa operação em lote com retry automático.

        Args:
            operation_func: Função que executa a operação em lote

        Returns:
            Resultado da operação

        """
        logger.info("Executando operação em lote com retry")

        start_time = time.time()
        result = operation_func()
        duration = time.time() - start_time

        logger.info(f"Operação em lote concluída em {duration:.2f}s")
        return result


class RetryMetrics:
    """Coleta métricas de retry para monitoramento.

    Permite rastrear taxa de sucesso, tentativas médias
    e identificar operações problemáticas.
    """

    def __init__(self):
        self.stats: Dict[str, List[Dict]] = {}

    def record_attempt(
        self,
        operation: str,
        attempt: int,
        success: bool,
        duration: float
    ):
        """Registra tentativa de operação."""
        if operation not in self.stats:
            self.stats[operation] = []

        self.stats[operation].append({
            'attempt': attempt,
            'success': success,
            'duration': duration,
            'timestamp': time.time()
        })

    def get_success_rate(self, operation: str) -> float:
        """Calcula taxa de sucesso de uma operação."""
        if operation not in self.stats:
            return 0.0

        attempts = self.stats[operation]
        successful = sum(1 for a in attempts if a['success'])

        return successful / len(attempts) if attempts else 0.0

    def get_avg_attempts(self, operation: str) -> float:
        """Calcula número médio de tentativas."""
        if operation not in self.stats:
            return 0.0

        attempts = self.stats[operation]
        total_attempts = sum(a['attempt'] for a in attempts)

        return total_attempts / len(attempts) if attempts else 0.0

    def get_summary(self) -> Dict[str, Dict]:
        """Retorna resumo de todas as operações."""
        summary = {}

        for operation in self.stats:
            summary[operation] = {
                'total_calls': len(self.stats[operation]),
                'success_rate': self.get_success_rate(operation),
                'avg_attempts': self.get_avg_attempts(operation),
                'last_24h': len([
                    a for a in self.stats[operation]
                    if a['timestamp'] > time.time() - 86400
                ])
            }

        return summary


# Singleton global para métricas
retry_metrics = RetryMetrics()


def with_metrics(operation_name: str):
    """Decorator para coletar métricas de retry.

    Uso:
        @with_metrics('consulta_cep')
        @api_retry
        def buscar_cep(cep):
            # Implementação
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            attempt = 1

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                retry_metrics.record_attempt(
                    operation_name, attempt, True, duration
                )

                return result

            except Exception:
                duration = time.time() - start_time

                retry_metrics.record_attempt(
                    operation_name, attempt, False, duration
                )

                raise

        return wrapper
    return decorator


# Exemplos de uso direto

# 1. Consulta de CEP
cep_service = CEPService()

# 2. Cliente para API de pagamento
payment_api = ExternalAPIClient("https://api.pagamento.com")

# 3. Executor de queries críticas
db_executor = DatabaseQueryExecutor()


if __name__ == "__main__":
    # Exemplos de teste

    # Teste de CEP
    try:
        endereco = cep_service.consultar("01310-100")
    except Exception:
        pass

    # Teste de métricas
