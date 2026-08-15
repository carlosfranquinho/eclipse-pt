"""Escreve, em portugues, o paragrafo de abertura de cada ficha.

Os numeros ja estao todos calculados; o que falta e dize-los. Este passo le as
fichas geradas por `build_index.py` e acrescenta-lhes um campo `texto_gerado`
com um paragrafo que resume o eclipse: quando foi, o que se viu, onde foi mais
fundo, por onde passou a faixa e o que apanharam as ilhas.

Duas decisoes que explicam a forma do modulo:

O tempo verbal. O catalogo vai de 1500 a 2100, e metade dele ainda nao aconteceu.
Um texto so, escrito no passado, envelheceria ao contrario. Gera-se por isso o
mesmo paragrafo nos dois tempos, e a ficha escolhe o que serve a data da build.

A variedade. Trezentas fichas com a mesma frase seriam trezentas fichas ilegiveis.
Cada frase tem duas ou tres formas alternativas, escolhidas por um gerador
aleatorio semeado com o identificador do eclipse: varia de eclipse para eclipse e
nunca varia entre execucoes, que e o que permite commitar o resultado.

    uv run python pipeline/build_text.py

Correr depois de `build_index.py`, que reescreve as fichas e leva o texto com ele.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DADOS = RAIZ / "site" / "public" / "data"

MESES = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)

NOMES_TERRITORIO = {
    "continente": "no continente",
    "acores": "nos Açores",
    "madeira": "na Madeira",
}

# Conjugacoes usadas nas frases, para o mesmo texto sair no passado e no futuro.
VERBOS = {
    "passado": {
        "houve": "houve",
        "atravessou": "atravessou",
        "foi": "foi",
        "cobriu": "cobriu",
        "tapou": "tapou",
        "passou": "passou",
        "chegou": "chegou",
        "durou": "durou",
    },
    "futuro": {
        "houve": "haverá",
        "atravessou": "atravessará",
        "foi": "será",
        "cobriu": "cobrirá",
        "tapou": "tapará",
        "passou": "passará",
        "chegou": "chegará",
        "durou": "durará",
    },
}

TIPOS = {
    "total": "um eclipse total do Sol",
    "anular": "um eclipse anular do Sol",
    "hibrido": "um eclipse híbrido do Sol",
    "parcial": "um eclipse parcial do Sol",
}


def maiuscula(texto: str) -> str:
    """Primeira letra em maiuscula, e so essa.

    O `capitalize()` do Python poe o resto em minusculas, e "ao por do Sol"
    ficaria "Ao por do sol". O Sol e nome proprio.
    """
    return texto[:1].upper() + texto[1:]


def so_concelho(nome: str | None) -> str | None:
    """"Ovar, Aveiro" fica "Ovar".

    O formato "Concelho, Distrito" e a convencao dos dados, mas em prosa o
    distrito so estorva, e em Braganca daria "Braganca, Braganca".
    """
    return nome.split(",")[0].strip() if nome else None


def data_por_extenso(iso: str) -> str:
    ano, mes, dia = (int(parte) for parte in iso.split("-"))
    return f"{dia} de {MESES[mes - 1]} de {ano}"


def periodo_do_dia(hora: str, alt_sol: float) -> str:
    """Como se refere a hora do maximo sem a dizer em numeros.

    Com o Sol quase no horizonte, o que importa nao e a hora e sim que o eclipse
    apanhou o nascer ou o por do Sol, que e a circunstancia mais memoravel que um
    eclipse pode ter.
    """
    horas = int(hora[:2])
    if alt_sol < 7:
        return "ao nascer do Sol" if horas < 12 else "ao pôr do Sol"
    if horas < 7:
        return "ao amanhecer"
    if horas < 12:
        return "na manhã"
    if horas < 14:
        return "por volta do meio-dia"
    if horas < 17:
        return "a meio da tarde"
    if horas < 20:
        return "ao fim da tarde"
    return "ao anoitecer"


def regiao(lat: float, territorio: str) -> str:
    """Onde, em linguagem corrente."""
    if territorio != "continente":
        return NOMES_TERRITORIO[territorio]
    if lat >= 40.8:
        return "no Norte do país"
    if lat >= 39.2:
        return "no Centro do país"
    if lat >= 38.2:
        return "na região de Lisboa"
    return "no Sul do país"


def altura_por_extenso(graus: float) -> str:
    """A altura do Sol dita como quem aponta para o ceu."""
    if graus < 2:
        return "com o Sol praticamente no horizonte"
    return f"com o Sol a {round(graus)} graus acima do horizonte"


def duracao_por_extenso(segundos: float) -> str:
    total = round(segundos)
    if total < 1:
        # Acontece de facto: em 1912 a fase anular na Madeira durou tres decimos
        # de segundo. "0 segundos" seria uma maneira infeliz de o dizer.
        return "menos de um segundo"
    if total < 60:
        return f"{total} segundos" if total != 1 else "um segundo"
    minutos, resto = divmod(total, 60)
    parte_minutos = "um minuto" if minutos == 1 else f"{minutos} minutos"
    if resto == 0:
        return parte_minutos
    parte_segundos = "um segundo" if resto == 1 else f"{resto} segundos"
    return f"{parte_minutos} e {parte_segundos}"


def percentagem_por_extenso(fraccao: float) -> str:
    return f"{round(fraccao * 100)} por cento"


def concordar(quantidade: int, singular: str, plural: str) -> str:
    return f"1 {singular}" if quantidade == 1 else f"{quantidade} {plural}"


def _territorio_principal(ficha: dict) -> tuple[str, dict] | None:
    """O territorio onde o eclipse foi mais fundo, que e o que abre o texto."""
    visiveis = [
        (nome, dados)
        for nome, dados in ficha["territorios"].items()
        if dados.get("visivel")
    ]
    if not visiveis:
        return None
    return max(visiveis, key=lambda par: par[1]["magnitude_max"])


def _abertura(ficha: dict, dados: dict, territorio: str, v: dict, sorte: random.Random) -> str:
    data = data_por_extenso(
        ficha["data_juliana"] or ficha["data_gregoriana"]
    )
    quando = periodo_do_dia(dados["maximo_local"], dados["alt_sol_graus"])
    tipo = TIPOS[ficha["tipo"]]
    onde = regiao(dados["local_mais_fundo"]["lat"], territorio)

    if dados["faixa_central"]:
        faixa = (
            "a faixa de totalidade"
            if dados["tipo_local"] == "total"
            else "a faixa de anularidade"
        )
        return sorte.choice(
            [
                f"{maiuscula(quando)} de {data} {v['houve']} {tipo},"
                f" com {faixa} a passar {onde}.",
                f"{maiuscula(quando)} de {data}, {faixa} de {tipo}"
                f" {v['atravessou']} território português, {onde}.",
            ]
        )

    return sorte.choice(
        [
            f"{maiuscula(quando)} de {data} {v['houve']} {tipo},"
            f" visto de Portugal como um eclipse parcial.",
            f"{maiuscula(quando)} de {data}, {tipo} {v['cobriu']}"
            f" parte do disco solar visto de Portugal.",
        ]
    )


def _mais_fundo(dados: dict, v: dict, sorte: random.Random) -> str:
    lugar = so_concelho(dados["local_mais_fundo"]["nome"]) or "território português"
    altura = altura_por_extenso(dados["alt_sol_graus"])

    if dados["tipo_local"] == "total" and dados["duracao_central_s"]:
        duracao = duracao_por_extenso(dados["duracao_central_s"])
        return sorte.choice(
            [
                f"Em {lugar}, onde {v['foi']} mais fundo, a Lua {v['tapou']}"
                f" o disco solar por completo durante {duracao}, {altura}.",
                f"O eclipse {v['foi']} mais fundo em {lugar}: {duracao}"
                f" de totalidade, {altura}.",
            ]
        )

    if dados["tipo_local"] == "anular" and dados["duracao_central_s"]:
        duracao = duracao_por_extenso(dados["duracao_central_s"])
        return (
            f"Em {lugar}, onde {v['foi']} mais fundo, o anel de luz"
            f" {v['durou']} {duracao}, {altura}."
        )

    coberto = percentagem_por_extenso(dados["obscuracao_max"])
    return sorte.choice(
        [
            f"Em {lugar}, onde {v['foi']} mais fundo, a Lua {v['chegou']} a"
            f" cobrir {coberto} do disco solar, {altura}.",
            f"O máximo {v['foi']} em {lugar}, com {coberto} do Sol coberto e"
            f" {altura.replace('com o Sol ', 'o astro ')}.",
        ]
    )


def _faixa(dados: dict, concelhos: int | None, v: dict) -> str | None:
    """Por onde entrou e saiu a faixa central, e quantos concelhos apanhou."""
    if not dados["faixa_central"]:
        return None

    entrada = so_concelho((dados.get("faixa_entrada") or {}).get("nome"))
    saida = so_concelho((dados.get("faixa_saida") or {}).get("nome"))
    if not entrada or not saida:
        return None

    quantos = (
        f", atravessando {concordar(concelhos, 'concelho', 'concelhos')}"
        if concelhos
        else ""
    )
    if entrada == saida:
        return f"A faixa {v['passou']} por {entrada}{quantos}."
    return f"A faixa {v['passou']} por {entrada} e por {saida}{quantos}."


def _outros_territorios(ficha: dict, principal: str, v: dict) -> list[str]:
    """Uma frase por territorio que tambem viu alguma coisa.

    Nao se resume tudo numa frase so porque os casos sao diferentes de mais: os
    Acores podem apanhar uma parcial rasante enquanto a Madeira apanha um anel.
    """
    frases = []
    for nome, dados in ficha["territorios"].items():
        if nome == principal or not dados.get("visivel"):
            continue

        onde = maiuscula(NOMES_TERRITORIO[nome])
        if dados["faixa_central"] and dados["tipo_local"] in ("total", "anular"):
            fase = "total" if dados["tipo_local"] == "total" else "anular"
            duracao = dados.get("duracao_central_s")
            quanto = f", por {duracao_por_extenso(duracao)}" if duracao else ""
            frases.append(f"{onde} o eclipse {v['chegou']} a ser {fase}{quanto}.")
        else:
            coberto = percentagem_por_extenso(dados["obscuracao_max"])
            frases.append(f"{onde} o máximo {v['foi']} de {coberto} do disco coberto.")
    return frases


def gerar(ficha: dict, concelhos: int | None, tempo: str) -> str:
    """O paragrafo completo, no tempo verbal pedido."""
    principal = _territorio_principal(ficha)
    if principal is None:
        return ""
    territorio, dados = principal

    v = VERBOS[tempo]
    # A semente junta o identificador e o tempo verbal para as duas versoes
    # escolherem as mesmas variantes e dizerem a mesma coisa.
    sorte = random.Random(ficha["id"])

    frases = [
        _abertura(ficha, dados, territorio, v, sorte),
        _mais_fundo(dados, v, random.Random(ficha["id"] + "fundo")),
        _faixa(dados, concelhos, v),
        *_outros_territorios(ficha, territorio, v),
    ]
    return " ".join(frase for frase in frases if frase)


def main() -> int:
    if not DADOS.exists():
        raise SystemExit(f"{DADOS} em falta. Correr build_index.py antes.")

    indice = json.loads((DADOS / "eclipses-index.json").read_text())
    escritas = 0
    for entrada in indice:
        pasta = DADOS / entrada["id"]
        caminho = pasta / "eclipse.json"
        ficha = json.loads(caminho.read_text())

        municipios = pasta / "municipios.json"
        concelhos = (
            json.loads(municipios.read_text())["total"] if municipios.exists() else None
        )

        ficha["texto_gerado"] = {
            "passado": gerar(ficha, concelhos, "passado"),
            "futuro": gerar(ficha, concelhos, "futuro"),
        }
        caminho.write_text(
            json.dumps(ficha, ensure_ascii=False, separators=(",", ":"))
        )
        escritas += 1

    print(f"texto gerado para {escritas} fichas")
    exemplo = json.loads((DADOS / "1900-05-28" / "eclipse.json").read_text())
    print("\n1900-05-28:\n " + exemplo["texto_gerado"]["passado"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
