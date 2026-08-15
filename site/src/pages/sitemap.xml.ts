/** Mapa do site, gerado a partir do proprio catalogo.
 *
 * Escrito a mao em vez de trazer o `@astrojs/sitemap`: sao vinte linhas, o site
 * tem tres tipos de pagina e nenhum deles precisa de prioridades nem de
 * frequencias de actualizacao, que os motores de busca ignoram ha anos.
 *
 * A data de alteracao e a da build, que e quando os dados podem de facto ter
 * mudado: o conteudo de cada ficha e gerado, nao editado. */

import type { APIContext } from "astro";
import { indice } from "../lib/dados";
import { caminho, urlEclipse } from "../lib/urls";

export function GET(contexto: APIContext): Response {
  const raiz = contexto.site;
  if (!raiz) throw new Error("`site` por definir no astro.config.mjs");

  const hoje = new Date().toISOString().slice(0, 10);
  const paginas = [
    caminho(""),
    caminho("sobre"),
    ...indice().map((entrada) => urlEclipse(entrada.id)),
  ];

  const corpo = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ...paginas.map(
      (pagina) =>
        `  <url><loc>${new URL(pagina, raiz).href}</loc><lastmod>${hoje}</lastmod></url>`,
    ),
    "</urlset>",
    "",
  ].join("\n");

  return new Response(corpo, {
    headers: { "Content-Type": "application/xml; charset=utf-8" },
  });
}
