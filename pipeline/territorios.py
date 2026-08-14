"""Amostragem do territorio portugues e identificacao de concelhos.

Para saber a magnitude maxima num territorio nao basta avaliar num ponto: e
preciso varrer a terra toda e ficar com o melhor valor. Este modulo prepara essa
grelha uma vez, a partir da CAOP, e permite depois perguntar em que concelho cai
um ponto qualquer.

Os tres territorios sao tratados em separado porque tem geometrias de
visibilidade muito diferentes. Os Acores apanham eclipses do Atlantico que o
continente nao chega a ver.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from shapely.geometry import Point, shape
from shapely.strtree import STRtree

RAIZ = Path(__file__).resolve().parents[1]
MUNICIPIOS = RAIZ / "site" / "public" / "geo" / "municipios.geojson"

# Passo da grelha de amostragem, em graus. No continente dois quilometros
# chegam: a magnitude varia devagar no espaco, e o que interessa e nao falhar o
# ponto mais fundo por muito. Nas ilhas usa-se passo mais fino porque sao
# pequenas e uma grelha grosseira podia nao apanhar nenhum ponto de terra.
PASSO_GRELHA = {"continente": 0.02, "acores": 0.005, "madeira": 0.005}

NOMES = ("continente", "acores", "madeira")


@dataclass
class Territorio:
    nome: str
    lats: np.ndarray          # latitudes dos pontos de terra
    lons: np.ndarray          # longitudes dos pontos de terra
    caixa: tuple[float, float, float, float]  # lat_min, lat_max, lon_min, lon_max
    sondas_lat: np.ndarray    # punhado de pontos para a rejeicao rapida
    sondas_lon: np.ndarray
    raio_graus: float         # meia diagonal da caixa, para a margem de rejeicao


@lru_cache(maxsize=1)
def _carregar_concelhos() -> tuple[list[dict], STRtree, list]:
    """Le a CAOP uma vez e prepara um indice espacial para as pesquisas."""
    if not MUNICIPIOS.exists():
        raise SystemExit(
            f"{MUNICIPIOS} em falta. Correr build_geo.py antes de build_index.py."
        )
    dados = json.loads(MUNICIPIOS.read_text())
    propriedades = [f["properties"] for f in dados["features"]]
    geometrias = [shape(f["geometry"]) for f in dados["features"]]
    return propriedades, STRtree(geometrias), geometrias


def concelho_em(lat: float, lon: float) -> dict | None:
    """Concelho que contem o ponto, ou None se cair fora de Portugal."""
    propriedades, arvore, geometrias = _carregar_concelhos()
    ponto = Point(lon, lat)
    for indice in arvore.query(ponto):
        if geometrias[indice].contains(ponto):
            return propriedades[indice]
    return None


@lru_cache(maxsize=1)
def carregar() -> dict[str, Territorio]:
    """Constroi a grelha de pontos de terra de cada territorio.

    O calculo e caro porque testa dezenas de milhares de pontos contra os
    poligonos dos concelhos, mas so se faz uma vez por execucao do pipeline.
    """
    propriedades, arvore, geometrias = _carregar_concelhos()

    por_territorio: dict[str, list] = {nome: [] for nome in NOMES}
    for props, geometria in zip(propriedades, geometrias):
        por_territorio[props["territorio"]].append(geometria)

    resultado: dict[str, Territorio] = {}
    for nome, formas in por_territorio.items():
        limites = np.array([g.bounds for g in formas])
        lon_min, lat_min = limites[:, 0].min(), limites[:, 1].min()
        lon_max, lat_max = limites[:, 2].max(), limites[:, 3].max()

        passo = PASSO_GRELHA[nome]
        lats = np.arange(lat_min, lat_max + passo, passo)
        lons = np.arange(lon_min, lon_max + passo, passo)
        malha_lat, malha_lon = np.meshgrid(lats, lons, indexing="ij")
        candidatos = np.column_stack([malha_lon.ravel(), malha_lat.ravel()])

        pontos = [Point(x, y) for x, y in candidatos]
        indice_terra = set()
        for indice_ponto, indice_forma in zip(*arvore.query(pontos, predicate="within")):
            indice_terra.add(int(indice_ponto))

        em_terra = np.array(sorted(indice_terra), dtype=int)
        lats_terra = candidatos[em_terra, 1]
        lons_terra = candidatos[em_terra, 0]

        # Sondas: os cantos da caixa e o centro. Servem para decidir depressa se
        # vale a pena avaliar a grelha toda, e para dar ao Newton um ponto de
        # partida sem ter de varrer o tempo sobre dezenas de milhares de pontos.
        sondas = np.array(
            [
                (lat_min, lon_min), (lat_min, lon_max),
                (lat_max, lon_min), (lat_max, lon_max),
                ((lat_min + lat_max) / 2, (lon_min + lon_max) / 2),
            ]
        )

        resultado[nome] = Territorio(
            nome=nome,
            lats=lats_terra,
            lons=lons_terra,
            caixa=(lat_min, lat_max, lon_min, lon_max),
            sondas_lat=sondas[:, 0],
            sondas_lon=sondas[:, 1],
            raio_graus=float(np.hypot(lat_max - lat_min, lon_max - lon_min) / 2),
        )
        print(
            f"  {nome}: {len(em_terra)} pontos de terra a {passo} graus"
            f" (caixa {lat_min:.2f}..{lat_max:.2f} N, {lon_min:.2f}..{lon_max:.2f} E)"
        )

    return resultado
