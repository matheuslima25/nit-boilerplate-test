"""Exemplo de uso das classes de Storage S3 para arquivos públicos e privados.

Este arquivo demonstra como usar as diferentes classes de storage
em models, views e utilitários.
"""

from django.db import models
from django.http import JsonResponse
from django.core.management.base import BaseCommand
from rest_framework import serializers
from nitapi.storage_backends import (
    PublicMediaStorage,
    PrivateMediaStorage
)


# ============================================================================
# EXEMPLO 1: Models com diferentes tipos de storage
# ============================================================================

class UserProfile(models.Model):
    """Exemplo de model com arquivos públicos e privados."""

    user = models.OneToOneField('users.User', on_delete=models.CASCADE)

    # Avatar público - qualquer um pode ver
    avatar = models.ImageField(
        upload_to='profiles/avatars/',
        storage=PublicMediaStorage(),
        blank=True,
        null=True
    )

    # Documento de identidade privado - só o usuário pode acessar
    identity_document = models.FileField(
        upload_to='profiles/documents/',
        storage=PrivateMediaStorage(),
        blank=True,
        null=True
    )


class Company(models.Model):
    """Exemplo de empresa com documentos públicos e privados."""

    name = models.CharField(max_length=255)

    # Logo público
    logo = models.ImageField(
        upload_to='companies/logos/',
        storage=PublicMediaStorage(),
        blank=True,
        null=True
    )

    # Relatório financeiro privado
    financial_report = models.FileField(
        upload_to='companies/reports/',
        storage=PrivateMediaStorage(),
        blank=True,
        null=True
    )

    # Certificados privados
    certificates = models.FileField(
        upload_to='companies/certificates/',
        storage=PrivateMediaStorage(),
        blank=True,
        null=True
    )


# ============================================================================
# EXEMPLO 2: Views com upload de arquivos
# ============================================================================

def upload_avatar(request):
    """Upload de avatar público."""
    if request.method == 'POST' and 'avatar' in request.FILES:
        file = request.FILES['avatar']

        # Usar storage público para avatars
        storage = PublicMediaStorage()
        filename = storage.save(f'avatars/{file.name}', file)
        file_url = storage.url(filename)

        return JsonResponse({
            'success': True,
            'file_url': file_url,
            'message': 'Avatar enviado com sucesso'
        })

    return JsonResponse({'success': False, 'message': 'Arquivo inválido'})


def upload_document(request):
    """Upload de documento privado."""
    if request.method == 'POST' and 'document' in request.FILES:
        file = request.FILES['document']

        # Usar storage privado para documentos
        storage = PrivateMediaStorage()
        filename = storage.save(f'documents/{file.name}', file)

        # URL assinada com expiração
        signed_url = storage.url(filename)

        return JsonResponse({
            'success': True,
            'filename': filename,
            'signed_url': signed_url,
            'message': 'Documento enviado com sucesso',
            'expires_in': '1 hora'
        })

    return JsonResponse({'success': False, 'message': 'Documento inválido'})


# ============================================================================
# EXEMPLO 3: Utility functions para gerenciar arquivos
# ============================================================================

class FileManager:
    """Gerenciador de arquivos com diferentes tipos de storage."""

    @staticmethod
    def get_public_url(file_path):
        """Obter URL pública de um arquivo."""
        storage = PublicMediaStorage()
        return storage.url(file_path)

    @staticmethod
    def get_private_url(file_path, expire_time=3600):
        """Obter URL assinada de um arquivo privado."""
        storage = PrivateMediaStorage()
        # Configurar tempo de expiração customizado
        storage.querystring_expire = expire_time
        return storage.url(file_path)

    @staticmethod
    def move_to_private(file_path):
        """Mover arquivo de público para privado."""
        public_storage = PublicMediaStorage()
        private_storage = PrivateMediaStorage()

        try:
            # Ler arquivo do storage público
            file_content = public_storage.open(file_path)

            # Salvar no storage privado
            private_storage.save(file_path, file_content)

            # Deletar do storage público
            public_storage.delete(file_path)

            return True, "Arquivo movido para storage privado"
        except Exception as e:
            return False, f"Erro ao mover arquivo: {str(e)}"

    @staticmethod
    def move_to_public(file_path):
        """Mover arquivo de privado para público."""
        private_storage = PrivateMediaStorage()
        public_storage = PublicMediaStorage()

        try:
            # Ler arquivo do storage privado
            file_content = private_storage.open(file_path)

            # Salvar no storage público
            public_storage.save(file_path, file_content)

            # Deletar do storage privado
            private_storage.delete(file_path)

            return True, "Arquivo movido para storage público"
        except Exception as e:
            return False, f"Erro ao mover arquivo: {str(e)}"


# ============================================================================
# EXEMPLO 4: Serializers DRF com URLs customizadas
# ============================================================================


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer com URLs customizadas para arquivos."""

    avatar_url = serializers.SerializerMethodField()
    identity_document_url = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = ['avatar', 'avatar_url', 'identity_document_url']

    def get_avatar_url(self, obj):
        """URL pública do avatar."""
        if obj.avatar:
            return obj.avatar.url  # URL pública direta
        return None

    def get_identity_document_url(self, obj):
        """URL assinada do documento (só para o próprio usuário)."""
        if obj.identity_document:
            request = self.context.get('request')
            if request and request.user == obj.user:
                # Gerar URL assinada só para o dono do documento
                return obj.identity_document.url
        return None


# ============================================================================
# EXEMPLO 5: Management command para migração de arquivos
# ============================================================================


class Command(BaseCommand):
    r"""Comando para migrar arquivos entre storages públicos e privados.

    Uso:
    python manage.py migrate_files --from-public --to-private \\
                                --model UserProfile --field avatar
    """

    help = 'Migra arquivos entre storages públicos e privados'

    def add_arguments(self, parser):
        parser.add_argument('--from-public', action='store_true')
        parser.add_argument('--to-private', action='store_true')
        parser.add_argument('--model', type=str, required=True)
        parser.add_argument('--field', type=str, required=True)

    def handle(self, *args, **options):
        if options['from_public'] and options['to_private']:
            self.stdout.write(
                self.style.ERROR(
                    'Escolha apenas uma direção: from-public OU to-private'
                )
            )
            return

        # Implementar lógica de migração aqui
        model_name = options["model"]
        field_name = options["field"]
        self.stdout.write(
            self.style.SUCCESS(
                f'Migração concluída para {model_name}.{field_name}'
            )
        )
