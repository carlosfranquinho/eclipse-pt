/** O ficheiro que os motores de busca leem primeiro.
 *
 * Nada esta vedado: o site e um catalogo publico e e para ser lido. So aponta o
 * caminho do mapa do site, que e a unica coisa que aqui faz falta. */

import type { APIContext } from "astro";
import { caminho } from "../lib/urls";

export function GET(contexto: APIContext): Response {
  const mapa = new URL(caminho("sitemap.xml"), contexto.site).href;
  const corpo = ["User-agent: *", "Allow: /", `Sitemap: ${mapa}`, ""].join("\n");

  return new Response(corpo, {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
}
