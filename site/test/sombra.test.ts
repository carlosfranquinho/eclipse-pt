/** Teste de ouro do nucleo lunar: o TypeScript da os mesmos numeros que o Python.
 *
 * Os casos vem de `pipeline/tests/golden/sombra.json`, gerado por
 * `pipeline/gerar_golden_lua.py` a partir do catalogo da NASA. Aqui recalcula-se
 * tudo com `src/lib/sombra.ts` e compara-se.
 *
 * As tolerancias sao apertadas de proposito, como no teste solar: as duas
 * implementacoes fazem as mesmas contas pela mesma ordem, e a unica diferenca
 * legitima e o ultimo bit da raiz quadrada e do `hypot`.
 *
 *     cd site && npm test
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import {
  instantesDosContactos,
  magnitudesNoInstante,
  ORDEM_DOS_CONTACTOS,
  faseNoInstante,
  intervaloDoEclipse,
} from "../src/lib/sombra.ts";
import type { ElementosSombra, NomeContacto } from "../src/lib/tipos.ts";

const CAMINHO = fileURLToPath(
  new URL("../../pipeline/tests/golden/sombra.json", import.meta.url),
);

/** Um instante em dias julianos, com 1e-9 dias a valer menos de um decimo de
 * milissegundo. As magnitudes sao adimensionais e da ordem da unidade. */
const TOLERANCIA = { instante: 1e-9, magnitude: 1e-12 };

interface Caso {
  id: string;
  tipo: string;
  elementos: ElementosSombra;
  esperado: {
    contactos_td: Partial<Record<NomeContacto, number>>;
    magnitude_umbral_publicada: number;
    magnitude_penumbral_publicada: number;
  };
  amostras: { jd_td: number; umbral: number; penumbral: number }[];
}

const dados = JSON.parse(readFileSync(CAMINHO, "utf8")) as { casos: Caso[] };

test("ha casos de ouro para comparar", () => {
  assert.ok(dados.casos.length >= 20, "poucos casos no ficheiro de ouro");
});

for (const caso of dados.casos) {
  test(`contactos de ${caso.id} (${caso.tipo})`, () => {
    const obtidos = instantesDosContactos(caso.elementos);
    const esperados = caso.esperado.contactos_td;

    assert.deepEqual(
      ORDEM_DOS_CONTACTOS.filter((nome) => obtidos[nome] !== undefined),
      ORDEM_DOS_CONTACTOS.filter((nome) => esperados[nome] !== undefined),
      "os contactos que existem nao sao os mesmos",
    );

    for (const [nome, esperado] of Object.entries(esperados)) {
      const obtido = obtidos[nome as NomeContacto]!;
      assert.ok(
        Math.abs(obtido - esperado) < TOLERANCIA.instante,
        `${caso.id} ${nome}: ${obtido} vs ${esperado}`,
      );
    }
  });

  test(`magnitudes de ${caso.id} (${caso.tipo})`, () => {
    for (const amostra of caso.amostras) {
      const obtida = magnitudesNoInstante(caso.elementos, amostra.jd_td);
      assert.ok(
        Math.abs(obtida.umbral - amostra.umbral) < TOLERANCIA.magnitude,
        `${caso.id} umbral em ${amostra.jd_td}: ${obtida.umbral} vs ${amostra.umbral}`,
      );
      assert.ok(
        Math.abs(obtida.penumbral - amostra.penumbral) < TOLERANCIA.magnitude,
        `${caso.id} penumbral em ${amostra.jd_td}: ${obtida.penumbral} vs ${amostra.penumbral}`,
      );
    }
  });
}

test("a magnitude no maximo reproduz a publicada pela NASA", () => {
  for (const caso of dados.casos) {
    const magnitudes = magnitudesNoInstante(
      caso.elementos,
      caso.elementos.jd_maximo_td,
    );
    assert.ok(
      Math.abs(magnitudes.umbral - caso.esperado.magnitude_umbral_publicada) <
        0.001,
      `${caso.id}: ${magnitudes.umbral} vs ${caso.esperado.magnitude_umbral_publicada}`,
    );
  }
});

test("a fase em cada contacto e a que o contacto anuncia", () => {
  for (const caso of dados.casos) {
    const contactos = instantesDosContactos(caso.elementos);
    const { inicio, fim } = intervaloDoEclipse(caso.elementos);

    // Fora do eclipse nao ha fase nenhuma, e um instante depois de P1 ja ha.
    assert.equal(faseNoInstante(caso.elementos, inicio - 0.01), "fora", caso.id);
    assert.equal(faseNoInstante(caso.elementos, fim + 0.01), "fora", caso.id);
    assert.notEqual(
      faseNoInstante(caso.elementos, (inicio + fim) / 2),
      "fora",
      caso.id,
    );

    if (contactos.u2 !== undefined) {
      assert.equal(
        faseNoInstante(caso.elementos, caso.elementos.jd_maximo_td),
        "total",
        `${caso.id}: com U2 e U3, o maximo tem de ser total`,
      );
    }
  }
});
