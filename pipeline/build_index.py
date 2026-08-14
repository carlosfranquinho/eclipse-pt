"""Constroi o indice de eclipses solares visiveis em Portugal.

Percorre os eclipses do canon e, para cada um, varre a terra dos tres
territorios para descobrir o que se viu de Portugal: magnitude maxima, onde, a
que horas, com o Sol a que altura, e se a faixa central chegou a tocar o pais.

Escreve dois ficheiros, por uma razao de peso: a pagina inicial carrega o indice
leve com centenas de eclipses, e so a ficha de cada eclipse carrega o detalhe.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

import besselian as b
import calendario as cal
import territorios

RAIZ = Path(__file__).resolve().parents[1]
CANON = Path(__file__).parent / "cache" / "canon" / "canon.json"
SAIDA = RAIZ / "site" / "public" / "data"

# Limiar acima do qual se geram os dados geograficos pesados: faixa,
# isomagnitudes e concelhos atravessados. Abaixo disto o eclipse continua no
# indice, com os numeros essenciais, mas sem cartografia propria. Baixar este
# valor aumenta o peso do site sem acrescentar muito interesse.
LIMIAR_DADOS_PESADOS = 0.5

# Abaixo desta magnitude considera-se que nao houve eclipse observavel. Serve
# para nao encher o indice de rocaduras invisiveis a olho nu.
MAGNITUDE_MINIMA = 0.001


def _jd_de_t(eclipse: dict, t: float) -> tuple[float, float]:
    """Dia juliano em TD e em UT, para um instante `t` em horas desde t0."""
    elementos = eclipse["elementos"]
    maior = eclipse["eclipse_maior"]
    jd_t0 = eclipse["jd"] - (maior["instante_td_h"] - elementos["t0_td"]) / 24.0
    jd_td = jd_t0 + t / 24.0
    return jd_td, jd_td - eclipse["delta_t_s"] / 86400.0


# Margem de seguranca da rejeicao rapida, em raios terrestres. As sondas cobrem
# os cantos do territorio, mas a sombra pode passar entre elas, por isso exige-se
# que fique bem afastada antes de se descartar o eclipse.
MARGEM_REJEICAO = 0.25


def _sondar(el: b.Elementos, territorio: territorios.Territorio) -> tuple[bool, float]:
    """Decide depressa se vale a pena avaliar a grelha inteira.

    Avalia so os cantos e o centro do territorio ao longo do tempo. Devolve se o
    eclipse pode ser visivel e o instante a partir do qual o Newton deve arrancar
    na grelha completa.

    Sem esta sondagem, o pipeline varria dezenas de milhares de pontos para os
    muitos eclipses que nem sequer se aproximam de Portugal.
    """
    instantes = b.instante_maximo_em_pontos(el, territorio.sondas_lat, territorio.sondas_lon)
    resultado = b.magnitude_em(el, instantes, territorio.sondas_lat, territorio.sondas_lon)

    folga = np.asarray(resultado["separacao"]) - np.asarray(resultado["l1_obs"])
    melhor = int(np.argmin(folga))
    pode_ser_visivel = bool(folga.min() < MARGEM_REJEICAO)
    return pode_ser_visivel, float(instantes[melhor])


def avaliar_territorio(
    el: b.Elementos, eclipse: dict, territorio: territorios.Territorio
) -> dict:
    """O que se viu deste eclipse num territorio."""
    pode_ser_visivel, t_sonda = _sondar(el, territorio)
    if not pode_ser_visivel:
        return {"visivel": False}

    instantes = b.instante_maximo_em_pontos(
        el, territorio.lats, territorio.lons, t_inicial=t_sonda
    )
    resultado = b.magnitude_em(el, instantes, territorio.lats, territorio.lons)

    magnitudes = np.where(resultado["sol_visivel"], resultado["magnitude"], 0.0)
    melhor = int(np.argmax(magnitudes))
    magnitude_max = float(magnitudes[melhor])

    if magnitude_max < MAGNITUDE_MINIMA:
        return {"visivel": False}

    lat = float(territorio.lats[melhor])
    lon = float(territorio.lons[melhor])
    concelho = territorios.concelho_em(lat, lon)

    # Circunstancias completas no ponto mais fundo, para ter os contactos.
    locais = b.circunstancias_locais(el, lat, lon, t_inicial=float(instantes[melhor]))

    _, jd_ut = _jd_de_t(eclipse, float(instantes[melhor]))
    hora = cal.hora_local(jd_ut, lon, territorio.nome)

    central = np.asarray(resultado["central"]) & np.asarray(resultado["sol_visivel"])
    tem_faixa = bool(central.any())

    ficha = {
        "visivel": True,
        "magnitude_max": round(magnitude_max, 4),
        "obscuracao_max": round(float(resultado["obscuracao"][melhor]), 4),
        "tipo_local": locais["tipo"],
        "faixa_central": tem_faixa,
        "local_mais_fundo": {
            "nome": concelho["nome"] if concelho else None,
            "concelho": concelho["concelho"] if concelho else None,
            "distrito": concelho["distrito"] if concelho else None,
            "lat": round(lat, 4),
            "lon": round(lon, 4),
        },
        "maximo_local": hora["hora"],
        "data_local": hora["data"],
        "sistema_hora": hora["sistema"],
        "designacao_fuso": hora["designacao_fuso"],
        "maximo_ut": cal.jd_para_civil(jd_ut, gregoriano=True).iso_hora(),
        "alt_sol_graus": round(float(resultado["alt_sol"][melhor]), 1),
        "az_sol_graus": round(float(resultado["az_sol"][melhor]), 1),
        "duracao_central_s": (
            round(locais["duracao_central_s"], 1)
            if locais.get("duracao_central_s")
            else None
        ),
        "fraccao_territorio_com_faixa": round(float(central.mean()), 4),
    }

    if tem_faixa:
        # Onde a faixa entrou e saiu, em concelhos, e util para a ficha.
        indices = np.flatnonzero(central)
        ordem = np.argsort(instantes[indices])
        primeiro, ultimo = indices[ordem[0]], indices[ordem[-1]]
        ficha["faixa_entrada"] = _descrever_ponto(territorio, primeiro)
        ficha["faixa_saida"] = _descrever_ponto(territorio, ultimo)

    return ficha


def _descrever_ponto(territorio: territorios.Territorio, indice: int) -> dict:
    lat = float(territorio.lats[indice])
    lon = float(territorio.lons[indice])
    concelho = territorios.concelho_em(lat, lon)
    return {
        "nome": concelho["nome"] if concelho else None,
        "lat": round(lat, 4),
        "lon": round(lon, 4),
    }


def main() -> int:
    dados = json.loads(CANON.read_text())
    eclipses = dados["eclipses"]
    print(f"{len(eclipses)} eclipses no canon, a carregar territorios:")
    todos = territorios.carregar()

    indice = []
    for numero, eclipse in enumerate(eclipses, 1):
        if numero % 200 == 0:
            print(f"  {numero}/{len(eclipses)}")

        el = b.Elementos.de_dict(eclipse["elementos"], eclipse["delta_t_s"])
        por_territorio = {
            nome: avaliar_territorio(el, eclipse, territorio)
            for nome, territorio in todos.items()
        }
        if not any(t["visivel"] for t in por_territorio.values()):
            continue

        jd_td, jd_ut = _jd_de_t(eclipse, eclipse["eclipse_maior"]["instante_td_h"] - eclipse["elementos"]["t0_td"])
        gregoriana = cal.jd_para_civil(eclipse["jd"], gregoriano=True)
        juliana = cal.jd_para_civil(eclipse["jd"], gregoriano=False)
        vigente = cal.calendario_vigente(eclipse["jd"])

        magnitude_global = max(
            t.get("magnitude_max", 0.0) for t in por_territorio.values()
        )
        tem_faixa = any(t.get("faixa_central") for t in por_territorio.values())

        indice.append(
            {
                "id": gregoriana.iso_data(),
                "jd": eclipse["jd"],
                "data_gregoriana": gregoriana.iso_data(),
                "data_juliana": juliana.iso_data() if vigente == "juliano" else None,
                "calendario_vigente_pt": vigente,
                "tipo": eclipse["tipo"],
                "saros": eclipse["saros"],
                "gamma": eclipse["gamma"],
                "magnitude_canon": eclipse["magnitude_canon"],
                "delta_t_s": eclipse["delta_t_s"],
                "maximo_global_ut": cal.jd_para_civil(
                    eclipse["jd"] - eclipse["delta_t_s"] / 86400.0, gregoriano=True
                ).iso_hora(),
                "pt": {
                    "magnitude_max": round(magnitude_global, 4),
                    "faixa_central": tem_faixa,
                    "territorios_visiveis": [
                        nome for nome, t in por_territorio.items() if t["visivel"]
                    ],
                },
                "territorios": por_territorio,
                "dados_pesados": magnitude_global >= LIMIAR_DADOS_PESADOS or tem_faixa,
                "elementos": eclipse["elementos"],
            }
        )

    SAIDA.mkdir(parents=True, exist_ok=True)

    # Indice leve, para a lista e os filtros da pagina inicial.
    leve = [
        {
            k: e[k]
            for k in (
                "id", "data_gregoriana", "data_juliana", "calendario_vigente_pt",
                "tipo", "saros", "pt", "dados_pesados",
            )
        }
        for e in indice
    ]
    caminho = SAIDA / "eclipses-index.json"
    caminho.write_text(json.dumps(leve, ensure_ascii=False, separators=(",", ":")))
    print(f"\ngravado {caminho.name}: {len(leve)} eclipses, {caminho.stat().st_size / 1e3:.0f} kB")

    # Detalhe por eclipse, incluindo os elementos besselianos para o browser.
    for eclipse in indice:
        pasta = SAIDA / eclipse["id"]
        pasta.mkdir(exist_ok=True)
        (pasta / "eclipse.json").write_text(
            json.dumps(eclipse, ensure_ascii=False, separators=(",", ":"))
        )
    print(f"gravadas {len(indice)} fichas em {SAIDA}")

    pesados = sum(1 for e in indice if e["dados_pesados"])
    com_faixa = sum(1 for e in indice if e["pt"]["faixa_central"])
    print(f"\n{pesados} eclipses acima do limiar de dados pesados")
    print(f"{com_faixa} com faixa central sobre territorio portugues")
    return 0


if __name__ == "__main__":
    sys.exit(main())
