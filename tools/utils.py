import base64
import datetime
import io
import logging
import mimetypes
import os
import random
import re
import tempfile
from typing import Union

import boto3
import pandas as pd
from django.apps import apps
from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned, ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger("django")


def get_local_datetime():
    """Retorna a data e hora atual ajustada para o timezone local.

    Utilizada para comparações e operações com datetime que precisam
    considerar o fuso horário configurado no Django.

    Returns:
        datetime: Data e hora atual no timezone local configurado.

    Example:
        >>> now = get_local_datetime()
        >>> print(now.tzinfo)  # Timezone configurado no Django

    """
    return timezone.localtime(timezone.now())


def get_local_datetime_iso():
    """Retorna a data e hora atual em formato ISO 8601 com timezone local.

    Especialmente útil para salvar em MongoDB como string legível
    que preserva informações de timezone.

    Returns:
        str: Data e hora atual em formato ISO 8601 com timezone.

    Example:
        >>> iso_time = get_local_datetime_iso()
        >>> print(iso_time)  # '2024-01-15T14:30:45.123456-03:00'

    """
    return timezone.localtime(timezone.now()).isoformat()


def rename_file():
    """Gera um nome de arquivo aleatório de 10 caracteres.

    Utiliza caracteres alfanuméricos (A-Z, a-z, 0-9) para criar
    um identificador único para renomeação de arquivos.

    Returns:
        str: String aleatória de 10 caracteres alfanuméricos.

    Example:
        >>> filename = rename_file()
        >>> print(len(filename))  # 10
        >>> print(filename)  # 'A3bX9kL2Qz'

    """
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890"
    randomstr = "".join((random.choice(chars)) for x in range(10))
    return randomstr


def path_and_rename(instance, filename):
    """Gera um caminho de upload e renomeia arquivo para evitar conflitos.

    Função utilizada como upload_to em campos FileField/ImageField do Django.
    Cria uma estrutura de pastas baseada no nome do modelo e renomeia
    o arquivo com um identificador único.

    Args:
        instance: Instância do modelo Django que está sendo salva.
        filename (str): Nome original do arquivo enviado.

    Returns:
        str: Caminho completo do arquivo no formato
            'files/modelo/nome_aleatorio.ext'.

    Example:
        >>> # Em um modelo Django:
        >>> file = models.FileField(upload_to=path_and_rename)
        >>> # Resultado: 'files/usuario/A3bX9kL2Qz.pdf'

    """
    # Obter o nome do modelo
    model_name = instance.__class__.__name__.lower()

    # Defir a pasta em que deseja salvar os arquivos
    upload_to = "{}/{}".format("files", model_name)

    # Gere um nome aleatório para o arquivo
    ext = filename.split(".")[-1]
    filename = "{}.{}".format(rename_file(), ext)

    # Retorne o caminho completo para o arquivo
    return os.path.join(upload_to, filename)


def send_email(
    subject: str,
    from_email: str,
    to_email: Union[list, str],
    data: dict,
    template: str,
):
    """Envia email HTML usando template com dados dinâmicos.

    Renderiza um template HTML com os dados fornecidos, cria versões
    HTML e texto plano do email, e envia usando o sistema de email do Django.
    O template é salvo temporariamente no sistema de arquivos.

    Args:
        subject (str): Assunto do email.
        from_email (str): Email do remetente.
        to_email (Union[list, str]): Email(s) do(s) destinatário(s).
            Pode ser string para um destinatário ou lista para múltiplos.
        data (dict): Dados para renderização do template.
        template (str): Conteúdo HTML do template como string.

    Returns:
        bool: True se o email foi enviado com sucesso, False caso contrário.

    Example:
        >>> template_html = "<h1>Olá {{nome}}!</h1><p>{{mensagem}}</p>"
        >>> dados = {"nome": "João", "mensagem": "Bem-vindo!"}
        >>> sucesso = send_email(
        ...     subject="Boas-vindas",
        ...     from_email="sistema@empresa.com",
        ...     to_email="joao@email.com",
        ...     data=dados,
        ...     template=template_html
        ... )
        >>> print(sucesso)  # True ou False

    Note:
        - O template é salvo temporariamente e removido após o uso
        - Logs são registrados para sucesso e erros
        - Requer EMAIL_TMP_DIR configurado no Django settings

    """
    if not isinstance(to_email, list):
        to_email = [to_email]

    try:
        with tempfile.NamedTemporaryFile(
            suffix=".html", dir=settings.EMAIL_TMP_DIR, delete=False
        ) as file:
            file.write(template.encode())
            file.flush()

            html_message = render_to_string(file.name, data)
            plain_message = strip_tags(html_message)

            msg = EmailMultiAlternatives(
                subject, plain_message, from_email, to_email
            )
            msg.attach_alternative(html_message, "text/html")
            msg.send()
            logger.info("The email has been sent...")
            return True

    except Exception as ex:
        logger.error(ex)
        return False

    finally:
        try:
            os.remove(file.name)
        except Exception as ex:
            logger.error(f"Error deleting temporary file: {ex}")


def random_code():
    """Gera um código aleatório de 6 caracteres alfanuméricos em maiúsculo.

    Seleciona 6 caracteres aleatórios (números e letras maiúsculas)
    e os organiza em formato "XXX-XXX".

    Returns:
        str: Código no formato "ABC123" (6 caracteres sem separador).

    Example:
        >>> codigo = random_code()
        >>> print(len(codigo))  # 6
        >>> print(codigo)  # "A3BX9K"

    Note:
        Utiliza random.sample() que garante caracteres únicos no resultado.

    """
    t = "".join(random.sample("0123456789QWERTYUIOPASDFGHJKLZXCVBNM", 6))
    return "%s%s" % (t[:3], t[3:6])


def convert_timedelta(duration):
    """Converte um objeto timedelta para horas totais.

    Calcula o número total de horas contidas em um período de tempo,
    considerando dias e segundos do timedelta.

    Args:
        duration (timedelta): Período de tempo a ser convertido.

    Returns:
        int: Número total de horas no período.

    Example:
        >>> from datetime import timedelta
        >>> periodo = timedelta(days=2, hours=3, minutes=30)
        >>> horas = convert_timedelta(periodo)
        >>> print(horas)  # 51 (2*24 + 3 horas, minutos ignorados)

    Note:
        Minutos e segundos são truncados, não arredondados.

    """
    days, seconds = duration.days, duration.seconds
    hours = days * 24 + seconds // 3600
    return hours


def str_to_bool(s):
    """Converte string para valor booleano.

    Converte representações em string dos valores booleanos
    para seus equivalentes bool.

    Args:
        s (str): String a ser convertida ("True" ou "False").

    Returns:
        bool: True se s == "True", False se s == "False".

    Raises:
        ValueError: Se a string não for "True" nem "False".

    Example:
        >>> resultado = str_to_bool("True")
        >>> print(resultado)  # True
        >>> resultado = str_to_bool("False")
        >>> print(resultado)  # False
        >>> str_to_bool("talvez")  # Raises ValueError

    """
    if s == "True":
        return True
    elif s == "False":
        return False
    else:
        raise ValueError


def get_user_data(request):
    """Obtém o perfil do usuário autenticado a partir do request.

    Busca o perfil associado ao usuário logado, tratando casos
    onde o perfil não existe ou há múltiplos perfis.

    Args:
        request: Objeto HttpRequest do Django contendo o usuário.

    Returns:
        Profile or None: Perfil do usuário se encontrado, None caso contrário.

    Example:
        >>> def minha_view(request):
        ...     perfil = get_user_data(request)
        ...     if perfil:
        ...         print(f"Usuário: {perfil.user.username}")
        ...     else:
        ...         print("Perfil não encontrado")

    Note:
        Retorna None em caso de:
        - Perfil não existe (DoesNotExist)
        - Múltiplos perfis encontrados (MultipleObjectsReturned)
        - Erro de tipo (TypeError)

    """
    Perfil = apps.get_model("users", "Profile")

    try:
        profile = Perfil.objects.get(user=request.user)
    except (Perfil.DoesNotExist, MultipleObjectsReturned, TypeError):
        profile = None

    return profile


DIVISOR = 11

CPF_WEIGHTS = ((10, 9, 8, 7, 6, 5, 4, 3, 2), (11, 10, 9, 8, 7, 6, 5, 4, 3, 2))
CNPJ_WEIGHTS = (
    (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2),
    (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2),
)


def calculate_first_digit(number):
    """Calcula o primeiro dígito verificador de CPF ou CNPJ.

    Aplica o algoritmo padrão brasileiro para calcular o primeiro
    dígito verificador usando os pesos específicos para CPF ou CNPJ.

    Args:
        number (str): CPF (9 dígitos) ou CNPJ (12 dígitos) sem os
            dígitos verificadores. Apenas números.

    Returns:
        str: Primeiro dígito verificador ("0" a "9").

    Example:
        >>> # CPF sem dígitos verificadores: 123.456.789
        >>> primeiro = calculate_first_digit("123456789")
        >>> print(primeiro)  # Resultado do cálculo

        >>> # CNPJ sem dígitos verificadores: 11.222.333/0001
        >>> primeiro = calculate_first_digit("112223330001")
        >>> print(primeiro)  # Resultado do cálculo

    Note:
        - CPF: usa pesos (10,9,8,7,6,5,4,3,2)
        - CNPJ: usa pesos (5,4,3,2,9,8,7,6,5,4,3,2)
        - Se resto da divisão < 2, retorna "0", senão retorna str(11-resto)

    """
    sum = 0
    if len(number) == 9:
        weights = CPF_WEIGHTS[0]
    else:
        weights = CNPJ_WEIGHTS[0]

    for i in range(len(number)):
        sum = sum + int(number[i]) * weights[i]
    rest_division = sum % DIVISOR
    if rest_division < 2:
        return "0"
    return str(11 - rest_division)


def calculate_second_digit(number):
    """Calcula o segundo dígito verificador de CPF ou CNPJ.

    Aplica o algoritmo padrão brasileiro para calcular o segundo
    dígito verificador. Deve ser chamada após calculate_first_digit.

    Args:
        number (str): CPF (10 dígitos) ou CNPJ (13 dígitos) incluindo
            o primeiro dígito verificador. Apenas números.

    Returns:
        str: Segundo dígito verificador ("0" a "9").

    Example:
        >>> # CPF com primeiro dígito: 123.456.789-0
        >>> segundo = calculate_second_digit("1234567890")
        >>> print(segundo)  # Resultado do cálculo

        >>> # CNPJ com primeiro dígito: 11.222.333/0001-7
        >>> segundo = calculate_second_digit("1122233300017")
        >>> print(segundo)  # Resultado do cálculo

    Note:
        - CPF: usa pesos (11,10,9,8,7,6,5,4,3,2)
        - CNPJ: usa pesos (6,5,4,3,2,9,8,7,6,5,4,3,2)
        - Se resto da divisão < 2, retorna "0", senão retorna str(11-resto)
        - Função deve ser chamada APÓS calculate_first_digit

    """
    sum = 0
    if len(number) == 10:
        weights = CPF_WEIGHTS[1]
    else:
        weights = CNPJ_WEIGHTS[1]

    for i in range(len(number)):
        sum = sum + int(number[i]) * weights[i]
    rest_division = sum % DIVISOR
    if rest_division < 2:
        return "0"
    return str(11 - rest_division)


def validate_cpf(cpf):
    """Valida um número de CPF brasileiro.

    Verifica se o CPF possui formato válido e dígitos verificadores corretos
    usando o algoritmo oficial da Receita Federal.

    Args:
        cpf (str): CPF com 11 dígitos numéricos (sem formatação).

    Returns:
        bool: True se o CPF é válido, False caso contrário.

    Example:
        >>> cpf_valido = validate_cpf("11144477735")
        >>> print(cpf_valido)  # True ou False

        >>> cpf_invalido = validate_cpf("11111111111")  # Todos iguais
        >>> print(cpf_invalido)  # False

        >>> cpf_curto = validate_cpf("123456789")  # Menos de 11 dígitos
        >>> print(cpf_curto)  # False

    Note:
        - CPF deve ter exatamente 11 dígitos
        - Rejeita CPFs com todos os dígitos iguais
        - Usa algoritmo oficial com pesos (10,9,8...2) e (11,10,9...2)

    """
    # Verificar se o CPF tem 11 dígitos
    if len(cpf) != 11:
        return False

    # Verificar se todos os dígitos são iguais (caso comum em CPFs inválidos)
    if len(set(cpf)) == 1:
        return False

    # Calcular o primeiro dígito verificador
    total = sum(int(cpf[i]) * (10 - i) for i in range(9))
    remainder = total % 11
    digit1 = 11 - remainder if remainder > 1 else 0

    # Verificar se o primeiro dígito verificador está correto
    if digit1 != int(cpf[9]):
        return False

    # Calcular o segundo dígito verificador
    total = sum(int(cpf[i]) * (11 - i) for i in range(10))
    remainder = total % 11
    digit2 = 11 - remainder if remainder > 1 else 0

    # Verificar se o segundo dígito verificador está correto
    if digit2 != int(cpf[10]):
        return False

    return True


def validate_cnpj(cnpj):
    """Valida um número de CNPJ brasileiro.

    Verifica se o CNPJ possui formato válido e dígitos verificadores corretos
    usando o algoritmo oficial da Receita Federal.

    Args:
        cnpj (str): CNPJ com 14 dígitos numéricos (sem formatação).

    Returns:
        bool: True se o CNPJ é válido, False caso contrário.

    Example:
        >>> cnpj_valido = validate_cnpj("11222333000181")
        >>> print(cnpj_valido)  # True ou False

        >>> cnpj_invalido = validate_cnpj("11111111111111")  # Todos iguais
        >>> print(cnpj_invalido)  # False

        >>> cnpj_curto = validate_cnpj("1122233300")  # Menos de 14 dígitos
        >>> print(cnpj_curto)  # False

    Note:
        - CNPJ deve ter exatamente 14 dígitos
        - Rejeita CNPJs com todos os dígitos iguais
        - Usa algoritmo oficial com pesos específicos para cada dígito

    """
    # Verificar se o CNPJ tem 14 dígitos
    if len(cnpj) != 14:
        return False

    # Verificar se todos os dígitos são iguais (caso comum em CNPJs inválidos)
    if len(set(cnpj)) == 1:
        return False

    # Calcular o primeiro dígito verificador
    weights = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    total = sum(int(cnpj[i]) * weights[i] for i in range(12))
    remainder = total % 11
    digit1 = 11 - remainder if remainder > 1 else 0

    # Verificar se o primeiro dígito verificador está correto
    if digit1 != int(cnpj[12]):
        return False

    # Calcular o segundo dígito verificador
    weights = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    total = sum(int(cnpj[i]) * weights[i] for i in range(13))
    remainder = total % 11
    digit2 = 11 - remainder if remainder > 1 else 0

    # Verificar se o segundo dígito verificador está correto
    if digit2 != int(cnpj[13]):
        return False

    return True


def validate_cpf_and_cnpj(cpf_cnpj):
    """Valida e limpa CPF ou CNPJ automaticamente.

    Remove caracteres não numéricos e valida o documento como CPF
    (11 dígitos) ou CNPJ (14 dígitos) usando os algoritmos oficiais.

    Args:
        cpf_cnpj (str): CPF ou CNPJ com ou sem formatação.

    Returns:
        str: Documento validado contendo apenas números.

    Raises:
        ValidationError: Se o documento é inválido ou tem formato incorreto.

    Example:
        >>> # CPF com formatação
        >>> cpf_limpo = validate_cpf_and_cnpj("111.444.777-35")
        >>> print(cpf_limpo)  # "11144477735"

        >>> # CNPJ com formatação
        >>> cnpj_limpo = validate_cpf_and_cnpj("11.222.333/0001-81")
        >>> print(cnpj_limpo)  # "11222333000181"

        >>> # Documento inválido
        >>> validate_cpf_and_cnpj("123.456.789-00")  # Raises ValidationError

    Note:
        - Remove automaticamente pontos, hífens e barras
        - Aceita apenas documentos com 11 (CPF) ou 14 (CNPJ) dígitos
        - Valida usando algoritmos oficiais da Receita Federal

    """
    # Remove non-numeric characters
    numbers = re.sub("[^0-9]", "", cpf_cnpj)

    # Check if it's a CPF (11 digits)
    if len(numbers) == 11:
        if validate_cpf(numbers):
            return numbers
        else:
            raise ValidationError("CPF inválido.")

    # Check if it's a CNPJ (14 digits)
    elif len(numbers) == 14:
        if validate_cnpj(numbers):
            return numbers
        else:
            raise ValidationError("CNPJ inválido.")

    # Otherwise, raise an exception
    else:
        raise ValidationError(
            (
                "Entrada inválida. Deve ser um CPF (11 dígitos) "
                "ou CNPJ (14 dígitos)."
            )
        )


def validate_cellphone(value):
    """Valida número de telefone celular brasileiro.

    Remove caracteres especiais e verifica se o número possui
    exatamente 11 dígitos (formato brasileiro com DDD + 9 dígitos).

    Args:
        value: Número de telefone (string ou número).

    Raises:
        ValidationError: Se o telefone não possui 11 dígitos.

    Example:
        >>> validate_cellphone("(11) 99999-9999")  # OK - 11 dígitos
        >>> validate_cellphone("11999999999")      # OK - 11 dígitos
        >>> validate_cellphone("1199999999")       # Raises ValidationError

    Note:
        - Remove automaticamente caracteres não numéricos
        - Formato esperado: DDD (2 dígitos) + número (9 dígitos)
        - Exemplo válido: 11999999999 (11 = DDD São Paulo)

    """
    # Remova caracteres especiais do número de telefone
    cleaned_value = re.sub(r"\D", "", str(value))

    # Verifique se o número de telefone possui 11 dígitos
    if not re.match(r"^\d{11}$", cleaned_value):
        raise ValidationError(_("Telefone celular inválido."), code="invalid")


def get_mytimezone_date(original_datetime):
    """Converte string datetime para objeto timezone-aware.

    Transforma uma string no formato ISO sem timezone em um
    objeto datetime com timezone configurado no Django.

    Args:
        original_datetime (str): Data/hora no formato "YYYY-MM-DDTHH:MM:SS".

    Returns:
        datetime: Objeto datetime com timezone do Django aplicado.

    Example:
        >>> data_str = "2024-01-15T14:30:45"
        >>> data_tz = get_mytimezone_date(data_str)
        >>> print(data_tz.tzinfo)  # Timezone configurado no Django

    Note:
        - Formato de entrada: "2024-01-15T14:30:45" (sem timezone)
        - Aplica o timezone configurado em settings.TIME_ZONE
        - Útil para converter dados de APIs externas

    """
    new_datetime = datetime.datetime.strptime(
        original_datetime, "%Y-%m-%dT%H:%M:%S"
    )
    tz = timezone.get_current_timezone()
    timezone_datetime = timezone.make_aware(new_datetime, tz)
    return timezone_datetime


def get_mime_type_from_extension(file_extension):
    """Determina o tipo MIME a partir da extensão do arquivo.

    Utiliza a biblioteca mimetypes do Python para identificar
    o Content-Type apropriado baseado na extensão fornecida.

    Args:
        file_extension (str): Extensão do arquivo (ex: "pdf", "jpg", "xlsx").

    Returns:
        str or None: Tipo MIME correspondente ou None se não identificado.

    Example:
        >>> tipo = get_mime_type_from_extension("pdf")
        >>> print(tipo)  # "application/pdf"

        >>> tipo = get_mime_type_from_extension("jpg")
        >>> print(tipo)  # "image/jpeg"

        >>> tipo = get_mime_type_from_extension("xyz")
        >>> print(tipo)  # None (extensão desconhecida)

    Note:
        - Não inclui o ponto na extensão
        - Baseado na tabela de tipos MIME do sistema

    """
    mime_type, _ = mimetypes.guess_type(f"dummy.{file_extension}")
    return mime_type


def retrieve_file_from_bytes(file_bytes, file_extension):
    """Cria objeto de arquivo Django a partir de bytes base64.

    Converte dados binários em base64 para um objeto InMemoryUploadedFile
    que pode ser usado em campos FileField/ImageField do Django.

    Args:
        file_bytes (str or bytes): Dados do arquivo em base64 ou bytes.
        file_extension (str): Extensão do arquivo (ex: "pdf", "jpg").

    Returns:
        InMemoryUploadedFile: Objeto de arquivo pronto para uso no Django.

    Example:
        >>> # Base64 de um pequeno PDF
        >>> base64_data = "JVBERi0xLjQKJdPr6eEKMSAwIG9iago..."
        >>> arquivo = retrieve_file_from_bytes(base64_data, "pdf")
        >>> print(arquivo.name)  # "A3bX9kL2Qz.pdf"
        >>> print(arquivo.content_type)  # "application/pdf"

        >>> # Usar em modelo Django
        >>> instance.documento = arquivo
        >>> instance.save()

    Note:
        - Gera nome aleatório para evitar conflitos
        - Determina Content-Type automaticamente
        - Decodifica base64 se necessário
        - Compatível com campos de arquivo do Django

    """
    # Gera um nome de arquivo aleatório com a extensão
    filename = f"{rename_file()}.{file_extension}"

    if isinstance(file_bytes, str):
        file_bytes = file_bytes.encode("utf-8")

    mime_type = get_mime_type_from_extension(file_extension)

    # Cria um objeto InMemoryUploadedFile com o nome do arquivo e os bytes
    file = InMemoryUploadedFile(
        io.BytesIO(
            bytearray(base64.b64decode(file_bytes))
        ),  # Bytes do arquivo
        None,  # Campo de arquivo do formulário
        filename,  # Nome do arquivo
        mime_type,  # Tipo de conteúdo do arquivo
        len(file_bytes),  # Tamanho do arquivo em bytes
        None,  # Codificação do arquivo
    )

    return file


def get_aws_pre_signed_url(object_key):
    """Gera URL temporária para acesso a objeto no AWS S3.

    Cria uma URL pré-assinada que permite acesso temporário
    a um arquivo armazenado no bucket S3 configurado.

    Args:
        object_key (str): Chave/caminho do objeto no bucket S3.

    Returns:
        str: URL pré-assinada válida por 60 segundos.

    Example:
        >>> url = get_aws_pre_signed_url("uploads/documento.pdf")
        >>> print(url)
        # "https://bucket.s3.amazonaws.com/media/uploads/documento.pdf?..."

        >>> # Usar em template ou API
        >>> response_data = {"download_url": url}

    Note:
        - URL expira em 60 segundos por segurança
        - Adiciona prefixo "media/" automaticamente
        - Requer credenciais AWS configuradas no Django settings
        - Objeto deve existir no bucket para URL funcionar

    """
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )

    url = s3_client.generate_presigned_url(
        ClientMethod="get_object",
        Params={
            "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
            "Key": f"media/{object_key}",
        },
        ExpiresIn=60,  # Tempo de expiração em segundos
    )
    return url


def extract_values_from_xlsx(file):
    """Extrai valores da primeira coluna de um arquivo Excel.

    Lê a primeira planilha de um arquivo XLSX e retorna todos
    os valores da coluna A como lista de strings.

    Args:
        file: Objeto de arquivo Excel (file-like object).

    Returns:
        list: Lista de strings com valores da coluna A.

    Example:
        >>> # Arquivo Excel com coluna A: ["João", "Maria", "Pedro"]
        >>> with open("dados.xlsx", "rb") as f:
        ...     valores = extract_values_from_xlsx(f)
        >>> print(valores)  # ["João", "Maria", "Pedro"]

        >>> # Usar com upload do Django
        >>> if request.FILES.get('planilha'):
        ...     valores = extract_values_from_xlsx(request.FILES['planilha'])

    Note:
        - Lê apenas a primeira planilha do arquivo
        - Não considera cabeçalhos (header=None)
        - Converte todos os valores para string
        - Útil para importação de listas de dados

    """
    # Lê a primeira planilha do Excel sem cabeçalho
    df = pd.read_excel(file, header=None, dtype=str)

    # Converte os valores da primeira coluna (coluna A) para string
    values = df.iloc[:, 0].astype(str).tolist()
    return values
