"""Sometimes in your Django model you want to raise a ``ValidationError``
in the ``save`` method, for some reason.
This exception is not managed by Django Rest Framework because it
occurs after its validation
process. So at the end, you'll have a 500.
Correcting this is as simple as overriding the exception handler, by
converting the Django
``ValidationError`` to a DRF one.
"""
import logging

from deep_translator import GoogleTranslator
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.views import Response, exception_handler as drf_exception_handler


def exception_handler(exc, context):
    """Handle Django ValidationError as an accepted exception
    Must be set in settings:
    REST_FRAMEWORK = {
    ...     # ...
    ...     'EXCEPTION_HANDLER': 'apps.commons.api.v1.exceptions.exception_handler',
    ...     # ...
    ... }
    For the parameters, see ``exception_handler``.
    """
    response = drf_exception_handler(exc, context)

    handlers = {
        "NotFound": _handle_not_found_error,
        "ValidationError": _handle_generic_error,
        "IntegrityError": _handle_integrity_error,
    }

    exception_class = exc.__class__.__name__

    logging.error(f"Original error detail and callstack: {exc}")

    if exception_class in handlers:
        return handlers[exception_class](exc, context, response)
    return response


def _handle_generic_error(exc, context, response):
    status_code = response.status_code
    response.data = {"status_code": status_code, "errors": response.data}

    return response


def _handle_integrity_error(exc, context, response):
    response = Response(
        {
            'errors': [('Parece que há um conflito entre os dados que você está tentando salvar e os seus dados atuais.'
                       ' Revise suas entradas e tente novamente.')]
        },
        status=status.HTTP_400_BAD_REQUEST
    )

    return response


def _handle_not_found_error(exc, context, response):
    view = context.get("view", None)

    if view and hasattr(view, "queryset") and view.queryset is not None:
        status_code = response.status_code
        error_key = view.queryset.model._meta.verbose_name
        response.data = {
            "status_code": status_code,
            "errors": {error_key: response.data["detail"]},
        }

    else:
        response = _handle_generic_error(exc, context, response)
    return response


def protuguese_exception_handler(exc, context):
    """Handle Django ValidationError as an accepted exception
    Must be set in settings:
    REST_FRAMEWORK = {
    ...     # ...
    ...     'EXCEPTION_HANDLER': 'apps.commons.api.v1.exceptions.protuguese_exception_handler',
    ...     # ...
    ... }
    For the parameters, see ``exception_handler``.
    """
    if isinstance(exc, Exception):
        if hasattr(exc, "message_dict"):
            if type(exc.message_dict) == dict:
                errors = ""
                for value in exc.message_dict.values():
                    if type(value) == list:
                        value = "".join(value)
                    errors += GoogleTranslator(source="en", target="pt").translate(
                        value
                    )
                exc = DRFValidationError(detail={"erro": errors})
        elif hasattr(exc, "message"):
            exc = DRFValidationError(
                detail={
                    "erro": GoogleTranslator(source="en", target="pt").translate(
                        exc.message
                    )
                }
            )
        else:
            errors = ""
            if type(exc.args) == tuple:
                try:
                    for value in exc.args:
                        value = "".join(
                            [e.title() for e in list(dict(value).values())[0]]
                        )
                        errors += GoogleTranslator(source="en", target="pt").translate(
                            f"{value} ", dest="pt"
                        )
                except ValueError:
                    for value in exc.args:
                        errors += GoogleTranslator(source="en", target="pt").translate(
                            f"{value.title()} ", dest="pt"
                        )
            else:
                for data in [dict(dt) for dt in exc.args]:
                    for _key, values in data.items():
                        for value in values:
                            errors += GoogleTranslator(
                                source="en", target="pt"
                            ).translate(f"{value.title()} ", dest="pt")
            exc = DRFValidationError(detail={"erro": errors})

        logging.error(f"Original error detail and callstack: {exc}")

    return drf_exception_handler(exc, context)
