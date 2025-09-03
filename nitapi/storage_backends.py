from storages.backends.s3boto3 import S3Boto3Storage


class StaticStorage(S3Boto3Storage):
    """Storage para arquivos estáticos públicos (CSS, JS, images)."""

    location = "static"
    default_acl = "public-read"


class PrivateStaticStorage(S3Boto3Storage):
    """Storage para arquivos estáticos privados (docs internos, configs)."""

    location = "static-private"
    default_acl = "private"
    querystring_auth = True
    querystring_expire = 3600  # 1 hora


class PublicMediaStorage(S3Boto3Storage):
    """Storage para arquivos de media públicos (avatars, logos)."""

    location = "media"
    default_acl = "public-read"
    file_overwrite = False


class PrivateMediaStorage(S3Boto3Storage):
    """Storage para arquivos de media privados (documentos, relatórios)."""

    location = "media-private"
    default_acl = "private"
    file_overwrite = False
    querystring_auth = True
    querystring_expire = 3600  # 1 hora
