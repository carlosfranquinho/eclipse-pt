/** Leitura dos dados do pipeline em tempo de build.
 *
 * Os ficheiros vivem em `public/data/` porque tambem sao servidos ao browser
 * tal como estao. As paginas leem-nos do disco, nao por fetch, para a build
 * ficar estatica e falhar cedo se faltar alguma coisa. */

import { readFileSync, existsSync, readdirSync } from "node:fs";
import type {
  Catalogo,
  Eclipse,
  EclipseLunar,
  EntradaCatalogo,
  EntradaIndice,
  EntradaIndiceLunar,
  MetadadosFaixa,
  MunicipiosAtravessados,
  Recursos,
  ZonaIsomagnitude,
} from "./tipos";

/** Caminho absoluto de `public/data/`, injectado pelo astro.config.mjs. */
declare const __DIR_DADOS__: string;
const RAIZ_DADOS = __DIR_DADOS__;

function ler<T>(caminhoRelativo: string): T {
  return JSON.parse(readFileSync(RAIZ_DADOS + caminhoRelativo, "utf8")) as T;
}

let cacheIndice: EntradaIndice[] | null = null;

/** O indice completo, por ordem cronologica crescente. */
export function indice(): EntradaIndice[] {
  if (cacheIndice === null) {
    cacheIndice = ler<EntradaIndice[]>("eclipses-index.json");
  }
  return cacheIndice;
}

/** Os metadados do catalogo, escritos pelo pipeline.
 *
 * O intervalo que aqui vem e o que o pipeline percorreu, e nao o dos eclipses
 * que encontrou. A diferenca importa nas pontas: procurou-se ate 2499 e o ultimo
 * eclipse visivel de Portugal e de 2498, mas o que se anuncia a quem le e o
 * ambito, nao o resultado. */
export function catalogo(): Catalogo {
  return ler<Catalogo>("catalogo.json");
}

export function intervaloDoCatalogo(): { inicio: number; fim: number } {
  const [inicio, fim] = catalogo().intervalo;
  return { inicio, fim };
}

export function eclipse(id: string): Eclipse {
  return ler<Eclipse>(`${id}/eclipse.json`);
}

let cacheIndiceLunar: EntradaIndiceLunar[] | null = null;

/** O indice dos eclipses lunares, por ordem cronologica crescente. */
export function indiceLunar(): EntradaIndiceLunar[] {
  if (cacheIndiceLunar === null) {
    cacheIndiceLunar = ler<EntradaIndiceLunar[]>("eclipses-lua-index.json");
  }
  return cacheIndiceLunar;
}

export function eclipseLunar(id: string): EclipseLunar {
  return ler<EclipseLunar>(`lua/${id}/eclipse.json`);
}

let cacheCompleto: EntradaCatalogo[] | null = null;

/** As duas familias no mesmo catalogo, por ordem cronologica.
 *
 * Ha dias com um eclipse solar e outro lunar? Nunca no mesmo dia, mas sim na
 * mesma quinzena, e e por isso que a chave de ordenacao tem de incluir a
 * familia: dois eclipses podem partilhar o identificador se um for do Sol e
 * outro da Lua noutro ano, mas nunca dentro da mesma lista ordenada. */
export function indiceCompleto(): EntradaCatalogo[] {
  if (cacheCompleto === null) {
    cacheCompleto = [...indice(), ...indiceLunar()].sort((a, b) =>
      a.data_gregoriana === b.data_gregoriana
        ? a.familia.localeCompare(b.familia)
        : a.data_gregoriana.localeCompare(b.data_gregoriana),
    );
  }
  return cacheCompleto;
}

export function municipios(id: string): MunicipiosAtravessados | null {
  return existe(id, "municipios.json")
    ? ler<MunicipiosAtravessados>(`${id}/municipios.json`)
    : null;
}

/** So os metadados do topo do GeoJSON da faixa. A geometria fica para o mapa,
 * que a vai buscar por fetch; aqui so interessa saber como desenha-la. */
export function metadadosFaixa(id: string): MetadadosFaixa | null {
  if (!existe(id, "band.geojson")) return null;
  const colecao = ler<{ properties?: MetadadosFaixa }>(`${id}/band.geojson`);
  return colecao.properties ?? null;
}

/** Os niveis de isomagnitude presentes no ficheiro, do mais baixo ao mais alto.
 * A legenda do mapa so mostra os que existem neste eclipse. */
export function niveisIsomagnitude(id: string): ZonaIsomagnitude[] {
  if (!existe(id, "isomag.geojson")) return [];
  const colecao = ler<{
    features: { properties: ZonaIsomagnitude }[];
  }>(`${id}/isomag.geojson`);
  const zonas = new Map<number, ZonaIsomagnitude>();
  for (const feicao of colecao.features) {
    const { de, ate } = feicao.properties;
    zonas.set(de, { de, ate });
  }
  return [...zonas.values()].sort((a, b) => a.de - b.de);
}

function existe(id: string, ficheiro: string): boolean {
  return existsSync(`${RAIZ_DADOS}${id}/${ficheiro}`);
}

export function recursos(id: string): Recursos {
  const url = (ficheiro: string) =>
    existe(id, ficheiro) ? `data/${id}/${ficheiro}` : null;
  return {
    linha_central: url("central.geojson"),
    faixa: url("band.geojson"),
    isomagnitudes: url("isomag.geojson"),
    municipios: url("municipios.json"),
  };
}

/** Ficheiros presentes na pasta de um eclipse. Serve para os testes de sanidade
 * da build, nao para a interface. */
export function ficheirosDe(id: string): string[] {
  const pasta = `${RAIZ_DADOS}${id}`;
  return existsSync(pasta) ? readdirSync(pasta).sort() : [];
}

export function vizinhos(id: string): {
  anterior: EntradaIndice | null;
  seguinte: EntradaIndice | null;
} {
  const lista = indice();
  const i = lista.findIndex((e) => e.id === id);
  return {
    anterior: i > 0 ? lista[i - 1]! : null,
    seguinte: i >= 0 && i < lista.length - 1 ? lista[i + 1]! : null,
  };
}

/** Os vizinhos de um eclipse lunar, dentro da sua propria familia: a navegacao
 * de uma ficha lunar leva a outra ficha lunar, e nao ao eclipse solar que por
 * acaso caiu duas semanas antes. */
export function vizinhosLunares(id: string): {
  anterior: EntradaIndiceLunar | null;
  seguinte: EntradaIndiceLunar | null;
} {
  const lista = indiceLunar();
  const i = lista.findIndex((e) => e.id === id);
  return {
    anterior: i > 0 ? lista[i - 1]! : null,
    seguinte: i >= 0 && i < lista.length - 1 ? lista[i + 1]! : null,
  };
}
