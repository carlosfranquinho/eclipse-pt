"""Gera a cartografia de cada eclipse: linha central, faixa e isomagnitudes.

So corre para os eclipses acima do limiar de dados pesados. Os restantes ficam no
indice com os numeros essenciais, sem cartografia propria, porque uma parcial de
dez por cento nao justifica meio megabyte de contornos.

Tudo aqui sai dos elementos besselianos por via analitica. Nao ha varrimento de
grelha para tracar a faixa, e por isso nao ha o problema classico da faixa a sair
aos blocos quando o passo temporal e grande demais.
"""

from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from contourpy import contour_generator
from shapely.geometry import LineString, MultiPolygon, Polygon, mapping, shape
from shapely.ops import unary_union

import besselian as b

RAIZ = Path(__file__).resolve().parents[1]
DADOS = RAIZ / "site" / "public" / "data"

# Janela cartografica: a Peninsula Iberica mais o Atlantico ate aos Acores, para
# a linha central chegar ao mapa inteira em vez de aparecer cortada a meio.
JANELA = {"lat_min": 25.0, "lat_max": 50.0, "lon_min": -40.0, "lon_max": 5.0}

# Caixas por territorio. Servem para saber onde procurar a faixa, nao para
# desenhar as zonas de magnitude, que sao calculadas de uma vez sobre a caixa
# toda do mapa.
CAIXAS = {
    "continente": (36.0, 43.0, -10.5, -5.5),
    "acores": (36.0, 40.5, -32.0, -24.0),
    "madeira": (29.5, 33.8, -18.0, -15.0),
}

# A caixa sobre a qual se desenham as zonas de magnitude: o pais todo, com o
# Atlantico pelo meio, e uma margem larga a volta.
#
# A margem nao e decorativa. O mapa abre enquadrado no pais inteiro, e as zonas
# tem de sair do ecra por todos os lados: se acabassem a vista, via-se a aresta
# da caixa em vez do fim natural da sombra. Se um dia o enquadramento inicial do
# mapa crescer (site/src/lib/territorios.ts), esta caixa tem de crescer com ele.
CAIXA_DO_MAPA = (30.0, 45.0, -34.5, -3.5)

# Fronteiras das zonas de igual magnitude. Cada par de valores seguidos e uma
# zona sombreada no mapa; a ultima vai do 0,99 ao fim, que num total chega a
# passar de 1. Sao mais apertadas junto ao 1 porque e ai que a diferenca se ve:
# entre 0,2 e 0,5 o dia e o mesmo, entre 0,95 e 0,99 nao e.
#
# Cinco zonas e nao sete: o mapa distingue-as pela transparencia de uma so cor, e
# a olho nao se separam mais do que meia duzia de tons da mesma cor. Com sete, a
# escala deixava de servir para o que serve, que e reconhecer no mapa a zona a
# que cada tom corresponde.
NIVEIS_ISOMAGNITUDE = [0.2, 0.5, 0.8, 0.95, 0.99]
LIMITE_SUPERIOR_ISOMAGNITUDE = 2.0

# Tolerancia de simplificacao dos poligonos de isomagnitude, em graus. Cerca de
# um quilometro: as curvas sao suaves a escala de um pais e sem isto os ficheiros
# triplicavam sem nada mudar no ecra.
TOLERANCIA_ISOMAGNITUDE = 0.02

# Abaixo desta largura, desenhar a faixa como poligono seria uma mentira visual:
# a escala do mapa, um poligono de um quilometro e mais fino que o traco. Nesses
# casos marca-se so a linha central, e a ficha explica porque.
LARGURA_MINIMA_POLIGONO_KM = 2.0

PASSO_LINHA_CENTRAL_S = 20.0
# Sete quilometros. As zonas de magnitude sao manchas suaves a escala de um
# oceano; uma grelha mais fina multiplicava o custo sem mudar o que se ve.
PASSO_GRELHA_ISOMAGNITUDE = 0.06

# De quantos em quantos pontos da grelha se faz o varrimento temporal completo.
# O instante de maximo varia devagar no espaco, por isso basta procura-lo de
# oitenta em oitenta quilometros e deixar o Newton afinar o resto. Sem isto, o
# varrimento sobre a grelha inteira era o custo dominante do pipeline.
PASSO_DA_SONDA = 8


def _na_janela(lat: float, lon: float) -> bool:
    return (
        JANELA["lat_min"] <= lat <= JANELA["lat_max"]
        and JANELA["lon_min"] <= lon <= JANELA["lon_max"]
    )


def linha_central_na_janela(el: b.Elementos) -> list[dict]:
    """Amostra a linha central e devolve os troços que caem na janela do mapa.

    Devolve varios troços porque a linha pode entrar e sair da janela, e uni-los
    daria um segmento a atravessar o mapa por onde a sombra nunca passou.
    """
    passo = PASSO_LINHA_CENTRAL_S / 3600.0
    trocos: list[list[tuple[float, float, float]]] = []
    actual: list[tuple[float, float, float]] = []

    for t in np.arange(-4.0, 4.0 + passo / 2, passo):
        ponto = b.linha_central(el, t)
        if bool(ponto["existe"]):
            lat, lon = float(ponto["lat"]), float(ponto["lon"])
            if _na_janela(lat, lon):
                actual.append((lon, lat, float(t)))
                continue
        if actual:
            trocos.append(actual)
            actual = []
    if actual:
        trocos.append(actual)

    return [
        {
            "coordenadas": [(lon, lat) for lon, lat, _ in troco],
            "t_inicio": troco[0][2],
            "t_fim": troco[-1][2],
        }
        for troco in trocos
        if len(troco) >= 2
    ]


def _pontos_na_terra(contorno: dict) -> list[tuple[float, float]]:
    """Pontos do contorno da umbra que caem na Terra, em ordem, como (lon, lat)."""
    existe = np.asarray(contorno["existe"])
    if not existe.any():
        return []
    return [
        (float(contorno["lon"][i]), float(contorno["lat"][i]))
        for i in np.flatnonzero(existe)
    ]


def _janela_temporal(el: b.Elementos) -> tuple[float, float] | None:
    """Intervalo em que a umbra toca a Terra dentro da janela do mapa.

    Varre-se com passo largo e poucos pontos de contorno, so para delimitar o
    intervalo. O trabalho fino faz-se depois, so onde interessa.

    Nao se usa a linha central para isto. Nos eclipses ao nascer ou ao por do
    Sol, o eixo da sombra falha a Terra enquanto o cone ainda lhe toca junto ao
    limbo, e nesses casos nao ha linha central nenhuma apesar de haver faixa.
    """
    passo = 2.0 / 60.0
    instantes = []
    for t in np.arange(-4.0, 4.0 + passo / 2, passo):
        contorno = b.contorno_sombra(el, t, n_pontos=24)
        if any(_na_janela(lat, lon) for lon, lat in _pontos_na_terra(contorno)):
            instantes.append(float(t))
    if not instantes:
        return None
    return (min(instantes) - passo, max(instantes) + passo)


def faixa_na_janela(
    el: b.Elementos, janela_t: tuple[float, float] | None
) -> tuple[object | None, list[dict]]:
    """Poligono da faixa central dentro da janela, e o perfil de largura.

    A faixa constroi-se de duas maneiras conforme a geometria, e e preciso as
    duas para cobrir todos os casos que Portugal apanha.

    Quando o eixo da sombra atinge a Terra, tracam-se os limites norte e sul e
    ligam-se instantes consecutivos por quadrilateros. Isto resolve o problema
    classico da faixa aos blocos: unir sombras instante a instante so funciona
    enquanto duas sombras consecutivas se sobrepoem, e falha exactamente nos
    casos mais interessantes, como o hibrido de 1912 com um quilometro de
    largura, que saia em dezenas de fragmentos soltos.

    Quando o eixo falha a Terra mas o cone ainda lhe toca de raspao, junto ao
    limbo, nao ha linha central mas ha faixa. Acontece nos eclipses ao nascer ou
    ao por do Sol, e em Portugal nao e raro: 1683, 1842 e 2026 sao todos assim. A
    faixa sai entao do proprio contorno da sombra, fechado pela corda que
    substitui a parte que caiu fora do globo.
    """
    if janela_t is None:
        return None, []

    passo = 20.0 / 3600.0
    perfil = []
    limites_seguidos: list[tuple] = []
    formas = []

    # A fita parte-se em trocos curtos antes de se fazer o poligono. Uma fita
    # que atravesse meio mundo tem curvatura suficiente para se cruzar a si
    # propria, e a reparacao da geometria resolveria isso deitando fora o meio.
    PASSOS_POR_TROCO = 40

    def fechar_fita() -> None:
        """Converte a sequencia de limites acumulada em fitas e guarda-as."""
        if len(limites_seguidos) >= 2:
            for inicio in range(0, len(limites_seguidos) - 1, PASSOS_POR_TROCO):
                troco = limites_seguidos[inicio : inicio + PASSOS_POR_TROCO + 1]
                if len(troco) < 2:
                    continue
                # Esquerda e direita face ao movimento, nao norte e sul: e a
                # unica atribuicao que se mantem coerente quando a sombra vira.
                esquerda = [(lim["esquerda"][1], lim["esquerda"][0]) for lim in troco]
                direita = [(lim["direita"][1], lim["direita"][0]) for lim in troco]
                fita = Polygon(esquerda + list(reversed(direita)))
                if not fita.is_valid:
                    fita = fita.buffer(0)
                if not fita.is_empty:
                    formas.append(fita)
        limites_seguidos.clear()

    for t in np.arange(janela_t[0], janela_t[1] + passo / 2, passo):
        limites = b.limites_faixa(el, t)

        if limites is not None:
            lat_centro, lon_centro = limites["centro"]
            if _na_janela(lat_centro, lon_centro):
                limites_seguidos.append(limites)
                perfil.append(
                    {
                        "t": round(float(t), 5),
                        "lat": round(lat_centro, 4),
                        "lon": round(lon_centro, 4),
                        "largura_km": round(limites["largura_km"], 3),
                        "eixo_na_terra": True,
                    }
                )
                continue
            fechar_fita()
            continue

        # Sem eixo na Terra: aproveita-se a parte do contorno que la esta.
        fechar_fita()
        contorno = b.contorno_sombra(el, t, n_pontos=180)
        pontos = _pontos_na_terra(contorno)
        if len(pontos) < 3:
            continue
        if not any(_na_janela(lat, lon) for lon, lat in pontos):
            continue

        sombra = Polygon(pontos)
        if not sombra.is_valid:
            sombra = sombra.buffer(0)
        if not sombra.is_empty and sombra.area > 0:
            formas.append(sombra)
            centro = sombra.centroid
            perfil.append(
                {
                    "t": round(float(t), 5),
                    "lat": round(float(centro.y), 4),
                    "lon": round(float(centro.x), 4),
                    "largura_km": None,
                    "eixo_na_terra": False,
                }
            )

    fechar_fita()

    if not formas:
        return None, perfil

    faixa = unary_union(formas)
    if not faixa.is_valid:
        faixa = faixa.buffer(0)
    return faixa, perfil


def _distancia_a_portugal_graus(lat: float, lon: float) -> float:
    """Distancia aproximada de um ponto as caixas dos tres territorios, em graus.

    Serve so para ordenar pontos por proximidade, nao para medir. Basta encostar
    o ponto a caixa mais proxima e medir a diferenca.
    """
    melhor = float("inf")
    for lat_min, lat_max, lon_min, lon_max in CAIXAS.values():
        dlat = max(lat_min - lat, 0.0, lat - lat_max)
        dlon = max(lon_min - lon, 0.0, lon - lon_max) * np.cos(np.radians(lat))
        melhor = min(melhor, float(np.hypot(dlat, dlon)))
    return melhor


def _larguras_relevantes(perfil: list[dict]) -> dict:
    """Reduz o perfil de largura aos numeros que a ficha precisa de mostrar.

    Distingue dois casos que se confundem facilmente. Ou a linha central passa
    sobre Portugal, e ha uma largura sobre o pais; ou a linha central passa ao
    largo e so a orla da faixa toca o territorio, como em 2026, em que a
    totalidade apenas roca o extremo nordeste. Dizer "sem largura" no segundo
    caso seria enganador.
    """
    com_largura = [p for p in perfil if p["largura_km"] is not None]
    if not com_largura:
        # Faixa inteiramente sem eixo na Terra: ha sombra, mas nao ha linha
        # central nem largura definida. E o caso dos eclipses rasantes ao nascer
        # ou ao por do Sol, que se desenham como area a mesma.
        return {
            "largura_maxima_km": None,
            "largura_sobre_pt_km": None,
            "linha_central_sobre_pt": False,
            "largura_junto_a_pt_km": None,
            "faixa_desenhavel": bool(perfil),
        }

    sobre_pt = [
        p for p in com_largura
        if _distancia_a_portugal_graus(p["lat"], p["lon"]) == 0.0
    ]
    mais_perto = min(
        com_largura, key=lambda p: _distancia_a_portugal_graus(p["lat"], p["lon"])
    )
    largura_referencia = (
        max(p["largura_km"] for p in sobre_pt) if sobre_pt else mais_perto["largura_km"]
    )

    return {
        "largura_maxima_km": round(max(p["largura_km"] for p in com_largura), 3),
        "largura_sobre_pt_km": round(largura_referencia, 3),
        "linha_central_sobre_pt": bool(sobre_pt),
        "largura_junto_a_pt_km": round(mais_perto["largura_km"], 3),
        "faixa_desenhavel": largura_referencia >= LARGURA_MINIMA_POLIGONO_KM,
    }


def isomagnitudes(el: b.Elementos) -> list[dict]:
    """Zonas de igual magnitude sobre a caixa toda do mapa.

    Sao areas e nao curvas: a leitura pretendida e a de uma sombra que vai
    escurecendo para dentro, a mesma ideia da faixa de totalidade, e nao a de um
    mapa topografico.

    Desenham-se de uma vez sobre o mar e sobre a terra, do Corvo a fronteira, e
    saem do ecra por todos os lados. E o que as torna legiveis: uma zona que se
    interrompesse na costa e recomecasse noutra ilha obrigava o leitor a
    reconstruir a mancha de cabeca, e nao havia como seguir uma faixa da terra
    para o mar. Sai tambem mais barato do que recortar cada uma pelo contorno
    dos territorios.
    """
    lat_min, lat_max, lon_min, lon_max = CAIXA_DO_MAPA
    lats = np.arange(lat_min, lat_max, PASSO_GRELHA_ISOMAGNITUDE)
    lons = np.arange(lon_min, lon_max, PASSO_GRELHA_ISOMAGNITUDE)
    malha_lat, malha_lon = np.meshgrid(lats, lons, indexing="ij")

    # O instante de maximo procura-se a serio numa grelha grossa e afina-se com
    # Newton em todos os pontos. Dar ao Newton um palpite a oitenta quilometros
    # de distancia chega: o instante varia devagar no espaco.
    sonda = b.instante_maximo_em_pontos(
        el,
        malha_lat[::PASSO_DA_SONDA, ::PASSO_DA_SONDA],
        malha_lon[::PASSO_DA_SONDA, ::PASSO_DA_SONDA],
    )
    palpite = np.repeat(
        np.repeat(sonda, PASSO_DA_SONDA, axis=0), PASSO_DA_SONDA, axis=1
    )[: malha_lat.shape[0], : malha_lat.shape[1]]

    instantes = b.instante_maximo_em_pontos(
        el, malha_lat, malha_lon, t_inicial=palpite
    )
    # A maior magnitude que ali se chegou a ver, e nao a do instante de maximo:
    # nos eclipses ao nascer ou ao por do Sol as duas coisas nao sao a mesma.
    magnitudes = b.magnitude_maxima_visivel(el, instantes, malha_lat, malha_lon)

    if magnitudes.max() < NIVEIS_ISOMAGNITUDE[0]:
        return []

    fronteiras = [*NIVEIS_ISOMAGNITUDE, LIMITE_SUPERIOR_ISOMAGNITUDE]
    gerador = contour_generator(
        x=lons, y=lats, z=magnitudes, fill_type="OuterOffset"
    )

    feicoes = []
    for inferior, superior in zip(fronteiras, fronteiras[1:]):
        if magnitudes.max() <= inferior:
            continue

        zona = _zona_entre(gerador, inferior, superior)
        if zona is None:
            continue

        feicoes.append(
            {
                "type": "Feature",
                "properties": {
                    # `magnitude` continua a ser o limite inferior, que e por
                    # onde a zona se identifica e se ordena.
                    "magnitude": inferior,
                    "de": inferior,
                    "ate": superior,
                    "percentagem": round(inferior * 100, 1),
                },
                "geometry": mapping(zona),
            }
        )
    return feicoes


def _zona_entre(gerador, inferior: float, superior: float):
    """A area onde a magnitude fica entre dois niveis, ja simplificada.

    O contourpy devolve cada poligono como um bloco de pontos mais os desvios
    que separam o contorno exterior dos buracos. E precisamente a forma de que a
    shapely precisa, com os buracos a explicar-se sozinhos: a zona de 0,8 a 0,9
    tem um buraco por dentro, que e a zona de 0,9 para cima.
    """
    lista_pontos, lista_desvios = gerador.filled(inferior, superior)

    poligonos = []
    for pontos, desvios in zip(lista_pontos, lista_desvios):
        aneis = [
            pontos[inicio:fim]
            for inicio, fim in zip(desvios, desvios[1:])
            if fim - inicio >= 4
        ]
        if not aneis:
            continue
        poligono = Polygon(aneis[0], aneis[1:])
        if not poligono.is_valid:
            poligono = poligono.buffer(0)
        if not poligono.is_empty:
            poligonos.append(poligono)

    if not poligonos:
        return None

    zona = unary_union(poligonos).simplify(
        TOLERANCIA_ISOMAGNITUDE, preserve_topology=True
    )
    return None if zona.is_empty else zona


def gerar(eclipse_id: str) -> dict:
    pasta = DADOS / eclipse_id
    dados = json.loads((pasta / "eclipse.json").read_text())
    el = b.Elementos.de_dict(dados["elementos"], dados["delta_t_s"])

    resumo = {"id": eclipse_id, "ficheiros": []}

    trocos = linha_central_na_janela(el)
    if trocos:
        colecao = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"t_inicio": t["t_inicio"], "t_fim": t["t_fim"]},
                    "geometry": mapping(LineString(t["coordenadas"])),
                }
                for t in trocos
            ],
        }
        (pasta / "central.geojson").write_text(
            json.dumps(colecao, separators=(",", ":"))
        )
        resumo["ficheiros"].append("central.geojson")

    faixa, perfil = faixa_na_janela(el, _janela_temporal(el))

    resumo.update(_larguras_relevantes(perfil))

    if faixa is not None and not faixa.is_empty:
        geometrias = faixa.geoms if isinstance(faixa, MultiPolygon) else [faixa]
        colecao = {
            "type": "FeatureCollection",
            "properties": {
                "largura_maxima_km": resumo["largura_maxima_km"],
                "largura_sobre_pt_km": resumo["largura_sobre_pt_km"],
                "linha_central_sobre_pt": resumo["linha_central_sobre_pt"],
                # A faixa existe sempre no ficheiro; este campo diz ao frontend se
                # faz sentido desenha-la como area ou se deve mostrar so a linha.
                "desenhavel_como_area": resumo["faixa_desenhavel"],
                "perfil_largura": perfil,
            },
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": mapping(g.simplify(0.001, preserve_topology=True)),
                }
                for g in geometrias
                if not g.is_empty
            ],
        }
        (pasta / "band.geojson").write_text(json.dumps(colecao, separators=(",", ":")))
        resumo["ficheiros"].append("band.geojson")

    feicoes = isomagnitudes(el)
    if feicoes:
        (pasta / "isomag.geojson").write_text(
            json.dumps(
                {"type": "FeatureCollection", "features": feicoes},
                separators=(",", ":"),
            )
        )
        resumo["ficheiros"].append("isomag.geojson")

    return resumo


def main() -> int:
    indice = json.loads((DADOS / "eclipses-index.json").read_text())
    pesados = [e for e in indice if e["dados_pesados"]]
    print(f"{len(pesados)} eclipses acima do limiar, de {len(indice)} no indice")

    sem_poligono = []
    for numero, entrada in enumerate(pesados, 1):
        resumo = gerar(entrada["id"])
        if not resumo["faixa_desenhavel"] and entrada["pt"]["faixa_central"]:
            sem_poligono.append((entrada["id"], resumo["largura_sobre_pt_km"]))
        if numero % 25 == 0:
            print(f"  {numero}/{len(pesados)}")

    if sem_poligono:
        print("\nfaixas demasiado estreitas para poligono, so linha central:")
        for eclipse_id, largura in sem_poligono:
            print(f"  {eclipse_id}: {largura:.2f} km")

    total = sum(
        f.stat().st_size
        for f in DADOS.rglob("*.geojson")
    )
    print(f"\ntotal de cartografia gerada: {total / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
