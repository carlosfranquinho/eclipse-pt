/** Circunstancias locais de um eclipse a partir dos elementos besselianos.
 *
 * Porto para TypeScript de `pipeline/besselian.py`, com um objectivo estreito:
 * o que o browser precisa para responder a um ponto do mapa. A magnitude, a
 * obscuracao, os quatro contactos, a altura e o azimute do Sol. A geometria da
 * faixa fica do lado do Python, porque o mapa recebe-a ja desenhada em GeoJSON
 * e nada ganharia em recalcula-la.
 *
 * As duas implementacoes partilham os mesmos coeficientes e o mesmo algoritmo,
 * por isso os numeros do hover e os da ficha sao os mesmos por construcao. O que
 * garante que assim continua e `test/besselian.test.ts`, que verifica algumas
 * centenas de casos gerados pelo Python em `pipeline/gerar_golden.py`.
 *
 * Quem mexer aqui tem de mexer no Python, e vice-versa. Em particular, o numero
 * de iteracoes e as condicoes de paragem sao parte do contrato: os dois lados
 * convergem para o mesmo valor porque dao exactamente os mesmos passos.
 *
 * Referencias:
 *   Explanatory Supplement to the Astronomical Ephemeris (1961), cap. 9.
 *   Jean Meeus, Astronomical Algorithms (2a ed.), cap. 54, "Solar Eclipses".
 *
 * Convencoes, as mesmas do modulo Python:
 *   - `t` e o tempo em horas de TDT contadas a partir de `t0_td`.
 *   - Longitudes positivas para leste.
 *   - `x`, `y`, `l1`, `l2` em raios equatoriais terrestres.
 *   - `d` e `mu` em graus nos coeficientes, radianos no calculo.
 *   - Angulos devolvidos ao chamador sempre em graus.
 */

import type { ElementosBesselianos, TipoLocal } from "./tipos";

/** Elipsoide terrestre, com os valores classicos usados no canon. */
export const RAIO_EQUATORIAL_KM = 6378.14;
const ACHATAMENTO = 0.99664719; // b/a, ou seja sqrt(1 - e^2)

/** Conversao de DeltaT (segundos) para o deslocamento em longitude entre o
 * meridiano de efemerides e o de Greenwich. 1,0027379 e a razao entre o dia
 * sideral e o dia solar, e 240 os segundos de tempo por grau de rotacao. */
const GRAUS_POR_SEGUNDO_DELTA_T = 1.0027379 / 240.0;

const GRAU = Math.PI / 180.0;

/** Os elementos de um eclipse mais o ΔT com que se converte tempo de efemerides
 * em tempo universal. Equivalente a dataclass `Elementos` do Python. */
export interface Elementos {
  t0_td: number;
  x: number[];
  y: number[];
  d: number[];
  mu: number[];
  l1: number[];
  l2: number[];
  tan_f1: number;
  tan_f2: number;
  delta_t_s: number;
}

/** Junta os elementos e o ΔT de uma ficha de eclipse num so objecto. */
export function elementosDe(eclipse: {
  elementos: ElementosBesselianos;
  delta_t_s: number;
}): Elementos {
  const e = eclipse.elementos;
  return {
    t0_td: e.t0_td,
    x: e.x,
    y: e.y,
    d: e.d,
    mu: e.mu,
    l1: e.l1,
    l2: e.l2,
    tan_f1: e.tan_f1,
    tan_f2: e.tan_f2,
    delta_t_s: eclipse.delta_t_s,
  };
}

/** Posicao e geometria da sombra no plano fundamental, num instante. */
export interface EstadoSombra {
  t: number;
  x: number;
  y: number;
  dx: number;
  dy: number;
  d: number; // radianos
  dd: number; // radianos por hora
  mu: number; // radianos
  dmu: number; // radianos por hora
  l1: number;
  l2: number;
}

/** Avalia o polinomio `coef` em `t`, com os coeficientes por potencia crescente. */
function poli(coef: number[], t: number): number {
  let resultado = 0;
  for (let potencia = 0; potencia < coef.length; potencia += 1) {
    resultado += coef[potencia]! * Math.pow(t, potencia);
  }
  return resultado;
}

/** Avalia a derivada do polinomio `coef` em `t`, por hora. */
function derivadaPoli(coef: number[], t: number): number {
  let resultado = 0;
  for (let potencia = 1; potencia < coef.length; potencia += 1) {
    resultado += potencia * coef[potencia]! * Math.pow(t, potencia - 1);
  }
  return resultado;
}

/** Avalia os polinomios besselianos no instante `t` (horas TDT desde t0). */
export function estadoSombra(e: Elementos, t: number): EstadoSombra {
  return {
    t,
    x: poli(e.x, t),
    y: poli(e.y, t),
    dx: derivadaPoli(e.x, t),
    dy: derivadaPoli(e.y, t),
    d: poli(e.d, t) * GRAU,
    dd: derivadaPoli(e.d, t) * GRAU,
    mu: poli(e.mu, t) * GRAU,
    dmu: derivadaPoli(e.mu, t) * GRAU,
    l1: poli(e.l1, t),
    l2: poli(e.l2, t),
  };
}

/** Converte latitude geodetica em `rho*sin(phi')` e `rho*cos(phi')`, as
 * coordenadas do observador em raios equatoriais terrestres. Meeus, 11.1. */
export function geodeticaParaGeocentrica(
  latGraus: number,
  alturaM = 0,
): { rhoSin: number; rhoCos: number } {
  const lat = latGraus * GRAU;
  const u = Math.atan(ACHATAMENTO * Math.tan(lat));
  const escala = alturaM / (RAIO_EQUATORIAL_KM * 1000.0);
  return {
    rhoSin: ACHATAMENTO * Math.sin(u) + escala * Math.sin(lat),
    rhoCos: Math.cos(u) + escala * Math.cos(lat),
  };
}

/** Angulo horario local do eixo da sombra, em radianos.
 *
 * `mu` esta referido ao meridiano de efemerides, que roda com o TDT. A correccao
 * de ΔT traz o resultado para o meridiano de Greenwich, ou seja para o Tempo
 * Universal, que e o que interessa ao observador. */
function anguloHorario(s: EstadoSombra, e: Elementos, lonGraus: number): number {
  const correccao = GRAUS_POR_SEGUNDO_DELTA_T * e.delta_t_s;
  return s.mu + (lonGraus - correccao) * GRAU;
}

/** Raios da penumbra e da umbra no plano do observador.
 *
 * Os `l1` e `l2` tabelados valem no plano fundamental, que passa pelo centro da
 * Terra. O observador esta a uma distancia `zeta` desse plano, mais perto da
 * Lua, e o cone e mais estreito ai. */
function raiosCones(
  s: EstadoSombra,
  e: Elementos,
  zeta: number,
): { l1Obs: number; l2Obs: number } {
  return { l1Obs: s.l1 - zeta * e.tan_f1, l2Obs: s.l2 - zeta * e.tan_f2 };
}

/** Fraccao da area do disco solar coberta, para dois discos que se cruzam. */
function obscuracaoDiscos(
  raioSol: number,
  raioLua: number,
  separacao: number,
): number {
  const rs = raioSol;
  const rm = raioLua;
  const sep = separacao;

  const cosA = (sep * sep + rs * rs - rm * rm) / (2.0 * sep * rs);
  const cosB = (sep * sep + rm * rm - rs * rs) / (2.0 * sep * rm);
  const alfa = Math.acos(limitar(cosA, -1.0, 1.0));
  const beta = Math.acos(limitar(cosB, -1.0, 1.0));
  const area =
    rs * rs * (alfa - Math.sin(2.0 * alfa) / 2.0) +
    rm * rm * (beta - Math.sin(2.0 * beta) / 2.0);
  const parcial = area / (Math.PI * rs * rs);

  // A ordem e a mesma do Python: parte-se do caso geral e os casos degenerados
  // sobrepoem-se-lhe, porque a formula dos dois discos nao vale quando um esta
  // todo dentro do outro nem quando nao se tocam.
  let resultado = Number.isFinite(parcial) ? parcial : 0.0;
  if (sep <= rs - rm) resultado = (rm / rs) ** 2; // anular
  if (sep <= rm - rs) resultado = 1.0; // total
  if (sep >= rs + rm) resultado = 0.0; // sem sobreposicao
  return limitar(resultado, 0.0, 1.0);
}

/** Magnitude e grandezas associadas num ponto e instante. */
export interface Magnitude {
  magnitude: number;
  obscuracao: number;
  alt_sol: number;
  az_sol: number;
  sol_visivel: boolean;
  ha_eclipse: boolean;
  central: boolean;
  total: boolean;
  separacao: number;
  l1_obs: number;
  l2_obs: number;
  zeta: number;
}

/** O que se ve num ponto, num instante.
 *
 * A magnitude devolvida e puramente geometrica: nao se anula quando o Sol esta
 * abaixo do horizonte. Quem quiser o que um observador realmente veria tem de
 * olhar tambem para `sol_visivel`. */
export function magnitudeEm(
  e: Elementos,
  t: number,
  latGraus: number,
  lonGraus: number,
  alturaM = 0,
): Magnitude {
  const s = estadoSombra(e, t);
  const { rhoSin, rhoCos } = geodeticaParaGeocentrica(latGraus, alturaM);
  const h = anguloHorario(s, e, lonGraus);

  const xi = rhoCos * Math.sin(h);
  const eta = rhoSin * Math.cos(s.d) - rhoCos * Math.cos(h) * Math.sin(s.d);
  const zeta = rhoSin * Math.sin(s.d) + rhoCos * Math.cos(h) * Math.cos(s.d);
  const { l1Obs, l2Obs } = raiosCones(s, e, zeta);

  const u = s.x - xi;
  const v = s.y - eta;
  const m = Math.hypot(u, v);

  // Raios aparentes do Sol e da Lua nas mesmas unidades que `m`. Para um eclipse
  // total `l2Obs` e negativo, e o raio lunar sai maior que o solar.
  const raioSol = (l1Obs + l2Obs) / 2.0;
  const raioLua = (l1Obs - l2Obs) / 2.0;

  const lat = latGraus * GRAU;
  const alt = Math.asin(
    limitar(
      Math.sin(lat) * Math.sin(s.d) + Math.cos(lat) * Math.cos(s.d) * Math.cos(h),
      -1.0,
      1.0,
    ),
  );
  const az = Math.atan2(
    -Math.sin(h),
    Math.cos(lat) * Math.tan(s.d) - Math.sin(lat) * Math.cos(h),
  );

  const solVisivel = alt > 0.0;
  const dentroDaPenumbra = m < l1Obs;

  return {
    magnitude: dentroDaPenumbra
      ? Math.max((l1Obs - m) / (l1Obs + l2Obs), 0.0)
      : 0.0,
    obscuracao: dentroDaPenumbra ? obscuracaoDiscos(raioSol, raioLua, m) : 0.0,
    alt_sol: alt / GRAU,
    az_sol: modulo(az / GRAU, 360.0),
    sol_visivel: solVisivel,
    ha_eclipse: dentroDaPenumbra && solVisivel,
    central: m < Math.abs(l2Obs) && solVisivel,
    total: m < Math.abs(l2Obs) && solVisivel && l2Obs < 0.0,
    separacao: m,
    l1_obs: l1Obs,
    l2_obs: l2Obs,
    zeta,
  };
}

/** Posicao relativa do observador ao eixo da sombra, e a sua taxa de variacao. */
function uVeDerivadas(
  e: Elementos,
  t: number,
  latGraus: number,
  lonGraus: number,
  alturaM: number,
): {
  u: number;
  v: number;
  du: number;
  dv: number;
  zeta: number;
  s: EstadoSombra;
} {
  const s = estadoSombra(e, t);
  const { rhoSin, rhoCos } = geodeticaParaGeocentrica(latGraus, alturaM);
  const h = anguloHorario(s, e, lonGraus);

  const xi = rhoCos * Math.sin(h);
  const eta = rhoSin * Math.cos(s.d) - rhoCos * Math.cos(h) * Math.sin(s.d);
  const zeta = rhoSin * Math.sin(s.d) + rhoCos * Math.cos(h) * Math.cos(s.d);

  // A derivada de xi so depende da rotacao da Terra; a de eta tambem do
  // movimento em declinacao do eixo da sombra.
  const dXi = s.dmu * rhoCos * Math.cos(h);
  const dEta = s.dmu * xi * Math.sin(s.d) - zeta * s.dd;

  return { u: s.x - xi, v: s.y - eta, du: s.dx - dXi, dv: s.dy - dEta, zeta, s };
}

/** Itera ate ao instante de maximo eclipse no ponto dado.
 *
 * Oito iteracoes de Newton sobre a condicao de minimo da distancia ao eixo da
 * sombra, exactamente como no Python. */
function instanteMaximoNewton(
  e: Elementos,
  latGraus: number,
  lonGraus: number,
  alturaM: number,
  tInicial: number,
): number {
  let t = tInicial;
  for (let i = 0; i < 8; i += 1) {
    const { u, v, du, dv } = uVeDerivadas(e, t, latGraus, lonGraus, alturaM);
    const n2 = du * du + dv * dv;
    if (n2 === 0) break;
    const tau = -(u * du + v * dv) / n2;
    t += tau;
    if (Math.abs(tau) < 1e-9) break;
  }
  return t;
}

/** Instante de um contacto, ou null se esse contacto nao ocorre.
 *
 * `interior` escolhe o cone da umbra (segundo e terceiro contactos) em vez do da
 * penumbra (primeiro e quarto). `antes` escolhe o contacto anterior ao maximo. */
function contacto(
  e: Elementos,
  latGraus: number,
  lonGraus: number,
  alturaM: number,
  tMaximo: number,
  interior: boolean,
  antes: boolean,
): number | null {
  let t = tMaximo;
  for (let i = 0; i < 12; i += 1) {
    const { u, v, du, dv, zeta, s } = uVeDerivadas(
      e,
      t,
      latGraus,
      lonGraus,
      alturaM,
    );
    const { l1Obs, l2Obs } = raiosCones(s, e, zeta);
    const raio = interior ? Math.abs(l2Obs) : l1Obs;

    const n = Math.hypot(du, dv);
    if (n === 0) return null;
    // Distancia perpendicular entre o observador e a trajectoria do eixo.
    const desvio = (u * dv - v * du) / n;
    const sobRadical = raio * raio - desvio * desvio;
    if (sobRadical < 0) return null;
    const deslocamento = Math.sqrt(sobRadical) / n;
    let tau = -(u * du + v * dv) / (n * n);
    tau = antes ? tau - deslocamento : tau + deslocamento;
    const tNovo = t + tau;
    if (Math.abs(tNovo - t) < 1e-9) {
      t = tNovo;
      break;
    }
    t = tNovo;
  }
  return t;
}

export interface Contactos {
  c1: number | null;
  c2: number | null;
  c3: number | null;
  c4: number | null;
}

/** Circunstancias completas do eclipse num ponto. Os instantes vao em horas de
 * TDT contadas desde `t0_td`; converter para UT subtraindo `delta_t_s / 3600`. */
export interface Circunstancias {
  visivel: boolean;
  magnitude: number;
  obscuracao: number;
  razao_diametros: number | null;
  tipo: TipoLocal;
  t_maximo_td: number;
  contactos_td: Contactos;
  duracao_central_s: number | null;
  alt_sol: number;
  az_sol: number;
}

/** Maximo e quatro contactos num ponto, a partir de um instante de partida. */
export function circunstanciasLocais(
  e: Elementos,
  latGraus: number,
  lonGraus: number,
  alturaM = 0,
  tInicial = 0,
): Circunstancias {
  const tMax = instanteMaximoNewton(e, latGraus, lonGraus, alturaM, tInicial);
  const noMaximo = magnitudeEm(e, tMax, latGraus, lonGraus, alturaM);

  if (!noMaximo.ha_eclipse) {
    return {
      visivel: false,
      magnitude: 0.0,
      obscuracao: 0.0,
      razao_diametros: null,
      tipo: "nenhum",
      t_maximo_td: tMax,
      contactos_td: { c1: null, c2: null, c3: null, c4: null },
      duracao_central_s: null,
      alt_sol: noMaximo.alt_sol,
      az_sol: noMaximo.az_sol,
    };
  }

  const central = noMaximo.central;
  const tipo: TipoLocal = central
    ? noMaximo.total
      ? "total"
      : "anular"
    : "parcial";

  const contactos: Contactos = {
    c1: contacto(e, latGraus, lonGraus, alturaM, tMax, false, true),
    c2: central ? contacto(e, latGraus, lonGraus, alturaM, tMax, true, true) : null,
    c3: central ? contacto(e, latGraus, lonGraus, alturaM, tMax, true, false) : null,
    c4: contacto(e, latGraus, lonGraus, alturaM, tMax, false, false),
  };

  const duracao =
    contactos.c2 !== null && contactos.c3 !== null
      ? (contactos.c3 - contactos.c2) * 3600.0
      : null;

  return {
    visivel: true,
    magnitude: noMaximo.magnitude,
    obscuracao: noMaximo.obscuracao,
    razao_diametros: razaoDiametros(noMaximo),
    tipo,
    t_maximo_td: tMax,
    contactos_td: contactos,
    duracao_central_s: duracao,
    alt_sol: noMaximo.alt_sol,
    az_sol: noMaximo.az_sol,
  };
}

/** Razao entre os diametros aparentes da Lua e do Sol.
 *
 * E esta a grandeza que o canon da NASA publica como "magnitude" para os
 * eclipses centrais, ao passo que para os parciais publica a fraccao do diametro
 * solar coberta. Sao definicoes diferentes e nao se devem misturar. */
export function razaoDiametros(m: Magnitude): number {
  return (m.l1_obs - m.l2_obs) / (m.l1_obs + m.l2_obs);
}

/** Instante de maximo eclipse num ponto, sem palpite de partida.
 *
 * Duas passagens, como no Python: um varrimento grosseiro que localiza a
 * aproximacao maxima do eixo da sombra ao ponto, e depois Newton sobre a
 * condicao de minimo da distancia. O varrimento nao serve para exactidao, serve
 * para garantir que o Newton parte da bacia certa: sem ele, um ponto longe da
 * sombra pode convergir para o instante errado.
 *
 * Os instantes do varrimento sao gerados como `inicio + i * passo`, que e o que
 * o `numpy.arange` do Python faz. Acumular somas daria valores ligeiramente
 * diferentes e as duas implementacoes deixavam de partir do mesmo sitio. */
export function instanteMaximoEmPonto(
  e: Elementos,
  latGraus: number,
  lonGraus: number,
  alturaM = 0,
  janelaHoras = 4.0,
  passoMinutos = 20.0,
): number {
  const passo = passoMinutos / 60.0;
  const n = Math.ceil((janelaHoras + passo / 2 - -janelaHoras) / passo);

  let melhorT = 0.0;
  let melhorSeparacao = Infinity;
  for (let i = 0; i < n; i += 1) {
    const t = -janelaHoras + i * passo;
    const { u, v } = uVeDerivadas(e, t, latGraus, lonGraus, alturaM);
    const separacao = Math.hypot(u, v);
    if (separacao < melhorSeparacao) {
      melhorSeparacao = separacao;
      melhorT = t;
    }
  }

  for (let i = 0; i < 6; i += 1) {
    const { u, v, du, dv } = uVeDerivadas(
      e,
      melhorT,
      latGraus,
      lonGraus,
      alturaM,
    );
    const n2 = du * du + dv * dv;
    const correccao = n2 > 0 ? -(u * du + v * dv) / n2 : 0.0;
    melhorT += Number.isFinite(correccao) ? correccao : 0.0;
  }

  return melhorT;
}

/** Circunstancias num ponto, partindo so de umas coordenadas.
 *
 * E o ponto de entrada do calculo ao vivo no mapa. Corresponde a
 * `circunstancias_no_ponto` do Python, passo por passo. */
export function circunstanciasNoPonto(
  e: Elementos,
  latGraus: number,
  lonGraus: number,
  alturaM = 0,
): Circunstancias {
  const tInicial = instanteMaximoEmPonto(e, latGraus, lonGraus, alturaM);
  return circunstanciasLocais(e, latGraus, lonGraus, alturaM, tInicial);
}

function limitar(valor: number, minimo: number, maximo: number): number {
  return Math.min(Math.max(valor, minimo), maximo);
}

/** Resto sempre positivo, como o operador `%` do Python. */
function modulo(valor: number, divisor: number): number {
  return ((valor % divisor) + divisor) % divisor;
}
