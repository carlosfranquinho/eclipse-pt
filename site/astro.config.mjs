// @ts-check
import { fileURLToPath } from "node:url";
import { defineConfig } from "astro/config";

// As paginas leem os dados do pipeline do disco, em tempo de build. O caminho
// tem de ser resolvido aqui: dentro dos modulos empacotados, `import.meta.url`
// ja aponta para o chunk gerado e nao para a arvore de fontes.
const dirDados = fileURLToPath(new URL("./public/data/", import.meta.url));

// O site publica-se como pagina de projeto do GitHub Pages, num subdiretorio.
// SITE_BASE e SITE_URL permitem servir noutro caminho sem tocar no codigo: todos
// os URLs internos passam por `caminho()` em src/lib/urls.ts, que usa BASE_URL.
// Na publicacao os dois valores vem do proprio GitHub, pelo `configure-pages`.
const base = normalizarBase(process.env.SITE_BASE ?? "/eclipse-pt/");
const site = process.env.SITE_URL ?? "https://exemplo.github.io";

/** Uma barra a frente, uma atras, e nunca duas seguidas.
 *
 * O `configure-pages` da o caminho sem barra final, e da-o vazio quando o site
 * fica na raiz do dominio. Sem esta normalizacao, o primeiro caso perdia a barra
 * e o segundo ficava com duas. */
function normalizarBase(caminho) {
  const limpo = caminho.replace(/^\/+|\/+$/g, "");
  return limpo === "" ? "/" : `/${limpo}/`;
}

export default defineConfig({
  site,
  base,
  trailingSlash: "ignore",
  build: {
    // Uma pasta por pagina, para os URLs ficarem sem extensao.
    format: "directory",
  },
  vite: {
    define: {
      __DIR_DADOS__: JSON.stringify(dirDados),
    },
    build: {
      // Sem isto o Astro embute no HTML os scripts pequenos, como o dos filtros
      // da pagina inicial. A politica de seguranca do site nao permite scripts
      // embutidos, e o script deixaria de correr, sem erro visivel a nao ser na
      // consola. Ver a nota sobre a politica em src/layouts/Base.astro.
      assetsInlineLimit: 0,
    },
  },
  i18n: {
    locales: ["pt"],
    defaultLocale: "pt",
    routing: {
      prefixDefaultLocale: false,
    },
  },
});
