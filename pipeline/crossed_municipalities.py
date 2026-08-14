"""Concelhos atravessados pela faixa central de cada eclipse.

Cruza o poligono da faixa com os limites administrativos da CAOP e ordena os
concelhos pela hora a que a sombra la entrou, que e a ordem por que a coisa
aconteceu e a que faz sentido ler numa ficha.

Uma nota que o site tem de mostrar: os concelhos sao os de hoje. Para um eclipse
de 1764 a divisao administrativa era outra, e nem sequer havia concelhos com
estes limites. O que aqui se diz e por onde a sombra passou, descrito na
geografia actual, e nao uma reconstituicao historica.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from shapely.geometry import shape
from shapely.ops import unary_union
from shapely.strtree import STRtree

import besselian as b
import calendario as cal
import territorios

RAIZ = Path(__file__).resolve().parents[1]
DADOS = RAIZ / "site" / "public" / "data"

AVISO_ADMINISTRATIVO = (
    "Os concelhos indicados sao os actuais. A divisao administrativa da epoca era "
    "outra: o que se diz e por onde passou a sombra, descrito na geografia de hoje."
)

# Para faixas mais estreitas do que isto, o poligono e mais fino do que a
# precisao dos limites administrativos e a interseccao passa a ser aleatoria.
# Nesses casos usa-se a linha central em vez da area.
LARGURA_MINIMA_PARA_AREA_KM = 2.0


def _instante_de_entrada(
    el: b.Elementos, geometria, perfil: list[dict]
) -> float | None:
    """Instante em que a sombra entrou num concelho, pelo ponto do perfil mais proximo."""
    if not perfil:
        return None
    centro = geometria.centroid
    melhor = min(
        perfil,
        key=lambda p: (p["lat"] - centro.y) ** 2 + (p["lon"] - centro.x) ** 2,
    )
    return melhor["t"]


def concelhos_atravessados(eclipse_id: str) -> dict | None:
    pasta = DADOS / eclipse_id
    caminho_faixa = pasta / "band.geojson"
    if not caminho_faixa.exists():
        return None

    dados = json.loads((pasta / "eclipse.json").read_text())
    faixa_json = json.loads(caminho_faixa.read_text())
    propriedades = faixa_json.get("properties", {})
    perfil = propriedades.get("perfil_largura", [])

    el = b.Elementos.de_dict(dados["elementos"], dados["delta_t_s"])

    formas = [shape(f["geometry"]) for f in faixa_json["features"]]
    if not formas:
        return None
    # Uniao, e nao coleccao de geometrias: a interseccao com uma
    # GeometryCollection nao devolve o que se espera, e a faixa vem partida em
    # varias pecas sempre que a sombra sai e volta a entrar na janela do mapa.
    faixa = unary_union(formas)

    municipios_json = json.loads(
        (RAIZ / "site" / "public" / "geo" / "municipios.geojson").read_text()
    )
    propriedades_concelhos = [f["properties"] for f in municipios_json["features"]]
    geometrias = [shape(f["geometry"]) for f in municipios_json["features"]]
    arvore = STRtree(geometrias)

    estreita = not propriedades.get("desenhavel_como_area", True)

    encontrados = []
    for indice in arvore.query(faixa):
        geometria = geometrias[int(indice)]
        if not geometria.intersects(faixa):
            continue

        props = propriedades_concelhos[int(indice)]
        interseccao = geometria.intersection(faixa)
        fraccao = interseccao.area / geometria.area if geometria.area else 0.0

        # Numa faixa estreita a fraccao de area e sempre praticamente zero, e o
        # criterio util passa a ser apenas se a linha central a atravessa.
        if not estreita and fraccao < 0.001:
            continue

        t_entrada = _instante_de_entrada(el, interseccao, perfil)
        centro = interseccao.centroid

        circunstancias = b.circunstancias_locais(
            el, float(centro.y), float(centro.x),
            t_inicial=t_entrada if t_entrada is not None else 0.0,
        )

        jd_t0 = dados["jd"] - (
            dados["elementos"]["t0_td"] - dados["elementos"]["t0_td"]
        ) / 24.0
        jd_ut = (
            jd_t0
            + circunstancias["t_maximo_td"] / 24.0
            - dados["delta_t_s"] / 86400.0
        )
        hora = cal.hora_local(jd_ut, float(centro.x), props["territorio"])

        encontrados.append(
            {
                "nome": props["nome"],
                "concelho": props["concelho"],
                "distrito": props["distrito"],
                "territorio": props["territorio"],
                "fraccao_area": round(float(fraccao), 4),
                "tipo_local": circunstancias["tipo"],
                "magnitude": round(circunstancias["magnitude"], 4),
                "duracao_central_s": (
                    round(circunstancias["duracao_central_s"], 1)
                    if circunstancias.get("duracao_central_s")
                    else None
                ),
                "maximo_local": hora["hora"],
                "sistema_hora": hora["sistema"],
                "t_entrada": t_entrada,
            }
        )

    # Ordena pela hora a que a sombra chegou, que e a ordem dos acontecimentos.
    encontrados.sort(key=lambda c: (c["t_entrada"] if c["t_entrada"] is not None else 0.0))
    for concelho in encontrados:
        concelho.pop("t_entrada")

    return {
        "id": eclipse_id,
        "aviso": AVISO_ADMINISTRATIVO,
        "faixa_estreita": estreita,
        "total": len(encontrados),
        "concelhos": encontrados,
    }


def main() -> int:
    indice = json.loads((DADOS / "eclipses-index.json").read_text())
    com_faixa = [e for e in indice if e["pt"]["faixa_central"]]
    print(f"{len(com_faixa)} eclipses com faixa central sobre Portugal")

    for entrada in com_faixa:
        resultado = concelhos_atravessados(entrada["id"])
        if resultado is None:
            print(f"  {entrada['id']}: sem faixa desenhada, ignorado")
            continue
        (DADOS / entrada["id"] / "municipios.json").write_text(
            json.dumps(resultado, ensure_ascii=False, separators=(",", ":"))
        )
        centrais = sum(1 for c in resultado["concelhos"] if c["tipo_local"] in ("total", "anular"))
        print(
            f"  {entrada['id']} {entrada['tipo']:8s}: {resultado['total']:3d} concelhos"
            f" ({centrais} com fase central)"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
