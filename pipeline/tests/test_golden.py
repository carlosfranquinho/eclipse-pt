"""O ficheiro de casos de ouro esta actualizado e faz sentido.

O teste de ouro do lado JavaScript compara o TypeScript com este ficheiro. Se o
ficheiro envelhecer em relacao ao Python, o teste JS passa a comparar o
TypeScript com uma versao antiga do nucleo e deixa de servir para nada. Por isso
o Python volta a calcular tudo aqui e exige que o resultado seja o mesmo.

Quando este teste falhar depois de uma alteracao deliberada a `besselian.py` ou
a `calendario.py`, a correccao e correr `uv run python pipeline/gerar_golden.py`
e commitar o ficheiro novo, nao mexer no que esta gravado.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import gerar_golden

GOLDEN = Path(__file__).parent / "golden" / "circunstancias.json"


@pytest.fixture(scope="module")
def gravado() -> dict:
    if not GOLDEN.exists():
        pytest.skip("casos de ouro em falta, correr gerar_golden.py")
    return json.loads(GOLDEN.read_text())


@pytest.fixture(scope="module")
def recalculado() -> dict:
    return gerar_golden.construir()


def test_ficheiro_corresponde_ao_codigo_actual(gravado, recalculado):
    """Byte a byte, pelo JSON: qualquer desvio no nucleo aparece aqui."""
    assert json.dumps(gravado, sort_keys=True) == json.dumps(
        recalculado, sort_keys=True
    ), "casos de ouro desactualizados: correr pipeline/gerar_golden.py"


class TestCobertura:
    """Os casos de ouro so valem se cobrirem os ramos que interessam."""

    def test_todos_os_tipos_locais(self, gravado):
        tipos = {caso["esperado"]["tipo"] for caso in gravado["circunstancias"]}
        assert tipos == {"total", "anular", "parcial", "nenhum"}

    def test_todos_os_sistemas_de_hora(self, gravado):
        sistemas = {caso["esperado"]["sistema"] for caso in gravado["horas"]}
        assert sistemas == {"hora_legal", "hora_solar_media_local"}

    def test_intervalo_completo(self, gravado):
        anos = [int(e["id"][:4]) for e in gravado["eclipses"]]
        assert min(anos) < 1600
        assert max(anos) > 2000

    def test_ha_casos_com_fase_central(self, gravado):
        centrais = [
            caso
            for caso in gravado["circunstancias"]
            if caso["esperado"]["duracao_central_s"] is not None
        ]
        assert len(centrais) >= 5
        for caso in centrais:
            assert caso["esperado"]["contactos_td"]["c2"] is not None
            assert caso["esperado"]["contactos_td"]["c3"] is not None

    def test_quatro_contactos_ordenados(self, gravado):
        for caso in gravado["circunstancias"]:
            esperado = caso["esperado"]
            if not esperado["visivel"]:
                continue
            contactos = esperado["contactos_td"]
            instantes = [
                contactos["c1"],
                contactos["c2"],
                esperado["t_maximo_td"],
                contactos["c3"],
                contactos["c4"],
            ]
            presentes = [i for i in instantes if i is not None]
            assert presentes == sorted(presentes), caso["lugar"]
