/** A escala de sombra das zonas de magnitude.
 *
 * Uma tabela so, usada em dois sitios que tem de concordar: o mapa, que pinta as
 * zonas, e a legenda, que diz o que cada tom quer dizer. Enquanto estiveram
 * separadas, a legenda mostrava um roxo forte onde o mapa punha um veu, e nao
 * havia maneira de casar uma coisa com a outra so de olhar.
 *
 * A cor e sempre a mesma, a da faixa de totalidade. O que muda e a transparencia:
 * a faixa e a sombra cheia, e cada zona seguinte e um pouco mais leve, ate ao
 * veu que sobra onde o Sol mal foi mordido. */

/** Opacidade da propria faixa de totalidade ou anularidade. E o tom mais
 * carregado da escala, e a referencia de todos os outros. */
export const OPACIDADE_FAIXA = 0.68;

/** Opacidade de cada zona, pelo limite inferior da sua magnitude.
 *
 * Cinco degraus, e largos. Sao poucos de proposito: a olho nao se separam mais
 * do que meia duzia de tons da mesma cor, e uma escala que nao se consegue casar
 * com o mapa nao serve para nada. Os degraus crescem para cima, onde a diferenca
 * importa: entre 0,95 e 0,99 o ceu muda, entre 0,2 e 0,5 nao muda nada. */
export const OPACIDADE_POR_ZONA: [number, number][] = [
  [0.2, 0.08],
  [0.5, 0.17],
  [0.8, 0.28],
  [0.95, 0.4],
  [0.99, 0.54],
];

export function opacidadeDaZona(de: number): number {
  let escolhida = OPACIDADE_POR_ZONA[0]![1];
  for (const [limite, opacidade] of OPACIDADE_POR_ZONA) {
    if (de >= limite) escolhida = opacidade;
  }
  return escolhida;
}

/** A mesma tabela na forma que o MapLibre entende: uma escada sobre o limite
 * inferior de cada zona. */
export function escadaDeOpacidade(): unknown[] {
  const escada: unknown[] = [
    "step",
    ["get", "magnitude"],
    OPACIDADE_POR_ZONA[0]![1],
  ];
  for (const [limite, opacidade] of OPACIDADE_POR_ZONA.slice(1)) {
    escada.push(limite, opacidade);
  }
  return escada;
}
