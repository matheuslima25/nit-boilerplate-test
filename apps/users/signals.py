import logging

from django.db.models import signals
from django.dispatch import receiver

from apps.users import models

logger = logging.getLogger("django")


@receiver(signals.pre_save, sender=models.User)
def user_pre_save_signal(sender, instance, *args, **kwargs):
    """
    Pre_save signal, only for add a username to the User
    instance if it won't have one
    :param sender:
    :param instance:
    :param args:
    :param kwargs:
    """
    if instance.email and not instance.username:
        email = str(instance.email).lower().replace(" ", "")
        logger.info(f"{email} username has been created.")
        instance.email = email
        instance.username = email


@receiver(signals.post_save, sender=models.User)
def post_save_user(sender, instance, created, raw, using, *args, **kwargs):
    # Verifica se algum atributo foi alterado
    [
        key
        for key, value in instance._get_current_state().items()
        if (
            key in instance._original_state
            and instance._original_state[key] != value
        )
    ]


@receiver(signals.pre_save, sender=models.Profile)
def profile_pre_save_signal(sender, instance, *args, **kwargs):
    if (
        instance.name
        and isinstance(instance.name, str)
        and not instance.name.isupper()
    ):
        instance.name = str(instance.name).upper()
