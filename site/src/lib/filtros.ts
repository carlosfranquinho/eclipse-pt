/** Atributos que ligam cada elemento filtravel aos filtros da pagina inicial.
 *
 * A lista e a linha temporal mostram os mesmos eclipses de duas maneiras. Em
 * vez de duplicar a logica, ambas marcam os seus elementos com os mesmos
 * `data-*` e o script dos filtros trata os dois de uma so vez. */

import type { EntradaCatalogo } from "./tipos";
import { anoDe, funduraEmPortugal } from "./formatacao";

export function atributosFiltro(
  eclipse: EntradaCatalogo,
): Record<string, string> {
  const ano = anoDe(eclipse.data_gregoriana);
  return {
    "data-eclipse": `${eclipse.familia}:${eclipse.id}`,
    "data-familia": eclipse.familia,
    "data-tipo": eclipse.tipo,
    "data-ano": String(ano),
    "data-periodo": String(Math.floor(ano / 100) * 100),
    // A profundidade numa escala so, para o deslizador nao ter de saber de que
    // familia e cada linha. Nunca negativa: um penumbral raso da magnitude
    // umbral negativa, e o deslizador no zero deixa passar tudo.
    "data-magnitude": Math.max(0, funduraEmPortugal(eclipse)).toFixed(4),
    "data-territorios": eclipse.pt.territorios_visiveis.join(" "),
    // So o Sol tem faixa central. Nos lunares o campo fica a zero e o filtro
    // da faixa exclui-os, que e o que faz sentido: pedir faixa central e pedir
    // eclipses solares.
    "data-faixa":
      eclipse.familia === "solar" && eclipse.pt.faixa_central ? "1" : "0",
    "data-data": eclipse.data_gregoriana,
  };
}

/** Os intervalos de cem anos cobertos pelo catalogo, do mais antigo ao mais
 * recente. No filtro sao rotulados pelo intervalo de anos, que e o que nao
 * deixa duvidas: 1500 e seculo XV pela contagem estrita e "os anos 1500" na
 * linguagem corrente. */
export function periodos(eclipses: EntradaCatalogo[]): number[] {
  const conjunto = new Set(
    eclipses.map((e) => Math.floor(anoDe(e.data_gregoriana) / 100) * 100),
  );
  return [...conjunto].sort((a, b) => a - b);
}

export interface GrupoSeculo {
  /** Primeiro ano do intervalo: 1500, 1600, ... */
  inicio: number;
  fim: number;
  /** Numero do seculo em algarismos romanos. Os anos 1500 sao o seculo XVI. */
  romano: string;
  eclipses: EntradaCatalogo[];
}

/** O catalogo repartido por seculos, do mais antigo ao mais recente.
 *
 * Mil anos numa lista unica sao ilegiveis. Por seculo, cada bloco tem algumas
 * dezenas de eclipses e o leitor escolhe onde entra. O rotulo traz o numero do
 * seculo e o intervalo de anos ao lado, para as duas contagens conviverem sem
 * mal-entendidos. */
export function porSeculo(eclipses: EntradaCatalogo[]): GrupoSeculo[] {
  const grupos = new Map<number, EntradaCatalogo[]>();
  for (const eclipse of eclipses) {
    const inicio = Math.floor(anoDe(eclipse.data_gregoriana) / 100) * 100;
    const lista = grupos.get(inicio);
    if (lista) lista.push(eclipse);
    else grupos.set(inicio, [eclipse]);
  }

  return [...grupos.entries()]
    .sort(([a], [b]) => a - b)
    .map(([inicio, lista]) => ({
      inicio,
      fim: inicio + 99,
      romano: numeroRomano(inicio / 100 + 1),
      eclipses: lista,
    }));
}

const ROMANOS: [number, string][] = [
  [1000, "M"],
  [900, "CM"],
  [500, "D"],
  [400, "CD"],
  [100, "C"],
  [90, "XC"],
  [50, "L"],
  [40, "XL"],
  [10, "X"],
  [9, "IX"],
  [5, "V"],
  [4, "IV"],
  [1, "I"],
];

export function numeroRomano(valor: number): string {
  let resto = valor;
  let saida = "";
  for (const [numero, simbolo] of ROMANOS) {
    while (resto >= numero) {
      saida += simbolo;
      resto -= numero;
    }
  }
  return saida;
}

/** Em que escalao de profundidade cai uma magnitude, de 1 a 4.
 *
 * Serve para dar cor a grelha da linha temporal: quatro degraus chegam para se
 * ver a olho a diferenca entre um eclipse que mal se nota e um que escurece o
 * dia, e mais degraus so fariam ruido. Os cortes estao onde a experiencia muda:
 * abaixo de 0,4 e preciso saber que ha eclipse para dar por ele, acima de 0,95 a
 * luz ja e outra.
 */
export function nivelDeMagnitude(magnitude: number): 1 | 2 | 3 | 4 {
  if (magnitude < 0.4) return 1;
  if (magnitude < 0.7) return 2;
  if (magnitude < 0.95) return 3;
  return 4;
}


/** O mesmo escalao, mas para um eclipse lunar.
 *
 * A escala nao pode ser a solar: a magnitude umbral passa de 1 nos totais, e
 * qualquer penumbral tem magnitude umbral negativa, o que num criterio pensado
 * para o Sol daria sempre o degrau mais baixo e apagava a diferenca entre um
 * penumbral raso e um que quase toca a umbra. Os degraus estao onde a
 * experiencia muda: sem umbra, uma dentada, meia Lua, e a Lua toda dentro da
 * sombra.
 */
export function nivelLunar(entrada: {
  pt: { magnitude_umbral: number; magnitude_penumbral: number };
}): 1 | 2 | 3 | 4 {
  const umbral = entrada.pt.magnitude_umbral;
  if (umbral <= 0) return 1;
  if (umbral < 0.5) return 2;
  if (umbral < 1) return 3;
  return 4;
}

/** O escalao de profundidade de qualquer entrada do catalogo. */
export function nivelDeFundura(entrada: EntradaCatalogo): 1 | 2 | 3 | 4 {
  return entrada.familia === "lunar"
    ? nivelLunar(entrada)
    : nivelDeMagnitude(entrada.pt.magnitude_max);
}
