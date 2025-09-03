"""Django Signals para a aplicação Core.

Signals são uma forma de permitir que certas aplicações sejam notificadas
quando certas ações ocorrem em outras partes da aplicação. São úteis para
desacoplar aplicações e implementar funcionalidades como auditoria,
notificações, cache invalidation, etc.

Documentação: https://docs.djangoproject.com/en/stable/topics/signals/
"""

import logging
from django.db.models import signals
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.core.cache import cache


logger = logging.getLogger(__name__)
User = get_user_model()


# =============================================================================
# POST_SAVE SIGNALS
# =============================================================================
# Executado APÓS um objeto ser salvo no banco de dados.
# Útil para: logs de auditoria, notificações, cache invalidation, etc.


@receiver(signals.post_save, sender=User)
def post_save_user(sender, instance, created, raw, using, **kwargs):
    """Signal executado após salvar um usuário.

    Args:
        sender: Model class que enviou o signal
        instance: Instância específica do model salvo
        created: Boolean indicando se foi criado ou atualizado
        raw: Boolean indicando se foi salvo via raw SQL
        using: Alias do banco de dados usado
        **kwargs: Argumentos adicionais do signal

    """
    if created:
        logger.info(f"Novo usuário criado: {instance.email}")
        # Exemplo: Criar perfil padrão, enviar email de boas-vindas, etc.
    else:
        logger.info(f"Usuário atualizado: {instance.email}")
        # Exemplo: Invalidar cache, notificar mudanças, etc.


# Exemplo com model da aplicação core (descomente conforme necessário)
# @receiver(signals.post_save, sender=models.Document)
# def post_save_document(sender, instance, created, raw, using, **kwargs):
#     """
#     Signal executado após salvar um documento.
#
#     Exemplo de uso: indexação para busca, notificações, backup, etc.
#     """
#     if created:
#         logger.info(f"Novo documento criado: {instance.title}")
#         # Implementar: indexação, notificações, etc.
#     else:
#         logger.info(f"Documento atualizado: {instance.title}")
#         # Implementar: re-indexação, cache invalidation, etc.


# =============================================================================
# PRE_SAVE SIGNALS
# =============================================================================
# Executado ANTES de um objeto ser salvo no banco de dados.
# Útil para: validações personalizadas, modificação de dados, etc.


@receiver(signals.pre_save, sender=User)
def pre_save_user(sender, instance, **kwargs):
    """Signal executado antes de salvar um usuário.

    Útil para: validações, normalização de dados, etc.
    """
    # Exemplo: Normalizar email para lowercase
    if instance.email:
        instance.email = instance.email.lower().strip()

    logger.debug(f"Preparando para salvar usuário: {instance.email}")


# Exemplo genérico para models da aplicação core
# @receiver(signals.pre_save, sender=models.YourModel)
# def pre_save_your_model(sender, instance, **kwargs):
#     """
#     Signal executado antes de salvar YourModel.
#
#     Exemplo: modificar campos antes de salvar, validações, etc.
#     """
#     # Exemplo: definir slug automático
#     if not instance.slug and instance.title:
#         instance.slug = slugify(instance.title)
#
#     logger.debug(f"Preparando para salvar {sender.__name__}: {instance}")


# =============================================================================
# PRE_DELETE SIGNALS
# =============================================================================
# Executado ANTES de um objeto ser deletado do banco de dados.
# Útil para: backup de dados, cleanup de arquivos, validações, etc.


@receiver(signals.pre_delete, sender=User)
def pre_delete_user(sender, instance, using, origin, **kwargs):
    """Signal executado antes de deletar um usuário.

    Args:
        sender: Model class que enviou o signal
        instance: Instância específica do model sendo deletado
        using: Alias do banco de dados usado
        origin: Origem da operação de delete
        **kwargs: Argumentos adicionais do signal

    """
    logger.warning(f"Usuário será deletado: {instance.email}")

    # Exemplo: Backup de dados importantes
    # backup_user_data(instance)

    # Exemplo: Cleanup de arquivos relacionados
    # cleanup_user_files(instance)

    # Exemplo: Notificar administradores
    # notify_user_deletion(instance)


# Exemplo genérico para models da aplicação core
# @receiver(signals.pre_delete, sender=models.Document)
# def pre_delete_document(sender, instance, using, origin, **kwargs):
#     """
#     Signal executado antes de deletar um documento.
#
#     Exemplo: backup, cleanup de arquivos, logs de auditoria, etc.
#     """
#     logger.warning(f"Documento será deletado: {instance.title}")
#
#     # Exemplo: Fazer backup do arquivo
#     if instance.file:
#         backup_file(instance.file)
#
#     # Exemplo: Remover do índice de busca
#     # remove_from_search_index(instance)


# =============================================================================
# POST_DELETE SIGNALS
# =============================================================================
# Executado APÓS um objeto ser deletado do banco de dados.
# Útil para: logs de auditoria, limpeza de cache, notificações, etc.


@receiver(signals.post_delete, sender=User)
def post_delete_user(sender, instance, using, origin, **kwargs):
    """Signal executado após deletar um usuário.

    Args:
        sender: Model class que enviou o signal
        instance: Instância específica do model deletado
        using: Alias do banco de dados usado
        origin: Origem da operação de delete
        **kwargs: Argumentos adicionais do signal

    """
    logger.info(f"Usuário deletado: {instance.email}")

    # Exemplo: Invalidar cache relacionado
    cache_key = f"user_data_{instance.id}"
    cache.delete(cache_key)

    # Exemplo: Log de auditoria
    # AuditLog.objects.create(
    #     action="DELETE",
    #     model_name="User",
    #     object_id=instance.id,
    #     details=f"User {instance.email} deleted"
    # )


# =============================================================================
# M2M_CHANGED SIGNALS
# =============================================================================
# Executado quando um relacionamento ManyToMany é alterado.
# Útil para: invalidação de cache, recálculos, notificações, etc.


@receiver(signals.m2m_changed, sender=User.groups.through)
def m2m_changed_user_groups(sender, instance, action, pk_set, **kwargs):
    """Signal executado quando grupos de um usuário são alterados.

    Args:
        sender: Model intermediário do M2M
        instance: Instância do usuário
        action: Tipo de ação (pre_add, post_add, pre_remove, post_remove, etc.)
        pk_set: Set de PKs dos objetos relacionados afetados
        **kwargs: Argumentos adicionais do signal

    """
    if action == "post_add":
        msg = f"Grupos adicionados ao usuário {instance.email}: {pk_set}"
        logger.info(msg)
        # Exemplo: Invalidar cache de permissões
        cache.delete(f"user_permissions_{instance.id}")

    elif action == "post_remove":
        msg = f"Grupos removidos do usuário {instance.email}: {pk_set}"
        logger.info(msg)
        # Exemplo: Recalcular permissões, notificações, etc.
        cache.delete(f"user_permissions_{instance.id}")


# =============================================================================
# MIGRATION SIGNALS
# =============================================================================
# Executados durante migrações do banco de dados.

# from django.db.models.signals import pre_migrate, post_migrate

# @receiver(pre_migrate)
# def pre_migrate_handler(sender, **kwargs):
#     """Signal executado antes de executar migrações."""
#     logger.info(f"Iniciando migração para {sender.label}")

# @receiver(post_migrate)
# def post_migrate_handler(sender, **kwargs):
#     """Signal executado após executar migrações."""
#     logger.info(f"Migração concluída para {sender.label}")
#     # Exemplo: criar dados iniciais, rebuild de índices, etc.


# =============================================================================
# SIGNALS PERSONALIZADOS
# =============================================================================
# Você pode criar seus próprios signals para eventos específicos da aplicação.

# from django.dispatch import Signal

# # Exemplo de signal personalizado
# user_logged_in_from_keycloak = Signal()

# @receiver(user_logged_in_from_keycloak)
# def handle_keycloak_login(sender, user, token_data, **kwargs):
#     """
#     Signal executado quando usuário faz login via Keycloak.
#
#     Args:
#         sender: Classe que enviou o signal
#         user: Instância do usuário
#         token_data: Dados do token JWT do Keycloak
#     """
#     logger.info(f"Login via Keycloak: {user.email}")
#
#     # Exemplo: Atualizar dados do usuário com informações do Keycloak
#     if token_data.get('given_name'):
#         user.first_name = token_data['given_name']
#     if token_data.get('family_name'):
#         user.last_name = token_data['family_name']
#     user.save()
#
#     # Exemplo: Registrar atividade de login
#     # LoginActivity.objects.create(user=user, login_method='keycloak')

# Para disparar o signal personalizado:
# user_logged_in_from_keycloak.send(
#     sender=KeycloakAuthentication,
#     user=user_instance,
#     token_data=decoded_token
# )
