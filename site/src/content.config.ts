/** Conteudo editorial por eclipse: notas e galeria.
 *
 * Duas coleccoes opcionais e independentes do pipeline. O pipeline nunca escreve
 * nestas pastas e nunca as apaga; a ficha so mostra as seccoes quando existe
 * ficheiro para aquele eclipse. O nome do ficheiro e o identificador do eclipse,
 * o mesmo que esta no URL: `1900-05-28.md`, `1900-05-28.yaml`.
 *
 * Na galeria, a licenca e campo obrigatorio. Nao e burocracia: e o que impede
 * que entre no site uma imagem de proveniencia duvidosa, e o schema recusa-se a
 * construir sem ela.
 *
 * Enquanto nao houver ficheiros, a build avisa que nao encontrou nada para estas
 * coleccoes. E esperado, e passa assim que existir a primeira nota.
 */

import { defineCollection } from "astro:content";
import { glob } from "astro/loaders";
// O `z` re-exportado por `astro:content` esta marcado como obsoleto na versao 4
// do Zod, que o Astro passou a usar. O modulo em si nao esta.
import * as z from "astro/zod";

/** Uma referencia: um livro, um artigo de jornal da epoca, uma pagina. */
const fonte = z.object({
  titulo: z.string(),
  autor: z.string().optional(),
  publicacao: z.string().optional(),
  ano: z.number().int().optional(),
  url: z.url().optional(),
});

const notas = defineCollection({
  loader: glob({ pattern: "[!_]*.md", base: "./src/content/notas" }),
  schema: z.object({
    titulo: z.string().optional(),
    fontes: z.array(fonte).optional(),
  }),
});

/** O conteudo de um ficheiro de galeria. Escrito a parte para as duas
 * coleccoes, a solar e a lunar, partilharem a mesma definicao. */
const esquemaGaleria = z.object({
    imagens: z
      .array(
        z.object({
          /** Nome do ficheiro dentro de `public/imagens/<id>/`. */
          ficheiro: z.string(),
          legenda: z.string(),
          autor: z.string().optional(),
          ano: z.number().int().optional(),
          fonte: z.string().optional(),
          url: z.url().optional(),
          /** Obrigatoria. Sem licenca conhecida, a imagem nao entra. */
          licenca: z.string(),
          /** Dimensoes em pixeis, para o browser reservar o espaco antes de a
           * imagem chegar e a pagina nao saltar. Opcionais, mas recomendadas. */
          largura: z.number().int().positive().optional(),
          altura: z.number().int().positive().optional(),
          /** Texto alternativo, para quem nao ve a imagem. Sem ele usa-se a
           * legenda, que quase sempre chega. */
          alternativo: z.string().optional(),
        }),
      )
      .min(1),
});

const galeria = defineCollection({
  loader: glob({ pattern: "[!_]*.yaml", base: "./src/content/galeria" }),
  schema: esquemaGaleria,
});

/** As mesmas duas coleccoes para os eclipses lunares, em pastas proprias.
 *
 * Podiam ser as mesmas com o identificador prefixado, mas dois eclipses, um do
 * Sol e outro da Lua, podem cair no mesmo dia do mesmo ano em anos diferentes e
 * a separacao por pasta e a que nunca se engana. Os padroes das coleccoes
 * solares nao apanham subpastas, por isso nao ha sobreposicao. */
const notasLua = defineCollection({
  loader: glob({ pattern: "[!_]*.md", base: "./src/content/notas/lua" }),
  schema: z.object({
    titulo: z.string().optional(),
    fontes: z.array(fonte).optional(),
  }),
});

const galeriaLua = defineCollection({
  loader: glob({ pattern: "[!_]*.yaml", base: "./src/content/galeria/lua" }),
  schema: esquemaGaleria,
});

export const collections = { notas, galeria, notasLua, galeriaLua };
