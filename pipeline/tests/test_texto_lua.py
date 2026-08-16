"""O texto lunar esta em todas as fichas, e esta bem escrito.

O irmao de `test_texto.py`. Um gerador de prosa falha de maneiras que um gerador
de numeros nao tem: uma concordancia errada, um "None" no meio da frase, um verbo
no passado num eclipse que ainda nao aconteceu. Estes testes cobrem o que se pode
verificar por regra, e o resto le-se.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import build_text_lua

DADOS = Path(__file__).resolve().parents[2] / "site" / "public" / "data"
INDICE = DADOS / "eclipses-lua-index.json"


@pytest.fixture(scope="module")
def fichas() -> list[dict]:
    if not INDICE.exists():
        pytest.skip("indice lunar em falta, correr build_index_lua.py")
    indice = json.loads(INDICE.read_text())
    return [
        json.loads((DADOS / "lua" / entrada["id"] / "eclipse.json").read_text())
        for entrada in indice
    ]


@pytest.fixture(scope="module")
def textos(fichas: list[dict]) -> list[tuple[str, str, str]]:
    juntos = []
    for ficha in fichas:
        gerado = ficha.get("texto_gerado")
        if not gerado:
            pytest.skip("texto em falta, correr build_text_lua.py")
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

    def test_sem_travessoes_nem_emojis(self, textos):
        for identificador, tempo, texto in textos:
            assert "—" not in texto and "–" not in texto, f"{identificador} ({tempo})"
            assert texto.isprintable(), f"{identificador} ({tempo})"

    def test_menciona_a_data_certa(self, fichas):
        for ficha in fichas:
            data = ficha["data_juliana"] or ficha["data_gregoriana"]
            ano = data[:4].lstrip("0")
            assert ano in ficha["texto_gerado"]["passado"], ficha["id"]

    def test_diz_o_tipo_do_eclipse(self, fichas):
        for ficha in fichas:
            assert ficha["tipo"] in ficha["texto_gerado"]["passado"], ficha["id"]

    def test_o_lugar_de_referencia_aparece(self, fichas):
        for ficha in fichas:
            nomes = [
                territorio["lugar"]["nome"]
                for territorio in ficha["territorios"].values()
                if territorio["visivel"]
            ]
            assert any(
                nome in ficha["texto_gerado"]["passado"] for nome in nomes
            ), ficha["id"]


class TestTempoVerbal:
    def test_o_passado_nao_fala_no_futuro(self, fichas):
        futuros = re.compile(
            r"\b(haverá|será|estará|entrará|chegará|durará|nascerá|ganhará"
            r"|atravessará|verá|ficará|esconderá)\b"
        )
        for ficha in fichas:
            assert not futuros.search(ficha["texto_gerado"]["passado"]), ficha["id"]

    def test_o_futuro_nao_fala_no_passado(self, fichas):
        passados = re.compile(
            r"\b(houve|foi|esteve|entrou|chegou|durou|nasceu|ganhou|atravessou"
            r"|viu|ficou|escondeu)\b"
        )
        for ficha in fichas:
            assert not passados.search(ficha["texto_gerado"]["futuro"]), ficha["id"]

    def test_as_duas_versoes_dizem_o_mesmo(self, fichas):
        numeros = re.compile(r"\d+")
        for ficha in fichas:
            passado = numeros.findall(ficha["texto_gerado"]["passado"])
            futuro = numeros.findall(ficha["texto_gerado"]["futuro"])
            assert passado == futuro, ficha["id"]


class TestConteudo:
    def test_a_cor_so_aparece_quando_ha_totalidade(self, fichas):
        """A Lua so fica vermelha dentro da umbra. Prometer a cor num eclipse
        penumbral seria mentir a quem for ver o proximo."""
        for ficha in fichas:
            texto = ficha["texto_gerado"]["passado"]
            if "cobre" in texto or "avermelhada" in texto:
                assert ficha["pt"]["tipo_local"] == "total", ficha["id"]

    def test_o_nascer_eclipsado_e_sempre_dito(self, fichas):
        for ficha in fichas:
            if not ficha["pt"]["nasceu_eclipsada"]:
                continue
            texto = ficha["texto_gerado"]["passado"]
            assert "nasceu já eclipsada" in texto, ficha["id"]

    def test_os_penumbrais_imperceptiveis_avisam(self, fichas):
        for ficha in fichas:
            if ficha["pt"]["perceptivel"]:
                continue
            assert "olho nu" in ficha["texto_gerado"]["passado"], ficha["id"]


class TestVariedade:
    def test_nao_e_sempre_a_mesma_frase(self, textos):
        aberturas = {texto.split(",")[0] for _, _, texto in textos}
        assert len(aberturas) > 100

    def test_e_reprodutivel(self, fichas):
        """Gerar duas vezes da o mesmo, que e o que permite commitar o
        resultado."""
        for ficha in fichas[:20]:
            assert build_text_lua.gerar(ficha, "passado") == ficha["texto_gerado"][
                "passado"
            ], ficha["id"]


class TestConcordancia:
    def test_duracoes_por_extenso(self):
        assert build_text_lua.duracao_por_extenso(1) == "um minuto"
        assert build_text_lua.duracao_por_extenso(43) == "43 minutos"
        assert build_text_lua.duracao_por_extenso(60) == "uma hora"
        assert build_text_lua.duracao_por_extenso(61) == "uma hora e um minuto"
        assert build_text_lua.duracao_por_extenso(102.4) == "uma hora e 42 minutos"
        assert build_text_lua.duracao_por_extenso(125) == "2 horas e 5 minutos"

    def test_a_hora_da_noite_encaixa_na_frase(self):
        """Todas as formas tem de ler bem seguidas de "de 12 de maio"."""
        for hora in ("00:30:00", "04:00:00", "07:15:00", "11:00:00",
                     "16:20:00", "20:00:00", "23:10:00"):
            frase = build_text_lua.hora_da_noite(hora)
            assert frase.startswith(("a ", "na ", "ao ", "perto ")), frase

    def test_maiuscula_nao_estraga_o_nome_da_lua(self):
        assert build_text_lua.maiuscula("a meio da noite") == "A meio da noite"
