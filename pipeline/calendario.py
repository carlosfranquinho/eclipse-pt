"""Datas e horas: calendario juliano ou gregoriano, e hora local em Portugal.

Duas armadilhas historicas que o projeto tem de tratar com cuidado.

Calendario. O canon da NASA usa o calendario juliano ate 1582 e o gregoriano a
partir dai. Portugal adoptou o gregoriano na data da bula, saltando de 4 para 15
de outubro de 1582, ou seja ao mesmo tempo que Roma e ao contrario de boa parte
da Europa. Cada eclipse guarda as duas datas e qual estava em vigor.

Hora. A hora legal so existe em Portugal desde 1912. Antes disso cada terra
regia-se pelo seu meio-dia, e a unica hora com significado num ponto e a hora
solar media do seu meridiano. Depois de 1912 usa-se a base de fusos horarios,
que ja trata da hora de verao historica e do periodo de 1992 a 1996 em que o
continente esteve na hora da Europa Central.

Traz tambem a conversao entre o tempo dos elementos besselianos e o calendario,
que e onde o canon exige mais cuidado: o dia juliano que publica esta arredondado
e o `t0` dos elementos pode cair no dia civil seguinte.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# Portugal passou de 4 de outubro (juliano) a 15 de outubro de 1582 (gregoriano).
JD_ADOPCAO_GREGORIANO_PT = 2299160.5

# A partir daqui ha hora legal em Portugal e a base de fusos e fiavel.
ANO_PRIMEIRA_HORA_LEGAL = 1912

FUSOS = {
    "continente": ZoneInfo("Europe/Lisbon"),
    "acores": ZoneInfo("Atlantic/Azores"),
    "madeira": ZoneInfo("Atlantic/Madeira"),
}

SISTEMA_HORA_LEGAL = "hora_legal"
SISTEMA_SOLAR_MEDIA = "hora_solar_media_local"


@dataclass(frozen=True)
class DataCivil:
    ano: int
    mes: int
    dia: int
    hora: int
    minuto: int
    segundo: float

    def iso_data(self) -> str:
        return f"{self.ano:04d}-{self.mes:02d}-{self.dia:02d}"

    def iso_hora(self) -> str:
        return f"{self.hora:02d}:{self.minuto:02d}:{int(self.segundo):02d}"


def jd_para_civil(jd: float, gregoriano: bool) -> DataCivil:
    """Converte um dia juliano na data civil do calendario pedido.

    Algoritmo do Meeus, Astronomical Algorithms, capitulo 7. O parametro escolhe
    explicitamente o calendario em vez de o inferir, porque a mesma data pode ter
    de ser apresentada nos dois.
    """
    jd = jd + 0.5
    z = math.floor(jd)
    f = jd - z

    if gregoriano:
        alfa = math.floor((z - 1867216.25) / 36524.25)
        a = z + 1 + alfa - math.floor(alfa / 4)
    else:
        a = z

    b = a + 1524
    c = math.floor((b - 122.1) / 365.25)
    d = math.floor(365.25 * c)
    e = math.floor((b - d) / 30.6001)

    dia_fraccionario = b - d - math.floor(30.6001 * e) + f
    dia = int(dia_fraccionario)
    mes = e - 1 if e < 14 else e - 13
    ano = c - 4716 if mes > 2 else c - 4715

    resto_horas = (dia_fraccionario - dia) * 24.0
    hora = int(resto_horas)
    resto_minutos = (resto_horas - hora) * 60.0
    minuto = int(resto_minutos)
    segundo = (resto_minutos - minuto) * 60.0

    return DataCivil(int(ano), int(mes), dia, hora, minuto, segundo)


def civil_para_jd(ano: int, mes: int, dia: float, gregoriano: bool) -> float:
    """Inverso de `jd_para_civil`, util nos testes e na ordenacao."""
    if mes <= 2:
        ano -= 1
        mes += 12
    if gregoriano:
        a = math.floor(ano / 100)
        b = 2 - a + math.floor(a / 4)
    else:
        b = 0
    return (
        math.floor(365.25 * (ano + 4716))
        + math.floor(30.6001 * (mes + 1))
        + dia
        + b
        - 1524.5
    )


def calendario_vigente(jd: float) -> str:
    """Qual dos calendarios estava em vigor em Portugal nesse dia juliano."""
    return "gregoriano" if jd >= JD_ADOPCAO_GREGORIANO_PT else "juliano"


def jd_maximo_td(eclipse: dict) -> float:
    """Dia juliano, em TD, do maximo global, sem o arredondamento do canon.

    O canon publica o dia juliano com tres casas decimais, o que deixa o
    instante indeterminado em quase um minuto, mas publica tambem a data civil e
    a hora do maximo ao segundo. Sao os dois ultimos que se usam aqui: um erro
    de quarenta segundos nao muda a magnitude em ponto nenhum, mas apareceria
    directamente nas horas mostradas em cada ficha.

    Antes de 1582-10-15 a data civil do canon esta no calendario juliano.
    """
    gregoriano = eclipse["jd"] >= JD_ADOPCAO_GREGORIANO_PT
    meia_noite = civil_para_jd(
        eclipse["ano"], eclipse["mes"], eclipse["dia"], gregoriano=gregoriano
    )
    return meia_noite + eclipse["eclipse_maior"]["instante_td_h"] / 24.0


def jd_t0_td(eclipse: dict) -> float:
    """Dia juliano, em TD, do instante `t = 0` dos elementos besselianos.

    E a ancora que liga o tempo dos polinomios ao calendario, e vai na ficha
    para o browser poder converter os seus proprios resultados em horas sem
    repetir esta aritmetica nem o cuidado que ela exige.

    O canon arredonda `t0` para a hora inteira mais proxima do maximo, e essa
    hora pode cair ja no dia seguinte: em 1500-05-27 o maximo e as 23h49 TD e
    `t0` e a meia-noite a seguir. Sem o envolvimento nas doze horas, `t0` sairia
    um dia inteiro ao lado, e as horas da ficha com ele.
    """
    instante = eclipse["eclipse_maior"]["instante_td_h"]
    desvio = (instante - eclipse["elementos"]["t0_td"] + 12.0) % 24.0 - 12.0
    return jd_maximo_td(eclipse) - desvio / 24.0


def hora_local(jd_ut: float, lon_graus: float, territorio: str) -> dict:
    """Hora local num ponto, no sistema que fazia sentido a data.

    Devolve a data e a hora ja convertidas, mais a etiqueta do sistema usado,
    para a interface poder dizer ao leitor o que esta a ver. Antes de 1912 nao
    havia hora legal e a hora devolvida e a solar media do meridiano do ponto.
    """
    civil_ut = jd_para_civil(jd_ut, gregoriano=True)

    if civil_ut.ano >= ANO_PRIMEIRA_HORA_LEGAL:
        instante = datetime(
            civil_ut.ano, civil_ut.mes, civil_ut.dia,
            civil_ut.hora, civil_ut.minuto, int(civil_ut.segundo),
            tzinfo=timezone.utc,
        )
        local = instante.astimezone(FUSOS[territorio])
        return {
            "data": local.strftime("%Y-%m-%d"),
            "hora": local.strftime("%H:%M:%S"),
            "sistema": SISTEMA_HORA_LEGAL,
            "designacao_fuso": local.tzname(),
            "desvio_utc_h": local.utcoffset().total_seconds() / 3600.0,
        }

    # Hora solar media do meridiano do ponto: quatro minutos por grau.
    jd_local = jd_ut + lon_graus / 360.0
    civil_local = jd_para_civil(jd_local, gregoriano=True)
    jd_juliano = jd_local
    civil_juliano = jd_para_civil(jd_juliano, gregoriano=False)
    juliano = calendario_vigente(jd_ut) == "juliano"

    return {
        "data": (civil_juliano if juliano else civil_local).iso_data(),
        "hora": civil_local.iso_hora(),
        "sistema": SISTEMA_SOLAR_MEDIA,
        "designacao_fuso": None,
        "desvio_utc_h": lon_graus / 15.0,
    }


def jd_maximo_td_lua(eclipse: dict) -> float:
    """Dia juliano, em TD, do maximo de um eclipse lunar.

    O catalogo lunar nao publica o dia juliano, so a data civil e a hora do
    maximo ao segundo, o que aqui ate simplifica: e a mesma aritmetica de
    `jd_maximo_td` sem o arredondamento de que aquela se defende. A data vem no
    calendario juliano ate 1582-10-04 e no gregoriano de 1582-10-15 em diante,
    convencao do proprio catalogo.
    """
    gregoriano = (eclipse["ano"], eclipse["mes"], eclipse["dia"]) >= (1582, 10, 15)
    meia_noite = civil_para_jd(
        eclipse["ano"], eclipse["mes"], eclipse["dia"], gregoriano=gregoriano
    )
    return meia_noite + eclipse["maximo"]["instante_td_h"] / 24.0
