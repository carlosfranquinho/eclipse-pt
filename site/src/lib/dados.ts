/** Leitura dos dados do pipeline em tempo de build.
 *
 * Os ficheiros vivem em `public/data/` porque tambem sao servidos ao browser
 * tal como estao. As paginas leem-nos do disco, nao por fetch, para a build
 * ficar estatica e falhar cedo se faltar alguma coisa. */

import { readFileSync, existsSync, readdirSync } from "node:fs";
import type {
  Eclipse,
  EntradaIndice,
  MetadadosFaixa,
  MunicipiosAtravessados,
  Recursos,
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

export function eclipse(id: string): Eclipse {
  return ler<Eclipse>(`${id}/eclipse.json`);
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
export function niveisIsomagnitude(id: string): number[] {
  if (!existe(id, "isomag.geojson")) return [];
  const colecao = ler<{
    features: { properties: { magnitude: number } }[];
  }>(`${id}/isomag.geojson`);
  const niveis = new Set(colecao.features.map((f) => f.properties.magnitude));
  return [...niveis].sort((a, b) => a - b);
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
