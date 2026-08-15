"""Testes dos dados gerados: indice, cartografia e concelhos atravessados.

Estes testes correm sobre os ficheiros que o pipeline produz, e por isso saltam
quando ainda nao foram gerados. Verificam duas coisas diferentes: que a estrutura
esta bem formada, e que os numeros correspondem ao que se sabe destes eclipses.

O teste mais valioso e o de coerencia entre metodos. A magnitude num ponto e a
faixa desenhada no mapa sao calculadas por caminhos independentes, um pontual e
outro geometrico. Quando divergem, ha um erro em algum dos dois, e ja apanhou
alguns.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from shapely.geometry import shape

import besselian as b
import territorios

DADOS = Path(__file__).resolve().parents[2] / "site" / "public" / "data"
INDICE = DADOS / "eclipses-index.json"


@pytest.fixture(scope="module")
def indice() -> list[dict]:
    if not INDICE.exists():
        pytest.skip("indice em falta, correr build_index.py")
    return json.loads(INDICE.read_text())


@pytest.fixture(scope="module")
def por_id(indice: list[dict]) -> dict[str, dict]:
    return {e["id"]: e for e in indice}


# Folga na comparacao de magnitudes dentro de uma zona. E o preco da resolucao
# da grelha com que os contornos sao tracados, quatro centesimos de grau: um
# ponto representativo pode cair encostado a fronteira da zona.
FOLGA_ISOMAGNITUDE = 0.03

# Largura maxima da orla em que duas zonas seguidas se podem sobrepor, em graus.
# Duas vezes a tolerancia com que os poligonos sao simplificados.
LARGURA_MAXIMA_DA_ORLA = 0.02


def ficha(eclipse_id: str) -> dict:
    return json.loads((DADOS / eclipse_id / "eclipse.json").read_text())


class TestEstruturaDoIndice:
    def test_dimensao_plausivel(self, indice):
        """Portugal ve algumas centenas de eclipses em mil anos.

        A conta grosseira: um eclipse solar em cada dois ou tres anos com fase
        visivel de um ponto qualquer do pais. Os limites sao largos de proposito,
        para o teste falhar quando o pipeline se enganar na conta e nao quando o
        catalogo crescer uns quantos.
        """
        assert 300 < len(indice) < 800

    def test_ordenado_e_sem_repetidos(self, indice):
        datas = [e["data_gregoriana"] for e in indice]
        assert datas == sorted(datas)
        assert len(set(datas)) == len(datas)

    def test_campos_obrigatorios(self, indice):
        for entrada in indice:
            assert entrada["tipo"] in ("total", "anular", "hibrido", "parcial")
            assert entrada["saros"] is not None
            assert entrada["calendario_vigente_pt"] in ("juliano", "gregoriano")
            assert entrada["pt"]["territorios_visiveis"]

    def test_calendario_juliano_so_antes_de_1582(self, indice):
        for entrada in indice:
            ano = int(entrada["data_gregoriana"][:4])
            if entrada["calendario_vigente_pt"] == "juliano":
                assert ano <= 1582, entrada["id"]
                assert entrada["data_juliana"] is not None
            else:
                assert entrada["data_juliana"] is None

    def test_todos_os_seculos_representados(self, indice):
        seculos = {int(e["data_gregoriana"][:4]) // 100 for e in indice}
        assert {15, 16, 17, 18, 19, 20} <= seculos


class TestHoraLocal:
    def test_sistema_de_hora_muda_em_1912(self, indice):
        for entrada in indice[:: max(1, len(indice) // 40)]:
            detalhe = ficha(entrada["id"])
            ano = int(entrada["data_gregoriana"][:4])
            for territorio in detalhe["territorios"].values():
                if not territorio["visivel"]:
                    continue
                esperado = (
                    "hora_legal" if ano >= 1912 else "hora_solar_media_local"
                )
                assert territorio["sistema_hora"] == esperado, entrada["id"]


class TestAncorasNosDados:
    def test_1900_totalidade_em_ovar(self, por_id):
        detalhe = ficha("1900-05-28")
        continente = detalhe["territorios"]["continente"]
        assert continente["faixa_central"]
        assert continente["tipo_local"] == "total"
        assert continente["magnitude_max"] == pytest.approx(1.01, abs=0.01)
        assert "Ovar" in continente["local_mais_fundo"]["nome"]

    def test_1912_faixa_estreita_demais_para_poligono(self, por_id):
        faixa = json.loads((DADOS / "1912-04-17" / "band.geojson").read_text())
        assert faixa["properties"]["largura_sobre_pt_km"] < 2.0
        assert faixa["properties"]["desenhavel_como_area"] is False

    def test_1764_anel_atravessa_o_sul(self, por_id):
        municipios = json.loads((DADOS / "1764-04-01" / "municipios.json").read_text())
        nomes = {c["concelho"] for c in municipios["concelhos"]}
        assert len(nomes) > 100
        assert {"Faro", "Lisboa"} <= nomes
        # O plano inicial dizia que passava na Marinha Grande. Nao passava.
        assert "Marinha Grande" not in nomes

    def test_2026_totalidade_so_toca_braganca(self, por_id):
        municipios = json.loads((DADOS / "2026-08-12" / "municipios.json").read_text())
        centrais = [c for c in municipios["concelhos"] if c["tipo_local"] == "total"]
        assert len(centrais) == 1
        assert centrais[0]["concelho"] == "Bragança"

    def test_saros_conhecidos(self, por_id):
        for eclipse_id, saros in {
            "1900-05-28": 126, "2026-08-12": 126, "1912-04-17": 137,
        }.items():
            assert por_id[eclipse_id]["saros"] == saros


class TestCoerenciaEntreMetodos:
    """A grelha de pontos e o poligono da faixa tem de contar a mesma historia."""

    ECLIPSES = ["1900-05-28", "1683-01-27", "2005-10-03", "1621-05-21", "2026-08-12"]

    @pytest.mark.parametrize("eclipse_id", ECLIPSES)
    def test_concelhos_da_grelha_estao_no_poligono(self, eclipse_id):
        detalhe = ficha(eclipse_id)
        el = b.Elementos.de_dict(detalhe["elementos"], detalhe["delta_t_s"])

        da_grelha = set()
        for nome, territorio in detalhe["territorios"].items():
            if not territorio.get("faixa_central"):
                continue
            amostra = territorios.carregar()[nome]
            instantes = b.instante_maximo_em_pontos(el, amostra.lats, amostra.lons)
            resultado = b.magnitude_em(el, instantes, amostra.lats, amostra.lons)
            central = np.asarray(resultado["central"]) & np.asarray(
                resultado["sol_visivel"]
            )
            for indice in np.flatnonzero(central):
                concelho = territorios.concelho_em(
                    float(amostra.lats[indice]), float(amostra.lons[indice])
                )
                if concelho:
                    da_grelha.add(concelho["nome"])

        municipios = json.loads((DADOS / eclipse_id / "municipios.json").read_text())
        do_poligono = {
            c["nome"] for c in municipios["concelhos"]
            if c["tipo_local"] in ("total", "anular")
        }

        em_falta = da_grelha - do_poligono
        assert not em_falta, f"o poligono nao cobre {sorted(em_falta)}"

    def test_eclipses_com_faixa_tem_concelhos(self, indice):
        """Se o indice diz que a faixa tocou Portugal, tem de haver concelhos."""
        for entrada in indice:
            if not entrada["pt"]["faixa_central"]:
                continue
            caminho = DADOS / entrada["id"] / "municipios.json"
            assert caminho.exists(), entrada["id"]
            municipios = json.loads(caminho.read_text())
            assert municipios["total"] > 0, entrada["id"]


class TestCartografia:
    def test_faixas_saem_inteiras(self, indice):
        """Uma faixa fragmentada em dezenas de pecas denuncia passo temporal curto.

        Foi assim que apareceu o problema em 1912: com um quilometro de largura,
        sombras a trinta segundos de distancia nao se tocam, e a uniao saia em
        170 pedacos soltos.
        """
        for entrada in indice:
            caminho = DADOS / entrada["id"] / "band.geojson"
            if not caminho.exists():
                continue
            faixa = json.loads(caminho.read_text())
            assert len(faixa["features"]) <= 4, entrada["id"]

    def test_isomagnitudes_bem_formadas(self, indice):
        """As zonas de igual magnitude sao areas, e cada uma vale o que diz.

        A verificacao que interessa nao e topologica: e ir a um ponto de dentro
        de cada zona, calcular ali a maior magnitude que se chegou a ver, e
        exigir que caia no intervalo que a zona anuncia. Se um contorno estiver
        deslocado, ou se as propriedades e a geometria se tiverem desencontrado,
        e aqui que se ve.

        As zonas nem sempre sao aneis encaixados: quando o eclipse so aprofunda
        para la da caixa do mapa, saem faixas paralelas cortadas pela moldura. O
        que se mantem sempre e que nao se sobrepoem.
        """
        for entrada in indice[:: max(1, len(indice) // 20)]:
            caminho = DADOS / entrada["id"] / "isomag.geojson"
            if not caminho.exists():
                continue

            dados = ficha(entrada["id"])
            el = b.Elementos.de_dict(dados["elementos"], dados["delta_t_s"])
            zonas = json.loads(caminho.read_text())

            zonas_do_eclipse: list = []
            for feicao in zonas["features"]:
                assert feicao["geometry"]["type"] in ("Polygon", "MultiPolygon")
                propriedades = feicao["properties"]
                assert 0 < propriedades["de"] < propriedades["ate"]
                assert propriedades["magnitude"] == propriedades["de"]

                forma = shape(feicao["geometry"])
                assert forma.is_valid, entrada["id"]

                ponto = forma.representative_point()
                instante = b.instante_maximo_em_pontos(
                    el, np.array([ponto.y]), np.array([ponto.x])
                )
                magnitude = float(
                    b.magnitude_maxima_visivel(el, instante, ponto.y, ponto.x)[0]
                )
                assert (
                    propriedades["de"] - FOLGA_ISOMAGNITUDE
                    <= magnitude
                    <= propriedades["ate"] + FOLGA_ISOMAGNITUDE
                ), (
                    f"{entrada['id']}: dentro da zona de {propriedades['de']}"
                    f" a {propriedades['ate']} a magnitude e {magnitude:.4f}"
                )

                zonas_do_eclipse.append((propriedades["de"], forma))

            zonas_do_eclipse.sort(key=lambda par: par[0])
            for (_, fora), (nivel, dentro) in zip(
                zonas_do_eclipse, zonas_do_eclipse[1:]
            ):
                # Duas zonas seguidas partilham a fronteira, e a simplificacao
                # mexe-lhe uns metros para cada lado. O que nao pode haver e
                # sobreposicao a serio, por isso mede-se a largura media da
                # lasca e nao a sua area: uma orla de umas centenas de metros e
                # o esperado, uma regiao contada duas vezes teria a largura da
                # propria regiao.
                lasca = fora.intersection(dentro).area
                largura = lasca / min(fora.length, dentro.length)
                assert largura < LARGURA_MAXIMA_DA_ORLA, (
                    f"{entrada['id']}: a zona de {nivel} sobrepoe-se a de fora"
                    f" numa orla de {largura:.4f} graus"
                )
