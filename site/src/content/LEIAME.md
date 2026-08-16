# Conteúdo editorial por eclipse

Duas pastas, ambas opcionais, ambas escritas à mão. O pipeline não escreve aqui e
não apaga nada daqui. A ficha de um eclipse só mostra estas secções quando existe
um ficheiro com o identificador desse eclipse, que é a data gregoriana no formato
`AAAA-MM-DD`, a mesma que está no endereço da página.

O formato dos dois ficheiros está definido em `src/content.config.ts`. Se um
campo obrigatório faltar, a build falha e diz qual é: é de propósito.

## `notas/<id>.md`

Relatos de época, referências em crónicas, observações publicadas, bibliografia.
Tudo o que não sai de um cálculo.

```markdown
---
titulo: Observado de Ovar por três expedições estrangeiras
fontes:
  - titulo: Relatório da expedição
    autor: Nome do autor
    publicacao: Nome da revista ou do jornal
    ano: 1900
    url: https://exemplo.org/documento
---

O texto corrido da nota, em Markdown. Pode ter vários parágrafos, listas,
citações e ligações.
```

O `titulo` e as `fontes` são opcionais. Sem `titulo`, a secção aparece com o
cabeçalho normal; as fontes, quando existem, são listadas no fim.

## `galeria/<id>.yaml`

Gravuras e desenhos nos eclipses históricos, fotografias nos modernos. As imagens
ficam em `public/imagens/<id>/` e o campo `ficheiro` é o nome do ficheiro dentro
dessa pasta.

```yaml
imagens:
  - ficheiro: coroa-1900.jpg
    legenda: A coroa solar fotografada durante a totalidade
    autor: Nome do autor
    ano: 1900
    fonte: Nome do arquivo ou da instituição
    url: https://exemplo.org/pagina-da-imagem
    licenca: Domínio público
    alternativo: Fotografia a preto e branco do disco negro do Sol rodeado pela coroa
    largura: 1600
    altura: 1200
```

**A licença é obrigatória.** Sem ela o ficheiro não passa na validação e a build
para. Não é burocracia: é o que impede que entre aqui uma imagem de proveniência
duvidosa. Se a licença não for conhecida, a imagem não entra.

O `alternativo` descreve a imagem para quem não a vê. Quando falta, usa-se a
legenda, que quase sempre chega.

A `largura` e a `altura` são as dimensões em pixéis do ficheiro. São opcionais,
mas convém dá-las: com elas o browser reserva o espaço antes de a imagem chegar e
a página não salta a meio da leitura.

## Ao remover um ficheiro

O Astro guarda em `site/.astro/` o que já leu destas pastas, e apagar um ficheiro
não chega para o tirar da build local. Depois de remover uma nota ou uma galeria,
correr `npx astro build --force`, que limpa essa cache. Na publicação o problema
não existe, porque o CI constrói sempre de raiz.

## Enquanto não houver conteúdo

A build avisa que não encontrou ficheiros para estas colecções. É esperado, e o
aviso desaparece com a primeira nota ou a primeira galeria.

## Eclipses lunares

As mesmas duas coleccoes existem para os eclipses lunares, em pastas proprias:
`notas/lua/<id>.md` e `galeria/lua/<id>.yaml`, com as imagens em
`public/imagens/lua/<id>/`. O formato e identico ao dos solares; a separacao por
pasta e o que impede que uma nota do Sol apareca numa ficha da Lua com a mesma
data.
