/** A geometria da simulacao do Sol.
 *
 * O desenho do disco solar nao tem contra o que ser comparado: o canon nao
 * publica angulos de posicao, e nao ha aqui um segundo motor que os calcule. O
 * que se pode fazer, e se faz, e exigir coerencia com o que ja esta validado:
 *
 *   - nos quatro contactos, os dois discos tem de estar exactamente tangentes,
 *     por fora no primeiro e no quarto, por dentro no segundo e no terceiro;
 *   - a magnitude desenhada e a magnitude calculada tem de ser a mesma grandeza,
 *     e sao-no por uma identidade simples entre a separacao e os raios;
 *   - a Lua tem de entrar pelo lado oeste do disco solar e sair pelo lado este,
 *     porque e para leste que ela se move em relacao ao Sol;
 *   - o angulo paralactico tem de dar o mesmo por duas vias independentes, uma
 *     a partir do angulo horario e da declinacao, outra a partir do azimute e da
 *     altura.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { anguloParalactico, aspectoEm, faseDoAspeto } from "../src/lib/aspecto.ts";
import {
  circunstanciasNoPonto,
  elementosDe,
  magnitudeEm,
  type Elementos,
} from "../src/lib/besselian.ts";

const GRAU = Math.PI / 180;

const golden = JSON.parse(
  readFileSync(
    fileURLToPath(
      new URL("../../pipeline/tests/golden/circunstancias.json", import.meta.url),
    ),
    "utf8",
  ),
) as {
  eclipses: { id: string; delta_t_s: number; elementos: never }[];
  circunstancias: {
    eclipse: string;
    lugar: string;
    lat: number;
    lon: number;
    esperado: {
      visivel: boolean;
      tipo: string;
      magnitude: number;
      contactos_td: Record<string, number | null>;
      t_maximo_td: number;
    };
  }[];
};

const elementos = new Map<string, Elementos>(
  golden.eclipses.map((e) => [e.id, elementosDe(e)]),
);

const visiveis = golden.circunstancias.filter((c) => c.esperado.visivel);

test("nos contactos exteriores os discos estao tangentes por fora", () => {
  for (const caso of visiveis) {
    const e = elementos.get(caso.eclipse)!;
    for (const chave of ["c1", "c4"] as const) {
      const instante = caso.esperado.contactos_td[chave];
      if (instante === null || instante === undefined) continue;
      const aspecto = aspectoEm(e, instante, caso.lat, caso.lon);
      assert.ok(
        Math.abs(aspecto.separacao - (1 + aspecto.razao)) < 1e-6,
        `${caso.eclipse} em ${caso.lugar}, ${chave}: separacao ${aspecto.separacao} contra ${1 + aspecto.razao}`,
      );
    }
  }
});

test("nos contactos interiores os discos estao tangentes por dentro", () => {
  let centrais = 0;
  for (const caso of visiveis) {
    const e = elementos.get(caso.eclipse)!;
    for (const chave of ["c2", "c3"] as const) {
      const instante = caso.esperado.contactos_td[chave];
      if (instante === null || instante === undefined) continue;
      centrais += 1;
      const aspecto = aspectoEm(e, instante, caso.lat, caso.lon);
      assert.ok(
        Math.abs(aspecto.separacao - Math.abs(aspecto.razao - 1)) < 1e-6,
        `${caso.eclipse} em ${caso.lugar}, ${chave}: separacao ${aspecto.separacao} contra ${Math.abs(aspecto.razao - 1)}`,
      );
    }
  }
  assert.ok(centrais >= 10, "poucos contactos interiores para o teste valer");
});

test("o desenho e a magnitude dizem a mesma coisa", () => {
  // magnitude = (1 + razao - separacao) / 2, por definicao das duas grandezas.
  for (const caso of visiveis) {
    const e = elementos.get(caso.eclipse)!;
    const aspecto = aspectoEm(e, caso.esperado.t_maximo_td, caso.lat, caso.lon);
    const daGeometria = (1 + aspecto.razao - aspecto.separacao) / 2;
    assert.ok(
      Math.abs(daGeometria - caso.esperado.magnitude) < 1e-9,
      `${caso.eclipse} em ${caso.lugar}: ${daGeometria} contra ${caso.esperado.magnitude}`,
    );
  }
});

test("a fase desenhada e o tipo local concordam", () => {
  for (const caso of visiveis) {
    const e = elementos.get(caso.eclipse)!;
    const aspecto = aspectoEm(e, caso.esperado.t_maximo_td, caso.lat, caso.lon);
    assert.equal(
      faseDoAspeto(aspecto),
      caso.esperado.tipo,
      `${caso.eclipse} em ${caso.lugar}`,
    );
  }
});

test("a Lua atravessa o disco de oeste para este", () => {
  // A Lua move-se para leste em relacao ao Sol, sempre: a sombra corre pelo
  // plano fundamental a meio raio terrestre por hora e a rotacao da Terra nunca
  // chega a metade disso. Portanto `u`, que e a componente para leste, so pode
  // crescer entre o primeiro contacto e o quarto.
  //
  // Onde exactamente a Lua entra e sai ja depende do eclipse. Num eclipse fundo
  // entra pelo lado oeste do disco e sai pelo lado este; num que apenas roce o
  // Sol, entra e sai quase no mesmo sitio e os dois contactos podem cair do
  // mesmo lado. Por isso a segunda parte so se exige a partir de meia magnitude.
  for (const caso of visiveis) {
    const e = elementos.get(caso.eclipse)!;
    const primeiro = caso.esperado.contactos_td.c1;
    const ultimo = caso.esperado.contactos_td.c4;
    if (primeiro === null || ultimo === null) continue;

    const entrada = aspectoEm(e, primeiro!, caso.lat, caso.lon).angulo_posicao;
    const saida = aspectoEm(e, ultimo!, caso.lat, caso.lon).angulo_posicao;
    assert.ok(
      magnitudeEm(e, ultimo!, caso.lat, caso.lon).u >
        magnitudeEm(e, primeiro!, caso.lat, caso.lon).u,
      `${caso.eclipse} em ${caso.lugar}: a Lua recuou para oeste`,
    );

    if (caso.esperado.magnitude < 0.5) continue;
    assert.ok(
      entrada > 180 && entrada < 360,
      `${caso.eclipse} em ${caso.lugar}: primeiro contacto a ${entrada} graus`,
    );
    assert.ok(
      saida > 0 && saida < 180,
      `${caso.eclipse} em ${caso.lugar}: quarto contacto a ${saida} graus`,
    );
  }
});

test("o angulo paralactico sai igual por duas vias", () => {
  // A primeira via e a formula do Meeus, com o angulo horario e a declinacao. A
  // segunda aplica a lei dos cossenos ao lado polo-zenite do mesmo triangulo, e
  // troca o angulo horario pela altura do Sol:
  //
  //   cos q = (sin(lat) - sin(alt) sin(dec)) / (cos(alt) cos(dec))
  //
  // A lei dos cossenos so da o valor absoluto. O sinal vem de o zenite ficar a
  // leste do norte depois da passagem meridiana e a oeste antes dela.
  for (const caso of visiveis) {
    const e = elementos.get(caso.eclipse)!;
    const m = magnitudeEm(e, caso.esperado.t_maximo_td, caso.lat, caso.lon);

    const pelaHora = anguloParalactico(caso.lat, m.angulo_horario, m.declinacao);

    const lat = caso.lat * GRAU;
    const alt = m.alt_sol * GRAU;
    const dec = m.declinacao * GRAU;
    const cosseno =
      (Math.sin(lat) - Math.sin(alt) * Math.sin(dec)) /
      (Math.cos(alt) * Math.cos(dec));
    const pelaAltura =
      Math.sign(m.angulo_horario) * Math.acos(limitar(cosseno));

    assert.ok(
      Math.abs(pelaHora - pelaAltura) < 1e-7,
      `${caso.eclipse} em ${caso.lugar}: ${pelaHora} contra ${pelaAltura}`,
    );
  }
});

test("com o Sol no zenite o desenho nao se desfaz", () => {
  // O angulo paralactico e indeterminado no zenite, e o desenho tem de continuar
  // a sair. Procura-se um caso com o Sol bem alto entre os casos de ouro.
  let maisAlto = { alt: -90, aspecto: null as ReturnType<typeof aspectoEm> | null };
  for (const caso of visiveis) {
    const e = elementos.get(caso.eclipse)!;
    const aspecto = aspectoEm(e, caso.esperado.t_maximo_td, caso.lat, caso.lon);
    if (aspecto.alt_sol > maisAlto.alt) maisAlto = { alt: aspecto.alt_sol, aspecto };
  }
  assert.ok(maisAlto.alt > 45, "sem casos com o Sol alto");
  assert.ok(Number.isFinite(maisAlto.aspecto!.x));
  assert.ok(Number.isFinite(maisAlto.aspecto!.y));
});

test("o afastamento desenhado e o mesmo em qualquer instante", () => {
  // x e y sao o vector separacao decomposto: o seu comprimento tem de bater
  // certo com a separacao, sempre.
  for (const caso of visiveis.slice(0, 60)) {
    const e = elementos.get(caso.eclipse)!;
    const circunstancias = circunstanciasNoPonto(e, caso.lat, caso.lon);
    for (const desvio of [-1, -0.25, 0, 0.25, 1]) {
      const aspecto = aspectoEm(
        e,
        circunstancias.t_maximo_td + desvio,
        caso.lat,
        caso.lon,
      );
      proximo(
        Math.hypot(aspecto.x, aspecto.y),
        aspecto.separacao,
        1e-12,
        `${caso.eclipse} em ${caso.lugar}`,
      );
    }
  }
});

function proximo(a: number, b: number, tolerancia: number, onde: string): void {
  assert.ok(Math.abs(a - b) <= tolerancia, `${onde}: ${a} contra ${b}`);
}

function limitar(valor: number): number {
  return Math.min(1, Math.max(-1, valor));
}
