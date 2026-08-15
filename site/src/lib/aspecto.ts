/** O aspeto do Sol visto de um ponto, num instante: onde esta a Lua sobre ele.
 *
 * O nucleo besseliano ja da tudo o que e preciso. A posicao do eixo da sombra em
 * relacao ao observador, `(u, v)`, e um vector no plano fundamental, que e
 * perpendicular a direccao do Sol; dividido pelo raio do cone da penumbra no
 * plano do observador, e exactamente o afastamento aparente entre o centro do
 * Sol e o centro da Lua, medido em raios solares. Nao ha aqui nenhuma astronomia
 * nova: ha uma mudanca de eixos.
 *
 * Duas rotacoes separam esse vector do desenho:
 *
 * 1. `(u, v)` vem com `u` para leste e `v` para norte celeste. O angulo de
 *    posicao da Lua, contado do norte para leste, e portanto `atan2(u, v)`.
 * 2. Ninguem ve o ceu com o norte celeste para cima. Ve-o com o zenite para
 *    cima, e o zenite esta a um angulo paralactico do norte. Subtraindo-o
 *    obtem-se o angulo do vertice, que e o que se desenha.
 *
 * O desenho fica entao com o zenite para cima e o leste a esquerda, que e a
 * convencao de qualquer carta celeste e o que se ve de facto ao olhar para o
 * Sol. */

// Os modulos de `src/lib` importam-se com a extensao a vista, ao contrario dos
// componentes: assim os mesmos ficheiros correm tal e qual sob `node --test`,
// que resolve os caminhos como o Node e nao como o empacotador.
import { magnitudeEm, type Elementos } from "./besselian.ts";

const GRAU = Math.PI / 180.0;

export interface AspectoDoSol {
  /** Afastamento entre os centros dos dois discos, em raios solares. Zero e
   * coincidencia, 1 + `razao` e o instante de contacto exterior. */
  separacao: number;
  /** Razao entre os diametros aparentes da Lua e do Sol. */
  razao: number;
  /** Centro da Lua em relacao ao centro do Sol, em raios solares, ja no sistema
   * do desenho: `x` para a direita e `y` para baixo, como em SVG. */
  x: number;
  y: number;
  magnitude: number;
  obscuracao: number;
  /** Angulo de posicao da Lua, em graus, contado do norte celeste para leste. */
  angulo_posicao: number;
  /** O mesmo angulo, mas contado a partir do zenite. E o que um observador
   * consegue apontar sem instrumentos: "a Lua entra por cima e a direita". */
  angulo_vertice: number;
  /** Angulo entre o norte celeste e o zenite, visto do Sol. */
  angulo_paralactico: number;
  alt_sol: number;
  az_sol: number;
  sol_visivel: boolean;
  /** Se os discos chegam a tocar-se neste instante. */
  ha_contacto: boolean;
}

/** Angulo paralactico: por onde fica o zenite, visto do astro.
 *
 * Formula classica a partir do angulo horario e da declinacao. Ha uma segunda
 * via, a partir do azimute e da altura, que `test/aspecto.test.ts` usa para
 * confirmar esta. */
export function anguloParalactico(
  latGraus: number,
  anguloHorarioGraus: number,
  declinacaoGraus: number,
): number {
  const lat = latGraus * GRAU;
  const h = anguloHorarioGraus * GRAU;
  const d = declinacaoGraus * GRAU;
  return Math.atan2(
    Math.sin(h),
    Math.tan(lat) * Math.cos(d) - Math.sin(d) * Math.cos(h),
  );
}

/** O aspeto do Sol num ponto e num instante `t` dos elementos besselianos. */
export function aspectoEm(
  e: Elementos,
  t: number,
  latGraus: number,
  lonGraus: number,
  alturaM = 0,
): AspectoDoSol {
  const m = magnitudeEm(e, t, latGraus, lonGraus, alturaM);

  // Raios aparentes nas unidades de `u` e `v`. Num eclipse total `l2_obs` e
  // negativo e o raio lunar sai maior que o solar, como deve ser.
  const raioSol = (m.l1_obs + m.l2_obs) / 2.0;
  const raioLua = (m.l1_obs - m.l2_obs) / 2.0;

  const separacao = m.separacao / raioSol;
  const razao = raioLua / raioSol;

  const posicao = Math.atan2(m.u, m.v);
  const paralactico = anguloParalactico(
    latGraus,
    m.angulo_horario,
    m.declinacao,
  );
  const vertice = posicao - paralactico;

  return {
    separacao,
    razao,
    // Leste a esquerda, zenite para cima: em SVG, `x` cresce para a direita e
    // `y` para baixo, e por isso os dois sinais negativos.
    x: -separacao * Math.sin(vertice),
    y: -separacao * Math.cos(vertice),
    magnitude: m.magnitude,
    obscuracao: m.obscuracao,
    angulo_posicao: emGraus(posicao),
    angulo_vertice: emGraus(vertice),
    angulo_paralactico: emGraus(paralactico),
    alt_sol: m.alt_sol,
    az_sol: m.az_sol,
    sol_visivel: m.sol_visivel,
    ha_contacto: separacao <= 1.0 + razao,
  };
}

/** Que nome dar ao que se esta a ver, para acompanhar o desenho. */
export function faseDoAspeto(
  aspecto: AspectoDoSol,
): "nenhuma" | "parcial" | "total" | "anular" {
  if (!aspecto.ha_contacto) return "nenhuma";
  if (aspecto.separacao > Math.abs(aspecto.razao - 1.0)) return "parcial";
  return aspecto.razao >= 1.0 ? "total" : "anular";
}

function emGraus(radianos: number): number {
  return (((radianos / GRAU) % 360.0) + 360.0) % 360.0;
}
