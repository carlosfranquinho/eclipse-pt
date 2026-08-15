/** Atributos que ligam cada elemento filtravel aos filtros da pagina inicial.
 *
 * A lista e a linha temporal mostram os mesmos eclipses de duas maneiras. Em
 * vez de duplicar a logica, ambas marcam os seus elementos com os mesmos
 * `data-*` e o script dos filtros trata os dois de uma so vez. */

import type { EntradaIndice } from "./tipos";
import { anoDe } from "./formatacao";

export function atributosFiltro(eclipse: EntradaIndice): Record<string, string> {
  const ano = anoDe(eclipse.data_gregoriana);
  return {
    "data-eclipse": eclipse.id,
    "data-tipo": eclipse.tipo,
    "data-ano": String(ano),
    "data-periodo": String(Math.floor(ano / 100) * 100),
    "data-magnitude": eclipse.pt.magnitude_max.toFixed(4),
    "data-territorios": eclipse.pt.territorios_visiveis.join(" "),
    "data-faixa": eclipse.pt.faixa_central ? "1" : "0",
    "data-data": eclipse.data_gregoriana,
  };
}

/** Os intervalos de cem anos cobertos pelo catalogo, do mais antigo ao mais
 * recente. No filtro sao rotulados pelo intervalo de anos, que e o que nao
 * deixa duvidas: 1500 e seculo XV pela contagem estrita e "os anos 1500" na
 * linguagem corrente. */
export function periodos(eclipses: EntradaIndice[]): number[] {
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
  eclipses: EntradaIndice[];
}

/** O catalogo repartido por seculos, do mais antigo ao mais recente.
 *
 * Mil anos numa lista unica sao ilegiveis. Por seculo, cada bloco tem algumas
 * dezenas de eclipses e o leitor escolhe onde entra. O rotulo traz o numero do
 * seculo e o intervalo de anos ao lado, para as duas contagens conviverem sem
 * mal-entendidos. */
export function porSeculo(eclipses: EntradaIndice[]): GrupoSeculo[] {
  const grupos = new Map<number, EntradaIndice[]>();
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
