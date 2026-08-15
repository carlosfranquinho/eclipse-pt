// @ts-check
import { fileURLToPath } from "node:url";
import { defineConfig } from "astro/config";

// As paginas leem os dados do pipeline do disco, em tempo de build. O caminho
// tem de ser resolvido aqui: dentro dos modulos empacotados, `import.meta.url`
// ja aponta para o chunk gerado e nao para a arvore de fontes.
const dirDados = fileURLToPath(new URL("./public/data/", import.meta.url));

// O site publica-se como pagina de projeto do GitHub Pages, num subdiretorio.
// SITE_BASE permite servir noutro caminho sem tocar no codigo: todos os URLs
// internos passam por `caminho()` em src/lib/urls.ts, que usa BASE_URL.
const base = process.env.SITE_BASE ?? "/eclipse-pt/";
const site = process.env.SITE_URL ?? "https://exemplo.github.io";

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
