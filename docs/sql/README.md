# Guia de Boas Práticas para Queries SQL

## 📋 Índice

- [Estrutura de Queries](#️-estrutura-de-queries)
- [Segurança - Prevenção SQL Injection](#-segurança---prevenção-sql-injection)
- [Nomenclatura e Organização](#-nomenclatura-e-organização)
- [Performance e Otimização](#-performance-e-otimização)
- [Integração com Django](#-integração-com-django)
- [Exemplos Práticos](#-exemplos-práticos)

## 🏗️ Estrutura de Queries

### Formato Padrão

Todas as queries devem seguir este formato:

```sql
-- name: NOME_DA_QUERY
-- description: Descrição clara do que a query faz
-- parameters: param1 (tipo), param2 (tipo), ...
SELECT
    campo1,
    campo2,
    campo3
FROM tabela t
WHERE t.condicao = %s
ORDER BY t.campo
LIMIT %s OFFSET %s;
```

### Convenções de Nomenclatura

- **Nome da Query**: MAIÚSCULO_COM_UNDERSCORES
- **Descrição**: Frase clara explicando o propósito
- **Parâmetros**: Nome (tipo) - seja específico sobre os tipos

## 🔒 Segurança - Prevenção SQL Injection

### ✅ SEMPRE Use Parâmetros

```sql
-- ✅ CORRETO - Usa parâmetros
SELECT * FROM users WHERE email = %s;

-- ❌ ERRADO - Concatenação de strings
SELECT * FROM users WHERE email = 'user@example.com';
```

### ✅ Validação de Parâmetros

```python
# Sempre valide parâmetros antes de usar
def get_users_by_status(status: str, limit: int = 10, offset: int = 0):
    # Validação de tipos
    if not isinstance(status, str):
        raise ValueError("Status deve ser string")
    if not isinstance(limit, int) or limit <= 0:
        raise ValueError("Limit deve ser inteiro positivo")
    if not isinstance(offset, int) or offset < 0:
        raise ValueError("Offset deve ser inteiro não-negativo")

    # Whitelist de valores permitidos
    allowed_statuses = ['active', 'inactive', 'pending']
    if status not in allowed_statuses:
        raise ValueError(f"Status deve ser um de: {allowed_statuses}")
```

### ✅ Escape de Caracteres Especiais

```python
# Para buscas LIKE, escape caracteres especiais
def escape_like_pattern(pattern: str) -> str:
    """Escapa caracteres especiais para queries LIKE"""
    return pattern.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')

# Uso:
domain = escape_like_pattern(user_input)
query = "SELECT * FROM users WHERE email LIKE %s"
params = [f"%@{domain}"]
```

## 📝 Nomenclatura e Organização

### Estrutura de Arquivos

```bash
tools/queries/
├── __init__.py
├── user_queries.sql       # Queries relacionadas a usuários
├── order_queries.sql      # Queries relacionadas a pedidos
├── report_queries.sql     # Queries para relatórios
└── example_queries.sql    # Exemplos e templates
```

### Agrupamento por Funcionalidade

```sql
-- ==============================================
-- SEÇÃO: CONSULTAS DE USUÁRIOS
-- ==============================================

-- name: USER_BY_ID
-- description: Busca usuário por ID
-- parameters: user_id (int)
SELECT id, username, email FROM auth_user WHERE id = %s;

-- name: USERS_BY_STATUS
-- description: Lista usuários por status
-- parameters: is_active (bool), limit (int), offset (int)
SELECT id, username, email FROM auth_user
WHERE is_active = %s
LIMIT %s OFFSET %s;

-- ==============================================
-- SEÇÃO: CONSULTAS DE ESTATÍSTICAS
-- ==============================================
```

## ⚡ Performance e Otimização

### Índices e Chaves

```sql
-- ✅ Use índices para campos frequentemente consultados
-- Evite SELECT * - especifique campos necessários
SELECT u.id, u.username, u.email  -- Não: SELECT *
FROM auth_user u
WHERE u.email = %s;  -- Campo indexado

-- ✅ Use LIMIT para evitar resultados muito grandes
SELECT id, name FROM products
WHERE category = %s
ORDER BY created_at DESC
LIMIT %s OFFSET %s;
```

### JOINs Eficientes

```sql
-- ✅ Use LEFT JOIN quando apropriado
SELECT
    u.id,
    u.username,
    p.phone
FROM auth_user u
LEFT JOIN user_profile p ON u.id = p.user_id
WHERE u.is_active = %s;

-- ✅ Evite N+1 queries - busque dados relacionados em uma query
```

## 🔧 Integração com Django

### Carregando Queries

```python
# tools/queries/__init__.py
import os
from pathlib import Path

def load_sql_queries(filename: str) -> dict:
    """Carrega queries SQL de um arquivo e retorna dict indexado por nome"""
    queries = {}
    file_path = Path(__file__).parent / filename

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Parse queries by -- name: comments
    current_query = None
    current_sql = []

    for line in content.split('\n'):
        if line.startswith('-- name:'):
            if current_query:
                queries[current_query] = '\n'.join(current_sql).strip()
            current_query = line.replace('-- name:', '').strip()
            current_sql = []
        elif not line.startswith('--') and current_query:
            current_sql.append(line)

    if current_query:
        queries[current_query] = '\n'.join(current_sql).strip()

    return queries

# Carrega queries
USER_QUERIES = load_sql_queries('user_queries.sql')
```

### Executando Queries

```python
from django.db import connection
from typing import List, Dict, Any

def execute_query(query_name: str, params: List[Any] = None) -> List[Dict]:
    """Executa query SQL e retorna resultados como lista de dicts"""
    if query_name not in USER_QUERIES:
        raise ValueError(f"Query '{query_name}' não encontrada")

    sql = USER_QUERIES[query_name]
    params = params or []

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

# Uso:
users = execute_query('USERS_BY_STATUS', [True, 10, 0])
```

### Validação e Logs

```python
import logging
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

def safe_execute_query(query_name: str, params: List[Any] = None) -> List[Dict]:
    """Executa query com logging e tratamento de erros"""
    try:
        logger.info(f"Executando query: {query_name} com params: {params}")

        # Validação básica
        if not query_name or not isinstance(query_name, str):
            raise ValidationError("Nome da query inválido")

        results = execute_query(query_name, params)
        logger.info(f"Query {query_name} executada com sucesso. {len(results)} resultados")

        return results

    except Exception as e:
        logger.error(f"Erro ao executar query {query_name}: {str(e)}")
        raise
```

## 📚 Exemplos Práticos

### 1. Query com Paginação

```sql
-- name: PAGINATED_USERS
-- description: Lista usuários com paginação
-- parameters: limit (int), offset (int)
SELECT
    id,
    username,
    email,
    date_joined
FROM auth_user
WHERE is_active = true
ORDER BY date_joined DESC
LIMIT %s OFFSET %s;
```

### 2. Query com Filtros Múltiplos

```sql
-- name: FILTERED_USERS
-- description: Busca usuários com múltiplos filtros opcionais
-- parameters: email_pattern (string), date_from (date), is_active (bool)
SELECT
    id,
    username,
    email,
    date_joined
FROM auth_user
WHERE
    (%s IS NULL OR email LIKE %s)
    AND (%s IS NULL OR date_joined >= %s)
    AND is_active = %s
ORDER BY date_joined DESC;
```

### 3. Query de Agregação

```sql
-- name: USER_STATISTICS
-- description: Estatísticas básicas de usuários
-- parameters: none
SELECT
    COUNT(*) as total_users,
    COUNT(CASE WHEN is_active THEN 1 END) as active_users,
    COUNT(CASE WHEN NOT is_active THEN 1 END) as inactive_users,
    MIN(date_joined) as first_user_date,
    MAX(date_joined) as last_user_date
FROM auth_user;
```

## 🛡️ Checklist de Segurança

- [ ] **Parâmetros**: Usa `%s` para todos os valores dinâmicos
- [ ] **Validação**: Valida tipos e valores antes da execução
- [ ] **Whitelist**: Para campos específicos, usa lista de valores permitidos
- [ ] **Escape**: Escapa caracteres especiais em padrões LIKE
- [ ] **Logs**: Registra execução de queries para auditoria
- [ ] **Permissões**: Verifica se usuário tem permissão para dados solicitados
- [ ] **Limite**: Define limites máximos para evitar sobrecarga
- [ ] **Timeout**: Configura timeout para queries longas

## 🔄 Manutenção

### Versionamento

```sql
-- version: 1.2.0
-- last_updated: 2024-01-15
-- author: equipe-backend
-- changes: Adicionada query FILTERED_USERS com múltiplos filtros
```

### Testes

```python
# tests/test_queries.py
def test_user_by_id_query():
    """Testa query USER_BY_ID"""
    result = execute_query('USER_BY_ID', [1])
    assert len(result) <= 1
    if result:
        assert 'id' in result[0]
        assert 'username' in result[0]
```

---

**📝 Nota**: Este documento deve ser atualizado sempre que novas patterns ou requisitos de segurança forem identificados.
