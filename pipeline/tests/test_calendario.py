"""Testes do tratamento de datas e horas."""

from __future__ import annotations

import pytest

import calendario as cal


class TestDiaJuliano:
    @pytest.mark.parametrize(
        "jd, esperado",
        [
            (2451545.0, (2000, 1, 1, 12)),
            (2436116.31, (1957, 10, 4, 19)),
            (2447187.5, (1988, 1, 27, 0)),
        ],
    )
    def test_exemplos_do_meeus(self, jd, esperado):
        d = cal.jd_para_civil(jd, gregoriano=True)
        assert (d.ano, d.mes, d.dia, d.hora) == esperado

    def test_ida_e_volta(self):
        for ano, mes, dia in [(1500, 3, 1), (1582, 10, 15), (1900, 5, 28), (2100, 12, 31)]:
            jd = cal.civil_para_jd(ano, mes, dia, gregoriano=True)
            d = cal.jd_para_civil(jd, gregoriano=True)
            assert (d.ano, d.mes, d.dia) == (ano, mes, dia)


class TestAdopcaoDoGregoriano:
    def test_data_da_adopcao_em_portugal(self):
        """Portugal saltou de 4 para 15 de outubro de 1582, ao mesmo tempo que Roma."""
        assert cal.civil_para_jd(1582, 10, 4, gregoriano=False) == 2299159.5
        assert cal.civil_para_jd(1582, 10, 15, gregoriano=True) == 2299160.5
        assert cal.JD_ADOPCAO_GREGORIANO_PT == 2299160.5

    def test_calendario_vigente(self):
        assert cal.calendario_vigente(cal.civil_para_jd(1500, 1, 1, False)) == "juliano"
        assert cal.calendario_vigente(2299159.5) == "juliano"
        assert cal.calendario_vigente(2299160.5) == "gregoriano"
        assert cal.calendario_vigente(cal.civil_para_jd(1900, 1, 1, True)) == "gregoriano"

    def test_desfasamento_de_dez_dias_no_seculo_xvi(self):
        jd = cal.civil_para_jd(1560, 1, 1, gregoriano=True)
        juliana = cal.jd_para_civil(jd, gregoriano=False)
        assert (juliana.ano, juliana.mes, juliana.dia) == (1559, 12, 22)


class TestHoraLocal:
    def test_antes_de_1912_usa_hora_solar_media(self):
        jd = cal.civil_para_jd(1900, 5, 28, True) + 16.04 / 24
        resultado = cal.hora_local(jd, -8.62, "continente")
        assert resultado["sistema"] == cal.SISTEMA_SOLAR_MEDIA
        assert resultado["designacao_fuso"] is None
        # Ovar esta 8,62 graus a oeste, ou seja cerca de 34 minutos atras de UT.
        assert resultado["hora"].startswith("15:2")

    def test_hora_solar_varia_com_a_longitude(self):
        """E este o ponto de nao haver hora legal: cada terra tinha a sua hora."""
        jd = cal.civil_para_jd(1764, 4, 1, True) + 10.0 / 24
        oeste = cal.hora_local(jd, -9.5, "continente")
        leste = cal.hora_local(jd, -6.2, "continente")
        assert oeste["hora"] < leste["hora"]

    def test_depois_de_1912_usa_hora_legal(self):
        jd = cal.civil_para_jd(2005, 10, 3, True) + 9.0 / 24
        resultado = cal.hora_local(jd, -8.5, "continente")
        assert resultado["sistema"] == cal.SISTEMA_HORA_LEGAL
        assert resultado["designacao_fuso"] is not None

    def test_hora_de_verao(self):
        """Em outubro de 2005 o continente ainda estava em hora de verao."""
        jd = cal.civil_para_jd(2005, 10, 3, True) + 9.0 / 24
        assert cal.hora_local(jd, -8.5, "continente")["desvio_utc_h"] == 1.0

    def test_periodo_da_hora_da_europa_central(self):
        """Entre 1992 e 1996 o continente esteve uma hora a frente do habitual.

        E a razao de se usar a base de fusos em vez de assumir que Portugal
        continental esteve sempre em UTC no inverno.
        """
        inverno_1993 = cal.civil_para_jd(1993, 1, 15, True) + 12.0 / 24
        assert cal.hora_local(inverno_1993, -9.0, "continente")["desvio_utc_h"] == 1.0

        inverno_1999 = cal.civil_para_jd(1999, 1, 15, True) + 12.0 / 24
        assert cal.hora_local(inverno_1999, -9.0, "continente")["desvio_utc_h"] == 0.0

    def test_fusos_das_ilhas(self):
        instante = cal.civil_para_jd(2020, 1, 15, True) + 12.0 / 24
        assert cal.hora_local(instante, -25.7, "acores")["desvio_utc_h"] == -1.0
        assert cal.hora_local(instante, -16.9, "madeira")["desvio_utc_h"] == 0.0
