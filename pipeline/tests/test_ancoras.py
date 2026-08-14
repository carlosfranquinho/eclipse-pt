"""Ancoras portuguesas: eclipses conhecidos que o pipeline tem de reproduzir.

Sao testes de regressao legiveis. Se algum destes falhar, alguma coisa se partiu
de forma visivel para quem conhece a historia destes eclipses.

Nota sobre a ancora de 1764: o plano inicial dizia que o anel passava "sobre a
regiao da Marinha Grande". Nao passa. A linha central entra pela costa sudoeste,
corre para nordeste pelo Alentejo e sai para Espanha perto de Elvas. A Marinha
Grande fica no limite norte da faixa, em fase parcial funda. A ancora aqui
codificada e a trajectoria verificada, nao a do plano inicial.
"""

from __future__ import annotations

import numpy as np
import pytest

import besselian as b

# Coordenadas em graus decimais, latitude e longitude.
LOCAIS = {
    "Ovar": (40.86, -8.62),
    "Faro": (37.02, -7.93),
    "Lisboa": (38.72, -9.14),
    "Porto": (41.15, -8.61),
    "Marinha Grande": (39.75, -8.93),
    "Penafiel": (41.21, -8.28),
    "Braganca": (41.81, -6.76),
    "Sagres": (37.00, -8.94),
}


def elementos(por_data: dict, chave: str) -> b.Elementos:
    e = por_data[chave]
    return b.Elementos.de_dict(e["elementos"], e["delta_t_s"])


def circunstancias(por_data: dict, chave: str, local: str) -> dict:
    lat, lon = LOCAIS[local]
    return b.circunstancias_locais(elementos(por_data, chave), lat, lon)


class TestTotal1900:
    """28 de maio de 1900: a totalidade entra pelo mar e passa em Ovar."""

    def test_totalidade_em_ovar(self, por_data):
        c = circunstancias(por_data, "1900-05-28", "Ovar")
        assert c["tipo"] == "total"
        assert c["magnitude"] == pytest.approx(1.01, abs=0.02)
        assert c["duracao_central_s"] == pytest.approx(89, abs=10)

    def test_parcial_funda_em_faro(self, por_data):
        c = circunstancias(por_data, "1900-05-28", "Faro")
        assert c["tipo"] == "parcial"
        assert c["magnitude"] == pytest.approx(0.91, abs=0.02)

    def test_hora_do_maximo_em_ovar(self, por_data):
        """Maximo pouco depois das 16h UT, ou seja ao fim da tarde em Portugal."""
        el = elementos(por_data, "1900-05-28")
        c = circunstancias(por_data, "1900-05-28", "Ovar")
        ut = el.t0_td + c["t_maximo_td"] - el.delta_t_s / 3600.0
        assert ut == pytest.approx(16.04, abs=0.05)

    def test_sol_alto(self, por_data):
        c = circunstancias(por_data, "1900-05-28", "Ovar")
        assert c["alt_sol"] == pytest.approx(41.7, abs=1.0)


class TestTotal1870:
    """22 de dezembro de 1870: a faixa raspa o Algarve."""

    def test_totalidade_no_algarve(self, por_data):
        for local in ("Faro", "Sagres"):
            c = circunstancias(por_data, "1870-12-22", local)
            assert c["tipo"] == "total", local
            assert c["magnitude"] > 1.0

    def test_norte_fica_de_fora(self, por_data):
        for local in ("Porto", "Ovar", "Braganca"):
            c = circunstancias(por_data, "1870-12-22", local)
            assert c["tipo"] == "parcial", local

    def test_limite_norte_da_faixa_junto_aos_37_graus(self, por_data):
        """O plano inicial situava o limite proximo dos 37 graus norte."""
        el = elementos(por_data, "1870-12-22")
        lons = np.full(400, -7.93)
        lats = np.linspace(36.0, 39.0, 400)
        t = b.t_desde_t0(el, 12.21)  # perto do maximo sobre Portugal
        r = b.magnitude_em(el, t, lats, lons)
        centrais = lats[np.asarray(r["central"])]
        assert centrais.size > 0
        assert centrais.max() == pytest.approx(37.5, abs=0.7)


class TestAnular1764:
    """1 de abril de 1764: o anel atravessa o sul do pais, na diagonal."""

    def test_anularidade_no_sul(self, por_data):
        for local in ("Faro", "Sagres", "Lisboa"):
            c = circunstancias(por_data, "1764-04-01", local)
            assert c["tipo"] == "anular", local

    def test_marinha_grande_fica_de_fora(self, por_data):
        """Contraria o plano inicial: fica no limite da faixa, em parcial funda."""
        c = circunstancias(por_data, "1764-04-01", "Marinha Grande")
        assert c["tipo"] == "parcial"
        assert c["magnitude"] == pytest.approx(0.93, abs=0.02)

    def test_trajectoria_de_sudoeste_para_nordeste(self, por_data):
        el = elementos(por_data, "1764-04-01")
        pontos = []
        for t in np.arange(-2.0, 2.0, 1 / 60):
            p = b.linha_central(el, t)
            if bool(p["existe"]) and 36 <= float(p["lat"]) <= 43 and -10 <= float(p["lon"]) <= -6:
                pontos.append((float(p["lat"]), float(p["lon"])))
        assert len(pontos) > 5
        # A latitude sobe e a longitude sobe: a sombra vai para nordeste.
        assert pontos[-1][0] > pontos[0][0]
        assert pontos[-1][1] > pontos[0][1]

    def test_faixa_larga(self, por_data):
        el = elementos(por_data, "1764-04-01")
        t = b.t_desde_t0(el, 9.9 + el.delta_t_s / 3600.0)
        assert b.largura_faixa_km(el, t) == pytest.approx(390, abs=40)


class TestHibrido1912:
    """17 de abril de 1912: faixa de cerca de 1 km sobre Ovar e Penafiel."""

    def test_faixa_sub_quilometrica(self, por_data):
        """A largura anda pelo quilometro, o que a torna impossivel de desenhar
        como poligono a escala do mapa. O frontend trata este caso a parte."""
        el = elementos(por_data, "1912-04-17")
        larguras = []
        for t in np.arange(-1.0, 1.0, 1 / 60):
            p = b.linha_central(el, t)
            if bool(p["existe"]) and 39 <= float(p["lat"]) <= 43 and -10 <= float(p["lon"]) <= -6:
                larguras.append(b.largura_faixa_km(el, t))
        assert larguras
        assert max(larguras) < 2.0
        assert min(larguras) > 0.5

    def test_linha_central_passa_em_ovar_e_penafiel(self, por_data):
        el = elementos(por_data, "1912-04-17")
        for local, tolerancia_km in (("Ovar", 12.0), ("Penafiel", 12.0)):
            lat, lon = LOCAIS[local]
            alvo = b._para_versor(lat, lon)
            melhor = 1e9
            for t in np.arange(-1.0, 1.0, 1 / 600):
                p = b.linha_central(el, t)
                if not bool(p["existe"]):
                    continue
                d = np.arccos(np.clip(b._para_versor(p["lat"], p["lon"]) @ alvo, -1, 1))
                melhor = min(melhor, float(d) * b.RAIO_EQUATORIAL_KM)
            assert melhor < tolerancia_km, f"{local}: {melhor:.1f} km da linha central"

    def test_quase_todo_o_pais_em_parcial_fundissima(self, por_data):
        """O plano inicial fala em 97 a 99,8 por cento no grosso do pais."""
        for local in ("Porto", "Penafiel", "Braganca", "Marinha Grande"):
            c = circunstancias(por_data, "1912-04-17", local)
            assert c["magnitude"] > 0.97, local
