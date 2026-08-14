"""Descarrega e normaliza os elementos besselianos do canon da NASA.

Fonte: "Five Millennium Canon of Solar Eclipses: -1999 to +3000", Fred Espenak e
Jean Meeus, NASA/TP-2006-214141. Os dados sao redistribuidos por
https://github.com/gmiller123456/FiveMillenniumCanonOfSolarEclipses-Besselian-Elements
em formatos legiveis por maquina.

Atribuicao obrigatoria em qualquer reutilizacao:
    "Eclipse Predictions by Fred Espenak, NASA's GSFC"

O ficheiro de origem cobre cinco milenios e pesa cerca de 12 MB. Este script filtra
para o intervalo do projeto e grava um cache normalizado, que fica commitado no
repositorio para o pipeline correr sem rede.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

CACHE_DIR = Path(__file__).parent / "cache" / "canon"
FONTE_URL = (
    "https://raw.githubusercontent.com/gmiller123456/"
    "FiveMillenniumCanonOfSolarEclipses-Besselian-Elements/main/"
    "FiveMillenniumCanonOfSolarEclipsesExtra.json"
)
ATRIBUICAO = "Eclipse Predictions by Fred Espenak, NASA's GSFC"

# Intervalo do projeto, em anos gregorianos prolepticos.
ANO_INICIO = 1500
ANO_FIM = 2100

# O canon usa uma letra por tipo de eclipse.
TIPOS = {"T": "total", "A": "anular", "H": "hibrido", "P": "parcial"}


def descarregar(url: str, destino: Path) -> None:
    """Descarrega o ficheiro bruto, se ainda nao existir em cache."""
    if destino.exists():
        print(f"ja em cache: {destino.name} ({destino.stat().st_size / 1e6:.1f} MB)")
        return
    print(f"a descarregar {url}")
    destino.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as resposta:
        destino.write_bytes(resposta.read())
    print(f"gravado {destino.name} ({destino.stat().st_size / 1e6:.1f} MB)")


def _hora_para_horas(valor: str) -> float:
    """Converte "04:21:20 TDT" ou " 4.000 TDT" em horas decimais."""
    texto = valor.strip().split()[0]
    if ":" in texto:
        partes = [float(p) for p in texto.split(":")]
        while len(partes) < 3:
            partes.append(0.0)
        return partes[0] + partes[1] / 60.0 + partes[2] / 3600.0
    return float(texto)


def normalizar(bruto: dict) -> dict:
    """Converte um registo do canon na forma usada pelo projeto.

    Agrupa os coeficientes polinomiais em listas, na ordem crescente de potencia
    de t (horas de TDT desde t0), e traduz o tipo de eclipse para portugues.
    """
    coef = lambda pref, n: [float(bruto[f"{pref}{i}"]) for i in range(1, n + 1)]

    return {
        "ano": int(bruto["year"]),
        "mes": int(bruto["month"]),
        "dia": int(bruto["day"]),
        "jd": float(bruto["jd"]),
        "tipo": TIPOS[bruto["eclipse_type"].strip()[0]],
        "tipo_canon": bruto["eclipse_type"].strip(),
        "saros": None,  # o ficheiro Extra nao traz Saros, e preenchido em build_index
        "lunacao": int(bruto["lunationnum"]),
        "gamma": float(bruto["gamma"]),
        "magnitude_canon": float(bruto["magnitude"]),
        "delta_t_s": float(bruto["deltat"]),
        # Elementos besselianos. t0 e a hora TDT de referencia; os polinomios sao
        # avaliados em t = (hora TDT) - t0, em horas.
        "elementos": {
            "t0_td": _hora_para_horas(bruto["t0"]),
            "x": coef("x", 4),
            "y": coef("y", 4),
            "d": coef("d", 4),      # graus
            "mu": coef("mu", 4),    # graus
            "l1": coef("l1", 4),    # raios equatoriais terrestres
            "l2": coef("l2", 4),
            "tan_f1": float(bruto["tanf1"]),
            "tan_f2": float(bruto["tanf2"]),
            "k1": float(bruto["k1"]),  # razao do raio da Lua, penumbra
            "k2": float(bruto["k2"]),  # razao do raio da Lua, umbra
        },
        # Circunstancias no eclipse maior, publicadas pela NASA. Servem de
        # referencia independente para validar a nossa implementacao.
        "eclipse_maior": {
            "instante_td_h": _hora_para_horas(bruto["instantOfGreatestEclipse"]),
            "instante_ut_h": _hora_para_horas(bruto["instantOfGreatestEclipseUT"]),
            "lat": float(bruto["greatestlatitude"]),
            "lon": float(bruto["greatestlongitude"]),
            "alt_sol": float(bruto["greatestalt"]),
            "az_sol": float(bruto["greatestaz"]),
            "largura_faixa_km": float(bruto["greatestpathwidth"]),
            "duracao_s": float(bruto["greatestduration"]),
        },
    }


def main() -> int:
    bruto_path = CACHE_DIR / "FiveMillenniumCanonOfSolarEclipsesExtra.json"
    descarregar(FONTE_URL, bruto_path)

    dados = json.loads(bruto_path.read_text())["data"]
    print(f"{len(dados)} eclipses no canon completo")

    seleccionados = [
        normalizar(e) for e in dados if ANO_INICIO <= int(e["year"]) <= ANO_FIM
    ]
    seleccionados.sort(key=lambda e: e["jd"])
    print(f"{len(seleccionados)} eclipses entre {ANO_INICIO} e {ANO_FIM}")

    contagem: dict[str, int] = {}
    for e in seleccionados:
        contagem[e["tipo"]] = contagem.get(e["tipo"], 0) + 1
    print("por tipo:", ", ".join(f"{k}={v}" for k, v in sorted(contagem.items())))

    saida = CACHE_DIR / "canon.json"
    saida.write_text(
        json.dumps(
            {
                "atribuicao": ATRIBUICAO,
                "fonte": FONTE_URL,
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
