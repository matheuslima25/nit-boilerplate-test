# Padrões de Desenvolvimento - NIT API

Esta pasta contém padrões e boas práticas para desenvolvimento no projeto NIT-API.

## 📁 Estrutura

- `tenacity-retry.md` - Documentação completa do padrão de retry exponencial
- `SETUP.md` - Guia de configuração e uso do Tenacity no projeto
- `../tools/retry_service.py` - Implementação prática do padrão

## 🚀 Início Rápido

### 1. Instalar Dependência

```bash
pip install tenacity>=8.0.0
```

### 2. Importar e Usar

```python
from tools.retry_service import api_retry, CEPService

# Decorator simples
@api_retry
def minha_funcao_api():
    return requests.get("https://api.externa.com").json()

# Serviço pronto
cep_service = CEPService()
endereco = cep_service.consultar("01310-100")
```

### 3. Monitorar

```python
from tools.retry_service import retry_metrics
print(retry_metrics.get_summary())
```

## 📋 Padrões Disponíveis

- ✅ **Retry Exponencial** - Tenacity para APIs, banco e arquivos
- 🔄 **Mais padrões em desenvolvimento**

## 📚 Documentação

- [Guia Completo do Tenacity](TENACITY-RETRY.md)
- [Configuração e Setup](SETUP.md)

## 🎯 Casos de Uso

- **APIs Externas**: CEP, pagamento, notificações
- **Banco de Dados**: Queries críticas, operações em lote
- **Arquivos**: Upload S3, processamento de documentos
- **Integrações**: Sistemas terceiros, webhooks
