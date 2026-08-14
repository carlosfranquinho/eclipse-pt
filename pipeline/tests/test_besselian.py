"""Testes unitarios do nucleo besseliano."""

from __future__ import annotations

import numpy as np
import pytest

import besselian as b


class TestGeodetica:
    def test_exemplo_publicado(self):
        """Valor trabalhado no Explanatory Supplement, para 38.92139 graus e 84 m.

        E o unico ponto do modulo em que ha um numero publicado independente para
        comparar, por isso vale a pena a tolerancia apertada.
        """
        rho_sin, rho_cos = b.geodetica_para_geocentrica(38.92139, 84.0)
        assert rho_sin == pytest.approx(0.624882, abs=1e-6)
        assert rho_cos == pytest.approx(0.779049, abs=1e-6)

    def test_equador_e_polo(self):
        rho_sin, rho_cos = b.geodetica_para_geocentrica(0.0, 0.0)
        assert rho_sin == pytest.approx(0.0, abs=1e-12)
        assert rho_cos == pytest.approx(1.0, abs=1e-12)

        rho_sin, rho_cos = b.geodetica_para_geocentrica(90.0, 0.0)
        assert rho_sin == pytest.approx(b.ACHATAMENTO, abs=1e-9)
        assert rho_cos == pytest.approx(0.0, abs=1e-9)

    def test_altura_aumenta_o_raio(self):
        ao_nivel = b.geodetica_para_geocentrica(40.0, 0.0)
        na_serra = b.geodetica_para_geocentrica(40.0, 2000.0)
        assert na_serra[0] > ao_nivel[0]
        assert na_serra[1] > ao_nivel[1]


class TestPolinomios:
    def test_avaliacao_e_derivada(self):
        coef = (1.0, 2.0, 3.0, 4.0)
        assert b._poli(coef, 2.0) == pytest.approx(1 + 4 + 12 + 32)
        assert b._derivada_poli(coef, 2.0) == pytest.approx(2 + 12 + 48)

    def test_derivada_numerica_coincide(self):
        coef = (0.3, -1.2, 0.05, -0.001)
        h = 1e-6
        analitica = b._derivada_poli(coef, 1.7)
        numerica = (b._poli(coef, 1.7 + h) - b._poli(coef, 1.7 - h)) / (2 * h)
        assert analitica == pytest.approx(numerica, rel=1e-6)


class TestEnvolvimentoDeMeiaNoite:
    """O `t0` do canon e o instante do maximo podem cair em dias civis diferentes."""

    def _elementos(self, t0: float) -> b.Elementos:
        return b.Elementos(
            t0_td=t0, x=(0.0, 0.5), y=(0.0, 0.1), d=(0.0,), mu=(0.0, 15.0),
            l1=(0.55,), l2=(0.01,), tan_f1=0.0046, tan_f2=0.0046, delta_t_s=0.0,
        )

    def test_sem_travessia(self):
        e = self._elementos(17.0)
        assert float(b.t_desde_t0(e, 16.5)) == pytest.approx(-0.5)

    def test_com_travessia(self):
        """t0 as 23h e maximo a 00h30 do dia seguinte dao t = +1.5, nao -22.5."""
        e = self._elementos(23.0)
        assert float(b.t_desde_t0(e, 0.5)) == pytest.approx(1.5)

    def test_travessia_ao_contrario(self):
        e = self._elementos(1.0)
        assert float(b.t_desde_t0(e, 23.0)) == pytest.approx(-2.0)


class TestObscuracao:
    def test_sem_sobreposicao(self):
        assert float(b._obscuracao(1.0, 1.0, 2.5)) == pytest.approx(0.0)

    def test_cobertura_total(self):
        """Lua maior que o Sol e centrada: o disco fica todo tapado."""
        assert float(b._obscuracao(1.0, 1.2, 0.0)) == pytest.approx(1.0)

    def test_anular_centrado(self):
        """Lua menor e centrada: tapa a razao das areas."""
        assert float(b._obscuracao(1.0, 0.9, 0.0)) == pytest.approx(0.81)

    def test_meio_disco(self):
        """Discos iguais com os centros a distancia de um raio."""
        valor = float(b._obscuracao(1.0, 1.0, 1.0))
        esperado = (2 * np.pi / 3 - np.sqrt(3) / 2) / np.pi
        assert valor == pytest.approx(esperado, rel=1e-9)

    def test_monotona(self):
        seps = np.linspace(0.0, 2.0, 40)
        valores = b._obscuracao(1.0, 1.0, seps)
        assert np.all(np.diff(valores) <= 1e-12)


class TestCircunstanciasLocais:
    def test_ordem_dos_contactos(self, por_data):
        """Os quatro contactos tem de sair por ordem, com o maximo pelo meio."""
        e = por_data["1900-05-28"]
        el = b.Elementos.de_dict(e["elementos"], e["delta_t_s"])
        c = b.circunstancias_locais(el, 40.86, -8.62)  # Ovar, dentro da faixa

        assert c["tipo"] == "total"
        t = c["contactos_td"]
        assert t["c1"] < t["c2"] < c["t_maximo_td"] < t["c3"] < t["c4"]

    def test_parcial_nao_tem_contactos_interiores(self, por_data):
        e = por_data["1900-05-28"]
        el = b.Elementos.de_dict(e["elementos"], e["delta_t_s"])
        c = b.circunstancias_locais(el, 37.02, -7.93)  # Faro, fora da faixa

        assert c["tipo"] == "parcial"
        assert c["contactos_td"]["c2"] is None
        assert c["contactos_td"]["c3"] is None
        assert c["contactos_td"]["c1"] < c["t_maximo_td"] < c["contactos_td"]["c4"]

    def test_magnitude_maxima_no_instante_de_maximo(self, por_data):
        """Por definicao, nenhum instante vizinho pode dar magnitude maior."""
        e = por_data["1900-05-28"]
        el = b.Elementos.de_dict(e["elementos"], e["delta_t_s"])
        c = b.circunstancias_locais(el, 40.86, -8.62)

        no_maximo = c["magnitude"]
        for desvio in (-0.05, -0.01, 0.01, 0.05):
            vizinho = b.magnitude_em(el, c["t_maximo_td"] + desvio, 40.86, -8.62)
            assert float(vizinho["magnitude"]) <= no_maximo + 1e-9

    def test_sem_eclipse_do_outro_lado_do_mundo(self, por_data):
        e = por_data["1900-05-28"]
        el = b.Elementos.de_dict(e["elementos"], e["delta_t_s"])
        c = b.circunstancias_locais(el, -41.0, 175.0)  # Nova Zelandia
        assert not c["visivel"]


class TestGeometriaDaFaixa:
    def test_contorno_rodeia_a_linha_central(self, por_data):
        """Todos os pontos do contorno ficam a mesma ordem de distancia do centro."""
        e = por_data["1900-05-28"]
        el = b.Elementos.de_dict(e["elementos"], e["delta_t_s"])
        t = b.t_desde_t0(el, e["eclipse_maior"]["instante_td_h"])

        centro = b.linha_central(el, t)
        contorno = b.contorno_sombra(el, t, n_pontos=72)
        assert np.all(contorno["existe"])

        centro_v = b._para_versor(centro["lat"], centro["lon"])
        pontos = b._para_versor(contorno["lat"], contorno["lon"])
        angulos = np.arccos(np.clip(pontos @ centro_v, -1, 1))
        raios_km = angulos * b.RAIO_EQUATORIAL_KM
        # Uma sombra quase circular perto do subsolar: o raio varia pouco.
        assert raios_km.min() > 0.0
        assert raios_km.max() / raios_km.min() < 2.0

    def test_sem_linha_central_num_eclipse_parcial(self, canon):
        parcial = next(e for e in canon if e["tipo"] == "parcial")
        el = b.Elementos.de_dict(parcial["elementos"], parcial["delta_t_s"])
        assert not bool(b.linha_central(el, 0.0)["existe"])


class TestVarrimentoEspacial:
    def test_magnitude_visivel_anula_se_o_sol_nao_nasceu(self, por_data):
        """A geometria pode dar eclipse onde ninguem o ve, por ser de noite."""
        e = por_data["1900-05-28"]
        el = b.Elementos.de_dict(e["elementos"], e["delta_t_s"])

        # Procura um ponto com eclipse geometrico e Sol abaixo do horizonte.
        lats, lons = np.meshgrid(np.arange(-80, 81, 5.0), np.arange(-180, 180, 5.0))
        r = b.magnitude_em(el, 0.0, lats, lons)
        escondidos = (r["magnitude"] > 0) & ~r["sol_visivel"]
        assert escondidos.any(), "esperava pontos com eclipse abaixo do horizonte"

        visivel = b.magnitude_visivel(el, 0.0, lats, lons)
        assert np.all(visivel[escondidos] == 0.0)

    def test_grelha_reproduz_o_calculo_pontual(self, por_data):
        """O varrimento tem de concordar com as circunstancias locais em Ovar."""
        e = por_data["1900-05-28"]
        el = b.Elementos.de_dict(e["elementos"], e["delta_t_s"])

        g = b.magnitude_maxima_na_grelha(
            el, 40.80, 40.92, -8.68, -8.56, passo_graus=0.02, passo_minutos=1.0
        )
        i = int(np.argmin(np.abs(g["lat"] - 40.86)))
        j = int(np.argmin(np.abs(g["lon"] - (-8.62))))

        pontual = b.circunstancias_locais(el, float(g["lat"][i]), float(g["lon"][j]))
        assert g["magnitude"][i, j] == pytest.approx(pontual["magnitude"], abs=1e-4)

    def test_magnitude_decresce_ao_afastar_da_faixa(self, por_data):
        """Descendo de Ovar para o Algarve, a magnitude tem de cair sempre."""
        e = por_data["1900-05-28"]
        el = b.Elementos.de_dict(e["elementos"], e["delta_t_s"])
        lats = np.arange(37.0, 41.0, 0.25)
        valores = [
            b.circunstancias_locais(el, float(la), -8.2)["magnitude"] for la in lats
        ]
        assert np.all(np.diff(valores) > 0)
