import re

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from tools.utils import calculate_first_digit, calculate_second_digit


class CPFCNPJField(models.CharField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate(self, value, model_instance):
        super().validate(value, model_instance)
        if value:
            if len(value) == 11:
                #  Obtém os números do CPF e ignora outros caracteres
                value = [int(char) for char in value if char.isdigit()]

                #  Verifica se o CPF tem todos os números iguais,
                #  ex: 111.111.111-11
                if value == value[::-1]:
                    raise ValidationError(_("CPF inválido."), "invalid")

                #  Valida os dois dígitos verificadores
                for i in range(9, 11):
                    number = sum(
                        (value[num] * ((i + 1) - num) for num in range(0, i))
                    )
                    digit = ((number * 10) % 11) % 10
                    if digit != value[i]:
                        raise ValidationError(_("CPF inválido."), "invalid")
            elif len(value) == 14:
                # CNPJ validation
                first_part = value[:12]
                second_part = value[:13]
                first_digit = value[12]
                second_digit = value[13]

                if not (first_digit == calculate_first_digit(first_part) and
                        second_digit == calculate_second_digit(second_part)):
                    raise ValidationError(_("CNPJ inválido."), "invalid")
            else:
                raise ValidationError(_("CPF ou CNPJ inválido."), "invalid")


class PhoneField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 11)
        super().__init__(*args, **kwargs)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value:
            return (
                value.replace("-", "")
                .replace("(", "")
                .replace(")", "")
                .replace(" ", "")
            )
        return value

    def validate(self, value, model_instance):
        super().validate(value, model_instance)
        if value and not re.match(r"^\d{10}$", value):
            raise ValidationError(_("Telefone fixo inválido."), "invalid")


class CellphoneField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 22)
        super().__init__(*args, **kwargs)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value:
            return (
                value.replace("-", "")
                .replace("(", "")
                .replace(")", "")
                .replace(" ", "")
                .replace("+", "")
            )
        return value

    def validate(self, value, model_instance):
        super().validate(value, model_instance)
        if value and not re.match(r"^\d{11}$", value):
            raise ValidationError(_("Telefone celular inválido."), "invalid")


class RGField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 50)
        super().__init__(*args, **kwargs)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value:
            return (
                value.replace("-", "")
                .replace(".", "")
                .replace(" ", "")
                .replace("/", "")
                .upper()
            )
        return value

    def validate(self, value, model_instance):
        super().validate(value, model_instance)
        if value and not re.match(r"^\d{7,8}[0-9xX]$", value):
            raise ValidationError(_("RG inválido."), "invalid")
