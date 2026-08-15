# Eclipses Solares em Portugal

Site estático que cataloga os eclipses solares visíveis em Portugal entre 1500 e 2100,
com uma ficha por eclipse, mapas dinâmicos e cálculo das circunstâncias locais em
qualquer ponto do território.

O plano de trabalho está em [`plano.md`](plano.md). O documento original que lhe deu
origem está em [`plano-inicial.md`](plano-inicial.md), mantido para registo.

## Estrutura

- `pipeline/` calcula os dados offline, em Python. O núcleo é `besselian.py`.
- `site/` é o frontend, em Astro com MapLibre GL JS.
- `site/public/data/` guarda os dados gerados pelo pipeline, commitados no repositório
  para o build do site não depender de Python.

## Correr o pipeline

```sh
uv venv && uv pip install -e ".[dev]"
uv run python pipeline/ingest_canon.py           # elementos besselianos e Saros
uv run python pipeline/build_geo.py              # CAOP para GeoJSON
uv run python pipeline/build_lugares.py          # um ponto por concelho, para a pesquisa
uv run python pipeline/build_index.py            # índice de eclipses visíveis
uv run python pipeline/build_paths.py            # faixas e isomagnitudes
uv run python pipeline/crossed_municipalities.py # concelhos atravessados
uv run python pipeline/build_text.py             # parágrafo de abertura de cada ficha
uv run python pipeline/gerar_golden.py           # casos de ouro para o teste do browser
uv run pytest                                    # validação completa
```

Os passos são independentes e a ordem acima é a das dependências entre eles. As
descargas ficam em cache local, fora do git; só os dados derivados são commitados.

Duas ordens que importam: `build_text.py` corre depois de `build_index.py`, porque
o índice reescreve as fichas e levaria o texto com ele; e `gerar_golden.py` corre
depois de qualquer alteração ao núcleo, senão o teste do browser passa a comparar
o TypeScript com uma versão antiga do Python. Os testes avisam nos dois casos.

## Correr o site

```sh
cd site
npm ci
npm run dev          # servidor de desenvolvimento
npm run check        # tipos e diagnósticos do Astro
npm test             # o núcleo em TypeScript contra o Python e contra as fichas
npm run build        # build estática para site/dist/
npm run preview      # servir a build, com o mesmo caminho base da publicação
```

O `npm test` corre no Node, sem dependências de teste: o Node 24 executa TypeScript
directamente e traz o `node --test`.

O site é publicado numa página de projeto do GitHub Pages, por isso a build usa
`base: "/eclipse-pt/"` por omissão. Para servir noutro caminho, definir `SITE_BASE`
(por exemplo `SITE_BASE=/ npm run build`); nenhum URL interno é escrito à mão,
todos passam por `caminho()` em `site/src/lib/urls.ts`.

O `npm run build` e o `npm run dev` copiam antes o MapLibre de `node_modules` para
`site/public/vendor/maplibre/`, que fica fora do git. A biblioteca tem de ser servida
como está e importada em tempo de execução: empacotá-la parte o caminho do worker que
ela própria calcula, e o mapa ficaria sem fontes de dados, sem dar erro.

## Cálculo ao vivo, e como se garante que bate certo

Cada ficha leva os elementos besselianos do seu eclipse, cerca de trinta números.
Com eles o browser calcula em qualquer ponto do mapa a magnitude, a obscuração, os
quatro contactos, a hora local no sistema em vigor à data e a altura do Sol, sem
consultar o servidor e sem nenhuma biblioteca de astronomia. O núcleo está em
`site/src/lib/besselian.ts` e é um porto directo de `pipeline/besselian.py`.

Duas implementações da mesma matemática divergem sozinhas. Contra isso há dois
testes, os dois em `site/test/`:

- `besselian.test.ts` recalcula os casos de ouro que o Python gravou em
  `pipeline/tests/golden/circunstancias.json` e exige concordância até ao último
  bit. Do lado do Python, `pipeline/tests/test_golden.py` garante que esse ficheiro
  não envelhece em relação ao código que o gerou.
- `ficha.test.ts` fecha o circuito com os dados publicados: para os eclipses todos,
  refaz no browser as circunstâncias no ponto que a ficha aponta e compara com os
  números que a ficha mostra.
- `aspecto.test.ts` cobre a simulação do disco solar, que não tem contra o que ser
  comparada e por isso se verifica por coerência: nos quatro contactos os discos
  têm de estar tangentes, a magnitude desenhada tem de ser a calculada, e a Lua
  tem de atravessar o Sol de oeste para leste.

## Publicação

`.github/workflows/publicar.yml` publica no GitHub Pages a cada alteração de
`main`, em três passos: verificar (`npm test` e `npm run check`), construir e
publicar. O pipeline de dados não corre no CI: os ficheiros que produz estão
commitados, e por isso a publicação é só frontend, sem Python e sem descarregar
nada. Quem mexer no pipeline corre-o localmente, corre o `pytest` e commita o
resultado.

O endereço não está escrito em lado nenhum. O `actions/configure-pages` diz qual
é, e a build recebe-o em `SITE_URL` e `SITE_BASE`; mudar o repositório de sítio
não obriga a corrigir nada. Para a primeira publicação é preciso pôr o Pages do
repositório em "GitHub Actions" nas definições.

O site traz `sitemap.xml` e `robots.txt`, ambos gerados do próprio catálogo.

## Segurança e acessibilidade

As páginas levam uma política de segurança de conteúdo em `meta`, porque o GitHub
Pages não deixa definir cabeçalhos. Só se permite o que o site precisa: o
`openstreetmap.org` para o fundo de terreno opcional do mapa, e mais nada de fora.
As duas permissões largas estão explicadas em `site/src/layouts/Base.astro`, e
uma delas, o `unsafe-eval`, existe por causa da forma como o MapLibre tem de ser
carregado.

Nenhum script vai embutido no HTML, o que é o que permite manter a política
apertada. O `assetsInlineLimit: 0` no `astro.config.mjs` garante isso, e sem ele
o Astro embutiria os scripts pequenos e a política bloqueá-los-ia em silêncio.

Com JavaScript desligado, as fichas mantêm o texto, as tabelas e o desenho do Sol;
o que não funciona sem ele esconde-se, em vez de ficar à vista sem reagir.

O Lighthouse dá 100 em desempenho, acessibilidade, boas práticas e SEO na página
inicial, numa ficha e na página sobre.

## Conteúdo escrito à mão

Cada ficha aceita duas peças de conteúdo editorial, ambas opcionais e ambas fora
do alcance do pipeline: uma nota em `site/src/content/notas/<id>.md`, para relatos
de época e bibliografia, e uma galeria em `site/src/content/galeria/<id>.yaml`,
para gravuras e fotografias. As secções só aparecem na ficha quando o ficheiro
existe. O formato dos dois está em [`site/src/content/LEIAME.md`](site/src/content/LEIAME.md).

Na galeria a licença é campo obrigatório: sem ela a build falha, de propósito.

## Convenções do projeto

- Português europeu. Evitar brasileirismos ("rever" e não "revisar", "ficheiro" e não
  "arquivo").
- Nunca usar travessões (em dash). Se for preciso um separador, hífen simples.
- Sem emojis no código nem no conteúdo.
- GeoJSON de municípios com campo `nome` no formato "Concelho, Distrito".
- Grandezas astronómicas em unidades SI ou graus decimais, nunca em sexagesimal, e sempre
  com o sistema de tempo indicado no nome do campo (`_ut`, `_td`, `_local`).
- Nenhum ficheiro de dados gerado é editado à mão. Se um valor está errado, corrige-se o
  gerador.
- Fornecer mensagem de commit sempre que houver alteração de código.

## Créditos e fontes

- Elementos besselianos e catálogo de eclipses: *Eclipse Predictions by Fred Espenak,
  NASA's GSFC*, do *Five Millennium Canon of Solar Eclipses*.
- Limites administrativos: Carta Administrativa Oficial de Portugal (CAOP), Direção-Geral
  do Território.
- Linha de costa e fronteiras: Natural Earth.
