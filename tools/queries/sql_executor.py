"""Exemplo de integração de queries SQL com Django.

Este módulo demonstra como carregar e executar queries SQL de forma segura
seguindo as melhores práticas de segurança e performance.
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from django.db import connection
from django.core.exceptions import ValidationError


logger = logging.getLogger(__name__)


def load_sql_queries(filename: str) -> Dict[str, str]:
    """Carrega queries SQL de um arquivo e retorna dict indexado por nome.

    Args:
        filename: Nome do arquivo SQL (ex: 'user_queries.sql')

    Returns:
        Dict com nome da query como chave e SQL como valor

    Raises:
        FileNotFoundError: Se arquivo não existe
        ValueError: Se formato do arquivo é inválido

    """
    file_path = Path(__file__).parent / filename

    if not file_path.exists():
        raise FileNotFoundError(
            f"Arquivo de queries não encontrado: {filename}"
        )

    queries = {}
    current_query = None
    current_sql = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        raise ValueError(f"Erro ao ler arquivo {filename}: {str(e)}")

    for line in content.split('\n'):
        line = line.strip()

        if line.startswith('-- name:'):
            # Salva query anterior se existe
            if current_query and current_sql:
                queries[current_query] = '\n'.join(current_sql).strip()

            # Inicia nova query
            current_query = line.replace('-- name:', '').strip()
            current_sql = []

        elif not line.startswith('--') and current_query and line:
            current_sql.append(line)

    # Salva última query
    if current_query and current_sql:
        queries[current_query] = '\n'.join(current_sql).strip()

    logger.info(f"Carregadas {len(queries)} queries de {filename}")
    return queries


def validate_query_params(params: List[Any]) -> List[Any]:
    """Valida e sanitiza parâmetros de query.

    Args:
        params: Lista de parâmetros para a query

    Returns:
        Lista de parâmetros validados

    Raises:
        ValidationError: Se parâmetros são inválidos

    """
    if not isinstance(params, list):
        raise ValidationError("Parâmetros devem ser uma lista")

    validated_params = []

    for param in params:
        # Validações básicas de tipo
        if param is None:
            validated_params.append(None)
        elif isinstance(param, (str, int, float, bool)):
            validated_params.append(param)
        else:
            raise ValidationError(
                f"Tipo de parâmetro não suportado: {type(param)}"
            )

    return validated_params


def execute_raw_query(
    query_name: str,
    queries_dict: Dict[str, str],
    params: Optional[List[Any]] = None
) -> List[Dict[str, Any]]:
    """Executa query SQL raw e retorna resultados como lista de dicts.

    Args:
        query_name: Nome da query a ser executada
        queries_dict: Dict contendo as queries carregadas
        params: Parâmetros para a query (opcional)

    Returns:
        Lista de dicts com resultados da query

    Raises:
        ValueError: Se query não existe
        ValidationError: Se parâmetros são inválidos
        Exception: Erros de execução SQL

    """
    if query_name not in queries_dict:
        available_queries = list(queries_dict.keys())
        raise ValueError(
            f"Query '{query_name}' não encontrada. "
            f"Queries disponíveis: {available_queries}"
        )

    sql = queries_dict[query_name]
    validated_params = validate_query_params(params or [])

    logger.info(f"Executando query: {query_name}")
    logger.debug(f"SQL: {sql}")
    logger.debug(f"Params: {validated_params}")

    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, validated_params)

            if cursor.description:
                columns = [col[0] for col in cursor.description]
                results = [
                    dict(zip(columns, row, strict=False))
                    for row in cursor.fetchall()
                ]

                logger.info(
                    f"Query {query_name} executada com sucesso. "
                    f"{len(results)} resultados"
                )
                return results
            else:
                # Query não retorna dados (INSERT, UPDATE, DELETE)
                affected_rows = cursor.rowcount
                logger.info(
                    f"Query {query_name} executada. "
                    f"{affected_rows} linhas afetadas"
                )
                return []

    except Exception as e:
        logger.error(f"Erro ao executar query {query_name}: {str(e)}")
        logger.error(f"SQL: {sql}")
        logger.error(f"Params: {validated_params}")
        raise


# Carrega queries do arquivo de exemplo
try:
    EXAMPLE_QUERIES = load_sql_queries('example_queries.sql')
except FileNotFoundError:
    logger.warning("Arquivo example_queries.sql não encontrado")
    EXAMPLE_QUERIES = {}


class QueryExecutor:
    """Classe para executar queries SQL de forma segura e organizada."""

    def __init__(self, queries_file: str):
        """Inicializa executor com arquivo de queries.

        Args:
            queries_file: Nome do arquivo SQL

        """
        self.queries = load_sql_queries(queries_file)
        self.queries_file = queries_file

    def get_users_by_status(
        self,
        is_active: bool,
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict]:
        """Busca usuários por status com validação de parâmetros.

        Args:
            is_active: Status do usuário (True/False)
            limit: Limite de resultados (máximo 100)
            offset: Offset para paginação

        Returns:
            Lista de usuários encontrados

        """
        # Validações específicas
        if not isinstance(is_active, bool):
            raise ValidationError("is_active deve ser boolean")

        if not isinstance(limit, int) or limit <= 0 or limit > 100:
            raise ValidationError("limit deve ser inteiro entre 1 e 100")

        if not isinstance(offset, int) or offset < 0:
            raise ValidationError("offset deve ser inteiro não-negativo")

        return execute_raw_query(
            'USERS_BY_STATUS',
            self.queries,
            [is_active, limit, offset]
        )

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Busca usuário específico por ID.

        Args:
            user_id: ID do usuário

        Returns:
            Dict com dados do usuário ou None se não encontrado

        """
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValidationError("user_id deve ser inteiro positivo")

        results = execute_raw_query('USER_BY_ID', self.queries, [user_id])
        return results[0] if results else None

    def count_active_users(self) -> int:
        """Conta total de usuários ativos.

        Returns:
            Número de usuários ativos

        """
        results = execute_raw_query('COUNT_ACTIVE_USERS', self.queries, [])
        return results[0]['total_users'] if results else 0

    def get_users_by_email_domain(
        self,
        domain: str,
        limit: int = 50
    ) -> List[Dict]:
        """Busca usuários por domínio de email.

        Args:
            domain: Domínio do email (ex: 'gmail.com')
            limit: Limite de resultados

        Returns:
            Lista de usuários do domínio

        """
        # Validação e sanitização
        if not isinstance(domain, str) or not domain.strip():
            raise ValidationError("domain deve ser string não-vazia")

        # Remove caracteres especiais perigosos
        domain = domain.strip().lower()
        if any(char in domain for char in ['%', '_', ';', '--', '/*', '*/']):
            raise ValidationError("domain contém caracteres não permitidos")

        if not isinstance(limit, int) or limit <= 0 or limit > 100:
            raise ValidationError("limit deve ser inteiro entre 1 e 100")

        return execute_raw_query(
            'USERS_BY_EMAIL_DOMAIN',
            self.queries,
            [domain]
        )[:limit]  # Aplicar limit no Python como segurança extra


# Exemplo de uso
def example_usage():
    """Demonstra como usar o sistema de queries."""
    try:
        # Inicializa executor
        executor = QueryExecutor('example_queries.sql')

        # Busca usuários ativos
        executor.get_users_by_status(
            is_active=True,
            limit=10,
            offset=0
        )

        # Busca usuário específico
        user = executor.get_user_by_id(user_id=1)
        if user:
            pass
        else:
            pass

        # Conta usuários ativos
        executor.count_active_users()

        # Busca por domínio
        executor.get_users_by_email_domain('gmail.com', limit=5)

    except Exception as e:
        logger.error(f"Erro no exemplo: {str(e)}")
        raise


if __name__ == "__main__":
    # Configurar logging para debug
    logging.basicConfig(level=logging.INFO)
    example_usage()
