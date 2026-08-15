"""O texto gerado esta em todas as fichas, e esta bem escrito.

Um gerador de prosa falha de maneiras que um gerador de numeros nao tem: uma
concordancia errada, um "None" no meio da frase, uma variante que se esqueceu do
ponto final. Estes testes cobrem o que se pode verificar por regra, e o resto
le-se.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import build_text

DADOS = Path(__file__).resolve().parents[2] / "site" / "public" / "data"
INDICE = DADOS / "eclipses-index.json"


@pytest.fixture(scope="module")
def fichas() -> list[dict]:
    if not INDICE.exists():
        pytest.skip("indice em falta, correr build_index.py")
    indice = json.loads(INDICE.read_text())
    return [
        json.loads((DADOS / entrada["id"] / "eclipse.json").read_text())
        for entrada in indice
    ]


@pytest.fixture(scope="module")
def textos(fichas: list[dict]) -> list[tuple[str, str, str]]:
    """Todos os textos, com o identificador e o tempo verbal a que pertencem."""
    juntos = []
    for ficha in fichas:
        gerado = ficha.get("texto_gerado")
        if not gerado:
            pytest.skip("texto em falta, correr build_text.py")
        for tempo in ("passado", "futuro"):
            juntos.append((ficha["id"], tempo, gerado[tempo]))
    return juntos


class TestEstrutura:
    def test_todas_as_fichas_tem_os_dois_tempos(self, fichas):
        for ficha in fichas:
            gerado = ficha.get("texto_gerado")
            assert gerado, ficha["id"]
            assert set(gerado) == {"passado", "futuro"}

    def test_frases_bem_formadas(self, textos):
        for identificador, tempo, texto in textos:
            onde = f"{identificador} ({tempo})"
            assert texto, onde
            assert texto[0].isupper(), onde
            assert texto.endswith("."), onde
            assert "  " not in texto, onde
            assert " ." not in texto and " ," not in texto, onde
            assert "None" not in texto, onde
            assert "  " not in texto, onde

    def test_sem_travessoes_nem_emojis(self, textos):
        """Convencoes do projeto, aplicadas tambem ao texto gerado."""
        for identificador, tempo, texto in textos:
            assert "—" not in texto and "–" not in texto, f"{identificador} ({tempo})"
            assert texto.isprintable(), f"{identificador} ({tempo})"

    def test_menciona_a_data_certa(self, fichas):
        for ficha in fichas:
            data = ficha["data_juliana"] or ficha["data_gregoriana"]
            ano = data[:4].lstrip("0")
            assert ano in ficha["texto_gerado"]["passado"], ficha["id"]

    def test_menciona_o_local_mais_fundo(self, fichas):
        for ficha in fichas:
            mais_fundo = max(
                (t for t in ficha["territorios"].values() if t.get("visivel")),
                key=lambda t: t["magnitude_max"],
            )
            concelho = mais_fundo["local_mais_fundo"]["concelho"]
            if concelho:
                assert concelho in ficha["texto_gerado"]["passado"], ficha["id"]


class TestTempoVerbal:
    def test_o_passado_nao_fala_no_futuro(self, fichas):
        futuros = re.compile(r"\b(haverá|será|cobrirá|tapará|passará|durará|chegará)\b")
        for ficha in fichas:
            assert not futuros.search(ficha["texto_gerado"]["passado"]), ficha["id"]

    def test_o_futuro_nao_fala_no_passado(self, fichas):
        passados = re.compile(r"\b(houve|foi|cobriu|tapou|passou|durou|chegou)\b")
        for ficha in fichas:
            assert not passados.search(ficha["texto_gerado"]["futuro"]), ficha["id"]

    def test_as_duas_versoes_dizem_o_mesmo(self, fichas):
        """Mesma estrutura, mesmos numeros: so mudam os verbos."""
        numeros = re.compile(r"\d+")
        for ficha in fichas:
            passado = numeros.findall(ficha["texto_gerado"]["passado"])
            futuro = numeros.findall(ficha["texto_gerado"]["futuro"])
            assert passado == futuro, ficha["id"]


class TestVariedade:
    def test_nao_e_sempre_a_mesma_frase(self, textos):
        aberturas = {texto.split(",")[0].split(" houve")[0] for _, _, texto in textos}
        assert len(aberturas) > 20

    def test_e_reprodutivel(self, fichas):
        """Gerar duas vezes da o mesmo, que e o que permite commitar o resultado."""
        for ficha in fichas[:20]:
            de_novo = build_text.gerar(ficha, None, "passado")
            gravado = ficha["texto_gerado"]["passado"]
            # O numero de concelhos nao vem na ficha, por isso compara-se o resto.
            assert de_novo.split(". ")[0] == gravado.split(". ")[0], ficha["id"]


class TestConcordancia:
    def test_singular_e_plural_dos_concelhos(self):
        assert build_text.concordar(1, "concelho", "concelhos") == "1 concelho"
        assert build_text.concordar(7, "concelho", "concelhos") == "7 concelhos"

    def test_duracoes_por_extenso(self):
        assert build_text.duracao_por_extenso(0.3) == "menos de um segundo"
        assert build_text.duracao_por_extenso(1) == "um segundo"
        assert build_text.duracao_por_extenso(45) == "45 segundos"
        assert build_text.duracao_por_extenso(60) == "um minuto"
        assert build_text.duracao_por_extenso(89.3) == "um minuto e 29 segundos"
        assert build_text.duracao_por_extenso(121) == "2 minutos e um segundo"

    def test_maiuscula_nao_estraga_o_sol(self):
        assert build_text.maiuscula("ao pôr do Sol") == "Ao pôr do Sol"

    def test_nome_do_concelho_sem_o_distrito(self):
        assert build_text.so_concelho("Ovar, Aveiro") == "Ovar"
        assert build_text.so_concelho("Bragança, Bragança") == "Bragança"
        assert build_text.so_concelho(None) is None
