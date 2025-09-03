"""Serializers para gerenciamento de usuários com autenticação Keycloak.

IMPORTANTE: Funcionalidades de autenticação (registro, login, reset de senha)
são gerenciadas pelo Keycloak. Estes serializers são apenas para gestão
de dados de usuários já autenticados.
"""
from django.apps import apps
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from rest_framework import serializers

from apps.commons.api.v1.serializers import BaseSerializer
from apps.users import models
from tools.utils import validate_cellphone

"""
User serializers
"""


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ("id", "name",)


class UserSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField(read_only=True)
    associated_clients = serializers.SerializerMethodField(read_only=True)

    def to_representation(self, instance):
        representation = super(UserSerializer, self).to_representation(
            instance
        )

        if instance.groups.all():
            groups_data = GroupSerializer(
                instance.groups.all(), many=True
            ).data
            representation["groups"] = groups_data

        return representation

    class Meta:
        model = models.User
        exclude = ("pkid",)
        extra_kwargs = {
            "password": {"write_only": True},
            "groups": {"read_only": True}
        }
        read_only_fields = (
            "is_active",
            "is_staff",
            "is_superuser",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "first_login_accomplished",
            "date_joined",
            "last_login",
        )

    def get_profile(self, instance):
        profile = models.Profile.objects.filter(user=instance).first()
        return ProfileSerializer(profile, many=False).data

    def get_associated_clients(self, instance):
        clients = models.Client.objects.filter(client=instance).distinct()
        return ClientSerializer(clients, many=True).data


class UserOnboardingSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        try:
            if "cellphone" in attrs:
                validate_cellphone(attrs.get("cellphone"))
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)

        return attrs

    name = serializers.CharField(required=True)
    cellphone = serializers.CharField(required=True)
    cep = serializers.CharField(required=True)
    state = serializers.CharField(required=False)
    city = serializers.CharField(required=True)
    district = serializers.CharField(required=True)
    street = serializers.CharField(required=True)
    number = serializers.CharField(required=True)
    complement = serializers.CharField(required=False, allow_blank=True)
    avatar = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = models.User
        fields = (
            "name",
            "first_login_accomplished",
            "status",
            "is_active",
            "groups",
            "cellphone",
            "cep",
            "state",
            "city",
            "district",
            "street",
            "number",
            "complement",
            "avatar",
        )


class ProfileUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=True)
    cellphone = serializers.CharField(required=False, allow_blank=True)
    cep = serializers.CharField(required=False, allow_blank=True)
    state = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(required=False, allow_blank=True)
    district = serializers.CharField(required=False, allow_blank=True)
    street = serializers.CharField(required=False, allow_blank=True)
    number = serializers.CharField(required=False, allow_blank=True)
    complement = serializers.CharField(required=False, allow_blank=True)
    avatar = serializers.FileField(required=False)


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer para atualização de dados de usuários autenticados via Keycloak.

    NOTA: Funcionalidades de senha foram removidas, pois são gerenciadas
    pelo Keycloak.
    """

    class Meta:
        model = models.User
        exclude = ("pkid", "password")
        extra_kwargs = {
            "email": {"read_only": True},  # Email gerenciado pelo Keycloak
            "groups": {"read_only": True}
        }
        read_only_fields = (
            "is_active",
            "is_staff",
            "is_superuser",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "first_login_accomplished",
            "date_joined",
            "last_login",
            "keycloak_id",  # ID do Keycloak
        )


class ProfileSerializer(BaseSerializer):
    """Serializer para dados de perfil de usuários."""

    class Meta(BaseSerializer.Meta):
        model = apps.get_model("users", "Profile")

    def to_representation(self, instance):
        representation = super(ProfileSerializer, self).to_representation(
            instance
        )

        if instance.address:
            # Serializar endereço separadamente
            address_serializer = BaseSerializer(instance.address, many=False)
            representation["address"] = address_serializer.data

        return representation


class ClientSerializer(BaseSerializer):
    """Serializer para dados de clientes."""

    class Meta(BaseSerializer.Meta):
        model = apps.get_model("users", "Client")
        fields = ("id", "name", "cpf_cnpj")
