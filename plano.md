# Plano de entrega: "Eclipses Solares em Portugal"

## Contexto

O `plano-inicial.md` deste repositório definiu um site estático que cataloga os
eclipses solares visíveis em Portugal entre 1500 e 2100, com fichas por eclipse e
mapas dinâmicos. O plano inicial está bem pensado
no âmbito e nas convenções, mas o desenho técnico tem quatro fragilidades que vão custar
caro a meio do trabalho:

1. Propõe `pyephem`, que é legado e menos exato nos séculos XVI a XVIII, precisamente a
   parte do catálogo em que a exatidão é mais difícil.
2. Traça as faixas por varrimento de grelha no tempo e no espaço. É lento, é aproximado,
   e o próprio plano já documenta as consequências (faixas "aos blocos", bandas de 1 km
   impossíveis de desenhar).
3. Usa um motor offline (Python) e outro no browser (`astronomy-engine`). Os dois vão
   divergir, e o utilizador vai ver o valor do hover a não bater certo com o valor da ficha.
4. Trata "hora de Portugal" como se houvesse hora legal antes de 1912, quando não havia.

A investigação feita durante o planeamento resolve os quatro pontos de uma vez: os
**elementos besselianos** do *Five Millennium Canon of Solar Eclipses* (Espenak/Meeus,
NASA) estão publicados em JSON e CSV a granel em
[github.com/gmiller123456/FiveMillenniumCanonOfSolarEclipses-Besselian-Elements](https://github.com/gmiller123456/FiveMillenniumCanonOfSolarEclipses-Besselian-Elements).
São cerca de vinte números por eclipse a partir dos quais se calcula, de forma fechada e
exata, tudo o que o site precisa: linha central, limites da faixa, magnitude em qualquer
ponto, tempos de contacto e altura do Sol.

**Resultado pretendido:** um site estático em GitHub Pages, em português europeu, com o
catálogo completo de 1500-2100, mapas fluidos e cálculo ao vivo ponto a ponto, em que os
números do browser e os números do pipeline são exactamente os mesmos por construção.

---

## Decisões fixadas com o Carlos

| Tema | Decisão |
|---|---|
| Territórios | Cálculo e índice cobrem continente, Açores e Madeira. Mapas de faixa detalhados só para o continente na v1. |
| Critério de inclusão | Todos os eclipses com fase visível entram no índice. Dados pesados (faixa, isomagnitudes, concelhos) só acima de um limiar. |
| Motor | Elementos besselianos como fonte única de verdade. Skyfield com DE441 como verificação independente. |
| Frontend | Astro + MapLibre GL JS. |
| Hora local pré-1912 | Hora solar média do meridiano do ponto, com nota explicativa. |
| Conteúdo da ficha | Dados calculados, texto gerado automaticamente, notas históricas manuais opcionais, simulação do aspeto do Sol e galeria de imagens opcional. |
| Validação | Em massa contra o catálogo completo da NASA, não só contra quatro âncoras. |
| Idioma | pt-PT publicado, estrutura de i18n pronta para inglês. |

---

## 1. Convenções obrigatórias

Herdadas do plano inicial e a aplicar em todo o projeto:

- Português europeu. Evitar brasileirismos ("rever" e não "revisar", "ficheiro" e não "arquivo").
- Nunca usar travessões (em dash). Se for preciso um separador, hífen simples.
- Sem emojis no código nem no conteúdo.
- GeoJSON de municípios com campo `nome` no formato "Concelho, Distrito".
- Fornecer mensagem de commit sempre que houver alteração de código.
- Pedir esclarecimento antes de avançar quando um requisito não estiver explícito.

Acrescento duas:

- Todas as grandezas astronómicas guardadas em unidades SI ou graus decimais, nunca em
  sexagesimal, e sempre com o sistema de tempo indicado no nome do campo (`_ut`, `_td`, `_local`).
- Nenhum ficheiro de dados gerado é editado à mão. Se um valor está errado, corrige-se o
  gerador.

---

## 2. Arquitetura: os elementos besselianos como fonte única

Este é o ponto central e o que mais difere do plano inicial.

Um eclipse solar descreve-se por um punhado de polinómios no tempo (as coordenadas `x` e
`y` do eixo da sombra no plano fundamental, a declinação `d` e o ângulo horário `mu` desse
eixo, os raios `l1` e `l2` dos cones de penumbra e umbra, e os ângulos `tan f1` e `tan f2`).
Com esses coeficientes, a matemática do *Explanatory Supplement to the Astronomical Almanac*
dá, sem iteração pesada:

- a **linha central** e os **limites norte e sul da faixa**, como curvas analíticas em vez
  de amostras de uma grelha. A faixa de 1 km do híbrido de 1912 sai tão bem definida como
  a faixa de 300 km de qualquer total, e o problema das faixas "aos blocos" deixa de existir;
- a **magnitude e a obscuração** num ponto qualquer, com os quatro tempos de contacto;
- a **altura e o azimute do Sol** no instante do máximo local.

Consequências práticas:

- **O payload por eclipse é minúsculo.** Cerca de trinta números chegam para o browser
  calcular tudo ao vivo. Não é preciso enviar grelhas de magnitude nem embutir uma
  biblioteca de efemérides no cliente.
- **Offline e online concordam por construção**, porque partilham os mesmos coeficientes
  e o mesmo algoritmo. Desaparece a categoria de bug "o hover não bate certo com a ficha".
- **A validação contra a NASA é quase trivial**, porque os coeficientes são os da NASA.

O algoritmo é implementado duas vezes, em Python (pipeline) e em TypeScript (browser), e um
teste de ouro garante que não divergem: o Python gera um ficheiro com algumas centenas de
casos (eclipse, lat, lon, saídas esperadas) e o teste JS verifica-o com tolerância apertada.

O Skyfield com efemérides DE441 entra como **auditor independente**, não como motor de
produção: calcula posições topocêntricas do Sol e da Lua a partir de outra cadeia de código
e confirma que a magnitude besseliana está certa em pontos de amostra. Se as duas
concordarem, a confiança é muito maior do que com qualquer das duas sozinha.

---

## 3. Pipeline de dados (Python, offline)

Executado à mão, com os resultados **commitados no repositório**. O build do site em CI é
então puramente frontend, rápido e sem dependências científicas.

Dependências: `numpy`, `skyfield`, `shapely`, `contourpy`, `pyproj`, `tzdata`. Gestão com
`uv`.

### 3.1 `ingest_canon.py`

Descarrega uma vez o JSON de elementos besselianos do canon e o catálogo de circunstâncias
(tipo, gamma, magnitude, ΔT, Saros, coordenadas do eclipse maior), filtra para 1500-2100 e
grava em `pipeline/cache/canon/`. O cache é commitado para o pipeline ser reprodutível sem
rede.

Atribuição obrigatória, a incluir no rodapé do site: *"Eclipse Predictions by Fred Espenak,
NASA's GSFC"*.

O ΔT usado é o que o canon publica por eclipse, para garantir consistência com as
coordenadas de referência da NASA.

### 3.2 `besselian.py`

O núcleo. Implementa, sem dependências para além de `numpy`:

- `local_circumstances(elements, lat, lon, alt)` que devolve tempos de contacto, magnitude
  máxima, obscuração, tipo local (total, anular, parcial, nenhum) e altura e azimute do Sol;
- `central_line(elements)` e `path_limits(elements)` que devolvem as curvas da linha central
  e dos limites norte e sul;
- `magnitude_grid(elements, bbox, step)` para as isomagnitudes.

Este é o ficheiro que tem de estar certo. Leva os comentários que explicam a matemática e
a maior densidade de testes do projeto.

### 3.3 `build_index.py`

Para cada eclipse do canon no intervalo, avalia a visibilidade nos três territórios e escreve
`public/data/eclipses.json`. Por território, guarda magnitude máxima, local mais fundo,
altura do Sol e se a faixa central o atravessa.

Aplica o **limiar de dados pesados**: gera-se faixa, isomagnitudes e concelhos quando a
magnitude máxima em território português for maior ou igual a 0,5, ou quando a faixa central
tocar território português. Os restantes ficam no índice com os números essenciais e um mapa
simples. O limiar fica numa constante configurável, para se poder baixar depois sem mexer no
código.

### 3.4 `build_paths.py`

Para os eclipses acima do limiar, escreve `central.geojson`, `band.geojson` e
`isomag.geojson` (contornos a 20, 40, 60, 80, 90, 95 e 99 por cento). Recorta ao
enquadramento ibérico e simplifica com tolerância adequada à escala, para os ficheiros não
incharem.

Caso especial das faixas sub-quilométricas (o híbrido de 1912): abaixo de 2 km de largura
desenha-se apenas a linha central com espessura fixa e uma nota na ficha, porque um polígono
dessa largura seria uma mentira visual à escala do mapa.

### 3.5 `crossed_municipalities.py`

Cruza a faixa com o GeoJSON de concelhos da CAOP e devolve a lista, com `nome` no formato
"Concelho, Distrito", ordenada pelo instante de entrada da sombra. Guarda também, por
concelho, a duração da totalidade ou anularidade na sede de concelho.

**Nota a exibir no site:** os concelhos são os atuais. Para um eclipse de 1764, a divisão
administrativa da época era outra. O site indica onde a sombra passou em termos de hoje, não
reconstitui a geografia administrativa histórica.

### 3.6 `build_text.py`

Gera o parágrafo de abertura de cada ficha a partir dos números, em pt-PT, com regras de
concordância e vocabulário variado por tipo de eclipse, período do dia e geografia. Sai para
um campo no índice, não para ficheiro solto, e é regenerável.

### 3.7 Tempo local

- **A partir de 1912-01-01:** `zoneinfo` com `Europe/Lisbon`, `Atlantic/Azores` e
  `Atlantic/Madeira`. A base tz já trata da hora de verão histórica e do período de
  1992 a 1996 em que o continente esteve na hora da Europa Central.
- **Antes de 1912:** hora solar média do meridiano do ponto, calculada como
  `UT + longitude/15`, com nota na ficha a explicar que não existia hora legal e que
  cada terra se regia pelo seu meio-dia.

O campo no JSON traz sempre a etiqueta do sistema usado, para a interface poder rotular
corretamente ("hora legal" ou "hora solar média local").

### 3.8 Calendário

O canon usa o calendário juliano antes de 1582-10-15. Portugal adotou o gregoriano na data
da bula, saltando de 4 para 15 de outubro de 1582. Portanto:

- cada eclipse guarda `data_juliana`, `data_gregoriana`, `calendario_vigente_pt` e o dia
  juliano `jd_maximo`;
- a ordenação e os identificadores usam sempre a data gregoriana proléptica, para haver uma
  chave estável e monótona;
- a interface mostra a data no calendário vigente em Portugal à data, com a outra entre
  parênteses quando diferem.

---

## 4. Modelo de dados

```json
{
  "id": "1900-05-28",
  "jd_maximo": 2415133.12,
  "data_gregoriana": "1900-05-28",
  "data_juliana": null,
  "calendario_vigente_pt": "gregoriano",
  "tipo": "total",
  "saros": 126,
  "gamma": 0.5334,
  "delta_t_s": -2.7,
  "maximo_global_ut": "14:53:00",
  "besselianos": {
    "t0_ut": 15.0,
    "x": [0.1, 0.5, 0.0, 0.0],
    "y": [0.2, 0.1, 0.0, 0.0],
    "d": [0.0, 0.0, 0.0],
    "mu": [0.0, 0.0, 0.0],
    "l1": [0.0, 0.0, 0.0],
    "l2": [0.0, 0.0, 0.0],
    "tan_f1": 0.0046,
    "tan_f2": 0.0046
  },
  "territorios": {
    "continente": {
      "visivel": true,
      "magnitude_max": 1.01,
      "obscuracao_max": 1.0,
      "faixa_central": true,
      "local_mais_fundo": { "nome": "Ovar, Aveiro", "lat": 40.86, "lon": -8.62 },
      "maximo_local": "15:28:00",
      "sistema_hora": "hora_legal",
      "alt_sol_graus": 42,
      "duracao_central_s": 92
    },
    "acores": { "visivel": true, "magnitude_max": 0.42, "faixa_central": false },
    "madeira": { "visivel": true, "magnitude_max": 0.61, "faixa_central": false }
  },
  "dados_pesados": true,
  "recursos": {
    "linha_central": "data/1900-05-28/central.geojson",
    "faixa": "data/1900-05-28/band.geojson",
    "isomagnitudes": "data/1900-05-28/isomag.geojson",
    "municipios": "data/1900-05-28/municipios.json"
  },
  "texto_gerado": "Ao fim da tarde de 28 de maio de 1900, ...",
  "incerteza": { "delta_t_km": 1.2, "nota": null },
  "ligacoes_externas": {
    "nasa": "https://eclipse.gsfc.nasa.gov/...",
    "jubier": "http://xjubier.free.fr/..."
  }
}
```

O índice completo carregado na página inicial não deve incluir os besselianos nem os textos
gerados. Divide-se em `eclipses-index.json` (leve, para a lista e os filtros) e
`data/<id>/eclipse.json` (completo, carregado só na ficha).

---

## 5. Frontend (Astro + MapLibre GL JS)

### 5.1 Estrutura

- Astro em modo estático, uma página por eclipse gerada de `eclipses.json` via
  `getStaticPaths`. Bom para SEO e para partilhar ligações diretas.
- i18n do Astro configurado com `defaultLocale: "pt"` e `prefixDefaultLocale: false`, com
  todas as cadeias de texto em `src/i18n/pt.json`. O inglês não se publica agora, mas nada
  no código fica com texto embutido.
- Ilhas de interatividade só onde é preciso (mapa, filtros, simulação). O resto é HTML
  estático.

### 5.2 Mapa

Base vetorial **própria**, servida do próprio repositório: linha de costa e fronteiras
(Natural Earth), concelhos (CAOP) e uma camada de pontos com as sedes de concelho e as
principais localidades. Vantagens sobre depender de tiles de terceiros: sem chave de API,
sem limites de tráfego, sem risco de o fornecedor desaparecer, carregamento rápido, e um
aspeto gráfico coerente e distinto em vez de um mapa genérico por baixo dos dados.

Um comutador opcional acrescenta um fundo raster do OpenStreetMap para quem quiser
referência de terreno.

Camadas comutáveis: faixa de totalidade ou anularidade, linha central, isomagnitudes,
concelhos atravessados, curvas de igual hora de máximo.

### 5.3 Interatividade ao vivo

Ao passar o rato ou tocar no mapa, o cliente calcula com os elementos besselianos a
magnitude, a obscuração, os quatro tempos de contacto, a hora local no sistema correto para
a época e a altura do Sol nesse ponto. Tudo em código próprio, sem bibliotecas externas de
astronomia. Uma caixa de pesquisa permite escolher uma localidade em vez de apontar o rato.

### 5.4 Simulação do aspeto do Sol

Componente SVG que desenha o disco solar com a Lua sobreposta na posição correta, com o
ângulo de posição verdadeiro, para o ponto e o instante selecionados. Acompanha o cursor no
mapa e tem um cursor de tempo para percorrer o eclipse do primeiro ao quarto contacto.

### 5.5 Conteúdo editorial por eclipse

Duas *content collections* do Astro, ambas opcionais e independentes do pipeline:

- `src/content/notas/<id>.md`, para relatos de época, referências em crónicas, fontes e
  bibliografia. A secção só aparece na ficha quando o ficheiro existe.
- `src/content/galeria/<id>.yaml`, para imagens: gravuras e desenhos nos eclipses
  históricos, fotografias nos modernos. Cada entrada leva legenda, autor, ano, fonte e
  licença, e a licença é campo obrigatório para não haver imagens de proveniência duvidosa
  no site. As imagens ficam em `public/imagens/<id>/`, servidas em formatos modernos e com
  `loading="lazy"`.

O pipeline nunca escreve nestas pastas e nunca as apaga.

### 5.6 Página inicial

Linha temporal navegável de 1500 a 2100 e lista filtrável por tipo, século, magnitude
mínima, território, "só com faixa central" e "já observável" (futuros contra passados).
Destaque para os próximos eclipses visíveis a partir da data de hoje.

---

## 6. Validação

Três níveis, do mais barato ao mais completo:

1. **Testes unitários de `besselian.py`** contra os exemplos trabalhados do *Explanatory
   Supplement* e do Meeus, com valores conhecidos.
2. **Âncoras do plano inicial**, que continuam a valer como testes de regressão legíveis:
   - 1900-05-28: totalidade sobre Ovar (magnitude cerca de 1,01), Faro cerca de 0,91.
   - 1870-12-22: faixa a raspar o Algarve, perto dos 37 graus N.
   - 1764-04-01: anular a cruzar o centro do país, região da Marinha Grande.
   - 1912-04-17: híbrido, faixa com cerca de 1 km e 2 segundos por Ovar e Penafiel, com
     quase todo o país entre 97 e 99,8 por cento.
3. **Validação em massa** de todos os eclipses de 1500-2100 contra o catálogo da NASA:
   tipo, instante do máximo global, gamma, magnitude e coordenadas do eclipse maior.
   Tolerâncias definidas e falha do teste acima delas. Mais uma comparação por amostragem
   contra o Skyfield com DE441 em cem pontos aleatórios de dez eclipses.

A incerteza do ΔT é convertida em quilómetros de deslocação da faixa e mostrada na ficha
para os eclipses antigos, porque afeta o limite exato da faixa, não o dia nem a magnitude
em terra.

---

## 7. Ficheiros e organização

```
eclipse-pt/
  pipeline/
    ingest_canon.py
    besselian.py            <- o núcleo, o ficheiro mais testado
    build_index.py
    build_paths.py
    build_text.py
    crossed_municipalities.py
    cache/canon/            <- dados da NASA, commitados
    tests/
      test_besselian.py
      test_ancoras.py
      test_canon_massa.py
      golden/               <- casos partilhados com o teste JS
  site/
    src/
      lib/besselian.ts      <- porto do núcleo, validado contra golden/
      components/ Mapa.astro, SimulacaoSol.astro, Filtros.astro
      pages/ index.astro, eclipse/[id].astro, sobre.astro
      content/ notas/, galeria/
      i18n/ pt.json
    public/
      data/                 <- gerado pelo pipeline, commitado
      geo/                  <- costa, concelhos, localidades
      imagens/
  .github/workflows/deploy.yml
  README.md
  plano.md                  <- este documento
```

---

## 8. Fases

| Fase | Entrega | Aceitação |
|---|---|---|
| M0 | `git init`, estrutura, `plano.md`, convenções no README | Repositório criado e plano aprovado |
| M1 | `ingest_canon.py` e `besselian.py` com testes unitários | Exemplos do Meeus reproduzidos dentro da tolerância |
| M2 | Índice e dados geográficos completos para 1500-2100 | As quatro âncoras passam e a validação em massa contra a NASA passa |
| M3 | Frontend base: lista, filtros, ficha e mapa com camadas | Navegar até 1900-05-28 e ver a faixa sobre Ovar |
| M4 | `besselian.ts` e interatividade ao vivo | Teste de ouro JS passa e o hover concorda com a ficha |
| M5 | Simulação do Sol, texto gerado, notas e galeria | Ficha de 1900 completa, com secções opcionais a aparecer só quando há conteúdo |
| M6 | Acabamento, acessibilidade, desempenho, GitHub Actions e publicação | Site publicado, Lighthouse acima de 90 em desempenho e acessibilidade |

Ordem inegociável: os dados primeiro. Sem M2 validado, não se toca no frontend.

---

## 9. Verificação de ponta a ponta

```bash
# Pipeline
cd pipeline
uv run python ingest_canon.py
uv run pytest tests/ -v                    # unitários, âncoras e validação em massa
uv run python build_index.py && uv run python build_paths.py
uv run python crossed_municipalities.py && uv run python build_text.py

# Frontend
cd ../site
npm ci
npm test                                   # teste de ouro besselian.ts contra o Python
npm run dev                                # verificação visual
npm run build && npm run preview           # confirmar que a build estática sai correta
```

Verificações manuais na `preview`, antes de publicar:

1. `/eclipse/1900-05-28` mostra a faixa a atravessar Ovar e lista os concelhos por ordem
   de entrada da sombra.
2. Passar o rato sobre Faro nesse eclipse dá magnitude perto de 0,91, e o valor coincide
   com o do painel.
3. `/eclipse/1912-04-17` mostra a linha central sem polígono de faixa e a nota do caso
   sub-quilométrico.
4. `/eclipse/1764-04-01` mostra a data no calendário gregoriano com nota, hora solar média
   local em vez de hora legal, e a barra de incerteza do ΔT.
5. Um eclipse anterior a 1582 mostra a data juliana como principal e a gregoriana entre
   parênteses.
6. Um eclipse visível apenas dos Açores aparece no índice com o território correto.
7. Os filtros da página inicial reduzem a lista sem recarregar a página.
8. O site funciona com JavaScript desligado ao nível do conteúdo textual das fichas.

---

## 10. Melhorias futuras (não bloqueantes)

- Mapas de faixa detalhados para Açores e Madeira.
- Animação do avanço da sombra sobre o mapa.
- Modo de comparação entre dois eclipses.
- Publicação da versão inglesa.
- Exportação das faixas em GeoJSON para reutilização noutros mapas.
- Perfil do limbo lunar para os eclipses rasantes, onde as montanhas da Lua deslocam o
  limite da faixa em uma a duas centenas de metros.

---

## 11. Riscos

| Risco | Mitigação |
|---|---|
| A matemática besseliana é fácil de implementar com erros subtis | Testes contra exemplos publicados antes de qualquer outra coisa, mais auditoria independente com Skyfield |
| Divergência entre a implementação Python e a TypeScript | Ficheiro de casos de ouro gerado pelo Python e verificado no teste JS em CI |
| Peso dos dados com centenas de eclipses | Índice leve separado do detalhe, limiar para dados pesados, simplificação de geometria |
| CAOP muda de formato ou de URL | Cópia dos GeoJSON derivados commitada no repositório, com o script de conversão à parte |
| Caminhos do GitHub Pages num subdiretório | `base` configurado no Astro desde M3 e verificado na `preview`, não só em `dev` |

---

## 12. Alterações depois da aprovação

Registo do que mudou em relação ao plano acima, por decisão tomada durante a
execução. O resto do documento fica como estava, que é o seu valor: o que se
combinou antes de começar.

**Intervalo alargado para 1500-2499.** Eram seiscentos anos, passam a mil certos.
O canon da NASA cobre até 3000, por isso não houve nada a inventar:
`ingest_canon.py` passou a descarregar também as páginas do catálogo até 2500 e o
filtro mudou de ano. O catálogo passou de 277 para 471 eclipses. O fim é o último
ano do século XXV e não o primeiro do XXVI, para não haver no catálogo um século
com um ano só lá dentro.

A metade futura vale o que valer o ΔT com que foi calculada. O canon publica uma
extrapolação, e é com ela que se calcula; até ao fim do século XXI o desvio não
muda nada do que se lê, mas nos últimos séculos pode ser da ordem dos minutos, o
que desloca a faixa dezenas de quilómetros. O dia e a magnitude em terra
mantêm-se. A página *Sobre* explica-o ao leitor.

**Página inicial reorganizada.** Três secções passaram a quatro: "Antes" com os
três últimos eclipses, "A seguir" com os três próximos, os filtros, e só depois a
linha temporal, que eles filtram. O catálogo deixou de ser uma tabela corrida e
passou a um acordeão por século, com o século actual aberto por omissão: mil anos
numa lista única não se leem. Os filtros escondem os séculos que ficam vazios e
abrem os que têm alguma coisa.

**Linha temporal em grelha.** A fita de marcas servia para seiscentos anos e
deixou de servir para mil: as marcas encostavam-se e o que se via era uma mancha.
Passou a uma grelha de um quadrado por ano e uma linha por século, à maneira do
calendário de contribuições do GitHub. A cor diz o tipo do eclipse mais fundo do
ano e a intensidade diz quanto do Sol chegou a ser tapado. Os anos sem eclipse
ficam apagados, o que torna visíveis os intervalos secos, que a fita escondia.

**As etiquetas dizem o que se viu daqui.** Um eclipse total no mundo pode não
passar de parcial visto de Portugal, e é o segundo dado que interessa a quem está
cá. A etiqueta passou a trazer as duas coisas: o tipo do eclipse e, quando
diferem, o que dele se viu no território onde foi mais fundo. Acontece em 356 dos
471 eclipses do catálogo. O índice leve ganhou o campo `pt.tipo_local` para isso.

**Isomagnitudes em zonas sombreadas.** Eram curvas de nivel, passam a areas: a
mesma sombra da faixa de totalidade, a esbater-se para fora. Cada feicao e a
zona entre dois niveis, recortada pelo contorno do territorio com uma margem de
mar, e o mapa da-lhe tanto mais cor quanto mais fundo o eclipse for la dentro.

Ao faze-lo apareceu um defeito que as curvas ja tinham: nos eclipses ao nascer e
ao por do Sol, o maximo geometrico da-se com o Sol ainda abaixo do horizonte, e
a magnitude visivel nesse instante e zero. O mapa punha um degrau a dizer que
nao se via nada onde se viu meio Sol tapado a nascer. Passou a usar-se a maior
magnitude atingida com o Sol acima do horizonte, que e o que ali se viu.

**A grelha da linha temporal le-se pelo tamanho.** A intensidade sozinha nao
chegava: num quadrado de quatro pixeis, e com a cor ja tomada pelo tipo de
eclipse, uma diferenca de opacidade nao se ve. A profundidade passou a mandar
tambem no tamanho do quadrado.

**Acordeao exclusivo.** Abrir um seculo fecha o anterior, pelo atributo `name`
dos `details`, sem JavaScript. Com filtro, abre-se o primeiro seculo que tenha
resultados.
