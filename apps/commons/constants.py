from django.utils.translation import gettext_lazy as _


class CommonConstants(object):
    ACRE = "AC"
    ALAGOAS = "AL"
    AMAPA = "AP"
    AMAZONAS = "AM"
    BAHIA = "BA"
    CEARA = "CE"
    DISTRITO_FEDERAL = "DF"
    ESPIRITO_SANTO = "ES"
    GOIAS = "GO"
    MARANHAO = "MA"
    MATO_GROSSO = "MT"
    MATO_GROSSO_DO_SUL = "MS"
    MINAS_GERAIS = "MG"
    PARA = "PA"
    PARAIBA = "PB"
    PARANA = "PR"
    PERNAMBUCO = "PE"
    PIAUI = "PI"
    RIO_DE_JANEIRO = "RJ"
    RIO_GRANDE_DO_NORTE = "RN"
    RIO_GRANDE_DO_SUL = "RS"
    RONDONIA = "RO"
    RORAIMA = "RR"
    SANTA_CATARINA = "SC"
    SAO_PAULO = "SP"
    SERGIPE = "SE"
    TOCANTINS = "TO"

    BRAZIL_STATES = [
        (ACRE, _("Acre")),
        (ALAGOAS, _("Alagoas")),
        (AMAPA, _("Amapá")),
        (AMAZONAS, _("Amazonas")),
        (BAHIA, _("Bahia")),
        (CEARA, _("Ceará")),
        (DISTRITO_FEDERAL, _("Distrito Federal")),
        (ESPIRITO_SANTO, _("Espírito Santo")),
        (GOIAS, _("Goiás")),
        (MARANHAO, _("Maranhão")),
        (MATO_GROSSO, _("Mato Grosso")),
        (MATO_GROSSO_DO_SUL, _("Mato Grosso do Sul")),
        (MINAS_GERAIS, _("Minas Gerais")),
        (PARA, _("Pará")),
        (PARAIBA, _("Paraíba")),
        (PARANA, _("Paraná")),
        (PERNAMBUCO, _("Pernambuco")),
        (PIAUI, _("Piauí")),
        (RIO_DE_JANEIRO, _("Rio de Janeiro")),
        (RIO_GRANDE_DO_NORTE, _("Rio Grande do Norte")),
        (RIO_GRANDE_DO_SUL, _("Rio Grande do Sul")),
        (RONDONIA, _("Rondônia")),
        (RORAIMA, _("Roraima")),
        (SANTA_CATARINA, _("Santa Catarina")),
        (SAO_PAULO, _("São Paulo")),
        (SERGIPE, _("Sergipe")),
        (TOCANTINS, _("Tocantins")),
    ]
