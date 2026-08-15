/** O calculo ao vivo concorda com o que esta escrito em cada ficha.
 *
 * O teste de ouro compara o TypeScript com o Python em pontos escolhidos. Este
 * vai mais longe e fecha o circuito com os dados publicados: para os 277
 * eclipses do catalogo, recalcula no browser as circunstancias no local mais
 * fundo de cada territorio e exige que batam certo com os numeros que a ficha
 * mostra ao lado do mapa.
 *
 * E o criterio de aceitacao da fase M4, escrito como teste: passar o rato sobre
 * o ponto que a ficha aponta tem de dar o que a ficha diz.
 *
 * As tolerancias vem de duas coisas, nao da qualidade do calculo:
 *   - a ficha arredonda a magnitude a quatro casas e os angulos a uma;
 *   - a ficha arredonda tambem as coordenadas do ponto a quatro casas, cerca de
 *     cinco metros, e cinco metros mudam de facto o que ali se ve, ainda que
 *     muito pouco.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { circunstanciasNoPonto, elementosDe } from "../src/lib/besselian.ts";
import { horaLocal, isoHora, jdParaCivil, jdUtDeT } from "../src/lib/tempo.ts";
import { TERRITORIOS } from "../src/lib/territorios.ts";
import type { Eclipse, EntradaIndice } from "../src/lib/tipos.ts";

const DADOS = fileURLToPath(new URL("../public/data/", import.meta.url));

const indice: EntradaIndice[] = JSON.parse(
  readFileSync(`${DADOS}eclipses-index.json`, "utf8"),
);

const fichas: Eclipse[] = indice.map((entrada) =>
  JSON.parse(readFileSync(`${DADOS}${entrada.id}/eclipse.json`, "utf8")),
);

/** Metade da ultima casa que a ficha guarda, mais folga para o arredondamento
 * das coordenadas do ponto. */
const TOLERANCIA = {
  magnitude: 1e-4,
  angulo_graus: 0.051,
  segundos: 1.01, // os segundos sao truncados dos dois lados
  duracao_relativa: 0.01,
  duracao_minima_s: 0.2,
};

/** Segundos desde a meia-noite de uma hora "HH:MM:SS". */
function segundosDoDia(hora: string): number {
  const [h, m, s] = hora.split(":").map(Number);
  return h! * 3600 + m! * 60 + s!;
}

function distanciaAngular(a: number, b: number): number {
  const bruta = Math.abs(a - b) % 360;
  return Math.min(bruta, 360 - bruta);
}

test("o catalogo esta gerado e completo", () => {
  assert.ok(fichas.length > 200, "poucas fichas: correr o pipeline");
  for (const ficha of fichas) {
    assert.ok(
      Number.isFinite(ficha.jd_t0_td),
      `${ficha.id}: sem jd_t0_td, correr build_index.py`,
    );
  }
});

test("magnitude, obscuracao e tipo local batem certo com a ficha", () => {
  for (const ficha of fichas) {
    const e = elementosDe(ficha);
    for (const territorio of TERRITORIOS) {
      const dados = ficha.territorios[territorio];
      if (!dados.visivel) continue;

      const onde = `${ficha.id} em ${territorio}`;
      const ponto = dados.local_mais_fundo;
      const calculado = circunstanciasNoPonto(e, ponto.lat, ponto.lon);

      assert.equal(calculado.tipo, dados.tipo_local, `${onde}: tipo local`);
      assert.ok(
        Math.abs(calculado.magnitude - dados.magnitude_max) <= TOLERANCIA.magnitude,
        `${onde}: magnitude ${calculado.magnitude} contra ${dados.magnitude_max}`,
      );
      assert.ok(
        Math.abs(calculado.obscuracao - dados.obscuracao_max) <= TOLERANCIA.magnitude,
        `${onde}: obscuracao ${calculado.obscuracao} contra ${dados.obscuracao_max}`,
      );
      assert.ok(
        Math.abs(calculado.alt_sol - dados.alt_sol_graus) <= TOLERANCIA.angulo_graus,
        `${onde}: altura do Sol ${calculado.alt_sol} contra ${dados.alt_sol_graus}`,
      );
      assert.ok(
        distanciaAngular(calculado.az_sol, dados.az_sol_graus) <=
          TOLERANCIA.angulo_graus,
        `${onde}: azimute do Sol ${calculado.az_sol} contra ${dados.az_sol_graus}`,
      );

      if (dados.duracao_central_s !== null && calculado.duracao_central_s !== null) {
        const tolerancia = Math.max(
          TOLERANCIA.duracao_minima_s,
          TOLERANCIA.duracao_relativa * dados.duracao_central_s,
        );
        assert.ok(
          Math.abs(calculado.duracao_central_s - dados.duracao_central_s) <=
            tolerancia,
          `${onde}: duracao central ${calculado.duracao_central_s} contra ${dados.duracao_central_s}`,
        );
      }
    }
  }
});

test("as horas do maximo batem certo com a ficha", () => {
  for (const ficha of fichas) {
    const e = elementosDe(ficha);
    for (const territorio of TERRITORIOS) {
      const dados = ficha.territorios[territorio];
      if (!dados.visivel) continue;

      const onde = `${ficha.id} em ${territorio}`;
      const ponto = dados.local_mais_fundo;
      const calculado = circunstanciasNoPonto(e, ponto.lat, ponto.lon);
      const jdUt = jdUtDeT(ficha, calculado.t_maximo_td);

      const ut = isoHora(jdParaCivil(jdUt, true));
      assert.ok(
        Math.abs(segundosDoDia(ut) - segundosDoDia(dados.maximo_ut)) <=
          TOLERANCIA.segundos,
        `${onde}: maximo em UT ${ut} contra ${dados.maximo_ut}`,
      );

      const local = horaLocal(jdUt, ponto.lon, territorio);
      assert.equal(local.sistema, dados.sistema_hora, `${onde}: sistema de hora`);
      assert.equal(local.data, dados.data_local, `${onde}: data local`);
      assert.ok(
        Math.abs(segundosDoDia(local.hora) - segundosDoDia(dados.maximo_local)) <=
          TOLERANCIA.segundos,
        `${onde}: maximo local ${local.hora} contra ${dados.maximo_local}`,
      );
    }
  }
});
