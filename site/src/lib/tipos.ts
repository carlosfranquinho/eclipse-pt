/** Formas dos dados gerados pelo pipeline. Espelham o que o Python escreve em
 * `public/data/`, sem transformacao pelo meio: se um campo aqui nao bate certo
 * com o gerador, o que esta errado e este ficheiro. */

export type TipoEclipse = "total" | "anular" | "hibrido" | "parcial";
export type TipoLocal = TipoEclipse | "nenhum";

/** Do Sol ou da Lua. As duas familias vivem no mesmo catalogo e e por este
 * campo que se distinguem, tanto nos dados como nos filtros. */
export type Familia = "solar" | "lunar";

/** Um eclipse lunar nao pode ser anular nem hibrido: a Terra e maior do que a
 * Lua e a sua sombra nunca se afunila antes de chegar la. */
export type TipoEclipseLunar = "total" | "parcial" | "penumbral";
export type TipoLocalLunar = TipoEclipseLunar | "nenhum";

/** Os sete contactos de um eclipse lunar. P e a penumbra, U e a umbra: P1 e o
 * primeiro toque da penumbra, U2 e U3 abrem e fecham a totalidade. Um eclipse
 * penumbral so tem P1, o maximo e P4. */
export type NomeContacto = "p1" | "u1" | "u2" | "maximo" | "u3" | "u4" | "p4";
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

/** O catalogo no seu conjunto, tal como o pipeline o descreve em
 * `data/catalogo.json`. */
export interface Catalogo {
  /** Primeiro e ultimo ano percorridos pelo pipeline. */
  intervalo: [number, number];
  total: number;
  com_faixa_central: number;
  com_dados_pesados: number;
  /** Contagens da familia lunar, acrescentadas por `build_index_lua.py` depois
   * de o solar escrever o ficheiro. */
  lua?: {
    /** Quantos se veem de Portugal. */
    total: number;
    /** Quantos ha no catalogo da NASA para o mesmo intervalo. */
    no_catalogo: number;
    perceptiveis: number;
  };
}

export interface EntradaIndice {
  id: string;
  familia: "solar";
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

/** Uma zona de igual magnitude, entre dois niveis. A ultima nao tem tecto: vai
 * do 0,99 ao que der, que num eclipse total passa de 1. */
export interface ZonaIsomagnitude {
  de: number;
  ate: number;
}

/** Que ficheiros existem para um eclipse, tal como estao em disco. */
export interface Recursos {
  linha_central: string | null;
  faixa: string | null;
  isomagnitudes: string | null;
  municipios: string | null;
}


// ---------------------------------------------------------------------------
// Eclipses lunares
// ---------------------------------------------------------------------------

/** O ponto de onde a ficha lunar conta as horas e as alturas, um por
 * territorio. Um eclipse lunar e igual em todo o pais; o que muda de lugar para
 * lugar e so a hora legal e uns graus de altura da Lua. */
export interface LugarDeReferencia {
  nome: string;
  lat: number;
  lon: number;
}

/** Um instante do eclipse, visto de um lugar. */
export interface MomentoLunar {
  jd_ut: number;
  hora_local: string;
  data_local: string;
  sistema_hora: SistemaHora;
  designacao_fuso: string | null;
  hora_ut: string;
  altura_graus: number;
  azimute_graus: number;
  acima_do_horizonte: boolean;
}

export interface TerritorioLunarInvisivel {
  visivel: false;
  lugar: LugarDeReferencia;
}

export interface TerritorioLunarVisivel {
  visivel: true;
  lugar: LugarDeReferencia;
  /** Nem todos os contactos existem: um eclipse parcial nao tem U2 nem U3. */
  contactos: Partial<Record<NomeContacto, MomentoLunar>>;
  contactos_visiveis: NomeContacto[];
  /** O que dali se viu, que pode ser menos do que o eclipse foi. */
  tipo_visto: TipoLocalLunar;
  magnitude_umbral_visivel: number;
  magnitude_penumbral_visivel: number;
  altura_maxima_graus: number;
  nasceu_eclipsada: boolean;
  poe_se_eclipsada: boolean;
  /** Instante em que a Lua nasceu, quando isso aconteceu com o eclipse ja a
   * decorrer. */
  nascer?: MomentoLunar;
  por?: MomentoLunar;
}

export type CircunstanciasLunares =
  | TerritorioLunarVisivel
  | TerritorioLunarInvisivel;

export interface ResumoPortugalLunar {
  tipo_local: TipoLocalLunar;
  magnitude_umbral: number;
  magnitude_penumbral: number;
  /** Falso nos penumbrais rasos, que existem no papel e nao no ceu. */
  perceptivel: boolean;
  territorios_visiveis: Territorio[];
  nasceu_eclipsada: boolean;
  poe_se_eclipsada: boolean;
}

/** O eclipse reduzido aos numeros com que se desenha, o equivalente lunar dos
 * elementos besselianos. Angulos em graus, vistos do centro da Terra. */
export interface ElementosSombra {
  jd_maximo_td: number;
  delta_t_s: number;
  raio_umbra: number;
  raio_penumbra: number;
  raio_lua: number;
  /** Distancia minima do centro da Lua ao eixo da sombra, com sinal: positiva
   * quando a Lua passa a norte do eixo. */
  y: number;
  /** Velocidade da Lua em relacao a sombra, em graus por hora. */
  velocidade: number;
}

export interface EntradaIndiceLunar {
  id: string;
  familia: "lunar";
  data_gregoriana: string;
  data_juliana: string | null;
  calendario_vigente_pt: Calendario;
  tipo: TipoEclipseLunar;
  saros: number;
  pt: ResumoPortugalLunar;
}

export interface EclipseLunar extends EntradaIndiceLunar {
  /** O codigo do Espenak, que distingue as variantes de penumbral e de total. */
  tipo_canon: string;
  gamma: number;
  magnitude_umbral: number;
  magnitude_penumbral: number;
  delta_t_s: number;
  maximo_global_ut: string;
  /** Duracoes das tres fases, em minutos, como o catalogo as publica. Nulas nas
   * fases que nao chegam a existir. */
  duracoes_min: {
    penumbral: number;
    parcial: number | null;
    total: number | null;
  };
  territorios: Record<Territorio, CircunstanciasLunares>;
  elementos: ElementosSombra;
  texto_gerado?: { passado: string; futuro: string };
}

/** Uma entrada do catalogo, seja de que familia for. E o que a lista, a linha
 * temporal e os filtros manipulam. */
export type EntradaCatalogo = EntradaIndice | EntradaIndiceLunar;
