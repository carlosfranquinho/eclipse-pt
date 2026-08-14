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
 * recente. Rotulados pelo intervalo e nao pelo numero do seculo, que so
 * confundiria: 1500 e seculo XV pela contagem estrita e "os anos 1500" na
 * linguagem corrente. */
export function periodos(eclipses: EntradaIndice[]): number[] {
  const conjunto = new Set(
    eclipses.map((e) => Math.floor(anoDe(e.data_gregoriana) / 100) * 100),
  );
  return [...conjunto].sort((a, b) => a - b);
}
