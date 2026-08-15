/** Os tres territorios, as suas caixas no mapa e a que territorio pertence um
 * ponto.
 *
 * Vive a parte de `dados.ts` porque tambem corre no browser: o calculo ao vivo
 * precisa de saber em que territorio caiu o cursor para escolher o fuso horario,
 * e `dados.ts` le do disco com `node:fs`, que no browser nao existe. */

import type { Territorio } from "./tipos";

export const TERRITORIOS: Territorio[] = ["continente", "acores", "madeira"];

/** Caixa de enquadramento por territorio, em [oeste, sul, este, norte].
 * Fixa aqui e nao calculada do GeoJSON para o mapa abrir sempre igual. */
export const CAIXAS: Record<Territorio, [number, number, number, number]> = {
  continente: [-9.6, 36.9, -6.1, 42.2],
  acores: [-31.4, 36.8, -24.9, 39.9],
  madeira: [-17.4, 32.3, -16.2, 33.2],
};

/** A que territorio pertence um ponto, para efeitos de hora legal.
 *
 * As tres caixas nao se tocam, e no mar em volta de cada uma vale o fuso desse
 * arquipelago. Fora de todas fica o continente, que e o que faz sentido para um
 * ponto na fronteira com Espanha ou ao largo da costa. Isto decide o fuso, nao
 * a soberania: um ponto no mar nao pertence a concelho nenhum, mas a hora que
 * ali se mostra tem de ser a de alguma parte. */
export function territorioDe(lat: number, lon: number): Territorio {
  for (const territorio of TERRITORIOS) {
    const [oeste, sul, este, norte] = CAIXAS[territorio];
    if (lon >= oeste && lon <= este && lat >= sul && lat <= norte) {
      return territorio;
    }
  }
  // Margem generosa a volta das ilhas, para o mar em redor nao passar a horas
  // do continente a poucos quilometros da costa.
  const margem = 3.0;
  for (const territorio of ["acores", "madeira"] as Territorio[]) {
    const [oeste, sul, este, norte] = CAIXAS[territorio];
    if (
      lon >= oeste - margem &&
      lon <= este + margem &&
      lat >= sul - margem &&
      lat <= norte + margem
    ) {
      return territorio;
    }
  }
  return "continente";
}
