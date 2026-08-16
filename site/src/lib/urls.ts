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

/** O endereco de uma ficha lunar. Os enderecos solares nao mudaram quando os
 * lunares chegaram, e e por isso que a familia so aparece nestes. */
export function urlEclipseLunar(id: string): string {
  return caminho(`eclipse/lua/${id}`);
}

/** O endereco da ficha de uma entrada do catalogo, seja de que familia for. */
export function urlDeEntrada(entrada: {
  id: string;
  familia: "solar" | "lunar";
}): string {
  return entrada.familia === "lunar"
    ? urlEclipseLunar(entrada.id)
    : urlEclipse(entrada.id);
}

export function urlDados(relativo: string): string {
  return caminho(relativo);
}
