from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import APIException


class AlreadyDidFirstLogin(APIException):
    status_code = 403
    default_detail = _("Você já fez o processo de onboarding.")
