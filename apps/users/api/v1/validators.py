import re

from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from apps.users.constants import UserConstants
from tools.validators import ModelSerializerValidator


class UserUsernameValidator(ModelSerializerValidator):
    def __call__(self, value):
        regex = re.compile(UserConstants.USERNAME_REGEX)
        if value.get("username") and not regex.match(value.get("username")):
            raise ValidationError({"username": UserConstants.USERNAME_VALIDATION_ERROR})


class UserIsActiveValidator(ModelSerializerValidator):
    def __call__(self, value):
        if not self.instance.is_active:
            raise ValidationError({"user": _("User is not active")})
