/** O que o browser recalcula concorda com o que cada ficha lunar diz.
 *
 * O teste de ouro compara o TypeScript com o Python em trinta eclipses
 * escolhidos. Este vai mais longe e fecha o circuito com os dados publicados:
 * para os mil e setecentos eclipses lunares do catalogo, refaz com `sombra.ts` e
 * `tempo.ts` os instantes e as magnitudes que a ficha mostra, e exige que batam
 * certo.
 *
 * Fecha em particular duas coisas que o teste de ouro nao cobre: a conversao das
 * horas, que do lado do Python usa a base de dados de fusos do sistema e do lado
 * do browser usa o `Intl`, e a coerencia entre a magnitude visivel de cada
 * territorio e a geometria de onde ela saiu.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import {
  instantesDosContactos,
  magnitudesNoInstante,
  paraUt,
} from "../src/lib/sombra.ts";
import { horaLocal } from "../src/lib/tempo.ts";
import { TERRITORIOS } from "../src/lib/territorios.ts";
import type {
  EclipseLunar,
  EntradaIndiceLunar,
  NomeContacto,
} from "../src/lib/tipos.ts";

const DADOS = fileURLToPath(new URL("../public/data/", import.meta.url));

const indice: EntradaIndiceLunar[] = JSON.parse(
  readFileSync(`${DADOS}eclipses-lua-index.json`, "utf8"),
);

const fichas: EclipseLunar[] = indice.map((entrada) =>
  JSON.parse(readFileSync(`${DADOS}lua/${entrada.id}/eclipse.json`, "utf8")),
);

/** A ficha guarda o dia juliano com seis casas decimais, ou seja um decimo de
 * segundo, que e tambem o erro maximo desse arredondamento. */
const TOLERANCIA_JD = 1e-6;

/** As magnitudes publicadas pela NASA vem com quatro casas, e a geometria deste
 * projeto reproduz-nas com erro de dois decimilesimos. */
const TOLERANCIA_MAGNITUDE = 0.001;

test("ha fichas lunares para verificar", () => {
  assert.ok(fichas.length > 1000, `so ${fichas.length} fichas lunares`);
});

test("os contactos da ficha saem dos elementos que ela publica", () => {
  for (const ficha of fichas) {
    const calculados = instantesDosContactos(ficha.elementos);
    for (const territorio of TERRITORIOS) {
      const dados = ficha.territorios[territorio];
      if (!dados.visivel) continue;
      for (const [nome, momento] of Object.entries(dados.contactos)) {
        const calculado = calculados[nome as NomeContacto];
        assert.ok(
          calculado !== undefined,
          `${ficha.id}: a ficha tem ${nome} e a geometria nao`,
        );
        const emUt = paraUt(ficha.elementos, calculado!);
        assert.ok(
          Math.abs(emUt - momento.jd_ut) < TOLERANCIA_JD,
          `${ficha.id} ${territorio} ${nome}: ${emUt} vs ${momento.jd_ut}`,
        );
      }
    }
  }
});

/** Data e hora locais num numero so, para as poder comparar sem tropecar na
 * meia-noite: 23:59:59 de um dia e 00:00:00 do seguinte estao a um segundo de
 * distancia, e como texto parecem estar a um dia. */
function emSegundos(data: string, hora: string): number {
  const [ano, mes, dia] = data.split("-").map(Number);
  const [h, m, s] = hora.split(":").map(Number);
  return (
    (ano! * 372 + mes! * 31 + dia!) * 86400 + h! * 3600 + m! * 60 + s!
  );
}

test("as horas locais da ficha sao as que o browser calcula", () => {
  for (const ficha of fichas) {
    for (const territorio of TERRITORIOS) {
      const dados = ficha.territorios[territorio];
      if (!dados.visivel) continue;
      for (const [nome, momento] of Object.entries(dados.contactos)) {
        const local = horaLocal(momento.jd_ut, dados.lugar.lon, territorio);
        // Um segundo de folga, e por uma razao que nao e o calculo: a ficha
        // guarda o dia juliano arredondado a um decimo de segundo, e o Python
        // gerou a hora a partir do valor inteiro. Quando o corte dos segundos
        // cai entre os dois, as duas horas ficam a um segundo uma da outra.
        const desvio = Math.abs(
          emSegundos(local.data, local.hora) -
            emSegundos(momento.data_local, momento.hora_local),
        );
        assert.ok(
          desvio <= 1,
          `${ficha.id} ${territorio} ${nome}: ${local.data} ${local.hora} vs ${momento.data_local} ${momento.hora_local}`,
        );
        assert.equal(
          local.sistema,
          momento.sistema_hora,
          `${ficha.id} ${territorio} ${nome}`,
        );
      }
    }
  }
});

test("as magnitudes no maximo reproduzem as publicadas pela NASA", () => {
  for (const ficha of fichas) {
    const magnitudes = magnitudesNoInstante(
      ficha.elementos,
      ficha.elementos.jd_maximo_td,
    );
    assert.ok(
      Math.abs(magnitudes.umbral - ficha.magnitude_umbral) <
        TOLERANCIA_MAGNITUDE,
      `${ficha.id} umbral: ${magnitudes.umbral} vs ${ficha.magnitude_umbral}`,
    );
    assert.ok(
      Math.abs(magnitudes.penumbral - ficha.magnitude_penumbral) <
        TOLERANCIA_MAGNITUDE,
      `${ficha.id} penumbral: ${magnitudes.penumbral} vs ${ficha.magnitude_penumbral}`,
    );
  }
});

test("a magnitude visivel bate com a geometria no instante em que se viu", () => {
  for (const ficha of fichas) {
    for (const territorio of TERRITORIOS) {
      const dados = ficha.territorios[territorio];
      if (!dados.visivel) continue;

      // Quando o maximo apanhou a Lua no ceu, a fase mais funda que dali se viu
      // e a do proprio maximo. Quando nao, foi menos, e nunca mais.
      const noMaximo = magnitudesNoInstante(
        ficha.elementos,
        ficha.elementos.jd_maximo_td,
      );
      if (dados.contactos.maximo?.acima_do_horizonte) {
        assert.ok(
          Math.abs(
            dados.magnitude_umbral_visivel - Math.max(noMaximo.umbral, 0),
          ) < 0.001,
          `${ficha.id} ${territorio}: ${dados.magnitude_umbral_visivel} vs ${noMaximo.umbral}`,
        );
      } else {
        assert.ok(
          dados.magnitude_penumbral_visivel <= noMaximo.penumbral + 0.001,
          `${ficha.id} ${territorio}: viu-se mais do que houve`,
        );
      }
    }
  }
});

test("o tipo visto nunca e mais fundo do que o eclipse foi", () => {
  const fundura = { nenhum: 0, penumbral: 1, parcial: 2, total: 3 };
  for (const ficha of fichas) {
    for (const territorio of TERRITORIOS) {
      const dados = ficha.territorios[territorio];
      if (!dados.visivel) continue;
      assert.ok(
        fundura[dados.tipo_visto] <= fundura[ficha.tipo],
        `${ficha.id} ${territorio}: ${dados.tipo_visto} de um eclipse ${ficha.tipo}`,
      );
    }
  }
});
