"""Efemerides da Lua e do Sol, e a geometria da sombra da Terra.

Um eclipse lunar nao precisa de elementos besselianos: a Lua entra na sombra da
Terra e toda a gente do lado da noite ve a mesma coisa ao mesmo tempo. O que
muda com o lugar e apenas se a Lua estava acima do horizonte, e para responder a
isso basta saber onde a Lua esta no ceu. E isso que este modulo da.

Os algoritmos sao os do Jean Meeus, "Astronomical Algorithms", 2a edicao:

  - capitulo 47, posicao da Lua, com as tabelas truncadas da ELP-2000/82. O
    proprio Meeus anuncia 10" de erro em longitude e 4" em latitude, uma ordem
    de grandeza melhor do que o preciso para dizer se a Lua estava acima do
    horizonte;
  - capitulo 25, posicao do Sol, na forma abreviada, que chega para a distancia
    ao Sol e para o seu semidiametro;
  - capitulo 22, nutacao, com os termos maiores;
  - capitulo 12, tempo sideral.

A geometria da sombra segue a pratica corrente: a umbra e a penumbra sao cones
cujo raio angular a distancia da Lua se escreve com as paralaxes e o
semidiametro do Sol, e a sombra e dilatada para dar conta da atmosfera da Terra,
que a torna maior do que a geometria pura previa. A regra de dilatacao nao e
unica, e a que se usa aqui foi escolhida por comparacao com as magnitudes
publicadas no catalogo, nao por adivinhacao: ver `REGRAS_DE_DILATACAO` e o teste
em massa em `tests/test_lua.py`.

Todas as funcoes aceitam escalares ou arrays do numpy.
"""

from __future__ import annotations

from typing import Any

import numpy as np

GRAU = np.pi / 180.0
RAIO_EQUATORIAL_KM = 6378.140

# Semidiametro do Sol a uma unidade astronomica, e paralaxe equatorial do Sol a
# mesma distancia, ambos em graus.
SEMIDIAMETRO_SOL_UA = 959.63 / 3600.0
PARALAXE_SOL_UA = 8.794 / 3600.0

# Razao entre o raio da Lua e o raio equatorial da Terra. Meeus usa 0.272481
# nos eclipses (capitulo 54); e o valor de que sai o semidiametro aparente da
# Lua a partir da sua paralaxe.
RAZAO_RAIO_LUA = 0.272481


# --------------------------------------------------------------------------
# Argumentos fundamentais
# --------------------------------------------------------------------------

def seculos_desde_j2000(jde: Any) -> Any:
    """Seculos julianos de TD desde 2000-01-01T12:00 TD."""
    return (np.asarray(jde, dtype=float) - 2451545.0) / 36525.0


def _argumentos_da_lua(t: Any) -> dict[str, Any]:
    """Os cinco argumentos do capitulo 47, em graus, mais A1, A2, A3 e E."""
    return {
        # Longitude media da Lua, incluindo a aberracao da luz.
        "L1": 218.3164477 + 481267.88123421 * t - 0.0015786 * t**2
        + t**3 / 538841.0 - t**4 / 65194000.0,
        # Elongacao media da Lua.
        "D": 297.8501921 + 445267.1114034 * t - 0.0018819 * t**2
        + t**3 / 545868.0 - t**4 / 113065000.0,
        # Anomalia media do Sol.
        "M": 357.5291092 + 35999.0502909 * t - 0.0001536 * t**2
        + t**3 / 24490000.0,
        # Anomalia media da Lua.
        "Ml": 134.9633964 + 477198.8675055 * t + 0.0087414 * t**2
        + t**3 / 69699.0 - t**4 / 14712000.0,
        # Argumento da latitude da Lua.
        "F": 93.2720950 + 483202.0175233 * t - 0.0036539 * t**2
        - t**3 / 3526000.0 + t**4 / 863310000.0,
        # Termos aditivos, devidos a Venus, a Jupiter e ao achatamento da Terra.
        "A1": 119.75 + 131.849 * t,
        "A2": 53.09 + 479264.290 * t,
        "A3": 313.45 + 481266.484 * t,
        # Correccao da excentricidade da orbita da Terra, que afecta os termos
        # com a anomalia do Sol.
        "E": 1.0 - 0.002516 * t - 0.0000074 * t**2,
    }


# Tabela 47.A: argumentos (D, M, M', F) e coeficientes de sin (longitude, em
# milionesimos de grau) e de cos (distancia, em milesimos de quilometro).
TERMOS_LONGITUDE_DISTANCIA = (
    (0, 0, 1, 0, 6288774, -20905355),
    (2, 0, -1, 0, 1274027, -3699111),
    (2, 0, 0, 0, 658314, -2955968),
    (0, 0, 2, 0, 213618, -569925),
    (0, 1, 0, 0, -185116, 48888),
    (0, 0, 0, 2, -114332, -3149),
    (2, 0, -2, 0, 58793, 246158),
    (2, -1, -1, 0, 57066, -152138),
    (2, 0, 1, 0, 53322, -170733),
    (2, -1, 0, 0, 45758, -204586),
    (0, 1, -1, 0, -40923, -129620),
    (1, 0, 0, 0, -34720, 108743),
    (0, 1, 1, 0, -30383, 104755),
    (2, 0, 0, -2, 15327, 10321),
    (0, 0, 1, 2, -12528, 0),
    (0, 0, 1, -2, 10980, 79661),
    (4, 0, -1, 0, 10675, -34782),
    (0, 0, 3, 0, 10034, -23210),
    (4, 0, -2, 0, 8548, -21636),
    (2, 1, -1, 0, -7888, 24208),
    (2, 1, 0, 0, -6766, 30824),
    (1, 0, -1, 0, -5163, -8379),
    (1, 1, 0, 0, 4987, -16675),
    (2, -1, 1, 0, 4036, -12831),
    (2, 0, 2, 0, 3994, -10445),
    (4, 0, 0, 0, 3861, -11650),
    (2, 0, -3, 0, 3665, 14403),
    (0, 1, -2, 0, -2689, -7003),
    (2, 0, -1, 2, -2602, 0),
    (2, -1, -2, 0, 2390, 10056),
    (1, 0, 1, 0, -2348, 6322),
    (2, -2, 0, 0, 2236, -9884),
    (0, 1, 2, 0, -2120, 5751),
    (0, 2, 0, 0, -2069, 0),
    (2, -2, -1, 0, 2048, -4950),
    (2, 0, 1, -2, -1773, 4130),
    (2, 0, 0, 2, -1595, 0),
    (4, -1, -1, 0, 1215, -3958),
    (0, 0, 2, 2, -1110, 0),
    (3, 0, -1, 0, -892, 3258),
    (2, 1, 1, 0, -810, 2616),
    (4, -1, -2, 0, 759, -1897),
    (0, 2, -1, 0, -713, -2117),
    (2, 2, -1, 0, -700, 2354),
    (2, 1, -2, 0, 691, 0),
    (2, -1, 0, -2, 596, 0),
    (4, 0, 1, 0, 549, -1423),
    (0, 0, 4, 0, 537, -1117),
    (4, -1, 0, 0, 520, -1571),
    (1, 0, -2, 0, -487, -1739),
    (2, 1, 0, -2, -399, 0),
    (0, 0, 2, -2, -381, -4421),
    (1, 1, 1, 0, 351, 0),
    (3, 0, -2, 0, -340, 0),
    (4, 0, -3, 0, 330, 0),
    (2, -1, 2, 0, 327, 0),
    (0, 2, 1, 0, -323, 1165),
    (1, 1, -1, 0, 299, 0),
    (2, 0, 3, 0, 294, 0),
    (2, 0, -1, -2, 0, 8752),
)

# Tabela 47.B: latitude, em milionesimos de grau.
TERMOS_LATITUDE = (
    (0, 0, 0, 1, 5128122),
    (0, 0, 1, 1, 280602),
    (0, 0, 1, -1, 277693),
    (2, 0, 0, -1, 173237),
    (2, 0, -1, 1, 55413),
    (2, 0, -1, -1, 46271),
    (2, 0, 0, 1, 32573),
    (0, 0, 2, 1, 17198),
    (2, 0, 1, -1, 9266),
    (0, 0, 2, -1, 8822),
    (2, -1, 0, -1, 8216),
    (2, 0, -2, -1, 4324),
    (2, 0, 1, 1, 4200),
    (2, 1, 0, -1, -3359),
    (2, -1, -1, 1, 2463),
    (2, -1, 0, 1, 2211),
    (2, -1, -1, -1, 2065),
    (0, 1, -1, -1, -1870),
    (4, 0, -1, -1, 1828),
    (0, 1, 0, 1, -1794),
    (0, 0, 0, 3, -1749),
    (0, 1, -1, 1, -1565),
    (1, 0, 0, 1, -1491),
    (0, 1, 1, 1, -1475),
    (0, 1, 1, -1, -1410),
    (0, 1, 0, -1, -1344),
    (1, 0, 0, -1, -1335),
    (0, 0, 3, 1, 1107),
    (4, 0, 0, -1, 1021),
    (4, 0, -1, 1, 833),
    (0, 0, 1, -3, 777),
    (4, 0, -2, 1, 671),
    (2, 0, 0, -3, 607),
    (2, 0, 2, -1, 596),
    (2, -1, 1, -1, 491),
    (2, 0, -2, 1, -451),
    (0, 0, 3, -1, 439),
    (2, 0, 2, 1, 422),
    (2, 0, -3, -1, 421),
    (2, 1, -1, 1, -366),
    (2, 1, 0, 1, -351),
    (4, 0, 0, 1, 331),
    (2, -1, 1, 1, 315),
    (2, -2, 0, -1, 302),
    (0, 0, 1, 3, -283),
    (2, 1, 1, -1, -229),
    (1, 1, 0, -1, 223),
    (1, 1, 0, 1, 223),
    (0, 1, -2, -1, -220),
    (2, 1, -1, -1, -220),
    (1, 0, 1, 1, -185),
    (2, -1, -2, -1, 181),
    (0, 1, 2, 1, -177),
    (4, 0, -2, -1, 176),
    (4, -1, -1, -1, 166),
    (1, 0, 1, -1, -164),
    (4, 0, 1, -1, 132),
    (1, 0, -1, -1, -119),
    (4, -1, 0, -1, 115),
    (2, -2, 0, 1, 107),
)


def posicao_da_lua(jde: Any) -> dict[str, Any]:
    """Longitude e latitude geocentricas da Lua, distancia e paralaxe.

    Devolve a posicao geometrica, sem nutacao nem aberracao: a longitude
    aparente sai de somar `nutacao(...)["longitude"]`, e e o que
    `posicoes_aparentes` faz.

    Longitude e latitude em graus, distancia em quilometros, paralaxe
    equatorial horizontal em graus.
    """
    t = seculos_desde_j2000(jde)
    a = _argumentos_da_lua(t)
    e = a["E"]

    soma_l = np.zeros_like(np.asarray(t, dtype=float))
    soma_r = np.zeros_like(soma_l)
    soma_b = np.zeros_like(soma_l)

    for cd, cm, cml, cf, coef_l, coef_r in TERMOS_LONGITUDE_DISTANCIA:
        arg = (cd * a["D"] + cm * a["M"] + cml * a["Ml"] + cf * a["F"]) * GRAU
        # Os termos com a anomalia do Sol dependem da excentricidade da orbita
        # da Terra, que muda ao longo dos seculos.
        fator = e ** abs(cm)
        soma_l = soma_l + coef_l * fator * np.sin(arg)
        soma_r = soma_r + coef_r * fator * np.cos(arg)

    for cd, cm, cml, cf, coef_b in TERMOS_LATITUDE:
        arg = (cd * a["D"] + cm * a["M"] + cml * a["Ml"] + cf * a["F"]) * GRAU
        soma_b = soma_b + coef_b * e ** abs(cm) * np.sin(arg)

    soma_l = (
        soma_l
        + 3958.0 * np.sin(a["A1"] * GRAU)
        + 1962.0 * np.sin((a["L1"] - a["F"]) * GRAU)
        + 318.0 * np.sin(a["A2"] * GRAU)
    )
    soma_b = (
        soma_b
        - 2235.0 * np.sin(a["L1"] * GRAU)
        + 382.0 * np.sin(a["A3"] * GRAU)
        + 175.0 * np.sin((a["A1"] - a["F"]) * GRAU)
        + 175.0 * np.sin((a["A1"] + a["F"]) * GRAU)
        + 127.0 * np.sin((a["L1"] - a["Ml"]) * GRAU)
        - 115.0 * np.sin((a["L1"] + a["Ml"]) * GRAU)
    )

    distancia_km = 385000.56 + soma_r / 1000.0
    return {
        "longitude": (a["L1"] + soma_l / 1e6) % 360.0,
        "latitude": soma_b / 1e6,
        "distancia_km": distancia_km,
        "paralaxe": np.degrees(np.arcsin(RAIO_EQUATORIAL_KM / distancia_km)),
    }


def posicao_do_sol(jde: Any) -> dict[str, Any]:
    """Longitude geometrica do Sol e distancia em unidades astronomicas.

    Forma abreviada do capitulo 25, com 0.01 graus de erro em longitude, que e
    irrelevante aqui: do Sol so se quer a distancia, de onde saem o seu
    semidiametro e a sua paralaxe, e essas ja o modelo abreviado da com
    exactidao de sobra.
    """
    t = seculos_desde_j2000(jde)
    l0 = 280.46646 + 36000.76983 * t + 0.0003032 * t**2
    m = 357.52911 + 35999.05029 * t - 0.0001537 * t**2
    excentricidade = 0.016708634 - 0.000042037 * t - 0.0000001267 * t**2
    centro = (
        (1.914602 - 0.004817 * t - 0.000014 * t**2) * np.sin(m * GRAU)
        + (0.019993 - 0.000101 * t) * np.sin(2 * m * GRAU)
        + 0.000289 * np.sin(3 * m * GRAU)
    )
    anomalia_verdadeira = m + centro
    raio_ua = (
        1.000001018
        * (1.0 - excentricidade**2)
        / (1.0 + excentricidade * np.cos(anomalia_verdadeira * GRAU))
    )
    return {"longitude": (l0 + centro) % 360.0, "raio_ua": raio_ua}


def nutacao(jde: Any) -> dict[str, Any]:
    """Nutacao em longitude e em obliquidade, em graus.

    Termos maiores do capitulo 22, bons ao meio segundo de arco. A nutacao nao
    muda nada nas magnitudes, mas entra na comparacao com o ponto do zenite
    publicado no catalogo, onde longitude aparente e tempo sideral aparente tem
    de ser coerentes um com o outro.
    """
    t = seculos_desde_j2000(jde)
    d = 297.85036 + 445267.111480 * t - 0.0019142 * t**2 + t**3 / 189474.0
    m = 357.52772 + 35999.050340 * t - 0.0001603 * t**2 - t**3 / 300000.0
    ml = 134.96298 + 477198.867398 * t + 0.0086972 * t**2 + t**3 / 56250.0
    f = 93.27191 + 483202.017538 * t - 0.0036825 * t**2 + t**3 / 327270.0
    omega = 125.04452 - 1934.136261 * t + 0.0020708 * t**2 + t**3 / 450000.0

    # Decimos de milissegundo de arco, como na tabela 22.A.
    delta_psi = (
        (-171996.0 - 174.2 * t) * np.sin(omega * GRAU)
        + (-13187.0 - 1.6 * t) * np.sin((-2 * d + 2 * f + 2 * omega) * GRAU)
        + (-2274.0 - 0.2 * t) * np.sin((2 * f + 2 * omega) * GRAU)
        + (2062.0 + 0.2 * t) * np.sin(2 * omega * GRAU)
        + (1426.0 - 3.4 * t) * np.sin(m * GRAU)
        + (712.0 + 0.1 * t) * np.sin(ml * GRAU)
        + (-517.0 + 1.2 * t) * np.sin((-2 * d + m + 2 * f + 2 * omega) * GRAU)
        + (-386.0 - 0.4 * t) * np.sin((2 * f + omega) * GRAU)
        - 301.0 * np.sin((ml + 2 * f + 2 * omega) * GRAU)
        + (217.0 - 0.5 * t) * np.sin((-2 * d - m + 2 * f + 2 * omega) * GRAU)
        - 158.0 * np.sin((-2 * d + ml) * GRAU)
        + (129.0 + 0.1 * t) * np.sin((-2 * d + 2 * f + omega) * GRAU)
        + 123.0 * np.sin((-ml + 2 * f + 2 * omega) * GRAU)
        + 63.0 * np.sin(2 * d * GRAU)
        + (63.0 + 0.1 * t) * np.sin((ml + omega) * GRAU)
        - 59.0 * np.sin((2 * d - ml + 2 * f + 2 * omega) * GRAU)
        + (-58.0 - 0.1 * t) * np.sin((-ml + omega) * GRAU)
        - 51.0 * np.sin((ml + 2 * f + omega) * GRAU)
        + 48.0 * np.sin((-2 * d + 2 * ml) * GRAU)
        + 46.0 * np.sin((-2 * ml + 2 * f + omega) * GRAU)
        - 38.0 * np.sin((2 * d + 2 * f + 2 * omega) * GRAU)
        - 31.0 * np.sin((2 * ml + 2 * f + 2 * omega) * GRAU)
        + 29.0 * np.sin(2 * ml * GRAU)
        + 29.0 * np.sin((-2 * d + ml + 2 * f + 2 * omega) * GRAU)
        + 26.0 * np.sin(2 * f * GRAU)
        - 22.0 * np.sin((-2 * d + 2 * f) * GRAU)
        + 21.0 * np.sin((-ml + 2 * f + omega) * GRAU)
    )
    delta_epsilon = (
        (92025.0 + 8.9 * t) * np.cos(omega * GRAU)
        + (5736.0 - 3.1 * t) * np.cos((-2 * d + 2 * f + 2 * omega) * GRAU)
        + (977.0 - 0.5 * t) * np.cos((2 * f + 2 * omega) * GRAU)
        + (-895.0 + 0.5 * t) * np.cos(2 * omega * GRAU)
        + (54.0 - 0.1 * t) * np.cos(m * GRAU)
        - 7.0 * np.cos(ml * GRAU)
        + (224.0 - 0.6 * t) * np.cos((-2 * d + m + 2 * f + 2 * omega) * GRAU)
        + 200.0 * np.cos((2 * f + omega) * GRAU)
        + (129.0 - 0.1 * t) * np.cos((ml + 2 * f + 2 * omega) * GRAU)
        + (-95.0 + 0.3 * t) * np.cos((-2 * d - m + 2 * f + 2 * omega) * GRAU)
        - 70.0 * np.cos((-2 * d + 2 * f + omega) * GRAU)
        - 53.0 * np.cos((-ml + 2 * f + 2 * omega) * GRAU)
        - 33.0 * np.cos((ml + omega) * GRAU)
        + 26.0 * np.cos((2 * d - ml + 2 * f + 2 * omega) * GRAU)
        + 32.0 * np.cos((-ml + omega) * GRAU)
        + 27.0 * np.cos((ml + 2 * f + omega) * GRAU)
        - 24.0 * np.cos((-2 * ml + 2 * f + omega) * GRAU)
        + 16.0 * np.cos((2 * d + 2 * f + 2 * omega) * GRAU)
        + 13.0 * np.cos((2 * ml + 2 * f + 2 * omega) * GRAU)
        - 12.0 * np.cos((-2 * d + ml + 2 * f + 2 * omega) * GRAU)
        - 10.0 * np.cos((-ml + 2 * f + omega) * GRAU)
    )
    return {
        "longitude": delta_psi / 36000000.0,
        "obliquidade": delta_epsilon / 36000000.0,
    }


def obliquidade_media(jde: Any) -> Any:
    """Obliquidade media da ecliptica, em graus (capitulo 22, formula de
    Laskar)."""
    u = seculos_desde_j2000(jde) / 100.0
    segundos = (
        21.448
        - u * (4680.93 + u * (1.55 - u * (1999.25 - u * (51.38 + u * (
            249.67 + u * (39.05 - u * (7.12 + u * (27.87 + u * (
                5.79 + u * 2.45)))))))))
    )
    return 23.0 + 26.0 / 60.0 + segundos / 3600.0


def equatoriais(longitude: Any, latitude: Any, obliquidade: Any) -> dict[str, Any]:
    """Da ecliptica para o equador. Angulos em graus, ascensao recta em
    [0, 360)."""
    lon = np.asarray(longitude, dtype=float) * GRAU
    lat = np.asarray(latitude, dtype=float) * GRAU
    eps = np.asarray(obliquidade, dtype=float) * GRAU
    ascensao = np.degrees(
        np.arctan2(np.sin(lon) * np.cos(eps) - np.tan(lat) * np.sin(eps), np.cos(lon))
    )
    declinacao = np.degrees(
        np.arcsin(np.sin(lat) * np.cos(eps) + np.cos(lat) * np.sin(eps) * np.sin(lon))
    )
    return {"ascensao_recta": ascensao % 360.0, "declinacao": declinacao}


def tempo_sideral_aparente(jd_ut: Any) -> Any:
    """Tempo sideral aparente em Greenwich, em graus (capitulo 12).

    Recebe dia juliano em UT, e nao em TD: o tempo sideral mede a rotacao da
    Terra, que e o que Delta T corrige.
    """
    jd = np.asarray(jd_ut, dtype=float)
    t = (jd - 2451545.0) / 36525.0
    medio = (
        280.46061837
        + 360.98564736629 * (jd - 2451545.0)
        + 0.000387933 * t**2
        - t**3 / 38710000.0
    )
    # A equacao dos equinocios, que leva o tempo sideral medio ao aparente.
    jde = jd  # a diferenca de Delta T nao chega a milesimos de segundo de arco
    n = nutacao(jde)
    obliquidade = obliquidade_media(jde) + n["obliquidade"]
    return (medio + n["longitude"] * np.cos(obliquidade * GRAU)) % 360.0


def posicoes_aparentes(jde: Any) -> dict[str, Any]:
    """Posicao aparente da Lua e do Sol num instante de TD.

    Devolve ascensao recta e declinacao da Lua, a sua paralaxe e distancia, e a
    distancia ao Sol, que e o que a geometria da sombra pede.
    """
    lua = posicao_da_lua(jde)
    sol = posicao_do_sol(jde)
    n = nutacao(jde)
    obliquidade = obliquidade_media(jde) + n["obliquidade"]
    # Aberracao da luz da Lua, ja incluida na longitude media do capitulo 47.
    coordenadas = equatoriais(
        lua["longitude"] + n["longitude"], lua["latitude"], obliquidade
    )
    return {
        **coordenadas,
        "longitude_lua": (lua["longitude"] + n["longitude"]) % 360.0,
        "latitude_lua": lua["latitude"],
        "distancia_km": lua["distancia_km"],
        "paralaxe": lua["paralaxe"],
        "raio_ua_sol": sol["raio_ua"],
        "obliquidade": obliquidade,
    }


def altura_e_azimute(
    ascensao_recta: Any, declinacao: Any, jd_ut: Any, lat_graus: Any, lon_graus: Any
) -> dict[str, Any]:
    """Altura e azimute de um astro, vistos de um lugar.

    Altura geocentrica, sem correccao de paralaxe nem de refraccao: quem quiser
    a altura aparente soma `paralaxe` (que baixa a Lua ate um grau junto ao
    horizonte) e a refraccao (que a levanta cerca de meio grau). Para decidir se
    a Lua estava ou nao acima do horizonte, e a altura topocentrica que conta, e
    e por isso que `acima_do_horizonte` existe a parte.

    Longitude positiva para leste, azimute contado do norte para leste.
    """
    hora = (tempo_sideral_aparente(jd_ut) + np.asarray(lon_graus, dtype=float)
            - np.asarray(ascensao_recta, dtype=float)) * GRAU
    lat = np.asarray(lat_graus, dtype=float) * GRAU
    dec = np.asarray(declinacao, dtype=float) * GRAU
    altura = np.degrees(
        np.arcsin(np.sin(lat) * np.sin(dec) + np.cos(lat) * np.cos(dec) * np.cos(hora))
    )
    azimute = np.degrees(
        np.arctan2(
            np.sin(hora),
            np.cos(hora) * np.sin(lat) - np.tan(dec) * np.cos(lat),
        )
    )
    return {
        "altura": altura,
        "azimute": (azimute + 180.0) % 360.0,
        "angulo_horario": (np.degrees(hora) + 180.0) % 360.0 - 180.0,
    }


def altura_topocentrica(altura_geocentrica: Any, paralaxe: Any) -> Any:
    """Corrige a altura da paralaxe diurna.

    A Lua esta perto, e um observador a superficie ve-a mais baixa do que o
    centro da Terra a veria: quase um grau junto ao horizonte, nada no zenite.
    Sem esta correccao, uma Lua a meio grau de altura geocentrica no momento do
    maximo passaria por visivel quando na verdade ainda estava por nascer.
    """
    altura = np.asarray(altura_geocentrica, dtype=float)
    return altura - np.asarray(paralaxe, dtype=float) * np.cos(altura * GRAU)


# --------------------------------------------------------------------------
# Geometria da sombra
# --------------------------------------------------------------------------

# A sombra da Terra e maior do que a geometria pura preve, porque a atmosfera
# absorve e desvia a luz que passaria rente ao limbo. Nao ha uma regra unica: a
# tradicional, de Chauvenet, aumenta o raio da sombra em 1/50; a de Danjon
# aumenta antes o raio da Terra em 1/85, o que nao e a mesma coisa, porque so a
# parte que vem da paralaxe cresce.
#
# A regra deste projeto nao foi escolhida por gosto: comparadas as magnitudes de
# todas as candidatas com as dos 2424 eclipses do catalogo, o raio da Terra
# aumentado em 1/100 reproduz as magnitudes publicadas com um erro quadratico
# medio de 0.00007 e um erro maximo de 0.00024, ou seja, dentro do
# arredondamento com que o proprio catalogo as publica. As outras erram entre
# 0.003 e 0.03, cem a quatrocentas vezes mais. O teste em massa fixa isto.
#
# Cada entrada e (fator sobre as paralaxes, fator sobre o raio da sombra).
REGRAS_DE_DILATACAO = {
    "1/100": (1.0 + 1.0 / 100.0, 1.0),
    "danjon-1/85": (1.0 + 1.0 / 85.0, 1.0),
    "chauvenet-1/50": (1.0, 1.02),
    "sem-dilatacao": (1.0, 1.0),
}

REGRA_ADOPTADA = "1/100"


def geometria_da_sombra(
    jde: Any, gamma: Any, regra: str = REGRA_ADOPTADA
) -> dict[str, Any]:
    """Raios angulares da umbra, da penumbra e da Lua, e as magnitudes.

    Tudo em graus, visto do centro da Terra, no instante `jde` (TD). `gamma` e a
    distancia minima do centro da Lua ao eixo da sombra, em raios equatoriais da
    Terra, tal como o catalogo a publica; aqui converte-se em angulo pela
    paralaxe da Lua.

    A magnitude e a fraccao do diametro da Lua coberta pela sombra no instante
    do maximo, e pode passar de 1 (a Lua cabe inteira na sombra) ou ser negativa
    (a sombra passa ao lado).
    """
    aparentes = posicoes_aparentes(jde)
    paralaxe_lua = aparentes["paralaxe"]
    raio_ua = aparentes["raio_ua_sol"]

    paralaxe_sol = PARALAXE_SOL_UA / raio_ua
    semidiametro_sol = SEMIDIAMETRO_SOL_UA / raio_ua
    raio_lua = RAZAO_RAIO_LUA * paralaxe_lua

    fator_paralaxe, fator_sombra = REGRAS_DE_DILATACAO[regra]
    paralaxes = fator_paralaxe * (paralaxe_lua + paralaxe_sol)
    raio_umbra = fator_sombra * (paralaxes - semidiametro_sol)
    raio_penumbra = fator_sombra * (paralaxes + semidiametro_sol)

    distancia = np.abs(np.asarray(gamma, dtype=float)) * paralaxe_lua
    return {
        "raio_umbra": raio_umbra,
        "raio_penumbra": raio_penumbra,
        "raio_lua": raio_lua,
        "distancia_minima": distancia,
        "paralaxe_lua": paralaxe_lua,
        "magnitude_umbral": (raio_umbra + raio_lua - distancia) / (2.0 * raio_lua),
        "magnitude_penumbral": (raio_penumbra + raio_lua - distancia)
        / (2.0 * raio_lua),
    }


def velocidade_relativa(jde: Any, intervalo_h: float = 2.0) -> Any:
    """Velocidade da Lua em relacao a sombra da Terra, em graus por hora.

    A sombra esta no ponto do ceu oposto ao Sol, e move-se com ele: a velocidade
    que interessa e a da Lua menos a do Sol. Mede-se por diferencas finitas em
    torno do instante dado, o que para uma travessia de poucas horas chega e
    sobra, porque a orbita da Lua nao muda de forma nesse intervalo.

    E esta velocidade que transforma as distancias da geometria em tempos, e
    portanto a que produz as duracoes das fases.
    """
    meio = intervalo_h / 48.0
    instante = np.asarray(jde, dtype=float)
    antes, depois = instante - meio, instante + meio

    def _posicao_relativa(momento: Any) -> tuple[Any, Any]:
        """Longitude e latitude da Lua em relacao ao centro da sombra."""
        lua_ = posicao_da_lua(momento)
        sol_ = posicao_do_sol(momento)
        centro_da_sombra = sol_["longitude"] + 180.0
        delta = (lua_["longitude"] - centro_da_sombra + 180.0) % 360.0 - 180.0
        return delta, lua_["latitude"]

    lon_antes, lat_antes = _posicao_relativa(antes)
    lon_depois, lat_depois = _posicao_relativa(depois)
    # A latitude e sempre pequena num eclipse, mas o cosseno custa nada.
    latitude_media = (lat_antes + lat_depois) / 2.0
    passo_lon = (lon_depois - lon_antes) * np.cos(latitude_media * GRAU)
    return np.hypot(passo_lon, lat_depois - lat_antes) / intervalo_h


def duracoes(jde: Any, gamma: Any, regra: str = REGRA_ADOPTADA) -> dict[str, Any]:
    """Duracoes das tres fases, em minutos, a partir da geometria.

    A Lua atravessa a sombra ao longo de uma corda: o tempo que demora e o
    comprimento da corda a dividir pela velocidade relativa. Devolve `nan` nas
    fases que nao chegam a existir, que e como o catalogo as publica.
    """
    g = geometria_da_sombra(jde, gamma, regra)
    velocidade = velocidade_relativa(jde)
    distancia = g["distancia_minima"]

    def _corda(raio: Any) -> Any:
        quadrado = np.asarray(raio, dtype=float) ** 2 - distancia**2
        return 2.0 * np.sqrt(np.where(quadrado > 0.0, quadrado, np.nan))

    return {
        "penumbral_min": _corda(g["raio_penumbra"] + g["raio_lua"]) / velocidade * 60.0,
        "parcial_min": _corda(g["raio_umbra"] + g["raio_lua"]) / velocidade * 60.0,
        "total_min": _corda(g["raio_umbra"] - g["raio_lua"]) / velocidade * 60.0,
    }
