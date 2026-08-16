/** A sombra da Terra, no browser. Porto de `pipeline/lua.py`.
 *
 * Um eclipse lunar reduz-se a meia duzia de numeros, os `ElementosSombra` que o
 * pipeline escreve em cada ficha: os raios da umbra, da penumbra e da Lua, a
 * distancia minima ao eixo da sombra e a velocidade com que a Lua a atravessa.
 * Com eles desenha-se o eclipse inteiro e calcula-se a magnitude em qualquer
 * instante, sem efemerides nem trigonometria esferica.
 *
 * O modelo: vista de frente, a sombra da Terra sao dois circulos concentricos, e
 * a Lua atravessa-os em linha recta e a velocidade constante. Nao e uma
 * simplificacao grosseira, e a geometria com que o proprio catalogo da NASA
 * publica as duracoes: as magnitudes que daqui saem reproduzem as publicadas com
 * erro de dez milesimos.
 *
 * Angulos em graus, tempos em dias julianos. Tem de dar os mesmos numeros que o
 * Python ate ao ultimo bit, e e isso que `test/sombra.test.ts` verifica contra
 * os casos gerados por `pipeline/gerar_golden_lua.py`.
 */

import type { ElementosSombra, NomeContacto } from "./tipos";

/** As tres fases, da mais exterior para a mais interior, com o contacto que
 * abre e o que fecha cada uma. */
export const FASES: {
  fase: "penumbral" | "parcial" | "total";
  entrada: NomeContacto;
  saida: NomeContacto;
}[] = [
  { fase: "penumbral", entrada: "p1", saida: "p4" },
  { fase: "parcial", entrada: "u1", saida: "u4" },
  { fase: "total", entrada: "u2", saida: "u3" },
];

/** Todos os contactos, pela ordem em que acontecem. */
export const ORDEM_DOS_CONTACTOS: NomeContacto[] = [
  "p1",
  "u1",
  "u2",
  "maximo",
  "u3",
  "u4",
  "p4",
];

/** O raio do circulo que a Lua tem de tocar para cada fase comecar. */
function raioDaFase(
  elementos: ElementosSombra,
  fase: "penumbral" | "parcial" | "total",
): number {
  if (fase === "penumbral") return elementos.raio_penumbra + elementos.raio_lua;
  if (fase === "parcial") return elementos.raio_umbra + elementos.raio_lua;
  return elementos.raio_umbra - elementos.raio_lua;
}

/** Meia corda que a Lua percorre dentro de um circulo, ou `null` se nem chega a
 * entrar nele. */
function meiaCorda(raio: number, y: number): number | null {
  const quadrado = raio * raio - y * y;
  return quadrado > 0 ? Math.sqrt(quadrado) : null;
}

/** Onde esta o centro da Lua, em relacao ao centro da sombra, num instante.
 *
 * `x` cresce no sentido do movimento e `y` e constante ao longo da travessia,
 * positivo quando a Lua passa a norte do eixo da sombra. Ambos em graus. */
export function posicaoDaLua(
  elementos: ElementosSombra,
  jdTd: number,
): { x: number; y: number } {
  return {
    x: (jdTd - elementos.jd_maximo_td) * 24 * elementos.velocidade,
    y: elementos.y,
  };
}

/** Magnitude umbral e penumbral num instante qualquer.
 *
 * Fora do eclipse dao negativas, que e a maneira honesta de dizer que a sombra
 * ainda esta ou ja esta a distancia da Lua. */
export function magnitudesNoInstante(
  elementos: ElementosSombra,
  jdTd: number,
): { umbral: number; penumbral: number } {
  const { x, y } = posicaoDaLua(elementos, jdTd);
  const distancia = Math.hypot(x, y);
  const raioLua = elementos.raio_lua;
  return {
    umbral: (elementos.raio_umbra + raioLua - distancia) / (2 * raioLua),
    penumbral: (elementos.raio_penumbra + raioLua - distancia) / (2 * raioLua),
  };
}

/** Os instantes dos contactos que existem, em dias julianos de TD.
 *
 * Um eclipse penumbral traz so P1, o maximo e P4; um parcial acrescenta U1 e
 * U4; so um total tem os sete. */
export function instantesDosContactos(
  elementos: ElementosSombra,
): Partial<Record<NomeContacto, number>> {
  const momentos: Partial<Record<NomeContacto, number>> = {
    maximo: elementos.jd_maximo_td,
  };
  for (const { fase, entrada, saida } of FASES) {
    const meia = meiaCorda(raioDaFase(elementos, fase), elementos.y);
    if (meia === null) continue;
    const metade = meia / elementos.velocidade / 24;
    momentos[entrada] = elementos.jd_maximo_td - metade;
    momentos[saida] = elementos.jd_maximo_td + metade;
  }
  return momentos;
}

/** O intervalo do eclipse, do primeiro ao ultimo contacto, em TD. */
export function intervaloDoEclipse(elementos: ElementosSombra): {
  inicio: number;
  fim: number;
} {
  const contactos = instantesDosContactos(elementos);
  return { inicio: contactos.p1!, fim: contactos.p4! };
}

/** O mesmo instante, em tempo universal. Delta T e a diferenca entre o tempo
 * dos relogios e o tempo uniforme em que a mecanica celeste se calcula. */
export function paraUt(elementos: ElementosSombra, jdTd: number): number {
  return jdTd - elementos.delta_t_s / 86400;
}

export function paraTd(elementos: ElementosSombra, jdUt: number): number {
  return jdUt + elementos.delta_t_s / 86400;
}

/** Em que fase esta o eclipse num instante, para o desenho e para a legenda. */
export function faseNoInstante(
  elementos: ElementosSombra,
  jdTd: number,
): "fora" | "penumbral" | "parcial" | "total" {
  const { umbral, penumbral } = magnitudesNoInstante(elementos, jdTd);
  if (umbral >= 1) return "total";
  if (umbral > 0) return "parcial";
  if (penumbral > 0) return "penumbral";
  return "fora";
}
