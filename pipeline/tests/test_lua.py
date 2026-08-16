"""Validacao das efemerides da Lua e da geometria da sombra da Terra.

Duas frentes, como do lado solar. Primeiro os exemplos trabalhados do Meeus, que
apanham um erro de transcricao numa tabela ou um sinal trocado numa formula.
Depois os 2424 eclipses lunares do catalogo da NASA, que apanham o que os
exemplos nao apanham: um erro que so aparece longe do seculo XX, ou uma escolha
de modelo que so se nota quando se olha para o milenio inteiro.

O catalogo publica, para cada eclipse, o ponto da Terra que tem a Lua no zenite
no instante do maximo, as duas magnitudes e as duracoes das tres fases. Nenhum
desses numeros veio daqui, e todos eles tem de sair deste modulo.
"""

from __future__ import annotations

import numpy as np
import pytest

import lua
from calendario import jd_maximo_td_lua

# O catalogo publica o ponto do zenite em graus inteiros, portanto meio grau e o
# maximo que uma implementacao correta pode errar so por causa do
# arredondamento.
TOLERANCIA_ZENITE = 0.5

# Na longitude ha uma segunda fonte de arredondamento: o instante do maximo e o
# Delta T vem ambos ao segundo inteiro, e a Terra roda 0.0042 graus por segundo.
# Sao milesimos, mas quatro dos 2424 eclipses caem mesmo em cima do limite sem
# esta folga. Que o desvio observado seja uniforme entre -0.5 e +0.5, com desvio
# padrao de 0.289 graus, e a assinatura do arredondamento e de mais nada.
TOLERANCIA_ZENITE_LON = TOLERANCIA_ZENITE + 360.0 / 86400.0

# As magnitudes vem com quatro casas decimais. Ficamos uma ordem de grandeza
# abaixo do arredondamento, que e o que a regra de dilatacao adoptada permite.
TOLERANCIA_MAGNITUDE = 0.0005

# As duracoes vem em decimos de minuto. Aqui a comparacao e mais grosseira de
# proposito: a travessia calcula-se com velocidade constante ao longo de uma
# corda recta, e a Lua nao anda bem assim. Um minuto e o erro maximo observado, e
# nas fases raspantes, onde a corda e curta e o modelo recto se nota mais.
TOLERANCIA_DURACAO_MIN = 1.1


# --------------------------------------------------------------------------
# Exemplos do Meeus
# --------------------------------------------------------------------------

def test_posicao_da_lua_exemplo_47a():
    """Exemplo 47.a, 1992 Abril 12 as 0h TD."""
    posicao = lua.posicao_da_lua(2448724.5)
    assert float(posicao["longitude"]) == pytest.approx(133.162655, abs=5e-6)
    assert float(posicao["latitude"]) == pytest.approx(-3.229126, abs=5e-6)
    assert float(posicao["distancia_km"]) == pytest.approx(368409.7, abs=0.1)
    assert float(posicao["paralaxe"]) == pytest.approx(0.991990, abs=5e-6)


def test_ascensao_recta_e_declinacao_exemplo_47a():
    """A mesma data, ja com nutacao e passada ao equador."""
    jde = 2448724.5
    aparente = lua.posicoes_aparentes(jde)
    assert float(aparente["ascensao_recta"]) == pytest.approx(134.688470, abs=5e-6)
    assert float(aparente["declinacao"]) == pytest.approx(13.768368, abs=5e-6)


def test_nutacao_exemplo_22a():
    """Exemplo 22.a, 1987 Abril 10 as 0h TD."""
    n = lua.nutacao(2446895.5)
    assert float(n["longitude"]) * 3600.0 == pytest.approx(-3.788, abs=0.05)
    assert float(n["obliquidade"]) * 3600.0 == pytest.approx(9.443, abs=0.05)
    assert float(lua.obliquidade_media(2446895.5)) == pytest.approx(
        23.0 + 26.0 / 60.0 + 27.407 / 3600.0, abs=1e-6
    )


def test_tempo_sideral_exemplo_12a():
    """Exemplo 12.a, 1987 Abril 10 as 0h UT: 13h 10m 46.3668s de tempo sideral
    medio, e 13h 10m 46.1351s de aparente."""
    aparente = float(lua.tempo_sideral_aparente(2446895.5)) / 15.0
    assert aparente == pytest.approx(13.0 + 10.0 / 60.0 + 46.1351 / 3600.0, abs=1e-6)


def test_posicao_do_sol_exemplo_25a():
    """Exemplo 25.a, 1992 Outubro 13 as 0h TD."""
    sol = lua.posicao_do_sol(2448908.5)
    assert float(sol["longitude"]) == pytest.approx(199.90988, abs=1e-5)
    # O metodo abreviado da 0.99766; sao os 0.99760853 do metodo completo, do
    # exemplo 25.b, que ele aproxima.
    assert float(sol["raio_ua"]) == pytest.approx(0.99766, abs=1e-5)


def test_altura_do_horizonte_e_simetrica():
    """Um astro no zenite de um lugar esta a noventa graus de altura, e a
    noventa graus do horizonte do lugar antipoda."""
    jd_ut = 2451545.0
    aparente = lua.posicoes_aparentes(jd_ut)
    sideral = float(lua.tempo_sideral_aparente(jd_ut))
    lat = float(aparente["declinacao"])
    lon = float(aparente["ascensao_recta"]) - sideral
    no_zenite = lua.altura_e_azimute(
        aparente["ascensao_recta"], aparente["declinacao"], jd_ut, lat, lon
    )
    nos_antipodas = lua.altura_e_azimute(
        aparente["ascensao_recta"], aparente["declinacao"], jd_ut, -lat, lon + 180.0
    )
    assert float(no_zenite["altura"]) == pytest.approx(90.0, abs=1e-6)
    assert float(nos_antipodas["altura"]) == pytest.approx(-90.0, abs=1e-6)


def test_paralaxe_baixa_a_lua_junto_ao_horizonte():
    """A paralaxe diurna e quase um grau no horizonte e nula no zenite."""
    assert float(lua.altura_topocentrica(0.0, 0.95)) == pytest.approx(-0.95, abs=1e-9)
    assert float(lua.altura_topocentrica(90.0, 0.95)) == pytest.approx(90.0, abs=1e-9)


# --------------------------------------------------------------------------
# O catalogo inteiro
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def calculado(canon_lua: list[dict]) -> dict[str, np.ndarray]:
    """Calcula de uma vez, para todos os eclipses, o que ha para comparar."""
    jde = np.array([jd_maximo_td_lua(e) for e in canon_lua])
    delta_t = np.array([e["delta_t_s"] for e in canon_lua])
    gamma = np.array([e["gamma"] for e in canon_lua])

    aparente = lua.posicoes_aparentes(jde)
    sideral = lua.tempo_sideral_aparente(jde - delta_t / 86400.0)
    geometria = lua.geometria_da_sombra(jde, gamma)
    return {
        "zenite_lat": aparente["declinacao"],
        "zenite_lon": (aparente["ascensao_recta"] - sideral + 180.0) % 360.0 - 180.0,
        **geometria,
        **lua.duracoes(jde, gamma),
    }


def _publicado(canon_lua: list[dict], caminho: str) -> np.ndarray:
    """Uma coluna do catalogo, com `nan` onde a fase nao existe."""
    valores = []
    for eclipse in canon_lua:
        alvo = eclipse
        for parte in caminho.split("."):
            alvo = alvo[parte]
        valores.append(np.nan if alvo is None else float(alvo))
    return np.array(valores)


def test_zenite_bate_com_o_catalogo(canon_lua, calculado):
    """Onde a Lua esta no ceu, no instante do maximo, para os 2424 eclipses.

    E a validacao independente das efemerides: a declinacao da Lua e a latitude
    do ponto que a tem no zenite, e a ascensao recta menos o tempo sideral e a
    longitude desse ponto. Se as tabelas do capitulo 47 estivessem mal
    transcritas, ou o tempo sideral fosse calculado em TD em vez de UT, isto
    partia-se aqui.
    """
    erro_lat = np.abs(calculado["zenite_lat"] - _publicado(canon_lua, "maximo.zenite_lat"))
    erro_lon = np.abs(
        (calculado["zenite_lon"] - _publicado(canon_lua, "maximo.zenite_lon") + 180.0)
        % 360.0 - 180.0
    )
    assert erro_lat.max() <= TOLERANCIA_ZENITE, (
        f"latitude do zenite errada em ate {erro_lat.max():.3f} graus, "
        f"no eclipse de {canon_lua[int(erro_lat.argmax())]['ano']}"
    )
    assert erro_lon.max() <= TOLERANCIA_ZENITE_LON, (
        f"longitude do zenite errada em ate {erro_lon.max():.3f} graus, "
        f"no eclipse de {canon_lua[int(erro_lon.argmax())]['ano']}"
    )


@pytest.mark.parametrize(
    "calculada,publicada",
    [
        ("magnitude_umbral", "magnitude_umbral"),
        ("magnitude_penumbral", "magnitude_penumbral"),
    ],
)
def test_magnitudes_batem_com_o_catalogo(canon_lua, calculado, calculada, publicada):
    erro = np.abs(calculado[calculada] - _publicado(canon_lua, publicada))
    pior = int(erro.argmax())
    assert erro.max() <= TOLERANCIA_MAGNITUDE, (
        f"{calculada} errada em ate {erro.max():.5f} no eclipse de "
        f"{canon_lua[pior]['ano']}-{canon_lua[pior]['mes']:02d}"
    )


@pytest.mark.parametrize(
    "calculada,publicada",
    [
        ("penumbral_min", "maximo.duracao_penumbral_min"),
        ("parcial_min", "maximo.duracao_parcial_min"),
        ("total_min", "maximo.duracao_total_min"),
    ],
)
def test_duracoes_batem_com_o_catalogo(canon_lua, calculado, calculada, publicada):
    """As duracoes calculadas contra as publicadas, e as fases que existem
    contra as que o catalogo diz existirem."""
    esperado = _publicado(canon_lua, publicada)
    obtido = calculado[calculada]
    assert list(np.isnan(obtido)) == list(np.isnan(esperado)), (
        "ha eclipses em que a fase calculada existe e a publicada nao, ou o "
        "contrario"
    )

    presentes = ~np.isnan(esperado)
    erro = np.abs(obtido[presentes] - esperado[presentes])
    assert erro.max() <= TOLERANCIA_DURACAO_MIN, (
        f"duracao {calculada} errada em ate {erro.max():.2f} minutos"
    )


def test_a_regra_de_dilatacao_adoptada_e_a_melhor(canon_lua, calculado):
    """A dilatacao da sombra e uma escolha, e esta e a que o catalogo suporta.

    As alternativas nao sao absurdas, sao as que a literatura usa: 1/50 de
    Chauvenet, 1/85 de Danjon. Ficam todas dez a quatrocentas vezes pior do que
    a adoptada, e este teste existe para que ninguem as troque por engano.
    """
    jde = np.array([jd_maximo_td_lua(e) for e in canon_lua])
    gamma = np.array([e["gamma"] for e in canon_lua])
    publicada = _publicado(canon_lua, "magnitude_umbral")

    erros = {}
    for regra in lua.REGRAS_DE_DILATACAO:
        magnitude = lua.geometria_da_sombra(jde, gamma, regra)["magnitude_umbral"]
        erros[regra] = float(np.sqrt(((magnitude - publicada) ** 2).mean()))

    melhor = min(erros, key=erros.get)
    assert melhor == lua.REGRA_ADOPTADA, (
        f"a regra adoptada e {lua.REGRA_ADOPTADA} mas a melhor e {melhor}: {erros}"
    )
