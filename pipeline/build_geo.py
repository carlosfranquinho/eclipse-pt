"""Converte a Carta Administrativa Oficial de Portugal em GeoJSON para o site.

Fonte: CAOP 2025, Direcao-Geral do Territorio, licenca CC-BY. Distribuida em
GeoPackage, um ficheiro por territorio, cada um na sua projeccao. Os Acores vem
ainda separados em dois grupos de ilhas, porque o arquipelago atravessa duas
zonas UTM.

O GeoPackage e uma base SQLite, e a geometria vem em WKB precedido de um
cabecalho binario proprio do formato. Le-se com o sqlite3 da biblioteca padrao
mais o shapely, sem precisar de GDAL.

Saidas, todas em WGS84 e em `site/public/geo/`:
  municipios.geojson  os 308 concelhos, com `nome` no formato "Concelho, Distrito"
  territorios.geojson o contorno de cada territorio, para a base do mapa

Os ficheiros de origem pesam 138 MB e ficam em cache local, fora do git. So o
GeoJSON derivado e commitado.
"""

from __future__ import annotations

import json
import sqlite3
import struct
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Iterator

import shapely
from pyproj import Transformer
from shapely.geometry import mapping
from shapely.ops import transform, unary_union

RAIZ = Path(__file__).resolve().parents[1]
CACHE = Path(__file__).parent / "cache" / "caop"
SAIDA = RAIZ / "site" / "public" / "geo"

BASE_URL = "https://geo2.dgterritorio.gov.pt/caop"
ATRIBUICAO = "Carta Administrativa Oficial de Portugal (CAOP) 2025, Direcao-Geral do Territorio, CC-BY"

# Por territorio: o ficheiro a descarregar e as tabelas de municipios que traz.
# Os Acores vem em dois GeoPackages porque o arquipelago abrange duas zonas UTM.
TERRITORIOS = {
    "continente": {
        "zip": "CAOP_Continente_2025-gpkg.zip",
        "tabelas": [("Continente_CAOP2025.gpkg", "cont_municipios")],
    },
    "acores": {
        "zip": "CAOP_RAA_2025-gpkg.zip",
        "tabelas": [
            ("ArqAcores_GCentral_GOriental_CAOP2025.gpkg", "raa_cen_ori_municipios"),
            ("ArqAcores_GOcidental_CAOP2025.gpkg", "raa_oci_municipios"),
        ],
    },
    "madeira": {
        "zip": "CAOP_RAM_2025-gpkg.zip",
        "tabelas": [("ArqMadeira_CAOP2025.gpkg", "ram_municipios")],
    },
}

# Tolerancia de simplificacao, em graus. Cerca de 55 m a esta latitude, que e
# bem abaixo do que se distingue a escala a que o mapa e usado, e reduz os
# ficheiros em mais de uma ordem de grandeza.
TOLERANCIA_GRAUS = 0.0005


def descarregar(nome_zip: str) -> Path:
    """Descarrega e extrai um GeoPackage da CAOP, se ainda nao estiver em cache."""
    CACHE.mkdir(parents=True, exist_ok=True)
    destino = CACHE / nome_zip
    if not destino.exists():
        url = f"{BASE_URL}/{nome_zip}"
        print(f"a descarregar {url}")
        with urllib.request.urlopen(url, timeout=600) as resposta:
            destino.write_bytes(resposta.read())
    with zipfile.ZipFile(destino) as z:
        z.extractall(CACHE)
    return destino


def _geometria_de_gpkg(blob: bytes) -> Any:  # noqa: F821
    """Extrai a geometria de um blob GeoPackage.

    O blob comeca por "GP", versao e flags. O bit 1 a 3 das flags diz quantos
    elementos tem a caixa envolvente, que vem antes do WKB e tem de ser saltada.
    """
    if blob[:2] != b"GP":
        raise ValueError("blob que nao e do formato GeoPackage")
    flags = blob[3]
    indicador_envelope = (flags >> 1) & 0x07
    dimensoes = {0: 0, 1: 4, 2: 6, 3: 6, 4: 8}[indicador_envelope]
    inicio = 8 + dimensoes * 8
    return shapely.from_wkb(blob[inicio:])


def _ler_municipios(caminho: Path, tabela: str) -> Iterator[dict]:
    """Le uma tabela de municipios e devolve geometrias ja em WGS84."""
    ligacao = sqlite3.connect(caminho)
    try:
        srs_id = list(
            ligacao.execute(
                "SELECT srs_id FROM gpkg_contents WHERE table_name = ?", (tabela,)
            )
        )[0][0]
        transformador = Transformer.from_crs(
            f"EPSG:{srs_id}", "EPSG:4326", always_xy=True
        )

        consulta = f'SELECT municipio, distrito_ilha, dtmn, geom FROM "{tabela}"'
        for municipio, distrito, codigo, blob in ligacao.execute(consulta):
            geometria = _geometria_de_gpkg(blob)
            geometria = transform(transformador.transform, geometria)
            yield {
                "codigo": codigo,
                "municipio": municipio,
                "distrito": distrito,
                "geometria": geometria,
            }
    finally:
        ligacao.close()


def _simplificar(geometria, tolerancia: float):
    """Simplifica preservando a topologia, e descarta o que fica degenerado."""
    simplificada = geometria.simplify(tolerancia, preserve_topology=True)
    return simplificada if not simplificada.is_empty else geometria


def main() -> int:
    SAIDA.mkdir(parents=True, exist_ok=True)

    concelhos: list[dict] = []
    contornos: dict[str, list] = {}

    for territorio, definicao in TERRITORIOS.items():
        descarregar(definicao["zip"])
        for ficheiro, tabela in definicao["tabelas"]:
            for registo in _ler_municipios(CACHE / ficheiro, tabela):
                geometria = _simplificar(registo["geometria"], TOLERANCIA_GRAUS)
                concelhos.append(
                    {
                        "territorio": territorio,
                        "codigo": registo["codigo"],
                        # A convencao do projeto: "Concelho, Distrito".
                        "nome": f"{registo['municipio']}, {registo['distrito']}",
                        "concelho": registo["municipio"],
                        "distrito": registo["distrito"],
                        "geometria": geometria,
                    }
                )
                contornos.setdefault(territorio, []).append(geometria)
        print(f"{territorio}: {sum(1 for c in concelhos if c['territorio'] == territorio)} concelhos")

    municipios = {
        "type": "FeatureCollection",
        "atribuicao": ATRIBUICAO,
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "nome": c["nome"],
                    "concelho": c["concelho"],
                    "distrito": c["distrito"],
                    "codigo": c["codigo"],
                    "territorio": c["territorio"],
                },
                "geometry": mapping(c["geometria"]),
            }
            for c in sorted(concelhos, key=lambda c: c["nome"])
        ],
    }
    caminho = SAIDA / "municipios.geojson"
    caminho.write_text(json.dumps(municipios, ensure_ascii=False))
    print(f"gravado {caminho.name}: {len(concelhos)} concelhos, {caminho.stat().st_size / 1e6:.1f} MB")

    # Contorno de cada territorio, para desenhar a costa sem depender de tiles.
    territorios = {
        "type": "FeatureCollection",
        "atribuicao": ATRIBUICAO,
        "features": [
            {
                "type": "Feature",
                "properties": {"territorio": nome},
                "geometry": mapping(
                    _simplificar(unary_union(geometrias), TOLERANCIA_GRAUS)
                ),
            }
            for nome, geometrias in contornos.items()
        ],
    }
    caminho = SAIDA / "territorios.geojson"
    caminho.write_text(json.dumps(territorios, ensure_ascii=False))
    print(f"gravado {caminho.name}: {caminho.stat().st_size / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
