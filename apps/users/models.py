from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.commons.models import BaseModel
from apps.users.constants import UserConstants
from tools.fields import CPFCNPJField, RGField, CellphoneField, PhoneField
from tools.utils import path_and_rename


class UserManager(BaseUserManager):
    """Custom user model manager where email is the unique identifiers
    for authentication instead of usernames.
    """

    use_in_migrations = True

    def email_validator(self, email):
        """Validate the user email
        :param email:
        """
        try:
            validate_email(email)
        except ValidationError:
            raise ValueError(_("You must provide a valid email address."))

    def create_user(self, email, password, **extra_fields):
        """Create and save a User with the given email and password.
        :rtype: object.
        """
        if not email:
            raise ValueError(_("The Email must be set"))
        else:
            email = self.normalize_email(email)
            self.email_validator(email)

        user = self.model(email=email, **extra_fields)
        user.is_active = True
        user.set_password(password)
        user.save()

        return user

    def create_superuser(self, email, password, **extra_fields):
        """Create and save a SuperUser with the given email and password.
        :rtype: object.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        user = self.create_user(email, password, **extra_fields)

        return user


class User(AbstractBaseUser, BaseModel, PermissionsMixin):
    class Meta:
        verbose_name = _("Usuário")
        verbose_name_plural = _("Usuários")
        ordering = ["-created_at"]

    # Credentials
    email = models.EmailField(_("Email"), max_length=255, unique=True)
    username = models.CharField(_("Username"), max_length=255, unique=True, blank=True, null=True)
    cpf_cnpj = CPFCNPJField(_("CPF/CNPJ"), max_length=14, unique=True, null=True, blank=True)
    rg = RGField(_(u"RG"), blank=True, null=True)

    # Keycloak integration
    keycloak_id = models.CharField(
        _("Keycloak ID"),
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        help_text=_("ID do usuário no Keycloak para autenticação agnóstica")
    )

    # Access informations and dates
    status = models.CharField(_("Status"), max_length=20, choices=UserConstants.USER_STATUSES, default=UserConstants.USER_STATUS_REGISTER_UNCOMPLETED)
    is_staff = models.BooleanField(_("Colaborador"), default=False)
    is_active = models.BooleanField(_("Ativo"), default=True)
    date_joined = models.DateTimeField(_("Data de entrada"), default=timezone.now)
    first_login_accomplished = models.BooleanField(_("Já entrou na plataforma pela primeira vez?"), default=False)

    # Consensus
    terms = models.BooleanField(_("Aceitou os termos e condições da plataforma?"), default=False)
    receive_emails = models.BooleanField(_("Aceitou receber comunicações via e-mail?"), default=False)

    # Others
    other_emails = models.TextField(_("Outros e-mails"), null=True, blank=True)

    objects = UserManager()

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def clean(self):
        if self.rg and User.objects.filter(Q(rg=self.rg) & Q(is_active=True) & ~Q(id=self.id)).exists():
            raise ValidationError(_(u"RG já cadastrado."))

    def get_profile(self):
        return Profile.objects.get(user=self) if Profile.objects.filter(user=self).exists() else None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._excluded_fields = ["pkid", "id", "created_at", "created_by", "updated_at", "updated_by", "deleted_at",
                                 "deleted_by",]
        self._original_state = self._get_current_state()

    def _get_current_state(self):
        return {key: value for key, value in self.__dict__.items() if key not in self._excluded_fields}

    def __str__(self):
        return self.get_profile().name if self.get_profile() else self.email


class Profile(BaseModel):
    class Meta:
        verbose_name = _(u"Perfil")
        verbose_name_plural = _(u"Perfis")
        ordering = ["-created_at"]

    user = models.OneToOneField("User", on_delete=models.DO_NOTHING, related_name="user")
    name = models.CharField(_(u"Nome"), max_length=255)
    phone = PhoneField(_(u"Telefone fixo"), blank=True, null=True, max_length=20)
    cellphone = CellphoneField(_(u"Telefone celular"), blank=True, null=True, max_length=20)
    born = models.DateField(_(u"Data de nascimento"), blank=True, null=True)
    avatar = models.FileField(_(u"Avatar"), null=True, blank=True, upload_to=path_and_rename)
    address = models.OneToOneField("commons.Address", on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_(u"Endereço"))

    def __str__(self):
        return f"{self._meta.verbose_name} #{self.name}"


class Client(BaseModel):
    class Meta:
        verbose_name = _(u"Cliente")
        verbose_name_plural = _(u"Clientes")
        ordering = ["-created_at"]

    client = models.ForeignKey("User", on_delete=models.DO_NOTHING, related_name="client")
    name = models.CharField(_(u"Nome"), max_length=255, null=True, blank=True)
    cpf_cnpj = CPFCNPJField(_("CPF/CNPJ"), max_length=14)

    def __str__(self):
        return self.name
