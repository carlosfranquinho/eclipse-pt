"""Gera os casos de ouro do nucleo lunar, do Python para o TypeScript.

O irmao de `gerar_golden.py`. O `site/src/lib/sombra.ts` refaz as contas de
`lua.py` no browser, e so um ficheiro de referencia comum garante que as duas
implementacoes nao se afastam: aqui calcula-se com o Python, e
`site/test/sombra.test.ts` recalcula com o TypeScript e compara.

Duas familias de casos:

  contactos   os sete instantes de cada eclipse. Apanha um erro na geometria da
              corda ou na conversao entre tempo dinamico e universal.
  amostras    a magnitude em instantes espalhados pelo eclipse, incluindo antes
              do primeiro contacto e depois do ultimo, onde as magnitudes sao
              negativas e o sinal e a propria informacao.

Correr depois de qualquer alteracao a `lua.py`, e commitar o resultado.
`tests/test_golden_lua.py` falha se o ficheiro estiver desactualizado.

    uv run python pipeline/gerar_golden_lua.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import calendario as cal
import lua

RAIZ = Path(__file__).resolve().parents[1]
CANON = Path(__file__).parent / "cache" / "canon" / "canon-lua.json"
DESTINO = Path(__file__).parent / "tests" / "golden" / "sombra.json"

# Casos escolhidos a mao, um por circunstancia que interessa cobrir: um total
# central, um total raspante, um parcial fundo, um parcial minimo, um penumbral
# profundo e um penumbral que mal toca a penumbra.
ANCORAS = (
    "2029-06-26",  # total, gama pequeno, visivel de Portugal
    "2025-09-07",  # total, com a Lua a nascer ja eclipsada
    "2028-12-31",  # total curto
    "2026-08-28",  # parcial fundo
    "2024-09-18",  # parcial minimo, a Lua mal entra na umbra
    "2027-02-20",  # penumbral
)

# Quantos eclipses acrescentar as ancoras, tirados do catalogo a passo
# constante, para os casos cobrirem o milenio inteiro e nao so o nosso seculo.
EXTRA = 24

# Onde amostrar a magnitude, em fraccao do intervalo entre o primeiro e o ultimo
# contacto. Os valores fora de [0, 1] sao de proposito: e onde as magnitudes sao
# negativas, e um erro de sinal so ali se ve.
FRACCOES = (-0.15, 0.0, 0.12, 0.3, 0.5, 0.68, 0.9, 1.0, 1.2)


def escolher(eclipses: list[dict]) -> list[dict]:
    por_data = {f"{e['ano']:04d}-{e['mes']:02d}-{e['dia']:02d}": e for e in eclipses}
    escolhidos = {}
    for data in ANCORAS:
        if data not in por_data:
            raise SystemExit(f"ancora {data} em falta no catalogo lunar")
        escolhidos[data] = por_data[data]

    passo = max(1, len(eclipses) // EXTRA)
    for indice in range(0, len(eclipses), passo):
        eclipse = eclipses[indice]
        data = f"{eclipse['ano']:04d}-{eclipse['mes']:02d}-{eclipse['dia']:02d}"
        escolhidos.setdefault(data, eclipse)

    return [escolhidos[data] for data in sorted(escolhidos)]


def caso(eclipse: dict) -> dict[str, Any]:
    elementos = lua.elementos_do_eclipse(
        cal.jd_maximo_td_lua(eclipse),
        eclipse["gamma"],
        eclipse["maximo"]["duracao_penumbral_min"],
        eclipse["delta_t_s"],
    )
    contactos = lua.instantes_dos_contactos(elementos)
    inicio, fim = contactos["p1"], contactos["p4"]

    amostras = []
    for fraccao in FRACCOES:
        jd_td = inicio + (fim - inicio) * fraccao
        magnitudes = lua.magnitudes_no_instante(elementos, jd_td)
        amostras.append(
            {
                "jd_td": jd_td,
                "umbral": float(magnitudes["umbral"]),
                "penumbral": float(magnitudes["penumbral"]),
            }
        )

    return {
        "id": f"{eclipse['ano']:04d}-{eclipse['mes']:02d}-{eclipse['dia']:02d}",
        "tipo": eclipse["tipo"],
        "elementos": elementos,
        "esperado": {
            "contactos_td": {
                nome: contactos[nome]
                for nome in lua.CONTACTOS_POR_ORDEM
                if nome in contactos
            },
            "magnitude_umbral_publicada": eclipse["magnitude_umbral"],
            "magnitude_penumbral_publicada": eclipse["magnitude_penumbral"],
        },
        "amostras": amostras,
    }


def construir() -> dict[str, Any]:
    """Calcula todos os casos. Separado da escrita para o teste os poder
    recalcular e comparar com o ficheiro commitado."""
    if not CANON.exists():
        raise SystemExit(f"{CANON} em falta. Correr ingest_canon_lua.py antes.")
    eclipses = json.loads(CANON.read_text())["eclipses"]
    return {
        "nota": (
            "Gerado por pipeline/gerar_golden_lua.py. Nao editar a mao: correr "
            "o script."
        ),
        "casos": [caso(eclipse) for eclipse in escolher(eclipses)],
    }


def main() -> int:
    dados = construir()
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(json.dumps(dados, ensure_ascii=False, indent=1))
    amostras = sum(len(c["amostras"]) for c in dados["casos"])
    print(
        f"gravados {len(dados['casos'])} eclipses e {amostras} amostras em "
        f"{DESTINO}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
