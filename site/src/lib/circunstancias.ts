/** O que mostrar sobre um ponto do mapa, ja calculado e ja escrito em pt-PT.
 *
 * E a ponte entre o nucleo besseliano e a interface: recebe umas coordenadas,
 * corre o calculo, converte os instantes para a hora que fazia sentido naquela
 * epoca e devolve linhas prontas a desenhar. Vive aqui, e nao dentro do
 * componente do mapa, para poder ser usada por qualquer outra parte do site e
 * para a formatacao dos numeros continuar toda no mesmo sitio.
 *
 * Todo este modulo corre no browser, a cada movimento do rato. Nada aqui le do
 * disco nem vai a rede: os elementos besselianos ja vieram na ficha, e sao trinta
 * numeros. */

import {
  circunstanciasNoPonto,
  elementosDe,
  magnitudeEm,
  type Circunstancias,
} from "./besselian.ts";
import {
  desvioUtc,
  horaLocal,
  isoData,
  isoHora,
  jdParaCivil,
  jdUtDeT,
} from "./tempo.ts";
import { territorioDe } from "./territorios.ts";
import {
  NOMES_TIPO_LOCAL,
  coordenadas,
  duracao,
  graus,
  magnitude as formatarMagnitude,
  percentagem,
  rotuloSistemaHora,
} from "./formatacao.ts";
import { t, type Chave } from "../i18n/index.ts";
import type { Eclipse, Territorio } from "./tipos";

/** So o que o calculo precisa da ficha do eclipse. */
export type EclipseCalculavel = Pick<
  Eclipse,
  "elementos" | "delta_t_s" | "jd_t0_td"
>;

/** Os quatro contactos, com o nome que lhes damos na interface. */
const ROTULOS_CONTACTO = {
  c1: "ponto.c1",
  c2: "ponto.c2",
  c3: "ponto.c3",
  c4: "ponto.c4",
} as const satisfies Record<string, Chave>;

export interface LinhaPonto {
  rotulo: string;
  valor: string;
}

export interface PontoCalculado {
  lat: number;
  lon: number;
  titulo: string;
  territorio: Territorio;
  visivel: boolean;
  /** Explica porque nao ha nada para ver, quando e o caso. */
  aviso: string | null;
  linhas: LinhaPonto[];
  circunstancias: Circunstancias;
}

/** Circunstancias num ponto, prontas para o painel do mapa.
 *
 * `nome` e o nome do lugar quando o ponto veio da caixa de pesquisa. Sem ele, o
 * titulo sao as proprias coordenadas, que e o que interessa a quem esta a
 * apontar o rato ao mapa. */
export function calcularPonto(
  eclipse: EclipseCalculavel,
  lat: number,
  lon: number,
  nome?: string,
): PontoCalculado {
  const elementos = elementosDe(eclipse);
  const territorio = territorioDe(lat, lon);
  const circunstancias = circunstanciasNoPonto(elementos, lat, lon);

  const paraHora = (tTd: number) =>
    horaLocal(jdUtDeT(eclipse, tTd), lon, territorio);
  const local = paraHora(circunstancias.t_maximo_td);

  const base = {
    lat,
    lon,
    titulo: nome ?? coordenadas(lat, lon),
    territorio,
    circunstancias,
  };

  if (!circunstancias.visivel) {
    // Distinguir as duas maneiras de nao se ver nada: estar fora da penumbra, ou
    // estar dentro dela com o Sol ja posto ou ainda por nascer. A segunda e
    // frequente nos eclipses ao amanhecer e ao anoitecer, e sem esta nota o
    // leitor ficava a pensar que o calculo estava errado.
    const noMaximo = magnitudeEm(
      elementos,
      circunstancias.t_maximo_td,
      lat,
      lon,
    );
    const naPenumbra = noMaximo.separacao < noMaximo.l1_obs;
    return {
      ...base,
      visivel: false,
      aviso: naPenumbra ? t("ponto.sol_abaixo") : t("ponto.sem_eclipse"),
      linhas: [],
    };
  }

  const sistema = rotuloSistemaHora(local.sistema, null);
  const linhas: LinhaPonto[] = [
    { rotulo: t("ficha.tipo_local"), valor: NOMES_TIPO_LOCAL[circunstancias.tipo] },
    {
      rotulo: t("ficha.magnitude_maxima"),
      valor: formatarMagnitude(circunstancias.magnitude),
    },
    { rotulo: t("ficha.obscuracao"), valor: percentagem(circunstancias.obscuracao) },
  ];

  if (circunstancias.duracao_central_s !== null) {
    linhas.push({
      rotulo: t("ficha.duracao_central"),
      valor: duracao(circunstancias.duracao_central_s),
    });
  }

  // A hora do maximo vai sem etiqueta de sistema, que aparece uma so vez mais
  // abaixo: repeti-la em cada linha de hora enchia o painel de parenteses.
  linhas.push(
    {
      rotulo: t("ponto.maximo"),
      valor: local.hora,
    },
    {
      rotulo: t("ficha.altura_sol"),
      valor: graus(circunstancias.alt_sol),
    },
    {
      rotulo: t("ficha.azimute_sol"),
      valor: graus(circunstancias.az_sol),
    },
  );

  for (const chave of ["c1", "c2", "c3", "c4"] as const) {
    const instante = circunstancias.contactos_td[chave];
    if (instante === null) continue;
    linhas.push({
      rotulo: t(ROTULOS_CONTACTO[chave]),
      valor: paraHora(instante).hora,
    });
  }

  const maximoUt = jdParaCivil(jdUtDeT(eclipse, circunstancias.t_maximo_td), true);
  linhas.push(
    {
      rotulo: t("ficha.maximo_ut"),
      valor: isoHora(maximoUt),
    },
    {
      rotulo: t("ponto.sistema_hora"),
      valor:
        local.sistema === "hora_legal"
          ? `${sistema}, ${desvioUtc(local.desvio_utc_h)}`
          : sistema,
    },
  );

  // A data local so aparece quando difere da data em UT, ou seja quando o
  // eclipse atravessa a meia-noite naquele ponto. E raro, mas quando acontece a
  // hora sozinha seria enganadora.
  if (local.data !== isoData(maximoUt)) {
    linhas.push({ rotulo: t("ponto.data_local"), valor: local.data });
  }

  return { ...base, visivel: true, aviso: null, linhas };
}
