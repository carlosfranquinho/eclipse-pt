"""Testes dos dados lunares gerados: indice e fichas.

Correm sobre os ficheiros que `build_index_lua.py` produz, e saltam quando ainda
nao foram gerados.

O que aqui se verifica nao e a astronomia, que ja tem o seu teste em massa contra
o catalogo, e sim a coerencia entre o que a ficha diz e o que ela mostra: que os
contactos estao pela ordem certa, que um eclipse dito total tem totalidade, que a
Lua nao esta acima e abaixo do horizonte ao mesmo tempo, e que nenhum eclipse
entrou no indice sem se ver de lado nenhum.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import lua
from build_index_lua import ALTURA_MINIMA_VISIVEL, LUGARES, ORDEM_DOS_CONTACTOS

DADOS = Path(__file__).resolve().parents[2] / "site" / "public" / "data"
INDICE = DADOS / "eclipses-lua-index.json"


@pytest.fixture(scope="module")
def indice() -> list[dict]:
    if not INDICE.exists():
        pytest.skip("indice lunar em falta, correr build_index_lua.py")
    return json.loads(INDICE.read_text())


@pytest.fixture(scope="module")
def fichas(indice: list[dict]) -> list[dict]:
    return [
        json.loads((DADOS / "lua" / entrada["id"] / "eclipse.json").read_text())
        for entrada in indice
    ]


class TestIndice:
    def test_ordenado_e_sem_repetidos(self, indice):
        identificadores = [e["id"] for e in indice]
        assert identificadores == sorted(identificadores)
        assert len(set(identificadores)) == len(identificadores)

    def test_dentro_do_intervalo_do_projeto(self, indice):
        anos = [int(e["id"][:4]) for e in indice]
        assert min(anos) >= 1500
        assert max(anos) <= 2499

    def test_todos_se_veem_de_algum_territorio(self, indice):
        for entrada in indice:
            assert entrada["pt"]["territorios_visiveis"], entrada["id"]

    def test_o_tipo_local_nunca_e_mais_fundo_do_que_o_global(self, indice):
        """Daqui pode ver-se menos do que aconteceu, nunca mais.

        Um eclipse total pode ser parcial em Portugal se a Lua se puser a meio;
        um eclipse parcial nao pode, de maneira nenhuma, ser total daqui.
        """
        fundura = {"nenhum": 0, "penumbral": 1, "parcial": 2, "total": 3}
        for entrada in indice:
            assert fundura[entrada["pt"]["tipo_local"]] <= fundura[entrada["tipo"]], (
                entrada["id"]
            )

    def test_o_indice_leve_e_mesmo_leve(self):
        """A pagina inicial carrega isto inteiro, e sao mil e setecentos
        eclipses."""
        assert INDICE.stat().st_size < 1_500_000


class TestFichas:
    def test_contactos_pela_ordem_certa(self, fichas):
        for ficha in fichas:
            for territorio in ficha["territorios"].values():
                if not territorio["visivel"]:
                    continue
                instantes = [
                    territorio["contactos"][nome]["jd_ut"]
                    for nome in ORDEM_DOS_CONTACTOS
                    if nome in territorio["contactos"]
                ]
                assert instantes == sorted(instantes), ficha["id"]

    def test_as_fases_correspondem_ao_tipo(self, fichas):
        """Um penumbral tem tres contactos, um parcial cinco, um total sete."""
        esperado = {"penumbral": 3, "parcial": 5, "total": 7}
        for ficha in fichas:
            visivel = next(
                t for t in ficha["territorios"].values() if t["visivel"]
            )
            assert len(visivel["contactos"]) == esperado[ficha["tipo"]], ficha["id"]

    def test_a_altura_decide_a_visibilidade_do_contacto(self, fichas):
        for ficha in fichas:
            for territorio in ficha["territorios"].values():
                if not territorio["visivel"]:
                    continue
                for nome, momento in territorio["contactos"].items():
                    # A altura vai para a ficha arredondada ao decimo, e a
                    # bandeira foi decidida sobre o valor exacto: no limiar, os
                    # dois podem discordar por meio decimo, e discordam mesmo.
                    if abs(momento["altura_graus"] - ALTURA_MINIMA_VISIVEL) <= 0.05:
                        continue
                    assert momento["acima_do_horizonte"] == (
                        momento["altura_graus"] >= ALTURA_MINIMA_VISIVEL
                    ), f"{ficha['id']} {nome}"

    def test_quem_nasceu_eclipsada_tem_o_principio_por_baixo(self, fichas):
        """Se a Lua nasceu a meio do eclipse, o primeiro contacto nao se viu, e
        o instante do nascer esta entre o primeiro e o ultimo."""
        for ficha in fichas:
            for territorio in ficha["territorios"].values():
                if not territorio.get("nasceu_eclipsada"):
                    continue
                contactos = territorio["contactos"]
                assert not contactos["p1"]["acima_do_horizonte"], ficha["id"]
                assert (
                    contactos["p1"]["jd_ut"]
                    < territorio["nascer"]["jd_ut"]
                    < contactos["p4"]["jd_ut"]
                ), ficha["id"]

    def test_quem_se_poe_eclipsada_tem_o_fim_por_baixo(self, fichas):
        for ficha in fichas:
            for territorio in ficha["territorios"].values():
                if not territorio.get("poe_se_eclipsada"):
                    continue
                contactos = territorio["contactos"]
                assert not contactos["p4"]["acima_do_horizonte"], ficha["id"]
                assert (
                    contactos["p1"]["jd_ut"]
                    < territorio["por"]["jd_ut"]
                    < contactos["p4"]["jd_ut"]
                ), ficha["id"]

    def test_o_pt_resume_o_melhor_dos_territorios(self, fichas):
        for ficha in fichas:
            visiveis = [t for t in ficha["territorios"].values() if t["visivel"]]
            melhor = max(visiveis, key=lambda t: t["magnitude_penumbral_visivel"])
            assert ficha["pt"]["tipo_local"] == melhor["tipo_visto"], ficha["id"]
            assert ficha["pt"]["magnitude_umbral"] == melhor[
                "magnitude_umbral_visivel"
            ], ficha["id"]

    def test_os_lugares_de_referencia_sao_os_declarados(self, fichas):
        for ficha in fichas[:50]:
            for nome, territorio in ficha["territorios"].items():
                assert territorio["lugar"] == LUGARES[nome], ficha["id"]


class TestElementos:
    """Os numeros que vao para o browser desenhar o eclipse.

    Sao poucos e chegam para tudo, mas so se estiverem certos: e com eles que a
    ficha desenha a sombra e o `sombra.ts` recalcula a magnitude no browser.
    """

    def test_a_magnitude_no_maximo_bate_com_a_publicada(self, fichas):
        for ficha in fichas:
            elementos = ficha["elementos"]
            magnitudes = lua.magnitudes_no_instante(
                elementos, elementos["jd_maximo_td"]
            )
            assert float(magnitudes["umbral"]) == pytest.approx(
                ficha["magnitude_umbral"], abs=0.001
            ), ficha["id"]
            assert float(magnitudes["penumbral"]) == pytest.approx(
                ficha["magnitude_penumbral"], abs=0.001
            ), ficha["id"]

    def test_a_geometria_e_consistente(self, fichas):
        for ficha in fichas:
            elementos = ficha["elementos"]
            assert 0.0 < elementos["raio_lua"] < elementos["raio_umbra"]
            assert elementos["raio_umbra"] < elementos["raio_penumbra"]
            assert elementos["velocidade"] > 0.0
            # A Lua tem de passar suficientemente perto do eixo para tocar a
            # penumbra: e a propria definicao de haver eclipse.
            assert abs(elementos["y"]) < (
                elementos["raio_penumbra"] + elementos["raio_lua"]
            ), ficha["id"]

    def test_a_duracao_penumbral_reproduz_a_publicada(self, fichas):
        """A velocidade vem da duracao publicada, portanto isto tem de fechar
        ao segundo: e a verificacao de que nada se perdeu no caminho."""
        for ficha in fichas:
            elementos = ficha["elementos"]
            contactos = lua.instantes_dos_contactos(elementos)
            duracao_min = (contactos["p4"] - contactos["p1"]) * 24.0 * 60.0
            assert duracao_min == pytest.approx(
                ficha["duracoes_min"]["penumbral"], abs=0.05
            ), ficha["id"]
