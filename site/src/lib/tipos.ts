/** Formas dos dados gerados pelo pipeline. Espelham o que o Python escreve em
 * `public/data/`, sem transformacao pelo meio: se um campo aqui nao bate certo
 * com o gerador, o que esta errado e este ficheiro. */

export type TipoEclipse = "total" | "anular" | "hibrido" | "parcial";
export type TipoLocal = TipoEclipse | "nenhum";
export type Territorio = "continente" | "acores" | "madeira";
export type SistemaHora = "hora_legal" | "hora_solar_media_local";
export type Calendario = "juliano" | "gregoriano";

export interface Lugar {
  nome: string;
  concelho: string;
  distrito: string;
  lat: number;
  lon: number;
}

/** Ponto de entrada ou saida da faixa, sem os campos administrativos. */
export interface PontoFaixa {
  nome: string;
  lat: number;
  lon: number;
}

export interface TerritorioInvisivel {
  visivel: false;
}

export interface TerritorioVisivel {
  visivel: true;
  magnitude_max: number;
  obscuracao_max: number;
  tipo_local: TipoLocal;
  faixa_central: boolean;
  local_mais_fundo: Lugar;
  maximo_local: string;
  data_local: string;
  sistema_hora: SistemaHora;
  designacao_fuso: string | null;
  maximo_ut: string;
  alt_sol_graus: number;
  az_sol_graus: number;
  duracao_central_s: number | null;
  fraccao_territorio_com_faixa: number;
  faixa_entrada?: PontoFaixa;
  faixa_saida?: PontoFaixa;
}

export type CircunstanciasTerritorio = TerritorioVisivel | TerritorioInvisivel;

export interface ResumoPortugal {
  magnitude_max: number;
  /** O que se viu de Portugal, no territorio onde o eclipse foi mais fundo. Um
   * eclipse total no mundo pode nao passar de parcial visto daqui. */
  tipo_local: TipoLocal;
  faixa_central: boolean;
  territorios_visiveis: Territorio[];
}

export interface EntradaIndice {
  id: string;
  data_gregoriana: string;
  data_juliana: string | null;
  calendario_vigente_pt: Calendario;
  tipo: TipoEclipse;
  saros: number;
  pt: ResumoPortugal;
  dados_pesados: boolean;
}

export interface ElementosBesselianos {
  t0_td: number;
  x: number[];
  y: number[];
  d: number[];
  mu: number[];
  l1: number[];
  l2: number[];
  tan_f1: number;
  tan_f2: number;
  k1: number;
  k2: number;
}

export interface Eclipse extends EntradaIndice {
  /** Dia juliano do maximo global, em TD, como o canon o publica: com tres
   * casas decimais, ou seja indeterminado em quase um minuto. Serve para
   * mostrar, nao para contar tempo. */
  jd: number;
  /** Dia juliano, em TD, do instante `t = 0` dos elementos besselianos. E este
   * o numero que converte os resultados do calculo em horas, e vem calculado
   * pelo pipeline a partir da data e da hora que o canon publica ao segundo. */
  jd_t0_td: number;
  gamma: number;
  magnitude_canon: number;
  delta_t_s: number;
  maximo_global_ut: string;
  territorios: Record<Territorio, CircunstanciasTerritorio>;
  elementos: ElementosBesselianos;
  /** Paragrafo de abertura, escrito pelo pipeline a partir destes numeros. Vem
   * nos dois tempos verbais porque metade do catalogo ainda nao aconteceu, e a
   * ficha escolhe o que serve a data da build. */
  texto_gerado?: { passado: string; futuro: string };
}

export interface ConcelhoAtravessado {
  nome: string;
  concelho: string;
  distrito: string;
  territorio: Territorio;
  fraccao_area: number;
  tipo_local: TipoLocal;
  magnitude: number;
  duracao_central_s: number | null;
  maximo_local: string;
  sistema_hora: SistemaHora;
}

export interface MunicipiosAtravessados {
  id: string;
  aviso: string;
  faixa_estreita: boolean;
  total: number;
  concelhos: ConcelhoAtravessado[];
}

/** Metadados no topo de `band.geojson`, fora do padrao GeoJSON mas onde o
 * pipeline os escreve: dizem se a faixa e larga o bastante para ser desenhada
 * como area ou se so a linha central e honesta a escala do mapa. */
export interface MetadadosFaixa {
  largura_maxima_km: number | null;
  largura_sobre_pt_km: number | null;
  linha_central_sobre_pt: boolean;
  desenhavel_como_area: boolean;
}

/** Que ficheiros existem para um eclipse, tal como estao em disco. */
export interface Recursos {
  linha_central: string | null;
  faixa: string | null;
  isomagnitudes: string | null;
  municipios: string | null;
}
