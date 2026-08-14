# Plano de entrega: site interativo "Eclipses Solares em Portugal"

Documento para o Claude Code executar. Objetivo: um site estático e interativo que
cataloga os eclipses solares visíveis em Portugal ao longo dos séculos, com fichas por
eclipse e mapas dinâmicos (faixa de totalidade/anularidade quando existe, isomagnitudes,
concelhos atravessados).

Contexto: a lógica astronómica já foi prototipada e validada. Este documento transfere
essa lógica e define arquitetura, dados, funcionalidades, fases e critérios de aceitação.

As escolhas de tecnologia neste documento são uma recomendação inicial, abertas e
sujeitas a sugestões do Claude Code. Se houver alternativas melhores, propor.

---

## 0. Convenções obrigatórias (aplicar em todo o projeto)

- Português europeu. Evitar brasileirismos (usar "rever", não "revisar"; "ficheiro", não "arquivo").
- Nunca usar travessões (em dash). Se for mesmo preciso um separador, usar hífen simples.
- Sem emojis no código.
- Horas apresentadas ao utilizador em hora de Portugal (converter de UT).
- GeoJSON de municípios: campo `nome` no formato "Concelho, Distrito" (ex.: "Vila Nova de Gaia, Porto").
- Fornecer uma mensagem de commit sempre que houver alteração de código.
- Quando um requisito não estiver suficientemente explícito, pedir esclarecimento antes de avançar.

---

## 1. Âmbito

Parâmetros já decididos:

- Horizonte temporal: 1500-2100.
- Alojamento: GitHub Pages (site estático).
- Tecnologia: as opções indicadas na secção 3 são uma recomendação inicial, abertas a sugestões. Confirmar a escolha final com o Carlos antes de fixar.

A confirmar com o Carlos no arranque (M0):

1. Territórios. Por omissão só Portugal continental. Confirmar se inclui Açores e Madeira (têm outra geometria de visibilidade).
2. Critério de "avistado". Por omissão qualquer fase parcial com o Sol acima do horizonte. A interface deve permitir filtrar por magnitude mínima.

Nota de calendário: no intervalo 1500-2100, atenção à transição juliano/gregoriano. Portugal adotou o gregoriano em 1582, por isso datas anteriores a essa data devem assinalar claramente o calendário usado.

---

## 2. Lógica astronómica validada (transferir tal e qual)

Motor de cálculo do protótipo: efemérides VSOP87 (Sol) e ELP2000 (Lua), posições
topocêntricas, sem refração. Validou-se contra casos conhecidos.

Para cada observador (lat, lon) e instante:

- Separação angular topocêntrica `d` entre centros do Sol e da Lua.
- Raios aparentes: `Rs` (Sol), `Rm` (Lua), a partir do diâmetro aparente.
- Magnitude (fração do diâmetro solar coberto): `mag = (Rs + Rm - d) / (2*Rs)`, com `mag <= 0` quando `d >= Rs + Rm` (sem eclipse).
- Classificação central: se `d <= |Rs - Rm|` o eclipse é central nesse ponto; é `Total` se `Rm >= Rs`, senão `Anular`. Caso contrário é `Parcial`.
- Exigir Sol acima do horizonte (`alt > 0`) para o ponto ter fase visível.

Âncoras de validação (o pipeline tem de as reproduzir):

- 1900-05-28: totalidade a passar em Ovar (mag ~1.01), parcial funda no resto (Faro ~0.91).
- 1870-12-22: faixa da totalidade a raspar o Algarve (~37 graus N).
- 1764-04-01: anel (anular) a cruzar o centro do país, sobre a região da Marinha Grande.
- 1912-04-17: híbrido, faixa de totalidade com cerca de 1 km de largura e ~2 s por Ovar-Penafiel; quase todo o país viu 97-99,8 por cento (parcial fundíssima).

Armadilhas encontradas (documentar no código):

- Faixa central contínua: ao traçar a faixa por varrimento temporal, usar passo de ~1 minuto. Com passos maiores a sombra "salta" e a faixa sai aos blocos.
- Resolução espacial: faixas estreitas (algumas de 90 a 360 km, o híbrido de 1912 com ~1 km) exigem grelha fina. Bandas sub-quilométricas (1912) não devem ser desenhadas como polígono de faixa; tratar como caso especial e marcar apenas a linha central e uma nota.
- Mascarar pontos com o Sol abaixo do horizonte (relevante em eclipses ao nascer/pôr do Sol, ex.: 1842).
- ΔT (incerteza da rotação da Terra) cresce para épocas antigas; afeta o limite exato da faixa em alguns km, não o dia nem a magnitude em terra. Assinalar essa incerteza nas fichas mais antigas.

---

## 3. Arquitetura recomendada (aberta a sugestões)

Princípio-chave: precalcular offline apenas o que é caro (traçado das faixas e limites),
e calcular as circunstâncias locais ao vivo no browser. Isto mantém o site leve e
totalmente dinâmico ao passar o rato.

### 3.1 Pipeline de dados (offline, Python)

Dependências mínimas: `ephem` (pyephem), `numpy`. Opcional: `shapely` (polígonos de faixa),
`contourpy` ou `matplotlib` (extrair isomagnitudes para GeoJSON).

Scripts:

- `compute_index.py`: para o intervalo escolhido, encontra todos os eclipses solares com fase visível em Portugal e calcula, por eclipse: tipo, instante de máximo (UT e hora de Portugal), Saros, magnitude máxima em Portugal, local mais fundo, regiões afetadas, altura do Sol. Escreve `data/eclipses.json`.
- `compute_paths.py`: para os eclipses centrais, calcula a linha central (LineString) e os limites da faixa (Polygon) em GeoJSON, por varrimento temporal a 1 minuto. Opcionalmente extrai isomagnitudes (contornos 60/80/90/95/100 por cento) para GeoJSON.
- `crossed_municipalities.py`: cruza a faixa central com o GeoJSON de concelhos (CAOP/DGT) e devolve a lista de concelhos atravessados, com `nome` no formato "Concelho, Distrito".

Saída em `public/data/`: `eclipses.json` (índice) e, por eclipse, `data/<id>/central.geojson`,
`band.geojson`, `isomag.geojson`, `municipios.json`.

### 3.2 Frontend (site estático)

Recomendação inicial, aberta a sugestões (confirmar em M0):

- Framework: Astro (estático, rápido, por componentes) ou Vite + JS simples.
- Mapa: Leaflet + tiles OpenStreetMap (sem chave de API) como opção robusta; MapLibre GL JS como alternativa vetorial mais bonita.
- Circunstâncias locais ao vivo: biblioteca JS `astronomy-engine` (Don Cross), que tem pesquisa de eclipses solares locais e dá obscuração/tipo num ponto. Serve para o "hover" e para os valores por localidade sem grelhas pesadas.
- Camadas geográficas empacotadas: fronteiras (Natural Earth) e concelhos (CAOP/DGT).
- Alojamento: GitHub Pages. Garantir que a build gera um site totalmente estático, com os caminhos corretos para o subdiretório do repositório se aplicável.

---

## 4. Modelo de dados (eclipse, índice)

```json
{
  "id": "1900-05-28",
  "data_utc": "1900-05-28",
  "tipo": "total|anular|hibrido|parcial",
  "maximo_utc": "14:53",
  "maximo_pt": "15:28",
  "saros": 126,
  "pt": {
    "magnitude_max": 1.01,
    "local_mais_fundo": { "nome": "Ovar", "lat": 40.86, "lon": -8.62 },
    "faixa_sobre_pt": true,
    "regioes": ["Norte", "Centro"],
    "alt_sol_graus": 42
  },
  "recursos": {
    "linha_central": "data/1900-05-28/central.geojson",
    "faixa": "data/1900-05-28/band.geojson",
    "isomagnitudes": "data/1900-05-28/isomag.geojson",
    "municipios": "data/1900-05-28/municipios.json"
  },
  "ligacoes_externas": {
    "nasa": "https://eclipse.gsfc.nasa.gov/...",
    "jubier": "http://xjubier.free.fr/..."
  }
}
```

---

## 5. Funcionalidades da interface

- Página inicial: linha temporal e lista filtrável (por tipo, século, magnitude mínima, região, "só com faixa central").
- Ficha de eclipse: mapa dinâmico com camadas comutáveis (faixa, linha central, isomagnitudes, concelhos atravessados). Ao passar o rato ou clicar num ponto, calcular ao vivo (astronomy-engine) a magnitude, a hora de Portugal e a altura do Sol nesse ponto. Painel com os dados, os concelhos atravessados e as ligações externas (NASA, Jubier).
- Opcional (avançado): animação do avanço da sombra sobre o mapa, a partir de fotogramas precalculados.

---

## 6. Fases e critérios de aceitação

- M0 Âmbito: confirmar Açores/Madeira, o critério de "avistado" e a stack final. Aceitação: âmbito escrito e aprovado.
- M1 Pipeline de dados: gerar `eclipses.json` e os GeoJSON. Aceitação: reproduz as quatro âncoras da secção 2 dentro de ~0.02 de magnitude e com a faixa no sítio certo.
- M2 Frontend base: lista, filtros e ficha com mapa a mostrar as camadas estáticas. Aceitação: navegar e ver a faixa de 1900 sobre Ovar.
- M3 Interatividade ao vivo: hover/click a devolver magnitude, hora de Portugal e altura do Sol via astronomy-engine. Aceitação: valores batem com o `eclipses.json` nos locais conhecidos.
- M4 Acabamento e deploy: desempenho, acessibilidade básica, pt-PT, publicação em GitHub Pages. Aceitação: site publicado e a carregar rápido.

---

## 7. Melhorias futuras (não bloqueantes)

- Açores e Madeira.
- Modo de comparação entre eclipses.
- Exportação das faixas em GeoJSON para reutilização noutros mapas.
- Ficha "o que se veria" com simulação do aspeto do Sol eclipsado à hora local.

---

## 8. Notas finais para o Claude Code

- Começa pelo pipeline de dados e valida contra as âncoras antes de tocar no frontend. Sem dados corretos, o resto não interessa.
- Mantém o cálculo pesado offline e o cálculo local ao vivo no cliente.
- As opções de tecnologia são recomendações; se tiveres melhores, propõe-nas ao Carlos.
- Segue as convenções da secção 0 em todo o código e conteúdo.
- Em qualquer ambiguidade de âmbito, pergunta ao Carlos antes de decidir.