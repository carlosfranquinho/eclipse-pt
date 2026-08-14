/** Copia a biblioteca do MapLibre para `public/vendor/maplibre/`.
 *
 * O MapLibre 6 vem repartido em tres modulos: o principal, um partilhado e o
 * do worker, que ele carrega com `new URL("./maplibre-gl-worker.mjs",
 * import.meta.url)`. O caminho e montado a partir de uma variavel, por isso
 * nenhum empacotador o consegue reescrever: se a biblioteca for empacotada com
 * o resto do codigo, o worker fica a apontar para um ficheiro que nao existe e
 * o mapa nunca chega a carregar as fontes, sem dar erro.
 *
 * A solucao e servi-la como esta, em `public/`, e importa-la em tempo de
 * execucao. Os ficheiros sao copiados de `node_modules` a cada build e ficam
 * fora do git.
 */

import { copyFileSync, mkdirSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const raiz = new URL("../", import.meta.url);
const origem = new URL("node_modules/maplibre-gl/dist/", raiz);
const destino = new URL("public/vendor/maplibre/", raiz);

const FICHEIROS = [
  "maplibre-gl.mjs",
  "maplibre-gl-shared.mjs",
  "maplibre-gl-worker.mjs",
];

mkdirSync(fileURLToPath(destino), { recursive: true });
for (const ficheiro of FICHEIROS) {
  copyFileSync(
    fileURLToPath(new URL(ficheiro, origem)),
    fileURLToPath(new URL(ficheiro, destino)),
  );
}

const { version } = JSON.parse(
  readFileSync(fileURLToPath(new URL("node_modules/maplibre-gl/package.json", raiz)), "utf8"),
);
console.log(`maplibre-gl ${version} copiado para public/vendor/maplibre/`);
