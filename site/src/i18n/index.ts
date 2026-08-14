/** Cadeias de texto da interface.
 *
 * Nada de texto embutido nos componentes: o ingles ainda nao se publica, mas
 * quando se publicar basta acrescentar `en.json` e escolher o dicionario pela
 * localizacao do URL. */

import pt from "./pt.json";

export type Chave = keyof typeof pt;

const dicionarios = { pt } as const;
export type Localizacao = keyof typeof dicionarios;

export const LOCALIZACAO_POR_OMISSAO: Localizacao = "pt";

export function traducoes(localizacao: Localizacao = LOCALIZACAO_POR_OMISSAO) {
  const dicionario = dicionarios[localizacao];
  return function t(chave: Chave, valores?: Record<string, string | number>): string {
    let texto: string = dicionario[chave] ?? chave;
    if (valores) {
      for (const [nome, valor] of Object.entries(valores)) {
        texto = texto.replaceAll(`{${nome}}`, String(valor));
      }
    }
    return texto;
  };
}

export const t = traducoes();
