import uuid

from django.apps import apps
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, ContentType, DELETION
from django.core.exceptions import FieldDoesNotExist
from django.db.models import FileField, Q
from django.utils import timezone
from django.utils.datastructures import MultiValueDictKeyError
from django.utils.module_loading import import_string
from django.utils.translation import gettext as _
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import DjangoModelPermissions, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.commons.api.v1 import serializers
from tools.utils import retrieve_file_from_bytes, get_mytimezone_date


class LoggingMethodMixin:
    """Adds methods that log changes made to users' data.
    To use this, subclass it and ModelViewSet, and override _get_logging_user(). Ensure
    that the viewset you're mixing this into has `self.model` and `self.serializer_class`
    attributes.
    """

    def _get_logging_user(self):
        """Return the user of this logged item. Needs overriding in any subclass."""
        raise NotImplementedError

    def extra_data(self, data):
        """Hook to append more data."""
        return {}

    def log(self, operation, instance):
        if operation == ADDITION:
            action_message = _('Created')
        if operation == CHANGE:
            action_message = _('Updated')
        if operation == DELETION:
            action_message = _('Deleted')
        LogEntry.objects.log_action(
            user_id=self.request.user.pkid,
            content_type_id=ContentType.objects.get_for_model(instance).pk,
            object_id=instance.pk,
            object_repr=str(instance),
            action_flag=operation,
            change_message=action_message + ' ' + str(instance))

    def _log_on_create(self, serializer):
        """Log the up-to-date serializer.data."""
        self.log(operation=ADDITION, instance=serializer.instance)

    def _log_on_update(self, serializer):
        """Log data from the updated serializer instance."""
        self.log(operation=CHANGE, instance=serializer.instance)

    def _log_on_destroy(self, instance):
        """Log data from the instance before it gets deleted."""
        self.log(operation=DELETION, instance=instance)


class BaseCreateApiViewSet(mixins.CreateModelMixin, GenericViewSet, LoggingMethodMixin):
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.validated_data["created_by"] = self.request.user
        serializer.save()
        self._log_on_create(serializer)

    def create(self, request, *args, **kwargs):
        data = request.data
        model_class = self.model

        # Verifica se o modelo possui um campo FileField
        has_file_field = any(
            isinstance(field, FileField)
            for field in model_class._meta.fields
        )
        has_bytes_fields = any(key.endswith("_bytes") for key in data.keys())

        updated_data = {}

        if has_file_field and has_bytes_fields:
            # Verifica se os campos _bytes estão presentes nos dados
            for field_name, field_value in data.items():
                if field_name.endswith('_bytes'):
                    # Verifica se o campo correspondente existe sem o sufixo _bytes
                    original_field_name = field_name[:-6]
                    # Pegando a extensão do arquivo
                    try:
                        file_extension = data[f"{original_field_name}_name"]
                    except MultiValueDictKeyError:
                        return Response(data={"error": _(
                            u"The field 'field_name'_extension is required for base64 to file conversion.")},
                            status=status.HTTP_400_BAD_REQUEST)
                    file_extension = file_extension.split(".")[-1]
                    # Faz a tentativa de conversão
                    converted_value = retrieve_file_from_bytes(field_value, file_extension)
                    updated_data[original_field_name] = converted_value

        if updated_data:
            mutable_data = data.copy()
            mutable_data._mutable = True
            mutable_data.update(updated_data)
            mutable_data._mutable = False
            data = mutable_data

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class BaseListApiViewSet(mixins.ListModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated, DjangoModelPermissions]
    model = None

    def get_queryset(self):
        if self.model:
            queryset = self.model.objects.all()
        else:
            queryset = super(BaseListApiViewSet, self).get_queryset()

        if getattr(self, "swagger_fake_view", False):
            return queryset.none()

        if self.request:

            if "page" not in self.request.query_params:
                self.pagination_class = None

            """
            To get filters and searches
            """
            filters = {}

            for param, value in self.request.GET.items():
                if param != "page":
                    field_name = param.split("__")[0]
                    try:
                        # Tenta obter o campo correspondente ao parâmetro da consulta
                        field = queryset.model._meta.get_field(field_name)
                    except FieldDoesNotExist:
                        # Descomentar a linha abaixo somente haja a necessidade de log dos parâmetros não aceitos
                        # print(f"[BaseListApiViewSet] Campo inválido para lookups: {field_name}")
                        continue

                    if value in ["bool(true)", "true", "True", "TRUE", True]:
                        filters[param] = True
                    elif value in ["bool(false)", "false", "False", "FALSE", False]:
                        filters[param] = False
                    elif field.get_internal_type() in ["BooleanField"]:
                        filters[field_name] = True if value.lower() == "true" else False
                    elif field.get_internal_type() in ["DateField"]:
                        filters[param] = get_mytimezone_date(value)
                    elif field.get_internal_type() in ["ForeignKey"]:
                        try:
                            value = uuid.UUID(value)
                            fk_param = str(param).split("__")
                            param = param if fk_param[-1] == "id" else f"{fk_param[0]}__id"
                            filters[param] = value
                        except ValueError:
                            filters[param] = value
                    else:
                        filters[param] = value

            if filters:
                queryset = queryset.filter(Q(**filters))

        if all(hasattr(queryset.model, attr) for attr in ["updated_by", "created_by", "is_active"]):
            return queryset.filter(is_active=True).order_by('-created_at', '-updated_at')

        return queryset.all().order_by("-id")


class BaseRetrieveApiViewSet(mixins.RetrieveModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated, DjangoModelPermissions]
    lookup_field = "id"

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if not hasattr(instance, "is_active") or instance.is_active:
            serializer = self.get_serializer(instance)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_404_NOT_FOUND)


class BaseUpdateApiViewSet(mixins.UpdateModelMixin, GenericViewSet, LoggingMethodMixin):
    permission_classes = [IsAuthenticated, DjangoModelPermissions]
    lookup_field = "id"

    def perform_update(self, serializer):
        serializer.validated_data["updated_by"] = self.request.user
        serializer.save()
        self._log_on_update(serializer)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # Verifica se o modelo possui um campo FileField
        has_file_field = any(
            isinstance(field, FileField)
            for field in instance.__class__._meta.fields
        )

        has_bytes_fields = any(key.endswith("_bytes") for key in request.data.keys())

        if has_file_field and has_bytes_fields:
            # Verifica se os campos _bytes estão presentes nos dados
            for field_name, field_value in request.data.items():
                if field_name.endswith('_bytes'):
                    # Verifica se o campo correspondente existe sem o sufixo _bytes
                    original_field_name = field_name[:-6]
                    # Pegando a extensão do arquivo
                    try:
                        file_extension = request.data[f"{original_field_name}_name"]
                    except MultiValueDictKeyError:
                        return Response(data={"erro": _(
                            u"É necessário o campo 'nome_do_campo'_extension para conversão de base64 para arquivo.")},
                            status=status.HTTP_400_BAD_REQUEST)
                    file_extension = file_extension.split(".")[-1]
                    # Faz a tentativa de conversão
                    converted_value = retrieve_file_from_bytes(field_value, file_extension)
                    setattr(instance, original_field_name, converted_value)

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)


class BaseDestroyApiViewSet(mixins.DestroyModelMixin, GenericViewSet, LoggingMethodMixin):
    permission_classes = [IsAuthenticated, DjangoModelPermissions]
    lookup_field = "id"

    def perform_destroy(self, instance):
        instance.deleted_by = self.request.user
        instance.deleted_at = timezone.now()
        instance.save()
        instance.delete()
        self._log_on_destroy(instance)


class BaseModelApiViewSet(BaseCreateApiViewSet,
                          BaseRetrieveApiViewSet,
                          BaseUpdateApiViewSet,
                          BaseDestroyApiViewSet,
                          BaseListApiViewSet,
                          GenericViewSet):
    """A viewset that provides default `create()`, `retrieve()`, `update()`,
    `partial_update()`, `destroy()` and `list()` actions.
    """

    model = None

    def get_serializer_class(self):
        model = self.get_queryset().model
        app_name = apps.get_containing_app_config(type(self).__module__).name
        serializer_name = f"{app_name}.api.v1.serializers.{model.__name__}Serializer"

        try:
            serializer_class = import_string(serializer_name)
        except (ImportError, AttributeError):
            if self.model:
                serializers.BaseSerializer.Meta.model = self.model
            serializer_class = serializers.BaseSerializer

        return serializer_class


class BaseReadOnlyModelViewSet(BaseRetrieveApiViewSet, BaseListApiViewSet, GenericViewSet):
    """A viewset that provides default `list()` and `retrieve()` actions."""

    model = None

    def get_serializer_class(self):
        model = self.get_queryset().model
        app_name = apps.get_containing_app_config(type(self).__module__).name
        serializer_name = f"{app_name}.api.v1.serializers.{model.__name__}Serializer"

        try:
            serializer_class = import_string(serializer_name)
        except (ImportError, AttributeError):
            if self.model:
                serializers.BaseSerializer.Meta.model = self.model
            serializer_class = serializers.BaseSerializer

        return serializer_class


class AddressViewSet(BaseModelApiViewSet):
    model = apps.get_model("commons", "Address")

    @action(
        methods=["get"],
        detail=False,
        url_path="mine",
        permission_classes=[IsAuthenticated],
    )
    def get_mine(self, request, *args, **kwargs):
        instance = apps.get_model("users", "Profile").objects.filter(user=self.request.user).first()
        return Response(self.get_serializer(instance.address, many=False).data, status=status.HTTP_200_OK)
