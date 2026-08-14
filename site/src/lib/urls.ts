/** Construcao de URLs internos.
 *
 * O site vive num subdiretorio no GitHub Pages, por isso nenhum caminho pode
 * ser escrito a mao com barra inicial. Tudo passa por aqui, que respeita o
 * `base` configurado no Astro. */

const BASE = import.meta.env.BASE_URL;

export function caminho(relativo: string): string {
  const limpo = relativo.replace(/^\/+/, "");
  return BASE.endsWith("/") ? BASE + limpo : `${BASE}/${limpo}`;
}

export function urlEclipse(id: string): string {
  return caminho(`eclipse/${id}`);
}

export function urlDados(relativo: string): string {
  return caminho(relativo);
}
