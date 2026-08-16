"""O ficheiro de casos de ouro lunares esta actualizado.

O mesmo papel que `test_golden.py` faz do lado solar: o teste JavaScript compara
o TypeScript com o ficheiro gravado, e se o ficheiro envelhecer em relacao ao
Python passa a comparar o porto com uma versao antiga do nucleo, o que nao
serve de nada. Aqui o Python volta a calcular tudo e exige o mesmo resultado.

Quando falhar depois de uma alteracao deliberada a `lua.py`, a correccao e
correr `uv run python pipeline/gerar_golden_lua.py` e commitar o ficheiro novo.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import gerar_golden_lua

GOLDEN = Path(__file__).parent / "golden" / "sombra.json"


@pytest.fixture(scope="module")
def gravado() -> dict:
    if not GOLDEN.exists():
        pytest.skip("casos de ouro lunares em falta, correr gerar_golden_lua.py")
    return json.loads(GOLDEN.read_text())


@pytest.fixture(scope="module")
def recalculado() -> dict:
    return gerar_golden_lua.construir()


def test_ficheiro_corresponde_ao_codigo_actual(gravado, recalculado):
    assert json.dumps(gravado, sort_keys=True) == json.dumps(
        recalculado, sort_keys=True
    ), "casos de ouro desactualizados: correr pipeline/gerar_golden_lua.py"


def test_cobre_os_tres_tipos(gravado):
    tipos = {caso["tipo"] for caso in gravado["casos"]}
    assert tipos == {"total", "parcial", "penumbral"}


def test_cobre_o_milenio(gravado):
    anos = [int(caso["id"][:4]) for caso in gravado["casos"]]
    assert min(anos) < 1600
    assert max(anos) > 2400


def test_as_magnitudes_no_maximo_batem_com_as_publicadas(gravado):
    """As amostras do meio do eclipse sao no maximo, e ai a magnitude calculada
    tem de reproduzir a que o catalogo publica."""
    for caso in gravado["casos"]:
        maximo = caso["elementos"]["jd_maximo_td"]
        no_maximo = min(caso["amostras"], key=lambda a: abs(a["jd_td"] - maximo))
        assert no_maximo["umbral"] == pytest.approx(
            caso["esperado"]["magnitude_umbral_publicada"], abs=0.001
        ), caso["id"]
