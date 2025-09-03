"""Signals da aplicação Commons.

Este módulo contém signals para automatizar processos relacionados aos
modelos base da aplicação Commons, incluindo inicialização de templates
de e-mail, logging de operações e validações automáticas.
"""

import logging
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import signals
from django.dispatch import receiver
from django.utils import timezone

from apps.commons import models

logger = logging.getLogger(__name__)


@receiver(signals.post_save, sender=models.Email)
def post_save_email_setup_templates(
    sender, instance, created, raw, using, **kwargs
):
    """
    Configura templates padrão quando uma nova configuração de Email é criada.

    Este signal é executado após a criação de uma instância do modelo Email
    e carrega automaticamente os templates HTML padrão dos arquivos do sistema.

    Args:
        sender: A classe do modelo (Email)
        instance: A instância do modelo Email
        created: Boolean indicando se foi uma criação nova
        raw: Boolean indicando se foi carregamento de fixture
        using: Nome do banco de dados usado
        **kwargs: Argumentos adicionais

    """
    if created and not raw:
        try:
            # Define o diretório base dos templates
            templates_dir = (
                Path(settings.BASE_DIR)
                / "apps"
                / "commons"
                / "templates"
                / "emails"
            )

            # Carrega template de notificação se existir
            notification_template_path = (
                templates_dir / "notification_template.html"
            )
            if notification_template_path.exists():
                with open(
                    notification_template_path, "r", encoding="utf-8"
                ) as f:
                    instance.notification_template = f.read()
                    logger.info(
                        f"Template de notificação carregado para "
                        f"Email #{instance.pkid}"
                    )

            # Salva apenas se algum template foi carregado
            if (
                instance.notification_template
            ):
                instance.save(
                    update_fields=[
                        "notification_template",
                    ]
                )

        except Exception as e:
            logger.error(f"Erro ao carregar templates de e-mail: {e}")


@receiver(signals.pre_save, sender=models.Email)
def pre_save_email_validation(sender, instance, raw, using, **kwargs):
    """Valida dados do modelo Email antes de salvar.

    Executa validações adicionais e normalização de dados antes
    que a instância seja salva no banco de dados.

    Args:
        sender: A classe do modelo (Email)
        instance: A instância do modelo Email
        raw: Boolean indicando se foi carregamento de fixture
        using: Nome do banco de dados usado
        **kwargs: Argumentos adicionais

    """
    if not raw:
        try:
            # Executa validação completa do modelo
            instance.full_clean()

            # Normaliza assuntos (remove espaços extras)
            if instance.notification_subject:
                instance.notification_subject = " ".join(
                    instance.notification_subject.split()
                )

            logger.debug(
                f"Validação pré-save executada para Email #{instance.pkid}"
            )

        except ValidationError as e:
            logger.error(f"Erro de validação no Email #{instance.pkid}: {e}")
            raise


@receiver(signals.post_save, sender=models.Address)
def post_save_address_logging(sender, instance, created, raw, using, **kwargs):
    """Log de operações no modelo Address.

    Registra operações de criação e atualização de endereços
    para auditoria e monitoramento.

    Args:
        sender: A classe do modelo (Address)
        instance: A instância do modelo Address
        created: Boolean indicando se foi uma criação nova
        raw: Boolean indicando se foi carregamento de fixture
        using: Nome do banco de dados usado
        **kwargs: Argumentos adicionais

    """
    if not raw:
        if created:
            logger.info(
                f"Novo endereço criado: {instance} "
                f"(ID: {instance.id}, por: {instance.created_by})"
            )
        else:
            logger.info(
                f"Endereço atualizado: {instance} "
                f"(ID: {instance.id}, por: {instance.updated_by})"
            )


@receiver(signals.pre_save, sender=models.Address)
def pre_save_address_normalization(sender, instance, raw, using, **kwargs):
    """Normaliza dados do endereço antes de salvar.

    Aplica formatação padrão em campos como CEP e normalização
    de texto em campos de endereço.

    Args:
        sender: A classe do modelo (Address)
        instance: A instância do modelo Address
        raw: Boolean indicando se foi carregamento de fixture
        using: Nome do banco de dados usado
        **kwargs: Argumentos adicionais

    """
    if not raw:
        # Normaliza campos de texto (capitalização)
        if instance.street:
            instance.street = instance.street.title().strip()
        if instance.district:
            instance.district = instance.district.title().strip()
        if instance.city:
            instance.city = instance.city.title().strip()
        if instance.complement:
            instance.complement = instance.complement.strip()

        # Normaliza país para formato padrão
        if instance.country:
            instance.country = instance.country.title().strip()
            if instance.country.lower() in ["brasil", "brazil", "br"]:
                instance.country = "Brasil"

        logger.debug(
            f"Normalização pré-save executada para Address #{instance.pkid}"
        )


# Signal genérico para rastreabilidade em todos os BaseModel
@receiver(signals.pre_save)
def pre_save_base_model_tracking(sender, instance, raw, using, **kwargs):
    """Adiciona rastreabilidade automática para todos os modelos BaseModel.

    Este signal é executado para qualquer modelo que herde de BaseModel
    e automatiza o preenchimento dos campos de rastreabilidade.

    Args:
        sender: A classe do modelo
        instance: A instância do modelo
        raw: Boolean indicando se foi carregamento de fixture
        using: Nome do banco de dados usado
        **kwargs: Argumentos adicionais

    """
    # Verifica se o modelo herda de BaseModel
    if (
        not raw
        and hasattr(instance, "_meta")
        and hasattr(instance, "created_at")
        and hasattr(instance, "updated_at")
    ):
        # Se é uma nova instância e não tem created_at, define agora
        if not instance.pk and not instance.created_at:
            instance.created_at = timezone.now()

        # Sempre atualiza o updated_at
        instance.updated_at = timezone.now()

        logger.debug(
            f"Rastreabilidade atualizada para {sender.__name__} "
            f"#{getattr(instance, 'pkid', 'new')}"
        )


@receiver(signals.post_delete)
def post_delete_base_model_logging(sender, instance, using, **kwargs):
    """Log de operações de hard delete em modelos BaseModel.

    Como os modelos BaseModel usam soft delete por padrão,
    este signal captura operações de hard delete (remoção física).

    Args:
        sender: A classe do modelo
        instance: A instância do modelo removida
        using: Nome do banco de dados usado
        **kwargs: Argumentos adicionais

    """
    # Verifica se o modelo herda de BaseModel
    if hasattr(instance, "_meta") and hasattr(instance, "pkid"):
        logger.warning(
            f"HARD DELETE executado: {sender.__name__} "
            f"#{getattr(instance, 'pkid', 'unknown')} "
            f"(ID: {getattr(instance, 'id', 'unknown')})"
        )


# Signal para validação de Singleton no modelo Email
@receiver(signals.pre_save, sender=models.Email)
def pre_save_email_singleton_validation(
    sender, instance, raw, using, **kwargs
):
    """Garante que apenas uma instância do modelo Email pode existir.

    Implementa o padrão Singleton validando que não existe
    outra instância ativa antes de salvar.

    Args:
        sender: A classe do modelo (Email)
        instance: A instância do modelo Email
        raw: Boolean indicando se foi carregamento de fixture
        using: Nome do banco de dados usado
        **kwargs: Argumentos adicionais

    """
    if not raw and not instance.pk:
        # Verifica se já existe uma configuração de email ativa
        existing = models.Email.objects.filter(is_active=True).first()
        if existing:
            logger.error(
                f"Tentativa de criar segunda instância de Email "
                f"(já existe: #{existing.pkid})"
            )
            raise ValidationError(
                "Só pode haver uma configuração de e-mail ativa no sistema."
            )
