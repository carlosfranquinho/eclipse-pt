"""Descarrega e normaliza o catalogo de eclipses lunares da NASA.

Fonte: "Five Millennium Catalog of Lunar Eclipses: -1999 to +3000", Fred Espenak
e Jean Meeus, NASA/TP-2009-214173, publicado em
https://eclipse.gsfc.nasa.gov/LEcat5/ , uma pagina por seculo, em tabelas de
largura fixa. E o irmao das paginas que `ingest_canon.py` ja le para os solares,
com o mesmo formato e a mesma atribuicao obrigatoria:
    "Eclipse Predictions by Fred Espenak, NASA's GSFC"

Ao contrario dos solares, aqui nao ha elementos besselianos para descarregar: um
eclipse lunar e o mesmo para toda a gente, e a tabela traz de uma vez tudo o que
ha para saber sobre ele. O que muda com o lugar, se a Lua estava acima do
horizonte e onde no ceu, calcula-se depois em `build_index_lua.py`.

O cache normalizado fica commitado no repositorio, para o pipeline correr sem
rede.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

CACHE_DIR = Path(__file__).parent / "cache" / "canon"
CATALOGO_URL = "https://eclipse.gsfc.nasa.gov/LEcat5/LE{inicio}-{fim}.html"
ATRIBUICAO = "Eclipse Predictions by Fred Espenak, NASA's GSFC"

# Uma pagina por seculo. A de 1401-1500 entra porque o primeiro ano do intervalo
# cai la, como acontece do lado solar.
CATALOGO_SECULOS = [
    (1401, 1500), (1501, 1600), (1601, 1700), (1701, 1800),
    (1801, 1900), (1901, 2000), (2001, 2100), (2101, 2200),
    (2201, 2300), (2301, 2400), (2401, 2500),
]

# Intervalo do projeto, o mesmo dos solares.
ANO_INICIO = 1500
ANO_FIM = 2499

MESES = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

# As colunas, tal como o cabecalho da tabela as anuncia:
#
#  Cat    Calendar   Greatest          Luna Saros Ecl.                Pen.    Um.   ---- Durations ----   in Zenith
#  Num      Date      Eclipse     DT    Num  Num  Type QSE   Gamma    Mag.    Mag.   Pen.   Par.  Total   Lat.  Lng.
#
# As duracoes das fases parcial e total vem com um travessao quando a fase nao
# chega a existir, que e o caso de todos os penumbrais e de todos os parciais.
LINHA_CATALOGO = re.compile(
    r"^\s*(\d{5})\s+(-?\d+)\s+([A-Z][a-z]{2})\s+(\d{2})\s+"
    r"(\d{2}:\d{2}:\d{2})\s+(-?\d+)\s+(-?\d+)\s+(\d+)\s+"
    r"([A-Za-z+-]+)\s+(\S+)\s+"
    r"(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+"
    r"([\d.]+|-)\s+([\d.]+|-)\s+([\d.]+|-)\s+"
    r"(\d+)([NS])\s+(\d+)([EW])\s*$"
)

# A primeira letra do codigo do Espenak da a familia: N e penumbral, com as
# variantes Nb, Ne e Nx conforme a Lua entra ou nao inteira na penumbra; P e
# parcial; T e total, com T+ e T- a distinguir as centrais das outras. O codigo
# original guarda-se, que e informacao a mais para deitar fora.
TIPOS = {"N": "penumbral", "P": "parcial", "T": "total"}


def descarregar_paginas() -> list[str]:
    """Descarrega as paginas do catalogo, se ainda nao estiverem em cache."""
    paginas = []
    for inicio, fim in CATALOGO_SECULOS:
        destino = CACHE_DIR / f"catalogo-lua-{inicio}-{fim}.html"
        if not destino.exists():
            url = CATALOGO_URL.format(inicio=inicio, fim=fim)
            print(f"a descarregar {url}")
            destino.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(url, timeout=120) as resposta:
                destino.write_bytes(resposta.read())
        paginas.append(destino.read_text(errors="replace"))
    return paginas


def _numero_ou_none(texto: str) -> float | None:
    """As duracoes das fases que nao existem vem como um travessao."""
    return None if texto.strip() == "-" else float(texto)


def _coordenada(valor: str, hemisferio: str) -> float:
    """"17S" fica -17.0, "81E" fica 81.0. Graus inteiros, que e o que o
    catalogo publica para o ponto em que a Lua esta no zenite."""
    graus = float(valor)
    return -graus if hemisferio in ("S", "W") else graus


def _horas(texto: str) -> float:
    horas, minutos, segundos = (float(p) for p in texto.split(":"))
    return horas + minutos / 60.0 + segundos / 3600.0


def normalizar(achado: re.Match) -> dict:
    """Converte uma linha da tabela na forma usada pelo projeto.

    As tres duracoes sao as das fases inteiras, em minutos, e sao simetricas em
    torno do maximo. Guardam-se tal como vem; e de `build_index_lua.py` que sai
    a conversao para os sete instantes de contacto.
    """
    (
        catalogo, ano, mes, dia, hora, delta_t, lunacao, saros,
        tipo, qse, gamma, mag_penumbral, mag_umbral,
        dur_penumbral, dur_parcial, dur_total,
        lat, lat_hemisferio, lon, lon_hemisferio,
    ) = achado.groups()

    codigo = tipo.strip()
    return {
        "catalogo": int(catalogo),
        "ano": int(ano),
        "mes": MESES[mes],
        "dia": int(dia),
        "tipo": TIPOS[codigo[0]],
        "tipo_canon": codigo,
        # As duas letras do Espenak dizem se o eclipse e visivel do ponto do
        # nascer e do por da Lua. Guardam-se por serem baratas e explicarem
        # discrepancias, mas o projeto nao as usa.
        "qse": qse.strip(),
        "saros": int(saros),
        "lunacao": int(lunacao),
        "gamma": float(gamma),
        "magnitude_penumbral": float(mag_penumbral),
        "magnitude_umbral": float(mag_umbral),
        "delta_t_s": float(delta_t),
        "maximo": {
            "instante_td_h": _horas(hora),
            "duracao_penumbral_min": _numero_ou_none(dur_penumbral),
            "duracao_parcial_min": _numero_ou_none(dur_parcial),
            "duracao_total_min": _numero_ou_none(dur_total),
            # Onde a Lua esta no zenite no instante do maximo. E a posicao
            # geocentrica da Lua dita de outra maneira: a latitude e a
            # declinacao, e a longitude e a ascensao recta menos o tempo
            # sideral. Serve para validar as efemerides deste projeto.
            "zenite_lat": _coordenada(lat, lat_hemisferio),
            "zenite_lon": _coordenada(lon, lon_hemisferio),
        },
    }


def main() -> int:
    paginas = descarregar_paginas()

    eclipses = []
    linhas_por_ler = []
    for texto in paginas:
        limpo = re.sub(r"<[^>]*>", "", texto)
        for linha in limpo.splitlines():
            if not re.match(r"^\s*\d{5}\s", linha):
                continue
            achado = LINHA_CATALOGO.match(linha)
            if achado is None:
                linhas_por_ler.append(linha.strip())
                continue
            eclipses.append(normalizar(achado))

    if linhas_por_ler:
        raise SystemExit(
            f"{len(linhas_por_ler)} linhas do catalogo nao correspondem ao "
            f"formato esperado, a primeira e:\n  {linhas_por_ler[0]}"
        )

    print(f"{len(eclipses)} eclipses lunares lidos do catalogo")

    seleccionados = [e for e in eclipses if ANO_INICIO <= e["ano"] <= ANO_FIM]
    seleccionados.sort(key=lambda e: (e["ano"], e["mes"], e["dia"]))
    print(f"{len(seleccionados)} eclipses entre {ANO_INICIO} e {ANO_FIM}")

    contagem: dict[str, int] = {}
    for e in seleccionados:
        contagem[e["tipo"]] = contagem.get(e["tipo"], 0) + 1
    print("por tipo:", ", ".join(f"{k}={v}" for k, v in sorted(contagem.items())))

    saida = CACHE_DIR / "canon-lua.json"
    saida.write_text(
        json.dumps(
            {
                "atribuicao": ATRIBUICAO,
                "fonte": CATALOGO_URL.format(inicio="AAAA", fim="AAAA"),
                "intervalo": [ANO_INICIO, ANO_FIM],
                "eclipses": seleccionados,
            },
            ensure_ascii=False,
            indent=1,
        )
    )
    print(f"gravado {saida} ({saida.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
