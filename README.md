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
uv run python pipeline/build_index.py            # índice de eclipses visíveis
uv run python pipeline/build_paths.py            # faixas e isomagnitudes
uv run python pipeline/crossed_municipalities.py # concelhos atravessados
uv run pytest                                    # validação completa
```

Os passos são independentes e a ordem acima é a das dependências entre eles. As
descargas ficam em cache local, fora do git; só os dados derivados são commitados.

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
