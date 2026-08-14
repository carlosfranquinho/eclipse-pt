"""Circunstancias de eclipses solares a partir de elementos besselianos.

Este e o nucleo do projeto. Toda a informacao mostrada no site sai daqui: a
magnitude num ponto, os quatro contactos, a altura do Sol, a linha central e os
limites da faixa. A mesma matematica esta portada para TypeScript em
`site/src/lib/besselian.ts`, e um ficheiro de casos de ouro garante que as duas
implementacoes nao divergem.

Referencias:
  Explanatory Supplement to the Astronomical Ephemeris (1961), cap. 9.
  Jean Meeus, Astronomical Algorithms (2a ed.), cap. 54, "Solar Eclipses".
  Fred Espenak e Jean Meeus, Five Millennium Canon of Solar Eclipses, NASA/TP-2006-214141.

Convencoes usadas em todo o modulo:
  - `t` e o tempo em horas de TDT (Tempo Dinamico) contadas a partir de `t0_td`.
  - Longitudes sao positivas para leste.
  - `x`, `y`, `l1`, `l2` vem em raios equatoriais terrestres.
  - `d` e `mu` vem em graus e sao convertidos internamente para radianos.
  - Angulos devolvidos ao chamador vao sempre em graus.

Nota sobre a Terra: o metodo classico achata a Terra numa esfera auxiliar,
dividindo a coordenada z por `ACHATAMENTO`. Todas as latitudes intermedias sao
latitudes nessa esfera, e so no fim se convertem para latitude geodetica.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

# Elipsoide terrestre, com os valores classicos usados no canon.
RAIO_EQUATORIAL_KM = 6378.140
ACHATAMENTO = 0.99664719          # b/a, ou seja sqrt(1 - e^2)
EXCENTRICIDADE_QUAD = 1.0 - ACHATAMENTO**2

# Conversao de DeltaT (segundos) para o deslocamento em longitude entre o
# meridiano de efemerides e o de Greenwich. 1.0027379 e a razao entre o dia
# sideral e o dia solar, e 240 os segundos de tempo por grau de rotacao.
GRAUS_POR_SEGUNDO_DELTA_T = 1.0027379 / 240.0

GRAU = np.pi / 180.0


@dataclass(frozen=True)
class Elementos:
    """Elementos besselianos de um eclipse, tal como o canon os publica."""

    t0_td: float
    x: tuple[float, ...]
    y: tuple[float, ...]
    d: tuple[float, ...]      # graus
    mu: tuple[float, ...]     # graus
    l1: tuple[float, ...]
    l2: tuple[float, ...]
    tan_f1: float
    tan_f2: float
    delta_t_s: float

    @classmethod
    def de_dict(cls, elementos: dict[str, Any], delta_t_s: float) -> "Elementos":
        return cls(
            t0_td=elementos["t0_td"],
            x=tuple(elementos["x"]),
            y=tuple(elementos["y"]),
            d=tuple(elementos["d"]),
            mu=tuple(elementos["mu"]),
            l1=tuple(elementos["l1"]),
            l2=tuple(elementos["l2"]),
            tan_f1=elementos["tan_f1"],
            tan_f2=elementos["tan_f2"],
            delta_t_s=delta_t_s,
        )


def t_desde_t0(e: Elementos, hora_td: Any) -> Any:
    """Converte uma hora TDT do dia do eclipse em `t`, horas desde `t0_td`.

    O `t0` tabelado e o instante do eclipse podem cair em dias civis diferentes,
    porque o canon arredonda `t0` para a hora inteira mais proxima do maximo. Sem
    envolvimento, um eclipse a meia-noite daria `t` proximo de 24 em vez de zero,
    e a sombra apareceria a dezenas de raios terrestres de distancia.
    """
    return (np.asarray(hora_td, dtype=float) - e.t0_td + 12.0) % 24.0 - 12.0


def _poli(coef: tuple[float, ...], t: Any) -> Any:
    """Avalia o polinomio `coef` em `t`, com os coeficientes por potencia crescente."""
    resultado = np.zeros_like(np.asarray(t, dtype=float))
    for potencia, c in enumerate(coef):
        resultado = resultado + c * np.power(t, potencia)
    return resultado


def _derivada_poli(coef: tuple[float, ...], t: Any) -> Any:
    """Avalia a derivada do polinomio `coef` em `t`, por hora."""
    resultado = np.zeros_like(np.asarray(t, dtype=float))
    for potencia, c in enumerate(coef):
        if potencia == 0:
            continue
        resultado = resultado + potencia * c * np.power(t, potencia - 1)
    return resultado


@dataclass
class EstadoSombra:
    """Posicao e geometria da sombra no plano fundamental, num instante."""

    t: Any
    x: Any
    y: Any
    dx: Any
    dy: Any
    d: Any        # radianos
    dd: Any       # radianos por hora
    mu: Any       # radianos
    dmu: Any      # radianos por hora
    l1: Any
    l2: Any


def estado_sombra(e: Elementos, t: Any) -> EstadoSombra:
    """Avalia os polinomios besselianos no instante `t` (horas TDT desde t0)."""
    return EstadoSombra(
        t=t,
        x=_poli(e.x, t),
        y=_poli(e.y, t),
        dx=_derivada_poli(e.x, t),
        dy=_derivada_poli(e.y, t),
        d=_poli(e.d, t) * GRAU,
        dd=_derivada_poli(e.d, t) * GRAU,
        mu=_poli(e.mu, t) * GRAU,
        dmu=_derivada_poli(e.mu, t) * GRAU,
        l1=_poli(e.l1, t),
        l2=_poli(e.l2, t),
    )


def geodetica_para_geocentrica(lat_graus: Any, altura_m: Any = 0.0) -> tuple[Any, Any]:
    """Converte latitude geodetica em `rho*sin(phi')` e `rho*cos(phi')`.

    Estas sao as coordenadas do observador em raios equatoriais terrestres, e sao
    a primeira coisa que qualquer calculo de eclipse precisa. Meeus, formula 11.1.
    """
    lat = np.asarray(lat_graus, dtype=float) * GRAU
    altura = np.asarray(altura_m, dtype=float)
    u = np.arctan(ACHATAMENTO * np.tan(lat))
    rho_sin = ACHATAMENTO * np.sin(u) + (altura / (RAIO_EQUATORIAL_KM * 1000.0)) * np.sin(lat)
    rho_cos = np.cos(u) + (altura / (RAIO_EQUATORIAL_KM * 1000.0)) * np.cos(lat)
    return rho_sin, rho_cos


def _angulo_horario(s: EstadoSombra, e: Elementos, lon_graus: Any) -> Any:
    """Angulo horario local do eixo da sombra, em radianos.

    `mu` esta referido ao meridiano de efemerides, que roda com o TDT. A correcao
    de DeltaT traz o resultado para o meridiano de Greenwich, ou seja para o
    Tempo Universal, que e o que interessa ao observador.
    """
    correccao = GRAUS_POR_SEGUNDO_DELTA_T * e.delta_t_s
    return s.mu + (np.asarray(lon_graus, dtype=float) - correccao) * GRAU


def _observador_no_plano(
    s: EstadoSombra, e: Elementos, lat_graus: Any, lon_graus: Any, altura_m: Any
) -> tuple[Any, Any, Any, Any]:
    """Coordenadas do observador no plano fundamental: xi, eta, zeta e H."""
    rho_sin, rho_cos = geodetica_para_geocentrica(lat_graus, altura_m)
    h = _angulo_horario(s, e, lon_graus)
    xi = rho_cos * np.sin(h)
    eta = rho_sin * np.cos(s.d) - rho_cos * np.cos(h) * np.sin(s.d)
    zeta = rho_sin * np.sin(s.d) + rho_cos * np.cos(h) * np.cos(s.d)
    return xi, eta, zeta, h


def _raios_cones(s: EstadoSombra, e: Elementos, zeta: Any) -> tuple[Any, Any]:
    """Raios da penumbra e da umbra no plano do observador.

    Os `l1` e `l2` tabelados valem no plano fundamental, que passa pelo centro da
    Terra. O observador esta a uma distancia `zeta` desse plano, mais perto da
    Lua, e o cone e mais estreito ai.
    """
    return s.l1 - zeta * e.tan_f1, s.l2 - zeta * e.tan_f2


def _obscuracao(raio_sol: Any, raio_lua: Any, separacao: Any) -> Any:
    """Fracao da area do disco solar coberta, para dois discos que se cruzam."""
    rs = np.asarray(raio_sol, dtype=float)
    rm = np.asarray(raio_lua, dtype=float)
    sep = np.asarray(separacao, dtype=float)

    resultado = np.zeros_like(sep)

    # Sem sobreposicao.
    fora = sep >= rs + rm
    # A Lua cobre o Sol por completo (total).
    total = sep <= rm - rs
    # O disco lunar esta todo dentro do solar (anular).
    anular = sep <= rs - rm

    with np.errstate(invalid="ignore", divide="ignore"):
        cos_a = (sep**2 + rs**2 - rm**2) / (2.0 * sep * rs)
        cos_b = (sep**2 + rm**2 - rs**2) / (2.0 * sep * rm)
        alfa = np.arccos(np.clip(cos_a, -1.0, 1.0))
        beta = np.arccos(np.clip(cos_b, -1.0, 1.0))
        area = (
            rs**2 * (alfa - np.sin(2.0 * alfa) / 2.0)
            + rm**2 * (beta - np.sin(2.0 * beta) / 2.0)
        )
        parcial = area / (np.pi * rs**2)

    resultado = np.where(np.isfinite(parcial), parcial, 0.0)
    resultado = np.where(anular, (rm / rs) ** 2, resultado)
    resultado = np.where(total, 1.0, resultado)
    resultado = np.where(fora, 0.0, resultado)
    return np.clip(resultado, 0.0, 1.0)


def magnitude_em(
    e: Elementos, t: Any, lat_graus: Any, lon_graus: Any, altura_m: Any = 0.0
) -> dict[str, Any]:
    """Magnitude e grandezas associadas num ponto e instante.

    Devolve a magnitude (fracao do diametro solar coberto), a obscuracao (fracao
    da area), a altura do Sol e o tipo de eclipse nesse ponto. Aceita escalares
    ou arrays, o que permite varrer uma grelha de uma so vez.
    """
    s = estado_sombra(e, t)
    xi, eta, zeta, h = _observador_no_plano(s, e, lat_graus, lon_graus, altura_m)
    l1_obs, l2_obs = _raios_cones(s, e, zeta)

    u = s.x - xi
    v = s.y - eta
    m = np.hypot(u, v)

    # Raios aparentes do Sol e da Lua nas mesmas unidades que `m`. Para um
    # eclipse total l2_obs e negativo, e o raio lunar sai maior que o solar.
    raio_sol = (l1_obs + l2_obs) / 2.0
    raio_lua = (l1_obs - l2_obs) / 2.0

    with np.errstate(invalid="ignore", divide="ignore"):
        magnitude = (l1_obs - m) / (l1_obs + l2_obs)

    # Altura do Sol. `zeta` e a distancia do observador ao plano fundamental,
    # medida ao longo do eixo da sombra, portanto o seno da altura geocentrica.
    lat = np.asarray(lat_graus, dtype=float) * GRAU
    alt = np.arcsin(
        np.clip(np.sin(lat) * np.sin(s.d) + np.cos(lat) * np.cos(s.d) * np.cos(h), -1.0, 1.0)
    )
    az = np.arctan2(
        -np.sin(h), np.cos(lat) * np.tan(s.d) - np.sin(lat) * np.cos(h)
    )

    sol_visivel = alt > 0.0
    ha_eclipse = (m < l1_obs) & sol_visivel
    central = (m < np.abs(l2_obs)) & sol_visivel
    total = central & (l2_obs < 0.0)

    # A magnitude devolvida e puramente geometrica: nao se anula quando o Sol
    # esta abaixo do horizonte. Quem quiser o que um observador realmente veria
    # deve usar `magnitude_visivel`, que aplica a mascara. Manter as duas coisas
    # separadas e o que permite validar a geometria contra o canon, que publica
    # circunstancias em pontos com o Sol no horizonte.
    magnitude = np.where(m < l1_obs, np.maximum(magnitude, 0.0), 0.0)
    obscuracao = np.where(m < l1_obs, _obscuracao(raio_sol, raio_lua, m), 0.0)

    return {
        "magnitude": magnitude,
        "obscuracao": obscuracao,
        "alt_sol": alt / GRAU,
        "az_sol": (az / GRAU) % 360.0,
        "sol_visivel": sol_visivel,
        "ha_eclipse": ha_eclipse,
        "central": central,
        "total": total,
        "separacao": m,
        "l1_obs": l1_obs,
        "l2_obs": l2_obs,
        "zeta": zeta,
    }


# ---------------------------------------------------------------------------
# Circunstancias locais: maximo e os quatro contactos
# ---------------------------------------------------------------------------


def _u_v_e_derivadas(
    e: Elementos, t: Any, lat_graus: Any, lon_graus: Any, altura_m: Any
) -> tuple[Any, ...]:
    """Posicao relativa do observador ao eixo da sombra, e a sua taxa de variacao."""
    s = estado_sombra(e, t)
    rho_sin, rho_cos = geodetica_para_geocentrica(lat_graus, altura_m)
    h = _angulo_horario(s, e, lon_graus)

    xi = rho_cos * np.sin(h)
    eta = rho_sin * np.cos(s.d) - rho_cos * np.cos(h) * np.sin(s.d)
    zeta = rho_sin * np.sin(s.d) + rho_cos * np.cos(h) * np.cos(s.d)

    # A derivada de xi so depende da rotacao da Terra; a de eta tambem do
    # movimento em declinacao do eixo da sombra.
    d_xi = s.dmu * rho_cos * np.cos(h)
    d_eta = s.dmu * xi * np.sin(s.d) - zeta * s.dd

    u = s.x - xi
    v = s.y - eta
    du = s.dx - d_xi
    dv = s.dy - d_eta
    return u, v, du, dv, zeta, s


def _instante_maximo(
    e: Elementos, lat_graus: float, lon_graus: float, altura_m: float, t_inicial: float
) -> float:
    """Itera ate ao instante de maximo eclipse no ponto dado."""
    t = t_inicial
    for _ in range(8):
        u, v, du, dv, _, _ = _u_v_e_derivadas(e, t, lat_graus, lon_graus, altura_m)
        n2 = du * du + dv * dv
        if n2 == 0:
            break
        tau = -(u * du + v * dv) / n2
        t = t + float(tau)
        if abs(float(tau)) < 1e-9:
            break
    return t


def _contacto(
    e: Elementos,
    lat_graus: float,
    lon_graus: float,
    altura_m: float,
    t_maximo: float,
    interior: bool,
    antes: bool,
) -> float | None:
    """Instante de um contacto, ou None se esse contacto nao ocorre.

    `interior` escolhe o cone da umbra (segundo e terceiro contactos) em vez do
    da penumbra (primeiro e quarto). `antes` escolhe o contacto anterior ao
    maximo.
    """
    t = t_maximo
    for _ in range(12):
        u, v, du, dv, zeta, s = _u_v_e_derivadas(e, t, lat_graus, lon_graus, altura_m)
        l1_obs, l2_obs = _raios_cones(s, e, zeta)
        raio = abs(float(l2_obs)) if interior else float(l1_obs)

        n = float(np.hypot(du, dv))
        if n == 0:
            return None
        # Distancia perpendicular entre o observador e a trajectoria do eixo.
        desvio = float(u * dv - v * du) / n
        sob_radical = raio * raio - desvio * desvio
        if sob_radical < 0:
            return None
        deslocamento = np.sqrt(sob_radical) / n
        tau = -(float(u) * float(du) + float(v) * float(dv)) / (n * n)
        tau = tau - deslocamento if antes else tau + deslocamento
        t_novo = t + tau
        if abs(t_novo - t) < 1e-9:
            t = t_novo
            break
        t = t_novo
    return t


def circunstancias_locais(
    e: Elementos,
    lat_graus: float,
    lon_graus: float,
    altura_m: float = 0.0,
    t_inicial: float = 0.0,
) -> dict[str, Any]:
    """Circunstancias completas do eclipse num ponto: maximo e quatro contactos.

    Os instantes vao em horas de TDT contadas desde `t0_td`. Converter para UT
    subtraindo `delta_t_s / 3600`.
    """
    t_max = _instante_maximo(e, lat_graus, lon_graus, altura_m, t_inicial)
    no_maximo = magnitude_em(e, t_max, lat_graus, lon_graus, altura_m)

    if not bool(no_maximo["ha_eclipse"]):
        return {
            "visivel": False,
            "magnitude": 0.0,
            "obscuracao": 0.0,
            "tipo": "nenhum",
            "t_maximo_td": t_max,
            "contactos_td": {"c1": None, "c2": None, "c3": None, "c4": None},
            "alt_sol": float(no_maximo["alt_sol"]),
            "az_sol": float(no_maximo["az_sol"]),
        }

    central = bool(no_maximo["central"])
    if central:
        tipo = "total" if bool(no_maximo["total"]) else "anular"
    else:
        tipo = "parcial"

    contactos = {
        "c1": _contacto(e, lat_graus, lon_graus, altura_m, t_max, False, True),
        "c2": _contacto(e, lat_graus, lon_graus, altura_m, t_max, True, True) if central else None,
        "c3": _contacto(e, lat_graus, lon_graus, altura_m, t_max, True, False) if central else None,
        "c4": _contacto(e, lat_graus, lon_graus, altura_m, t_max, False, False),
    }

    duracao_central_s = None
    if contactos["c2"] is not None and contactos["c3"] is not None:
        duracao_central_s = (contactos["c3"] - contactos["c2"]) * 3600.0

    return {
        "visivel": True,
        "magnitude": float(no_maximo["magnitude"]),
        "obscuracao": float(no_maximo["obscuracao"]),
        "razao_diametros": float(razao_diametros(no_maximo)),
        "tipo": tipo,
        "t_maximo_td": t_max,
        "contactos_td": contactos,
        "duracao_central_s": duracao_central_s,
        "alt_sol": float(no_maximo["alt_sol"]),
        "az_sol": float(no_maximo["az_sol"]),
    }


def razao_diametros(circunstancias: dict[str, Any]) -> Any:
    """Razao entre os diametros aparentes da Lua e do Sol.

    E esta a grandeza que o canon da NASA publica como "magnitude" para os
    eclipses centrais, ao passo que para os parciais publica a fracao do
    diametro solar coberta. Sao definicoes diferentes e nao se devem misturar:
    no site, a fracao coberta e o que interessa ao observador num ponto, e a
    razao de diametros e a caracteristica global do eclipse.
    """
    l1 = circunstancias["l1_obs"]
    l2 = circunstancias["l2_obs"]
    return (l1 - l2) / (l1 + l2)


# ---------------------------------------------------------------------------
# Geometria da faixa central
# ---------------------------------------------------------------------------


def _eixo_para_superficie(
    s: EstadoSombra, e: Elementos, x: Any, y: Any
) -> dict[str, Any]:
    """Onde e que a recta paralela ao eixo da sombra que passa por (x, y) atinge a Terra.

    Usa a esfera auxiliar: achata-se a Terra numa esfera dividindo z pelo
    achatamento, resolve-se a interseccao com a esfera, e converte-se a latitude
    de volta para geodetica no fim. Com (x, y) igual a posicao do eixo obtem-se a
    linha central; com (x, y) num circulo em torno do eixo obtem-se o contorno da
    sombra.

    `existe=False` quando a recta passa ao lado da Terra.
    """
    rho1 = np.sqrt(1.0 - EXCENTRICIDADE_QUAD * np.cos(s.d) ** 2)
    sin_d1 = np.sin(s.d) / rho1
    cos_d1 = ACHATAMENTO * np.cos(s.d) / rho1

    eta1 = np.asarray(y, dtype=float) / rho1
    sob_radical = 1.0 - np.asarray(x, dtype=float) ** 2 - eta1**2
    existe = sob_radical > 0.0

    with np.errstate(invalid="ignore"):
        zeta1 = np.sqrt(np.where(existe, sob_radical, 0.0))

        sin_lat_esfera = eta1 * cos_d1 + zeta1 * sin_d1
        cos_lat_cos_h = zeta1 * cos_d1 - eta1 * sin_d1
        h = np.arctan2(np.asarray(x, dtype=float), cos_lat_cos_h)
        lat_esfera = np.arcsin(np.clip(sin_lat_esfera, -1.0, 1.0))

        lat = np.arctan(np.tan(lat_esfera) / ACHATAMENTO)

        correccao = GRAUS_POR_SEGUNDO_DELTA_T * e.delta_t_s
        lon = (h / GRAU) - (s.mu / GRAU) + correccao
        lon = (lon + 180.0) % 360.0 - 180.0

    return {
        "existe": existe,
        "lat": np.where(existe, lat / GRAU, np.nan),
        "lon": np.where(existe, lon, np.nan),
        "zeta1": zeta1,
    }


def linha_central(e: Elementos, t: Any) -> dict[str, Any]:
    """Ponto onde o eixo da sombra encontra a superficie da Terra.

    `existe=False` quando o eixo passa ao lado da Terra, ou seja quando o
    eclipse nao e central nesse instante.
    """
    s = estado_sombra(e, t)
    return _eixo_para_superficie(s, e, s.x, s.y)


def contorno_sombra(e: Elementos, t: float, n_pontos: int = 180) -> dict[str, Any]:
    """Contorno da umbra sobre a superficie da Terra, num instante.

    A seccao da umbra e um circulo de raio `l2` perpendicular ao eixo, mas o raio
    a usar depende da distancia do ponto ao plano fundamental, que so se conhece
    depois de resolver a interseccao. Por isso itera-se: parte-se de `l2` no
    plano fundamental e corrige-se com o `zeta` de cada ponto.

    Devolve os pontos do contorno, com `existe` a marcar os que caem na Terra. Um
    contorno parcialmente fora significa que a sombra esta a entrar ou a sair
    pelo terminador.
    """
    s = estado_sombra(e, t)
    theta = np.linspace(0.0, 2.0 * np.pi, n_pontos, endpoint=False)

    raio = np.full(n_pontos, abs(float(s.l2)))
    resultado = None
    for _ in range(4):
        px = float(s.x) + raio * np.cos(theta)
        py = float(s.y) + raio * np.sin(theta)
        resultado = _eixo_para_superficie(s, e, px, py)
        raio = np.abs(float(s.l2) - resultado["zeta1"] * e.tan_f2)

    return resultado


def _para_versor(lat_graus: Any, lon_graus: Any) -> Any:
    """Converte latitude e longitude em versores cartesianos.

    Trabalhar em vectores evita os dois modos de falha da aritmetica directa em
    latitude e longitude: a descontinuidade no meridiano dos 180 graus e o
    esmagamento dos meridianos junto aos polos.
    """
    lat = np.asarray(lat_graus, dtype=float) * GRAU
    lon = np.asarray(lon_graus, dtype=float) * GRAU
    return np.stack(
        [np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)], axis=-1
    )


def largura_faixa_km(e: Elementos, t: float) -> float:
    """Largura da faixa central na superficie, em quilometros.

    Mede-se a extensao angular do contorno da umbra na direccao perpendicular ao
    movimento da linha central, que e como a largura da faixa e convencionalmente
    definida. Uma formula fechada a partir do raio do cone daria a elongacao
    maxima da elipse da sombra, que e outra coisa e sobrestima a faixa sempre que
    o Sol nao esta perto do zenite.

    Devolve NaN quando a sombra roca o terminador, porque ai o contorno sai
    parcialmente da Terra e a nocao de largura deixa de ter significado pratico.
    """
    centro = linha_central(e, t)
    if not bool(centro["existe"]):
        return float("nan")

    passo = 1.0 / 60.0
    antes = linha_central(e, t - passo)
    depois = linha_central(e, t + passo)
    if not (bool(antes["existe"]) and bool(depois["existe"])):
        return float("nan")

    contorno = contorno_sombra(e, t, n_pontos=360)
    if not np.all(contorno["existe"]):
        return float("nan")

    centro_v = _para_versor(centro["lat"], centro["lon"])
    movimento = _para_versor(depois["lat"], depois["lon"]) - _para_versor(
        antes["lat"], antes["lon"]
    )
    # Componente do movimento tangente a superficie no ponto central.
    movimento = movimento - centro_v * np.dot(movimento, centro_v)
    norma = np.linalg.norm(movimento)
    if norma == 0.0:
        return float("nan")
    movimento = movimento / norma

    # Versor perpendicular ao movimento e tangente a superficie.
    perpendicular = np.cross(centro_v, movimento)

    pontos = _para_versor(contorno["lat"], contorno["lon"])
    projeccao = pontos @ perpendicular
    return float(np.ptp(np.arcsin(projeccao)) * RAIO_EQUATORIAL_KM)


# ---------------------------------------------------------------------------
# Varrimento espacial: o que se ve em cada ponto do territorio
# ---------------------------------------------------------------------------


def magnitude_visivel(
    e: Elementos, t: Any, lat_graus: Any, lon_graus: Any, altura_m: Any = 0.0
) -> Any:
    """Magnitude que um observador realmente veria, zero com o Sol abaixo do horizonte.

    E a diferenca entre a geometria e a experiencia: um ponto pode estar dentro do
    cone da penumbra e nao ver nada porque o Sol ainda nao nasceu. Relevante nos
    eclipses ao nascer ou ao por do Sol.
    """
    r = magnitude_em(e, t, lat_graus, lon_graus, altura_m)
    return np.where(r["sol_visivel"], r["magnitude"], 0.0)


def magnitude_maxima_na_grelha(
    e: Elementos,
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
    passo_graus: float = 0.02,
    passo_minutos: float = 5.0,
    janela_horas: float = 3.0,
) -> dict[str, Any]:
    """Maior magnitude atingida em cada ponto de uma grelha, ao longo do eclipse.

    E a base das isomagnitudes. Faz-se em duas passagens: um varrimento grosseiro
    no tempo para encontrar a vizinhanca do maximo em cada ponto, e depois um
    refinamento de Newton que converge para o instante exacto.

    O refinamento nao e um luxo. Num eclipse total a magnitude tem um pico
    estreito, e um varrimento de um minuto pode errar o valor de meio por cento,
    o suficiente para a curva dos cem por cento sair do sitio. O varrimento
    grosseiro so tem de acertar na bacia certa; o Newton faz o resto.
    """
    lats = np.arange(lat_min, lat_max + passo_graus / 2, passo_graus)
    lons = np.arange(lon_min, lon_max + passo_graus / 2, passo_graus)
    grelha_lat, grelha_lon = np.meshgrid(lats, lons, indexing="ij")

    melhor = np.zeros_like(grelha_lat)
    instante = np.zeros_like(grelha_lat)

    passo = passo_minutos / 60.0
    for t in np.arange(-janela_horas, janela_horas + passo / 2, passo):
        atual = magnitude_visivel(e, t, grelha_lat, grelha_lon)
        melhorou = atual > melhor
        melhor = np.where(melhorou, atual, melhor)
        instante = np.where(melhorou, t, instante)

    # Refinamento: o maximo da magnitude ocorre onde a distancia ao eixo da
    # sombra e minima, ou seja onde u*u' + v*v' se anula.
    for _ in range(4):
        u, v, du, dv, _, _ = _u_v_e_derivadas(e, instante, grelha_lat, grelha_lon, 0.0)
        n2 = du * du + dv * dv
        with np.errstate(invalid="ignore", divide="ignore"):
            correccao = np.where(n2 > 0, -(u * du + v * dv) / n2, 0.0)
        instante = instante + np.nan_to_num(correccao)

    refinada = magnitude_visivel(e, instante, grelha_lat, grelha_lon)

    return {
        "lat": lats,
        "lon": lons,
        "magnitude": np.maximum(melhor, refinada),
        "t_maximo_td": instante,
    }
