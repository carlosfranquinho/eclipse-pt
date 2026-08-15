"""Um ponto por concelho, para a caixa de pesquisa do mapa.

O calculo ao vivo responde a um ponto qualquer, mas apontar o rato nao serve a
quem navega pelo teclado nem a quem quer saber o que se viu de um sitio com
nome. A caixa de pesquisa da ficha precisa entao de uma lista curta de lugares
com coordenadas, e os 308 concelhos sao a lista natural: ja sao a unidade em que
o resto do site fala.

O ponto de cada concelho e interior a ele, mas nao e a sede: a CAOP publica
limites, nao localidades. Fica escrito no ficheiro, e a interface diz o mesmo,
para ninguem tomar estas coordenadas por coordenadas de uma vila.

Le o GeoJSON ja derivado por `build_geo.py` em vez dos GeoPackage originais, que
pesam 138 MB e teriam de ser descarregados outra vez. Assim este passo corre em
segundos sobre o que ja esta no repositorio.

    uv run python pipeline/build_lugares.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from shapely.geometry import shape

RAIZ = Path(__file__).resolve().parents[1]
GEO = RAIZ / "site" / "public" / "geo"
ORIGEM = GEO / "municipios.geojson"
DESTINO = GEO / "lugares.json"

NOTA = (
    "Ponto interior de cada concelho, derivado dos limites da CAOP. Nao e a sede"
    " de concelho: a CAOP publica limites administrativos, nao localidades."
)


def ponto_do_concelho(geometria) -> tuple[float, float]:
    """Um ponto dentro do concelho, na sua parte principal.

    Nos concelhos insulares e nos que tem ilhas ao largo, a geometria vem em
    varias partes. Escolhe-se a maior, para o ponto de Angra do Heroismo nao ir
    parar a um ilheu.

    Usa-se o ponto representativo e nao o centroide porque o centroide de um
    concelho em ferradura, como Odemira em torno de Vila Nova de Milfontes, cai
    fora dele.
    """
    if geometria.geom_type == "MultiPolygon":
        geometria = max(geometria.geoms, key=lambda parte: parte.area)
    ponto = geometria.representative_point()
    return round(ponto.y, 5), round(ponto.x, 5)


def main() -> int:
    if not ORIGEM.exists():
        raise SystemExit(f"{ORIGEM} em falta. Correr build_geo.py antes.")

    dados = json.loads(ORIGEM.read_text())
    lugares = []
    for feicao in dados["features"]:
        propriedades = feicao["properties"]
        lat, lon = ponto_do_concelho(shape(feicao["geometry"]))
        lugares.append(
            {
                "nome": propriedades["nome"],
                "concelho": propriedades["concelho"],
                "distrito": propriedades["distrito"],
                "territorio": propriedades["territorio"],
                "lat": lat,
                "lon": lon,
            }
        )

    lugares.sort(key=lambda lugar: lugar["nome"])
    conteudo = {
        "atribuicao": dados.get("atribuicao"),
        "nota": NOTA,
        "lugares": lugares,
    }
    DESTINO.write_text(
        json.dumps(conteudo, ensure_ascii=False, separators=(",", ":"))
    )
    print(
        f"gravado {DESTINO.relative_to(RAIZ)}: {len(lugares)} lugares,"
        f" {DESTINO.stat().st_size / 1e3:.0f} kB"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
