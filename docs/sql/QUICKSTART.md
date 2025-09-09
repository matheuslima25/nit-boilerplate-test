# Documentação SQL

Esta pasta contém documentação e exemplos para uso seguro de queries SQL no projeto.

## 📁 Estrutura

- `README.md` - Guia completo de boas práticas
- `SECURITY.md` - Configurações e padrões de segurança
- `../tools/queries/` - Arquivos SQL e código Python

## 🚀 Início Rápido

### 1. Criar Query

```sql
-- name: MINHA_QUERY
-- description: Busca dados específicos
-- parameters: param1 (int), param2 (string)
SELECT campo FROM tabela WHERE id = %s AND status = %s;
```

### 2. Usar no Python

```python
from tools.queries.sql_executor import QueryExecutor

executor = QueryExecutor('meu_arquivo.sql')
resultados = executor.execute_query('MINHA_QUERY', [123, 'ativo'])
```

## ⚡ Comandos Essenciais

- **Validar SQL**: `make lint-file FILE=tools/queries/arquivo.sql`
- **Testar Queries**: `python manage.py shell`
- **Ver Logs**: `tail -f nitapi/logs/base.log`

## 🔒 Segurança

**SEMPRE use parâmetros** - Nunca concatene strings em SQL:

```python
# ✅ CORRETO
cursor.execute("SELECT * FROM users WHERE id = %s", [user_id])

# ❌ ERRADO
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
```

## 📚 Documentação Completa

- [Guia de Boas Práticas](README.md)
- [Configurações de Segurança](security.md)
- [Exemplos de Código](../queries/)
