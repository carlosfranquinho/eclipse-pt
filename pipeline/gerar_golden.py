"""Gera os casos de ouro que ligam o nucleo Python ao porto TypeScript.

O mesmo eclipse e o mesmo ponto tem de dar o mesmo numero no pipeline e no
browser. Como as duas implementacoes sao codigo diferente, so um ficheiro de
referencia comum garante que nao divergem: este script calcula algumas centenas
de casos com o Python e grava-os, e `site/test/besselian.test.ts` volta a
calcula-los com o TypeScript e compara.

Guarda tres familias de casos, porque falham de maneiras diferentes:

  circunstancias  o resultado completo num ponto, com maximo e contactos. Apanha
                  divergencias na iteracao de Newton e na escolha do tipo local.
  amostras        a magnitude em instantes fixos, sem iteracao nenhuma. Separa um
                  erro na avaliacao dos polinomios de um erro na convergencia.
  horas           a conversao de dia juliano em hora local. Apanha divergencias
                  no calendario e nas regras de fuso horario.

Correr depois de qualquer alteracao a `besselian.py` ou a `calendario.py`, e
commitar o resultado. `tests/test_golden.py` falha se o ficheiro estiver
desactualizado.

    uv run python pipeline/gerar_golden.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import besselian as b
import calendario as cal

RAIZ = Path(__file__).resolve().parents[1]
CANON = Path(__file__).parent / "cache" / "canon" / "canon.json"
DESTINO = Path(__file__).parent / "tests" / "golden" / "circunstancias.json"

# As quatro ancoras do plano, que sao tambem os casos mais interessantes: uma
# totalidade sobre Ovar, uma faixa a raspar o Algarve, uma anular pelo centro do
# pais e o hibrido de faixa quilometrica.
ANCORAS = ("1900-05-28", "1870-12-22", "1764-04-01", "1912-04-17")

# Quantos eclipses acrescentar as ancoras, tirados do catalogo a passo
# constante. Espalha os casos por todo o intervalo e pelos quatro tipos sem
# depender de os escolher a mao.
EXTRA = 12

# Pontos de prova. Cidades dos tres territorios, os locais das ancoras, e uns
# quantos pontos escolhidos por serem dificeis: no mar, na fronteira, e um do
# outro lado do mundo onde nunca ha eclipse nenhum.
PONTOS = [
    ("Lisboa", 38.7223, -9.1393),
    ("Porto", 41.1495, -8.6108),
    ("Faro", 37.0194, -7.9304),
    ("Ovar", 40.8618, -8.617),
    ("Braganca", 41.8061, -6.7567),
    ("Guarda", 40.5373, -7.2676),
    ("Evora", 38.5714, -7.9135),
    ("Beja", 38.0151, -7.8632),
    ("Coimbra", 40.2033, -8.4103),
    ("Marinha Grande", 39.7482, -8.9299),
    ("Penafiel", 41.2079, -8.284),
    ("Viana do Castelo", 41.6918, -8.8344),
    ("Sagres", 37.0075, -8.9407),
    ("Funchal", 32.6669, -16.9241),
    ("Porto Santo", 33.0662, -16.3401),
    ("Ponta Delgada", 37.7412, -25.6756),
    ("Angra do Heroismo", 38.6553, -27.2164),
    ("Horta", 38.5346, -28.6266),
    ("Corvo", 39.6996, -31.1122),
    ("Santa Maria", 36.9711, -25.0961),
    ("Mar a oeste do Cabo da Roca", 38.78, -10.5),
    ("Fronteira em Elvas", 38.8814, -7.1631),
    ("Wellington", -41.29, 174.78),
]

# Casos de hora escolhidos a mao, para cobrir as fronteiras que os eclipses
# sozinhos nao garantem cobrir.
HORAS_ESCOLHIDAS = [
    # Ultimo dia sem hora legal em Portugal e primeiro dia com ela.
    (1911, 12, 31, 12.0, -9.1393, "continente"),
    (1912, 1, 2, 12.0, -9.1393, "continente"),
    # Hora de verao antiga, quando o continente adiantava o relogio em junho.
    (1940, 6, 1, 12.0, -9.1393, "continente"),
    # O periodo de 1992 a 1996 na hora da Europa Central.
    (1994, 5, 10, 12.0, -9.1393, "continente"),
    (1994, 5, 10, 12.0, -25.6756, "acores"),
    (1994, 5, 10, 12.0, -16.9241, "madeira"),
    # Hora de verao actual, nos tres territorios.
    (2026, 8, 12, 18.0, -9.1393, "continente"),
    (2026, 8, 12, 18.0, -25.6756, "acores"),
    (2026, 8, 12, 18.0, -16.9241, "madeira"),
    # Inverno, com os tres fusos em hora de inverno.
    (2027, 1, 15, 9.0, -9.1393, "continente"),
    (2027, 1, 15, 9.0, -25.6756, "acores"),
    # Antes da reforma do calendario, onde a data local e a juliana.
    (1560, 3, 20, 15.0, -8.4103, "continente"),
    (1581, 6, 10, 15.0, -8.4103, "continente"),
    # Uma passagem da meia-noite pela hora solar media, a leste e a oeste.
    (1800, 6, 1, 0.2, -8.4103, "continente"),
    (1800, 6, 1, 23.9, -31.1122, "acores"),
]


def escolher(eclipses: list[dict]) -> list[dict]:
    """As ancoras mais uma amostra regular do resto do canon."""
    por_data = {f"{e['ano']:04d}-{e['mes']:02d}-{e['dia']:02d}": e for e in eclipses}
    escolhidos = {}
    for data in ANCORAS:
        if data not in por_data:
            raise SystemExit(f"ancora {data} em falta no canon")
        escolhidos[data] = por_data[data]

    passo = max(1, len(eclipses) // EXTRA)
    for indice in range(0, len(eclipses), passo):
        eclipse = eclipses[indice]
        data = f"{eclipse['ano']:04d}-{eclipse['mes']:02d}-{eclipse['dia']:02d}"
        escolhidos.setdefault(data, eclipse)

    return [escolhidos[data] for data in sorted(escolhidos)]


def circunstancias(el: b.Elementos, lat: float, lon: float) -> dict[str, Any]:
    """O caso completo num ponto, mais duas amostras sem iteracao.

    As amostras sao tiradas meia hora antes e meia hora depois do maximo local.
    Se so o caso completo divergisse, seria preciso adivinhar se o erro estava na
    geometria ou na convergencia; com as amostras, sabe-se.
    """
    resultado = b.circunstancias_no_ponto(el, lat, lon)
    t_maximo = resultado["t_maximo_td"]

    amostras = []
    for desvio in (-0.5, 0.5):
        t = t_maximo + desvio
        m = b.magnitude_em(el, t, lat, lon)
        amostras.append(
            {
                "t": t,
                "magnitude": float(m["magnitude"]),
                "obscuracao": float(m["obscuracao"]),
                "alt_sol": float(m["alt_sol"]),
                "az_sol": float(m["az_sol"]),
                "u": float(m["u"]),
                "v": float(m["v"]),
                "angulo_horario": float(m["angulo_horario"]),
                "declinacao": float(m["declinacao"]),
                "separacao": float(m["separacao"]),
                "l1_obs": float(m["l1_obs"]),
                "l2_obs": float(m["l2_obs"]),
            }
        )

    esperado = {
        "visivel": bool(resultado["visivel"]),
        "tipo": resultado["tipo"],
        "magnitude": float(resultado["magnitude"]),
        "obscuracao": float(resultado["obscuracao"]),
        "razao_diametros": (
            float(resultado["razao_diametros"])
            if resultado.get("razao_diametros") is not None
            else None
        ),
        "t_maximo_td": float(t_maximo),
        "contactos_td": {
            chave: (None if valor is None else float(valor))
            for chave, valor in resultado["contactos_td"].items()
        },
        "duracao_central_s": (
            float(resultado["duracao_central_s"])
            if resultado.get("duracao_central_s") is not None
            else None
        ),
        "alt_sol": float(resultado["alt_sol"]),
        "az_sol": float(resultado["az_sol"]),
    }
    return {"esperado": esperado, "amostras": amostras}


def caso_de_hora(jd_ut: float, lon: float, territorio: str) -> dict[str, Any]:
    hora = cal.hora_local(jd_ut, lon, territorio)
    return {
        "jd_ut": jd_ut,
        "lon": lon,
        "territorio": territorio,
        "esperado": {
            "data": hora["data"],
            "hora": hora["hora"],
            "sistema": hora["sistema"],
            "desvio_utc_h": hora["desvio_utc_h"],
        },
    }


def construir() -> dict[str, Any]:
    """Calcula todos os casos. Separado da escrita para o teste os poder
    recalcular e comparar com o ficheiro commitado."""
    if not CANON.exists():
        raise SystemExit(f"{CANON} em falta. Correr ingest_canon.py antes.")
    eclipses = json.loads(CANON.read_text())["eclipses"]
    escolhidos = escolher(eclipses)

    fichas = []
    casos = []
    horas = []

    for eclipse in escolhidos:
        el = b.Elementos.de_dict(eclipse["elementos"], eclipse["delta_t_s"])
        jd_t0 = cal.jd_t0_td(eclipse)
        identificador = cal.jd_para_civil(eclipse["jd"], gregoriano=True).iso_data()

        fichas.append(
            {
                "id": identificador,
                "tipo": eclipse["tipo"],
                "jd_t0_td": jd_t0,
                "delta_t_s": eclipse["delta_t_s"],
                "elementos": eclipse["elementos"],
            }
        )

        for nome, lat, lon in PONTOS:
            calculado = circunstancias(el, lat, lon)
            casos.append(
                {
                    "eclipse": identificador,
                    "lugar": nome,
                    "lat": lat,
                    "lon": lon,
                    **calculado,
                }
            )

            # A hora do maximo em cada ponto e o caso de hora mais realista que
            # ha: e exactamente a conversao que o mapa faz a cada movimento do
            # rato.
            if calculado["esperado"]["visivel"]:
                jd_ut = jd_t0 + calculado["esperado"]["t_maximo_td"] / 24.0
                jd_ut -= eclipse["delta_t_s"] / 86400.0
                territorio = "continente"
                if lon < -20.0:
                    territorio = "acores"
                elif lon < -15.0:
                    territorio = "madeira"
                horas.append(caso_de_hora(jd_ut, lon, territorio))

    for ano, mes, dia, hora, lon, territorio in HORAS_ESCOLHIDAS:
        gregoriano = cal.civil_para_jd(ano, mes, dia, gregoriano=True) >= (
            cal.JD_ADOPCAO_GREGORIANO_PT
        )
        jd_ut = cal.civil_para_jd(ano, mes, dia, gregoriano=gregoriano) + hora / 24.0
        horas.append(caso_de_hora(jd_ut, lon, territorio))

    return {
        "gerado_por": "pipeline/gerar_golden.py",
        "aviso": "Ficheiro gerado. Nao editar a mao; correr o gerador.",
        "eclipses": fichas,
        "circunstancias": casos,
        "horas": horas,
    }


def main() -> int:
    conteudo = construir()
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(json.dumps(conteudo, ensure_ascii=False, indent=1) + "\n")
    print(
        f"gravado {DESTINO.relative_to(RAIZ)}: {len(conteudo['eclipses'])} eclipses,"
        f" {len(conteudo['circunstancias'])} circunstancias,"
        f" {len(conteudo['horas'])} horas,"
        f" {DESTINO.stat().st_size / 1e3:.0f} kB"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
