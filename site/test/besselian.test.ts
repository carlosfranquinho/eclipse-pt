/** Teste de ouro: o nucleo TypeScript da os mesmos numeros que o Python.
 *
 * Os casos vem de `pipeline/tests/golden/circunstancias.json`, gerado por
 * `pipeline/gerar_golden.py` a partir do mesmo canon. Aqui recalcula-se tudo com
 * `src/lib/besselian.ts` e `src/lib/tempo.ts` e compara-se.
 *
 * As tolerancias sao apertadas de proposito. As duas implementacoes fazem as
 * mesmas contas pela mesma ordem, em virgula flutuante de dupla precisao, por
 * isso a unica diferenca legitima e o ultimo bit das funcoes trigonometricas.
 * Uma tolerancia larga aqui esconderia exactamente o que este teste existe para
 * apanhar.
 *
 *     cd site && npm test
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import {
  circunstanciasNoPonto,
  elementosDe,
  magnitudeEm,
  type Elementos,
} from "../src/lib/besselian.ts";
import { horaLocal } from "../src/lib/tempo.ts";
import type { SistemaHora, Territorio } from "../src/lib/tipos.ts";

const CAMINHO = fileURLToPath(
  new URL("../../pipeline/tests/golden/circunstancias.json", import.meta.url),
);

/** Tolerancias por grandeza. Horas para os instantes, graus para os angulos.
 *
 * Os desvios medidos ficam entre 1e-16 e 1e-13, ou seja no ultimo bit. Estes
 * valores deixam algumas ordens de grandeza de folga para as diferencas de
 * arredondamento das funcoes trigonometricas entre plataformas, e continuam
 * muito abaixo de qualquer divergencia que tenha significado fisico. */
const TOLERANCIA = {
  instante_h: 1e-10, // 0,36 microssegundos
  magnitude: 1e-11,
  angulo_graus: 1e-9,
  duracao_s: 1e-7,
  geometria: 1e-12, // separacao e raios dos cones, em raios terrestres
  desvio_utc_h: 1e-9,
};

interface CasoCircunstancias {
  eclipse: string;
  lugar: string;
  lat: number;
  lon: number;
  esperado: {
    visivel: boolean;
    tipo: string;
    magnitude: number;
    obscuracao: number;
    razao_diametros: number | null;
    t_maximo_td: number;
    contactos_td: Record<string, number | null>;
    duracao_central_s: number | null;
    alt_sol: number;
    az_sol: number;
  };
  amostras: {
    t: number;
    magnitude: number;
    obscuracao: number;
    u: number;
    v: number;
    angulo_horario: number;
    declinacao: number;
    alt_sol: number;
    az_sol: number;
    separacao: number;
    l1_obs: number;
    l2_obs: number;
  }[];
}

interface CasoHora {
  jd_ut: number;
  lon: number;
  territorio: Territorio;
  esperado: {
    data: string;
    hora: string;
    sistema: SistemaHora;
    desvio_utc_h: number;
  };
}

interface Golden {
  eclipses: { id: string; jd_t0_td: number; delta_t_s: number; elementos: never }[];
  circunstancias: CasoCircunstancias[];
  horas: CasoHora[];
}

const golden: Golden = JSON.parse(readFileSync(CAMINHO, "utf8"));

const elementos = new Map<string, Elementos>(
  golden.eclipses.map((e) => [e.id, elementosDe(e)]),
);

/** Diferenca angular em graus, pelo caminho mais curto: o azimute passa por zero
 * e uma comparacao ingenua acusaria 360 graus de erro. */
function distanciaAngular(a: number, b: number): number {
  const bruta = Math.abs(a - b) % 360;
  return Math.min(bruta, 360 - bruta);
}

function proximo(
  obtido: number,
  esperado: number,
  tolerancia: number,
  contexto: string,
): void {
  const desvio = Math.abs(obtido - esperado);
  assert.ok(
    desvio <= tolerancia,
    `${contexto}: obtido ${obtido}, esperado ${esperado}, desvio ${desvio.toExponential(3)} acima de ${tolerancia}`,
  );
}

test("o ficheiro de casos de ouro esta la e tem substancia", () => {
  assert.ok(golden.eclipses.length >= 10);
  assert.ok(golden.circunstancias.length >= 300);
  assert.ok(golden.horas.length >= 100);
});

test("magnitude e altura do Sol em instantes fixos", () => {
  // Sem iteracao nenhuma pelo meio: se este teste falha, o erro esta na
  // avaliacao dos polinomios ou na geometria do observador, nao na convergencia.
  for (const caso of golden.circunstancias) {
    const e = elementos.get(caso.eclipse)!;
    for (const amostra of caso.amostras) {
      const onde = `${caso.eclipse} em ${caso.lugar}, t=${amostra.t}`;
      const obtido = magnitudeEm(e, amostra.t, caso.lat, caso.lon);

      proximo(obtido.magnitude, amostra.magnitude, TOLERANCIA.magnitude, `${onde}: magnitude`);
      proximo(obtido.obscuracao, amostra.obscuracao, TOLERANCIA.magnitude, `${onde}: obscuracao`);
      proximo(obtido.u, amostra.u, TOLERANCIA.geometria, `${onde}: u`);
      proximo(
        distanciaAngular(obtido.angulo_horario, amostra.angulo_horario),
        0,
        TOLERANCIA.angulo_graus,
        `${onde}: angulo horario`,
      );
      proximo(
        obtido.declinacao,
        amostra.declinacao,
        TOLERANCIA.angulo_graus,
        `${onde}: declinacao`,
      );
      proximo(obtido.v, amostra.v, TOLERANCIA.geometria, `${onde}: v`);
      proximo(obtido.separacao, amostra.separacao, TOLERANCIA.geometria, `${onde}: separacao`);
      proximo(obtido.l1_obs, amostra.l1_obs, TOLERANCIA.geometria, `${onde}: l1_obs`);
      proximo(obtido.l2_obs, amostra.l2_obs, TOLERANCIA.geometria, `${onde}: l2_obs`);
      proximo(obtido.alt_sol, amostra.alt_sol, TOLERANCIA.angulo_graus, `${onde}: altura do Sol`);
      proximo(
        distanciaAngular(obtido.az_sol, amostra.az_sol),
        0,
        TOLERANCIA.angulo_graus,
        `${onde}: azimute do Sol`,
      );
    }
  }
});

test("circunstancias completas num ponto", () => {
  for (const caso of golden.circunstancias) {
    const e = elementos.get(caso.eclipse)!;
    const esperado = caso.esperado;
    const onde = `${caso.eclipse} em ${caso.lugar}`;
    const obtido = circunstanciasNoPonto(e, caso.lat, caso.lon);

    assert.equal(obtido.visivel, esperado.visivel, `${onde}: visibilidade`);
    assert.equal(obtido.tipo, esperado.tipo, `${onde}: tipo local`);
    proximo(obtido.t_maximo_td, esperado.t_maximo_td, TOLERANCIA.instante_h, `${onde}: instante do maximo`);
    proximo(obtido.magnitude, esperado.magnitude, TOLERANCIA.magnitude, `${onde}: magnitude`);
    proximo(obtido.obscuracao, esperado.obscuracao, TOLERANCIA.magnitude, `${onde}: obscuracao`);
    proximo(obtido.alt_sol, esperado.alt_sol, TOLERANCIA.angulo_graus, `${onde}: altura do Sol`);
    proximo(
      distanciaAngular(obtido.az_sol, esperado.az_sol),
      0,
      TOLERANCIA.angulo_graus,
      `${onde}: azimute do Sol`,
    );

    if (esperado.razao_diametros === null) {
      assert.equal(obtido.razao_diametros, null, `${onde}: razao de diametros`);
    } else {
      proximo(
        obtido.razao_diametros!,
        esperado.razao_diametros,
        TOLERANCIA.magnitude,
        `${onde}: razao de diametros`,
      );
    }

    for (const chave of ["c1", "c2", "c3", "c4"] as const) {
      const alvo = esperado.contactos_td[chave];
      const meu = obtido.contactos_td[chave];
      if (alvo === null) {
        assert.equal(meu, null, `${onde}: contacto ${chave} nao devia existir`);
      } else {
        assert.notEqual(meu, null, `${onde}: contacto ${chave} em falta`);
        proximo(meu!, alvo, TOLERANCIA.instante_h, `${onde}: contacto ${chave}`);
      }
    }

    if (esperado.duracao_central_s === null) {
      assert.equal(obtido.duracao_central_s, null, `${onde}: duracao central`);
    } else {
      proximo(
        obtido.duracao_central_s!,
        esperado.duracao_central_s,
        TOLERANCIA.duracao_s,
        `${onde}: duracao central`,
      );
    }
  }
});

test("hora local, no sistema em vigor a data", () => {
  for (const caso of golden.horas) {
    const onde = `jd ${caso.jd_ut} em ${caso.territorio}, lon ${caso.lon}`;
    const obtido = horaLocal(caso.jd_ut, caso.lon, caso.territorio);

    assert.equal(obtido.sistema, caso.esperado.sistema, `${onde}: sistema de hora`);
    assert.equal(obtido.data, caso.esperado.data, `${onde}: data local`);
    assert.equal(obtido.hora, caso.esperado.hora, `${onde}: hora local`);
    proximo(
      obtido.desvio_utc_h,
      caso.esperado.desvio_utc_h,
      TOLERANCIA.desvio_utc_h,
      `${onde}: desvio em relacao ao UTC`,
    );
  }
});
