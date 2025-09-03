# Configurações de Segurança para Queries SQL

## 🔒 Checklist de Segurança

### ✅ Parâmetros Obrigatórios

- [ ] Todas as queries usam `%s` para valores dinâmicos
- [ ] Nenhuma concatenação de strings em SQL
- [ ] Parâmetros validados antes da execução
- [ ] Tipos de dados verificados

### ✅ Validação de Entrada

- [ ] Whitelist para valores categóricos
- [ ] Limites máximos para paginação
- [ ] Sanitização de strings
- [ ] Verificação de caracteres especiais

### ✅ Controle de Acesso

- [ ] Verificação de permissões do usuário
- [ ] Filtros por proprietário/organização
- [ ] Logs de acesso auditáveis
- [ ] Rate limiting implementado

### ✅ Performance e Limites

- [ ] LIMIT definido em todas as queries de listagem
- [ ] Timeout configurado para queries longas
- [ ] Índices otimizados para campos consultados
- [ ] Monitoramento de performance

## 🛡️ Padrões de Segurança

### Escape de Caracteres LIKE

```python
def escape_like_pattern(pattern: str) -> str:
    """Escapa caracteres especiais para queries LIKE seguras"""
    return (pattern
            .replace('\\', '\\\\')
            .replace('%', '\\%')
            .replace('_', '\\_'))
```

### Validação de Domínios

```python
def validate_email_domain(domain: str) -> str:
    """Valida e sanitiza domínio de email"""
    import re

    if not domain or not isinstance(domain, str):
        raise ValueError("Domínio inválido")

    # Remove espaços e converte para minúsculo
    domain = domain.strip().lower()

    # Regex para domínio válido
    domain_pattern = r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(domain_pattern, domain):
        raise ValueError("Formato de domínio inválido")

    # Verificar caracteres perigosos
    dangerous_chars = ['%', '_', ';', '--', '/*', '*/', "'", '"']
    if any(char in domain for char in dangerous_chars):
        raise ValueError("Domínio contém caracteres não permitidos")

    return domain
```

### Limites de Paginação

```python
class PaginationLimits:
    """Limites seguros para paginação"""
    MAX_LIMIT = 100
    DEFAULT_LIMIT = 10
    MAX_OFFSET = 10000

    @classmethod
    def validate_pagination(cls, limit: int, offset: int) -> tuple:
        """Valida e ajusta parâmetros de paginação"""
        # Validar limit
        if not isinstance(limit, int) or limit <= 0:
            limit = cls.DEFAULT_LIMIT
        elif limit > cls.MAX_LIMIT:
            limit = cls.MAX_LIMIT

        # Validar offset
        if not isinstance(offset, int) or offset < 0:
            offset = 0
        elif offset > cls.MAX_OFFSET:
            raise ValueError(f"Offset máximo permitido: {cls.MAX_OFFSET}")

        return limit, offset
```

## 🔍 Auditoria e Logs

### Log de Execução

```python
import logging
from datetime import datetime

def log_query_execution(
    user_id: int,
    query_name: str,
    params: list,
    execution_time: float,
    result_count: int
):
    """Registra execução de query para auditoria"""
    logger = logging.getLogger('sql_audit')

    log_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'user_id': user_id,
        'query_name': query_name,
        'params_hash': hash(str(params)),  # Hash para privacidade
        'execution_time_ms': round(execution_time * 1000, 2),
        'result_count': result_count,
    }

    logger.info(f"SQL_EXEC: {log_data}")
```

### Detecção de Anomalias

```python
def detect_query_anomalies(
    query_name: str,
    execution_time: float,
    result_count: int
) -> list:
    """Detecta possíveis anomalias na execução"""
    warnings = []

    # Query muito lenta
    if execution_time > 5.0:  # 5 segundos
        warnings.append(f"Query lenta: {execution_time:.2f}s")

    # Muitos resultados
    if result_count > 1000:
        warnings.append(f"Muitos resultados: {result_count}")

    # Queries frequentes
    # (implementar cache de frequência)

    return warnings
```

## 🚨 Casos de Emergência

### Bloqueio de Query Suspeita

```python
BLOCKED_PATTERNS = [
    'UNION SELECT',
    'DROP TABLE',
    'DELETE FROM',
    'INSERT INTO',
    'UPDATE SET',
    '--',
    '/*',
    'xp_',
    'sp_',
]

def check_blocked_patterns(sql: str) -> bool:
    """Verifica se SQL contém padrões bloqueados"""
    sql_upper = sql.upper()

    for pattern in BLOCKED_PATTERNS:
        if pattern in sql_upper:
            return True

    return False
```

### Rate Limiting

```python
from collections import defaultdict
from datetime import datetime, timedelta

class QueryRateLimit:
    """Rate limiting para queries por usuário"""

    def __init__(self):
        self.user_requests = defaultdict(list)
        self.window_minutes = 5
        self.max_requests = 100

    def is_allowed(self, user_id: int) -> bool:
        """Verifica se usuário pode executar query"""
        now = datetime.utcnow()
        cutoff = now - timedelta(minutes=self.window_minutes)

        # Remove requests antigos
        self.user_requests[user_id] = [
            req_time for req_time in self.user_requests[user_id]
            if req_time > cutoff
        ]

        # Verifica limite
        if len(self.user_requests[user_id]) >= self.max_requests:
            return False

        # Adiciona request atual
        self.user_requests[user_id].append(now)
        return True
```

## 📋 Testes de Segurança

### Teste de SQL Injection

```python
def test_sql_injection_protection():
    """Testa proteção contra SQL injection"""
    malicious_inputs = [
        "'; DROP TABLE users; --",
        "1 OR 1=1",
        "admin'--",
        "1'; INSERT INTO users...",
        "1 UNION SELECT password FROM users",
    ]

    executor = QueryExecutor('example_queries.sql')

    for malicious_input in malicious_inputs:
        try:
            # Deve falhar na validação
            executor.get_user_by_id(malicious_input)
            assert False, f"Deveria falhar: {malicious_input}"
        except (ValidationError, ValueError, TypeError):
            # Esperado - validação funcionou
            pass
```

### Teste de Performance

```python
def test_query_performance():
    """Testa se queries respeitam limites de performance"""
    import time

    executor = QueryExecutor('example_queries.sql')

    start_time = time.time()
    results = executor.get_users_by_status(True, limit=100)
    execution_time = time.time() - start_time

    # Query deve ser rápida
    assert execution_time < 1.0, f"Query muito lenta: {execution_time}s"

    # Deve respeitar limite
    assert len(results) <= 100, f"Muitos resultados: {len(results)}"
```

## 📚 Referências

- [OWASP SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)
- [Django Database Security](https://docs.djangoproject.com/en/stable/topics/security/#sql-injection-protection)
- [PostgreSQL Security](https://www.postgresql.org/docs/current/runtime-config-connection.html#RUNTIME-CONFIG-CONNECTION-SECURITY)
