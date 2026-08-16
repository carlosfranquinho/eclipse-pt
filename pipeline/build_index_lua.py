"""Constroi o indice de eclipses lunares visiveis em Portugal.

Um eclipse lunar e o mesmo para toda a gente: nao ha faixa a atravessar o pais
nem magnitude que mude de concelho para concelho. O que muda com o lugar e uma
coisa so, e e decisiva: se a Lua estava acima do horizonte. Um eclipse total
soberbo, se acontecer as duas da tarde, daqui nao se ve nada.

Por isso este pipeline nao varre grelhas: acompanha cada eclipse contacto a
contacto num ponto de referencia de cada territorio, e escreve o que dali se via.
Onde o solar diz "em que concelho foi mais fundo", o lunar diz "a Lua ja estava
no ceu quando comecou, ou nasceu a meio".

Escreve `eclipses-lua-index.json` para a lista e `lua/<id>/eclipse.json` para
cada ficha, com a mesma divisao de peso do lado solar.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

import calendario as cal
import lua

RAIZ = Path(__file__).resolve().parents[1]
CANON = Path(__file__).parent / "cache" / "canon" / "canon-lua.json"
SAIDA = RAIZ / "site" / "public" / "data"
PASTA_LUA = SAIDA / "lua"

# O ponto de referencia de cada territorio. As horas e as alturas de uma ficha
# sao as deste ponto, e a ficha di-lo. Dentro do continente a diferenca de horas
# entre Bragança e Sagres nao chega a um quarto de hora, e so importa quando a
# Lua esta mesmo a nascer ou a por-se; entre arquipelagos importa muito, e por
# isso e que sao tres e nao um.
LUGARES = {
    "continente": {"nome": "Lisboa", "lat": 38.7223, "lon": -9.1393},
    "acores": {"nome": "Ponta Delgada", "lat": 37.7412, "lon": -25.6756},
    "madeira": {"nome": "Funchal", "lat": 32.6669, "lon": -16.9241},
}

# Ordem em que os contactos acontecem, para percorrer o eclipse do principio ao
# fim sem depender da ordem por que um dicionario os guarda.
ORDEM_DOS_CONTACTOS = ("p1", "u1", "u2", "maximo", "u3", "u4", "p4")

# Nomes por extenso, para a ficha nao ter de os saber de cor.
NOMES_DOS_CONTACTOS = {
    "p1": "inicio do eclipse penumbral",
    "u1": "inicio do eclipse parcial",
    "u2": "inicio da totalidade",
    "maximo": "maximo do eclipse",
    "u3": "fim da totalidade",
    "u4": "fim do eclipse parcial",
    "p4": "fim do eclipse penumbral",
}

# Uma Lua a menos de meio grau do horizonte esta atras dos telhados, da serra ou
# da bruma, e na pratica nao se ve. Zero graus seria a definicao geometrica; meio
# grau e a honesta. Abaixo disto conta-se como nao visivel.
ALTURA_MINIMA_VISIVEL = 0.5

# A magnitude penumbral abaixo da qual nem quem sabe onde olhar nota alguma
# coisa. A penumbra e um degrade suave e so o seu bordo interior escurece a Lua
# de forma perceptivel; os eclipses penumbrais rasos existem no papel e nao no
# ceu. Ficam no catalogo, mas assinalados.
MAGNITUDE_PENUMBRAL_PERCEPTIVEL = 0.7


def _altura(jd_td: Any, delta_t_s: float, lugar: dict) -> dict[str, Any]:
    """Altura e azimute da Lua num lugar, num instante de TD.

    A altura devolvida e a topocentrica: a paralaxe baixa a Lua quase um grau
    junto ao horizonte, e e precisamente junto ao horizonte que a diferenca
    decide se um contacto se viu ou nao.
    """
    jd_ut = jd_td - delta_t_s / 86400.0
    aparente = lua.posicoes_aparentes(jd_td)
    no_ceu = lua.altura_e_azimute(
        aparente["ascensao_recta"],
        aparente["declinacao"],
        jd_ut,
        lugar["lat"],
        lugar["lon"],
    )
    return {
        "altura": lua.altura_topocentrica(no_ceu["altura"], aparente["paralaxe"]),
        "azimute": no_ceu["azimute"],
    }


def _acima(jd_td: Any, delta_t_s: float, lugar: dict) -> Any:
    return _altura(jd_td, delta_t_s, lugar)["altura"] >= ALTURA_MINIMA_VISIVEL


# Passo da varredura que procura a janela em que a Lua esteve visivel. Seis
# minutos apanham qualquer nesga de eclipse que valha a pena contar, e a Lua nao
# faz nada de subtil entre duas amostras.
PASSO_DA_VARREDURA_H = 0.1


def _bordo(dentro: float, fora: float, delta_t_s: float, lugar: dict) -> float:
    """Afina, por bisseccao, o instante em que a Lua cruzou o horizonte."""
    for _ in range(30):
        meio = (dentro + fora) / 2.0
        if _acima(meio, delta_t_s, lugar):
            dentro = meio
        else:
            fora = meio
    return (dentro + fora) / 2.0


def janela_visivel(
    inicio: float, fim: float, delta_t_s: float, lugar: dict
) -> tuple[float, float] | None:
    """Entre que instantes do eclipse e que a Lua esteve acima do horizonte.

    Varre o eclipse todo em vez de olhar so para os extremos: ha eclipses em que
    a Lua nasce e se poe dentro do proprio eclipse, e olhar so para o principio e
    para o fim daria os dois abaixo do horizonte e concluiria, ao contrario da
    verdade, que dali nao se viu nada.

    Devolve `None` se a Lua esteve sempre abaixo do horizonte.
    """
    amostras = np.linspace(
        inicio, fim, max(3, int((fim - inicio) * 24.0 / PASSO_DA_VARREDURA_H) + 1)
    )
    acima = np.asarray(_acima(amostras, delta_t_s, lugar))
    if not acima.any():
        return None

    primeira, ultima = int(np.argmax(acima)), int(len(acima) - 1 - np.argmax(acima[::-1]))
    comeco = (
        inicio
        if primeira == 0
        else _bordo(amostras[primeira], amostras[primeira - 1], delta_t_s, lugar)
    )
    termo = (
        fim
        if ultima == len(acima) - 1
        else _bordo(amostras[ultima], amostras[ultima + 1], delta_t_s, lugar)
    )
    return float(comeco), float(termo)


def _momento(jd_td: float, delta_t_s: float, lugar: dict, territorio: str) -> dict:
    """Um instante do eclipse, dito de todas as maneiras que a ficha precisa."""
    jd_ut = jd_td - delta_t_s / 86400.0
    hora = cal.hora_local(jd_ut, lugar["lon"], territorio)
    no_ceu = _altura(jd_td, delta_t_s, lugar)
    altura = float(no_ceu["altura"])
    return {
        "jd_ut": round(jd_ut, 6),
        "hora_local": hora["hora"],
        "data_local": hora["data"],
        "sistema_hora": hora["sistema"],
        "designacao_fuso": hora["designacao_fuso"],
        "hora_ut": cal.jd_para_civil(jd_ut, gregoriano=True).iso_hora(),
        "altura_graus": round(altura, 1),
        "azimute_graus": round(float(no_ceu["azimute"]), 1),
        "acima_do_horizonte": altura >= ALTURA_MINIMA_VISIVEL,
    }


def _tipo_visto(magnitude_umbral: float, magnitude_penumbral: float) -> str:
    """O que um observador teria visto, dada a fase mais funda que apanhou."""
    if magnitude_umbral >= 1.0:
        return "total"
    if magnitude_umbral > 0.0:
        return "parcial"
    if magnitude_penumbral > 0.0:
        return "penumbral"
    return "nenhum"


def avaliar_territorio(
    elementos: dict, contactos: dict[str, float], territorio: str
) -> dict:
    """O que se viu deste eclipse no ponto de referencia de um territorio."""
    lugar = LUGARES[territorio]
    delta_t = elementos["delta_t_s"]
    inicio, fim = contactos["p1"], contactos["p4"]

    janela = janela_visivel(inicio, fim, delta_t, lugar)
    if janela is None:
        return {"visivel": False, "lugar": lugar}
    comeco, termo = janela

    momentos = {
        nome: _momento(contactos[nome], delta_t, lugar, territorio)
        for nome in ORDEM_DOS_CONTACTOS
        if nome in contactos
    }

    # A Lua pode nascer ou por-se a meio do eclipse, e sao esses os eclipses de
    # que vale a pena falar: uma Lua que aparece no horizonte ja mordida e uma
    # imagem que nao se esquece.
    nasceu = bool(comeco > inicio)
    poe_se = bool(termo < fim)

    # A magnitude cresce ate ao maximo e decresce a seguir, portanto a fase mais
    # funda que dali se viu e a do maximo, se ele apanhou a Lua no ceu, ou a do
    # extremo da janela mais proximo dele.
    instante_mais_fundo = min(max(contactos["maximo"], comeco), termo)
    magnitudes = lua.magnitudes_no_instante(elementos, instante_mais_fundo)
    umbral = float(magnitudes["umbral"])
    penumbral = float(magnitudes["penumbral"])

    ficha = {
        "visivel": True,
        "lugar": lugar,
        "contactos": momentos,
        "contactos_visiveis": [
            nome for nome in ORDEM_DOS_CONTACTOS
            if nome in momentos and momentos[nome]["acima_do_horizonte"]
        ],
        "tipo_visto": _tipo_visto(umbral, penumbral),
        "magnitude_umbral_visivel": round(max(umbral, 0.0), 4),
        "magnitude_penumbral_visivel": round(max(penumbral, 0.0), 4),
        "altura_maxima_graus": round(
            max(m["altura_graus"] for m in momentos.values()), 1
        ),
        "nasceu_eclipsada": nasceu,
        "poe_se_eclipsada": poe_se,
    }
    if nasceu:
        ficha["nascer"] = _momento(comeco, delta_t, lugar, territorio)
    if poe_se:
        ficha["por"] = _momento(termo, delta_t, lugar, territorio)
    return ficha


def main() -> int:
    dados = json.loads(CANON.read_text())
    eclipses = dados["eclipses"]
    print(f"{len(eclipses)} eclipses lunares no catalogo")

    indice = []
    for numero, eclipse in enumerate(eclipses, 1):
        if numero % 500 == 0:
            print(f"  {numero}/{len(eclipses)}")

        jd_maximo = cal.jd_maximo_td_lua(eclipse)
        elementos = lua.elementos_do_eclipse(
            jd_maximo,
            eclipse["gamma"],
            eclipse["maximo"]["duracao_penumbral_min"],
            eclipse["delta_t_s"],
        )
        contactos = lua.instantes_dos_contactos(elementos)

        por_territorio = {
            territorio: avaliar_territorio(elementos, contactos, territorio)
            for territorio in LUGARES
        }
        visiveis = {n: t for n, t in por_territorio.items() if t["visivel"]}
        if not visiveis:
            continue

        jd_ut = jd_maximo - eclipse["delta_t_s"] / 86400.0
        gregoriana = cal.jd_para_civil(jd_ut, gregoriano=True)
        juliana = cal.jd_para_civil(jd_ut, gregoriano=False)
        vigente = cal.calendario_vigente(jd_ut)

        mais_fundo = max(
            visiveis.values(), key=lambda t: t["magnitude_penumbral_visivel"]
        )

        indice.append(
            {
                "id": gregoriana.iso_data(),
                "familia": "lunar",
                "data_gregoriana": gregoriana.iso_data(),
                "data_juliana": juliana.iso_data() if vigente == "juliano" else None,
                "calendario_vigente_pt": vigente,
                "tipo": eclipse["tipo"],
                "tipo_canon": eclipse["tipo_canon"],
                "saros": eclipse["saros"],
                "gamma": eclipse["gamma"],
                "magnitude_umbral": eclipse["magnitude_umbral"],
                "magnitude_penumbral": eclipse["magnitude_penumbral"],
                "delta_t_s": eclipse["delta_t_s"],
                "maximo_global_ut": gregoriana.iso_hora(),
                "duracoes_min": {
                    "penumbral": eclipse["maximo"]["duracao_penumbral_min"],
                    "parcial": eclipse["maximo"]["duracao_parcial_min"],
                    "total": eclipse["maximo"]["duracao_total_min"],
                },
                "pt": {
                    # O tipo do eclipse e o que ele foi no ceu; este e o que se
                    # viu daqui. Um total pode nao passar de parcial em Portugal
                    # se a Lua se puser a meio, e e isso que interessa a quem
                    # esta ca.
                    "tipo_local": mais_fundo["tipo_visto"],
                    "magnitude_umbral": mais_fundo["magnitude_umbral_visivel"],
                    "magnitude_penumbral": mais_fundo["magnitude_penumbral_visivel"],
                    "perceptivel": (
                        mais_fundo["magnitude_umbral_visivel"] > 0.0
                        or mais_fundo["magnitude_penumbral_visivel"]
                        >= MAGNITUDE_PENUMBRAL_PERCEPTIVEL
                    ),
                    "territorios_visiveis": sorted(visiveis),
                    "nasceu_eclipsada": any(
                        t["nasceu_eclipsada"] for t in visiveis.values()
                    ),
                    "poe_se_eclipsada": any(
                        t["poe_se_eclipsada"] for t in visiveis.values()
                    ),
                },
                "territorios": por_territorio,
                "elementos": {
                    chave: round(valor, 8) for chave, valor in elementos.items()
                },
            }
        )

    PASTA_LUA.mkdir(parents=True, exist_ok=True)

    leve = [
        {
            chave: eclipse[chave]
            for chave in (
                "id", "familia", "data_gregoriana", "data_juliana",
                "calendario_vigente_pt", "tipo", "saros", "pt",
            )
        }
        for eclipse in indice
    ]
    caminho = SAIDA / "eclipses-lua-index.json"
    caminho.write_text(json.dumps(leve, ensure_ascii=False, separators=(",", ":")))
    print(
        f"\ngravado {caminho.name}: {len(leve)} eclipses visiveis de Portugal, "
        f"{caminho.stat().st_size / 1e3:.0f} kB"
    )

    conhecidos = {eclipse["id"] for eclipse in indice}
    for pasta in sorted(PASTA_LUA.iterdir()):
        if pasta.is_dir() and pasta.name not in conhecidos:
            for ficheiro in pasta.iterdir():
                ficheiro.unlink()
            pasta.rmdir()
            print(f"removida a pasta orfa lua/{pasta.name}")

    for eclipse in indice:
        pasta = PASTA_LUA / eclipse["id"]
        pasta.mkdir(exist_ok=True)
        (pasta / "eclipse.json").write_text(
            json.dumps(eclipse, ensure_ascii=False, separators=(",", ":"))
        )
    print(f"gravadas {len(indice)} fichas em {PASTA_LUA}")

    # As contagens da Lua juntam-se as do Sol no mesmo ficheiro de metadados, que
    # o `build_index.py` escreve antes deste correr.
    catalogo = SAIDA / "catalogo.json"
    if catalogo.exists():
        metadados = json.loads(catalogo.read_text())
        metadados["lua"] = {
            "total": len(indice),
            "no_catalogo": len(eclipses),
            "perceptiveis": sum(1 for e in indice if e["pt"]["perceptivel"]),
        }
        catalogo.write_text(json.dumps(metadados, ensure_ascii=False, indent=1))

    contagem: dict[str, int] = {}
    for eclipse in indice:
        contagem[eclipse["pt"]["tipo_local"]] = (
            contagem.get(eclipse["pt"]["tipo_local"], 0) + 1
        )
    print("vistos de Portugal:", ", ".join(f"{k}={v}" for k, v in sorted(contagem.items())))
    print(f"{sum(1 for e in indice if not e['pt']['perceptivel'])} dificeis de notar")
    return 0


if __name__ == "__main__":
    sys.exit(main())
