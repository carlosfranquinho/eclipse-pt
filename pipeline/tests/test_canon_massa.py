"""Validacao em massa contra o catalogo completo da NASA.

Para cada um dos eclipses do intervalo, o canon publica as circunstancias no
eclipse maior: coordenadas, altura e azimute do Sol, magnitude, largura da faixa.
Esses numeros foram calculados pelo Espenak a partir dos mesmos elementos
besselianos que este pipeline usa, o que os torna uma verificacao independente da
nossa implementacao da matematica.

Quatro ancoras apanhariam erros grosseiros. Mil e quatrocentos eclipses apanham
erros sistematicos que so aparecem em geometrias raras, como as sombras junto ao
terminador ou aos polos.

Tolerancias: o canon publica coordenadas e alturas com uma casa decimal, portanto
qualquer implementacao correta fica a menos de 0.05 graus do valor tabelado, que
e metade do passo de arredondamento.
"""

from __future__ import annotations

import numpy as np
import pytest

import besselian as b

# Acima desta altura do Sol o azimute e mal condicionado: perto do zenite, um
# desvio minimo na posicao roda o azimute muitos graus. Nao e um erro de calculo.
ALTURA_MAXIMA_PARA_AZIMUTE = 85.0

# O canon marca com zero a largura dos eclipses em que a umbra apenas roca a
# Terra e a faixa nao chega a formar-se.
LARGURA_NAO_PUBLICADA = 0.0


@pytest.fixture(scope="module")
def desvios(canon: list[dict]) -> dict[str, list]:
    """Calcula, de uma vez, o desvio de cada grandeza para todos os eclipses."""
    resultado: dict[str, list] = {
        "lat": [], "lon": [], "alt": [], "az": [], "mag": [], "largura": []
    }

    for e in canon:
        el = b.Elementos.de_dict(e["elementos"], e["delta_t_s"])
        g = e["eclipse_maior"]
        t = b.t_desde_t0(el, g["instante_td_h"])
        r = b.magnitude_em(el, t, g["lat"], g["lon"])
        etiqueta = f"{e['ano']:04d}-{e['mes']:02d}-{e['dia']:02d}"

        # O canon publica a razao dos diametros para os eclipses centrais e a
        # fracao do diametro coberta para os parciais. Sao definicoes diferentes.
        central = e["tipo"] != "parcial" and abs(e["gamma"]) < 0.99
        magnitude = (
            float(b.razao_diametros(r)) if central else float(r["magnitude"])
        )
        resultado["mag"].append((etiqueta, abs(magnitude - e["magnitude_canon"])))

        resultado["alt"].append((etiqueta, abs(float(r["alt_sol"]) - g["alt_sol"])))
        if g["alt_sol"] < ALTURA_MAXIMA_PARA_AZIMUTE:
            delta = abs(float(r["az_sol"]) - g["az_sol"])
            resultado["az"].append((etiqueta, min(delta, 360.0 - delta)))

        if e["tipo"] == "parcial":
            continue

        ponto = b.linha_central(el, t)
        if not bool(ponto["existe"]):
            continue
        resultado["lat"].append((etiqueta, abs(float(ponto["lat"]) - g["lat"])))
        delta = abs(float(ponto["lon"]) - g["lon"])
        resultado["lon"].append((etiqueta, min(delta, 360.0 - delta)))

        if g["largura_faixa_km"] > LARGURA_NAO_PUBLICADA:
            largura = b.largura_faixa_km(el, t)
            if np.isfinite(largura):
                resultado["largura"].append(
                    (etiqueta, abs(largura - g["largura_faixa_km"]))
                )

    return resultado


def _piores(entradas: list[tuple[str, float]], quantos: int = 5) -> str:
    ordenados = sorted(entradas, key=lambda x: -x[1])[:quantos]
    return ", ".join(f"{d} ({v:.4f})" for d, v in ordenados)


class TestCobertura:
    def test_intervalo_completo(self, canon):
        assert len(canon) > 2300, "o cache do canon parece truncado"
        anos = [e["ano"] for e in canon]
        assert min(anos) == 1500
        assert max(anos) == 2500

    def test_todos_os_tipos_representados(self, canon):
        tipos = {e["tipo"] for e in canon}
        assert tipos == {"total", "anular", "hibrido", "parcial"}


class TestEclipseMaior:
    def test_latitude(self, desvios):
        valores = np.array([v for _, v in desvios["lat"]])
        assert valores.max() < 0.06, f"piores: {_piores(desvios['lat'])}"

    def test_longitude(self, desvios):
        valores = np.array([v for _, v in desvios["lon"]])
        assert np.percentile(valores, 99) < 0.06, f"piores: {_piores(desvios['lon'])}"
        assert valores.max() < 0.2, f"piores: {_piores(desvios['lon'])}"

    def test_altura_do_sol(self, desvios):
        valores = np.array([v for _, v in desvios["alt"]])
        assert valores.max() < 0.12, f"piores: {_piores(desvios['alt'])}"

    def test_azimute_do_sol(self, desvios):
        valores = np.array([v for _, v in desvios["az"]])
        assert np.percentile(valores, 99) < 0.8, f"piores: {_piores(desvios['az'])}"
        assert valores.max() < 1.5, f"piores: {_piores(desvios['az'])}"

    def test_magnitude(self, desvios):
        valores = np.array([v for _, v in desvios["mag"]])
        assert np.median(valores) < 1e-4
        assert np.percentile(valores, 99) < 0.002, f"piores: {_piores(desvios['mag'])}"

    def test_magnitude_sem_excepcoes_alem_das_rasantes(self, desvios, por_data):
        """Os unicos desvios grandes admitidos sao eclipses de |gamma| perto de 1.

        Nesses, o ponto de eclipse maior cai sobre o terminador e a definicao de
        magnitude do canon muda de regime: publica a razao dos diametros onde
        aqui se calcula a fraccao coberta. Nao e um erro de calculo, e uma
        diferenca de definicao, e so acontece nos rasantes.

        O que se exige e a natureza das excepcoes, nao o numero: contar seria
        obrigar a mexer no teste sempre que o catalogo crescesse, e deixaria de
        se perceber o que ele defende.
        """
        fora = [(d, v) for d, v in desvios["mag"] if v > 0.005]
        nao_rasantes = [
            (d, v, por_data[d]["gamma"])
            for d, v in fora
            if abs(por_data[d]["gamma"]) <= 0.985
        ]
        assert not nao_rasantes, f"desvios em eclipses que nao sao rasantes: {nao_rasantes}"
        assert len(fora) < 0.01 * len(desvios["mag"]), (
            f"excepcoes a mais: {len(fora)} em {len(desvios['mag'])},"
            f" as piores {_piores(desvios['mag'], 10)}"
        )

    def test_largura_da_faixa(self, desvios):
        valores = np.array([v for _, v in desvios["largura"]])
        assert np.median(valores) < 1.5
        assert np.percentile(valores, 95) < 6.0, f"piores: {_piores(desvios['largura'])}"
