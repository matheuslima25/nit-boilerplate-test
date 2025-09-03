"""API ViewSets para gerenciamento de usuários com autenticação Keycloak.

IMPORTANTE: Todas as operações de autenticação (login, logout, registro,
reset de senha) são gerenciadas pelo Keycloak. Estas views são apenas
para gestão de dados de usuários já autenticados.
"""
from apps.commons.api.v1.permissions import MineOrReadOnly
from apps.commons.api.v1.viewsets import BaseModelApiViewSet
from apps.users.api.v1 import exceptions, serializers
from apps.users.constants import UserConstants
from django.apps import apps
from django.utils.translation import gettext_lazy as _
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


class UserViewSet(BaseModelApiViewSet):
    """ViewSet para gerenciamento de usuários autenticados via Keycloak."""

    model = apps.get_model("users", "User")

    def get_serializer_class(self):
        """Retorna o serializer apropriado baseado no método HTTP."""
        if self.request and self.request.method in ("PATCH", "PUT"):
            return serializers.UserUpdateSerializer
        return serializers.UserSerializer

    @action(
        methods=["get"],
        detail=False,
        url_path="me",
        permission_classes=[IsAuthenticated],
    )
    def get_me(self, request, *args, **kwargs):
        """Retorna os dados do usuário autenticado via Keycloak."""
        serializer_data = self.get_serializer(
            self.request.user, many=False
        ).data
        return Response(serializer_data, status=status.HTTP_200_OK)


class UserOnboardingViewSet(viewsets.ViewSet, generics.GenericAPIView):
    """ViewSet para onboarding de usuários autenticados via Keycloak."""

    serializer_class = serializers.UserOnboardingSerializer

    @action(
        methods=["post"],
        detail=False,
        permission_classes=[IsAuthenticated],
    )
    def onboarding(self, request, *args, **kwargs):
        """Executa o onboarding inicial do usuário.

        O usuário já foi autenticado via Keycloak, este endpoint
        apenas coleta dados adicionais necessários.
        """
        if not self.request.user.first_login_accomplished:
            # Dados para atualização do usuário
            data = {
                "name": request.data["name"],
                "first_login_accomplished": True,
                "status": UserConstants.USER_STATUS_ACTIVE,
                "is_active": True,
                "groups": [
                    group.pk for group in self.request.user.groups.all()
                ],
                "cellphone": request.data["cellphone"],
                "cep": request.data["cep"],
                "state": request.data["state"],
                "city": request.data["city"],
                "district": request.data["district"],
                "street": request.data["street"],
                "number": request.data["number"],
                "complement": request.data["complement"],
            }

            serializer = self.get_serializer(self.request.user, data=data)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            # Criar ou atualizar perfil
            Profile = apps.get_model("users", "Profile")
            profile, created = Profile.objects.get_or_create(
                user=self.request.user,
                defaults={
                    "name": self.request.data["name"],
                    "cellphone": self.request.data["cellphone"]
                }
            )

            # Criar endereço se necessário
            if not profile.address:
                Address = apps.get_model("commons", "Address")
                address = Address.objects.create(
                    cep=request.data["cep"],
                    state=request.data["state"],
                    city=request.data["city"],
                    district=request.data["district"],
                    street=request.data["street"],
                    number=request.data["number"],
                    complement=request.data["complement"]
                )

                profile.address = address
                profile.save()

            user_data = serializers.UserSerializer(self.request.user).data
            return Response(user_data, status=status.HTTP_200_OK)
        else:
            raise exceptions.AlreadyDidFirstLogin


class ProfileViewSet(BaseModelApiViewSet):
    """ViewSet para gerenciamento de perfis de usuários autenticados."""

    model = apps.get_model("users", "Profile")
    permission_classes = [MineOrReadOnly]

    @action(
        methods=["get"],
        detail=False,
        url_path="mine",
        permission_classes=[IsAuthenticated],
    )
    def get_mine(self, request, *args, **kwargs):
        """Retorna o perfil do usuário autenticado."""
        instance = self.model.objects.filter(user=self.request.user).first()
        serializer_data = self.get_serializer(instance, many=False).data
        return Response(serializer_data, status=status.HTTP_200_OK)

    @action(
        methods=["patch"],
        detail=False,
        url_path="update-mine",
        permission_classes=[IsAuthenticated],
    )
    def update_mine(self, request, *args, **kwargs):
        """Atualiza o perfil do usuário autenticado."""
        instance = self.model.objects.filter(user=self.request.user).first()

        data = {
            "is_active": True,
            "groups": [group.pk for group in self.request.user.groups.all()],
        }

        optional_fields = [
            "name", "cellphone", "cep", "state", "city",
            "district", "street", "number", "complement", "avatar"
        ]

        for field in optional_fields:
            if field in request.data:
                data[field] = request.data[field]

        if "name" in data and not data["name"]:
            return Response(
                data={"error": _("É necessário um nome")},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = serializers.ProfileUpdateSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        profile_data = {
            "name": request.data.get(
                "name", instance.name if instance else ""
            ),
            "avatar": request.data.get(
                "avatar", instance.avatar if instance else None
            ),
            "cellphone": request.data.get(
                "cellphone", instance.cellphone if instance else ""
            ),
        }

        Profile = apps.get_model("users", "Profile")
        profile, created = Profile.objects.update_or_create(
            user=self.request.user,
            defaults=profile_data
        )

        # Atualizar endereço se necessário
        if instance and instance.address:
            address_data = {
                "cep": request.data.get("cep", instance.address.cep),
                "state": request.data.get("state", instance.address.state),
                "city": request.data.get("city", instance.address.city),
                "district": request.data.get(
                    "district", instance.address.district
                ),
                "street": request.data.get("street", instance.address.street),
                "number": request.data.get("number", instance.address.number),
                "complement": request.data.get(
                    "complement", instance.address.complement
                ),
            }

            # Atualiza os campos do endereço
            for key, value in address_data.items():
                setattr(profile.address, key, value)

            profile.address.save()

        return Response(status=status.HTTP_200_OK)


# =============================================================================
# IMPORTANTE: Todas as operações de autenticação são gerenciadas pelo Keycloak
# =============================================================================
# ✅ KEYCLOAK GERENCIA:
# - Login/Logout de usuários
# - Registro de novos usuários
# - Reset de senhas
# - Verificação de email
# - Geração e validação de tokens JWT
# - Single Sign-On (SSO)
#
# As views acima são apenas para gestão de dados de usuários
# já autenticados via Keycloak.
#
# =============================================================================
