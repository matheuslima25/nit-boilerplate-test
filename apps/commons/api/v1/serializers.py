import json
import uuid
from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers


class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


class PkToIdMixin:
    def to_representation(self, instance):
        data = super().to_representation(instance)
        for field_name, field in self.fields.items():
            if isinstance(field, serializers.PrimaryKeyRelatedField):
                related_instance = getattr(instance, field_name)
                if related_instance:
                    data[field_name] = related_instance.id
                else:
                    data[field_name] = None
        return json.loads(UUIDEncoder().encode(data))


class UUIDPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        return super().get_queryset()

    def to_internal_value(self, data):
        try:
            # Tentar converter o valor para UUID
            uuid_value = uuid.UUID(data)
            # Obter o modelo associado ao campo de chave estrangeira
            model_class = self.queryset.model
            # Tentar obter o objeto usando o UUID
            obj = model_class.objects.get(id=uuid_value)
            return obj
        except (ValueError, ObjectDoesNotExist):
            raise serializers.ValidationError(f"{self.queryset.model.__name__} object with id {data} does not exist.")


class BaseSerializer(PkToIdMixin, serializers.ModelSerializer):
    class Meta:
        model = None
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        read_only_fields = ["created_at", "updated_at", "deleted_at", "created_by", "updated_by", "deleted_by",
                            "is_active"]
        if not all(hasattr(self.Meta.model, attr) for attr in read_only_fields):
            read_only_fields = []
        self.Meta.read_only_fields = read_only_fields

    def get_fields(self):
        fields = super().get_fields()
        fields.pop("pkid", None)
        for field_name, field in fields.items():
            if isinstance(field, serializers.PrimaryKeyRelatedField) and not field.read_only:
                if hasattr(field, "queryset"):
                    fields[field_name] = UUIDPrimaryKeyRelatedField(queryset=field.queryset,
                                                                    allow_null=field.allow_null,
                                                                    required=field.required)
        return fields
