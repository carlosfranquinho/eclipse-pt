"""Escreve, em portugues, o paragrafo de abertura de cada ficha lunar.

O irmao de `build_text.py`, com as mesmas duas regras: o texto sai nos dois
tempos verbais, porque metade do catalogo ainda nao aconteceu, e cada frase tem
variantes escolhidas por um gerador semeado com o identificador do eclipse, para
mil e setecentas fichas nao dizerem todas a mesma coisa pela mesma ordem.

O vocabulario e que e outro. Num eclipse solar conta-se onde a sombra passou; num
eclipse lunar nao ha onde, ha quando: a que horas da noite, com a Lua a que
altura, e se ela ja vinha eclipsada quando nasceu. E ha a cor, que e a unica
coisa que um eclipse lunar tem e um solar nao: a Lua dentro da umbra nao
desaparece, fica vermelha, iluminada pela luz que a atmosfera da Terra lhe
desvia.

    uv run python pipeline/build_text_lua.py

Correr depois de `build_index_lua.py`, que reescreve as fichas e leva o texto com
ele.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DADOS = RAIZ / "site" / "public" / "data" / "lua"
INDICE = RAIZ / "site" / "public" / "data" / "eclipses-lua-index.json"

MESES = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)

NOMES_TERRITORIO = {
    "continente": "no continente",
    "acores": "nos Açores",
    "madeira": "na Madeira",
}

VERBOS = {
    "passado": {
        "houve": "houve",
        "foi": "foi",
        "esteve": "esteve",
        "entrou": "entrou",
        "chegou": "chegou",
        "durou": "durou",
        "nasceu": "nasceu",
        "poe_se": "pôs-se",
        "ganhou": "ganhou",
        "atravessou": "atravessou",
        "viu": "viu",
        "viu_se_todo": "viu-se do princípio ao fim",
        "ficou": "ficou",
        "escondeu": "escondeu",
    },
    "futuro": {
        "houve": "haverá",
        "foi": "será",
        "esteve": "estará",
        "entrou": "entrará",
        "chegou": "chegará",
        "durou": "durará",
        "nasceu": "nascerá",
        "poe_se": "pôr-se-á",
        "ganhou": "ganhará",
        "atravessou": "atravessará",
        "viu": "verá",
        "viu_se_todo": "ver-se-á do princípio ao fim",
        "ficou": "ficará",
        "escondeu": "esconderá",
    },
}

TIPOS = {
    "total": "um eclipse total da Lua",
    "parcial": "um eclipse parcial da Lua",
    "penumbral": "um eclipse penumbral da Lua",
}

TIPOS_LOCAIS = {
    "total": "total",
    "parcial": "parcial",
    "penumbral": "apenas penumbral",
}


def maiuscula(texto: str) -> str:
    return texto[:1].upper() + texto[1:]


def data_por_extenso(iso: str) -> str:
    ano, mes, dia = (int(parte) for parte in iso.split("-"))
    return f"{dia} de {MESES[mes - 1]} de {ano}"


def hora_da_noite(hora: str) -> str:
    """A que horas da noite, dito como quem conta e nao como quem tabela.

    Um eclipse lunar so se ve com a Lua no ceu, portanto e sempre de noite, o
    que da a esta escala um significado que a solar nao tem: a diferenca entre
    um eclipse ao inicio da noite, que toda a gente ve, e um as quatro da manha,
    que quase ninguem viu.
    """
    horas = int(hora[:2])
    if horas < 3:
        return "a meio da noite"
    if horas < 6:
        return "na madrugada"
    if horas < 9:
        return "ao amanhecer"
    if horas < 15:
        # Raro mas possivel: a Lua ainda por cima do horizonte depois do nascer
        # do Sol, com o eclipse a decorrer a luz do dia.
        return "na manhã"
    if horas < 18:
        return "ao fim do dia"
    if horas < 22:
        return "ao anoitecer"
    return "perto da meia-noite"


def altura_por_extenso(graus: float) -> str:
    if graus < 5:
        return "com a Lua rente ao horizonte"
    if graus < 20:
        return f"com a Lua baixa, a {round(graus)} graus do horizonte"
    if graus < 50:
        return f"com a Lua a {round(graus)} graus de altura"
    return "com a Lua bem alta no céu"


def duracao_por_extenso(minutos: float) -> str:
    total = round(minutos)
    if total < 60:
        return "um minuto" if total == 1 else f"{total} minutos"
    horas, resto = divmod(total, 60)
    parte_horas = "uma hora" if horas == 1 else f"{horas} horas"
    if resto == 0:
        return parte_horas
    parte_minutos = "um minuto" if resto == 1 else f"{resto} minutos"
    return f"{parte_horas} e {parte_minutos}"


def percentagem_por_extenso(fraccao: float) -> str:
    return f"{round(fraccao * 100)} por cento"


def _territorio_principal(ficha: dict) -> tuple[str, dict] | None:
    """Onde o eclipse se viu melhor, que e por onde o texto comeca."""
    visiveis = [
        (nome, dados)
        for nome, dados in ficha["territorios"].items()
        if dados.get("visivel")
    ]
    if not visiveis:
        return None
    return max(visiveis, key=lambda par: par[1]["magnitude_penumbral_visivel"])


def _abertura(ficha: dict, dados: dict, v: dict, sorte: random.Random) -> str:
    data = data_por_extenso(ficha["data_juliana"] or ficha["data_gregoriana"])
    quando = hora_da_noite(dados["contactos"]["maximo"]["hora_local"])
    tipo = TIPOS[ficha["tipo"]]
    visto = dados["tipo_visto"]

    if visto == ficha["tipo"]:
        return sorte.choice(
            [
                f"{maiuscula(quando)} de {data} {v['houve']} {tipo}, visível de"
                " Portugal.",
                f"{maiuscula(quando)} de {data}, {tipo} {v['foi']} visível de"
                " Portugal.",
            ]
        )

    # O eclipse foi uma coisa no ceu e outra vista daqui, e e a diferenca que
    # interessa a quem esta ca.
    return sorte.choice(
        [
            f"{maiuscula(quando)} de {data} {v['houve']} {tipo}, que de Portugal"
            f" se {v['viu']} como {TIPOS_LOCAIS[visto]}.",
            f"{maiuscula(quando)} de {data} {v['houve']} {tipo}. Daqui, a fase"
            f" que se {v['chegou']} a ver {v['foi']} {TIPOS_LOCAIS[visto]}.",
        ]
    )


def _o_que_se_viu(ficha: dict, dados: dict, v: dict, sorte: random.Random) -> str:
    """A frase central: a fase mais funda, a altura da Lua e a cor."""
    lugar = dados["lugar"]["nome"]
    altura = altura_por_extenso(dados["contactos"]["maximo"]["altura_graus"])
    visiveis = set(dados["contactos_visiveis"])
    visto = dados["tipo_visto"]

    if visto == "total":
        if {"u2", "u3"} <= visiveis and ficha["duracoes_min"]["total"]:
            duracao = duracao_por_extenso(ficha["duracoes_min"]["total"])
            return sorte.choice(
                [
                    f"Em {lugar}, a Lua {v['esteve']} inteiramente dentro da"
                    f" sombra da Terra durante {duracao}, {altura}, com a cor"
                    " avermelhada que a totalidade lhe dá.",
                    f"A totalidade {v['durou']} {duracao} e {v['foi']} visível"
                    f" de {lugar}, {altura}: a Lua não desaparece, {v['ganhou']}"
                    " o tom de cobre da luz que a atmosfera da Terra lhe desvia.",
                ]
            )
        return (
            f"Em {lugar}, a totalidade {v['foi']} visível apenas em parte: o"
            " resto aconteceu com a Lua já abaixo do horizonte."
        )

    if visto == "parcial":
        coberto = percentagem_por_extenso(min(dados["magnitude_umbral_visivel"], 1.0))
        return sorte.choice(
            [
                f"Em {lugar}, a sombra da Terra {v['chegou']} a cobrir"
                f" {coberto} do diâmetro da Lua, {altura}.",
                f"O máximo visível de {lugar} {v['foi']} de {coberto} do"
                f" diâmetro da Lua dentro da umbra, {altura}.",
            ]
        )

    if not ficha["pt"]["perceptivel"]:
        return (
            f"Em {lugar}, a Lua {v['chegou']} apenas à orla exterior da"
            " penumbra, um escurecimento que a olho nu não se distingue de uma"
            " noite qualquer."
        )
    return (
        f"Em {lugar}, a Lua {v['entrou']} fundo na penumbra sem tocar a umbra:"
        f" um escurecimento subtil de um dos bordos, {altura}."
    )


def _na_umbra(dados: dict, momento: dict) -> bool:
    """Se, nesse instante, a Lua ainda tinha um bocado dentro da umbra."""
    contactos = dados["contactos"]
    if "u1" not in contactos or "u4" not in contactos:
        return False
    return contactos["u1"]["jd_ut"] <= momento["jd_ut"] <= contactos["u4"]["jd_ut"]


def _horizonte(dados: dict, v: dict) -> str | None:
    """A Lua que nasce ou se poe a meio do eclipse, que e o caso memoravel."""
    if dados.get("nascer"):
        return (
            f"A Lua {v['nasceu']} já eclipsada, às"
            f" {dados['nascer']['hora_local'][:5]}, e o que veio antes disso"
            f" {v['ficou']} por ver."
        )
    if dados.get("por"):
        estado = (
            "ainda dentro da sombra"
            if _na_umbra(dados, dados["por"])
            else "ainda eclipsada"
        )
        return (
            f"A Lua {v['poe_se']} às {dados['por']['hora_local'][:5]}, {estado},"
            f" e {v['escondeu']} o resto do eclipse."
        )
    return None


def _outros_territorios(ficha: dict, principal: str, v: dict) -> list[str]:
    """Uma frase por territorio que tenha visto outra coisa.

    So se escreve quando ha mesmo diferenca: os Acores estao duas horas de arco a
    oeste, e ha eclipses que dali se veem inteiros e do continente so pela
    metade. Quando os tres territorios veem o mesmo, calar e melhor.
    """
    frases = []
    for nome, dados in ficha["territorios"].items():
        if nome == principal:
            continue
        onde = maiuscula(NOMES_TERRITORIO[nome])
        if not dados.get("visivel"):
            frases.append(f"{onde} não {v['foi']} visível.")
            continue
        principal_dados = ficha["territorios"][principal]
        inteiro_aqui = not dados.get("nascer") and not dados.get("por")
        inteiro_la = not principal_dados.get("nascer") and not principal_dados.get("por")
        if dados["tipo_visto"] == principal_dados["tipo_visto"] and inteiro_aqui:
            # Se o eclipse foi o mesmo e ali nao houve nascer nem por a meio, so
            # ha noticia quando o principal ficou a meio e este nao.
            if not inteiro_la:
                frases.append(f"{onde} o eclipse {v['viu_se_todo']}.")
            continue
        if dados.get("nascer"):
            frases.append(
                f"{onde} a Lua {v['nasceu']} já eclipsada, às"
                f" {dados['nascer']['hora_local'][:5]}."
            )
        elif dados.get("por"):
            frases.append(
                f"{onde} a Lua {v['poe_se']} ainda eclipsada, às"
                f" {dados['por']['hora_local'][:5]}."
            )
        else:
            frases.append(
                f"{onde} o eclipse {v['foi']} {TIPOS_LOCAIS[dados['tipo_visto']]}."
            )
    return frases


def gerar(ficha: dict, tempo: str) -> str:
    principal = _territorio_principal(ficha)
    if principal is None:
        return ""
    territorio, dados = principal
    v = VERBOS[tempo]

    frases = [
        _abertura(ficha, dados, v, random.Random(ficha["id"])),
        _o_que_se_viu(ficha, dados, v, random.Random(ficha["id"] + "viu")),
        _horizonte(dados, v),
        *_outros_territorios(ficha, territorio, v),
    ]
    return " ".join(frase for frase in frases if frase)


def main() -> int:
    if not INDICE.exists():
        raise SystemExit(f"{INDICE} em falta. Correr build_index_lua.py antes.")

    indice = json.loads(INDICE.read_text())
    for entrada in indice:
        caminho = DADOS / entrada["id"] / "eclipse.json"
        ficha = json.loads(caminho.read_text())
        ficha["texto_gerado"] = {
            "passado": gerar(ficha, "passado"),
            "futuro": gerar(ficha, "futuro"),
        }
        caminho.write_text(json.dumps(ficha, ensure_ascii=False, separators=(",", ":")))

    print(f"texto gerado para {len(indice)} fichas lunares")
    for exemplo in ("2025-09-07", "2029-06-26"):
        pasta = DADOS / exemplo
        if pasta.exists():
            ficha = json.loads((pasta / "eclipse.json").read_text())
            print(f"\n{exemplo}:\n " + ficha["texto_gerado"]["passado"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
