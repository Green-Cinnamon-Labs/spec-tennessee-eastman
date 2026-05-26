# Entrega 1 — Gráficos de Controle Embutidos no SVG

**Escopo:** `tep-ihm` (frontend only)  
**Complexidade:** Média — novo componente JS, sem dependência de backend ou persistência  
**Pré-requisito:** Nenhum além do SVG já carregado

---

## Objetivo

Adicionar mini-gráficos de tendência diretamente no diagrama SVG da planta, posicionados ao lado dos sensores críticos. Não são ferramentas de análise — são indicadores de consciência operacional: o operador (ou observador de experimento) vê em tempo real se a variável está deviando e se o atuador está respondendo.

> Variável desvia → atuador responde → sistema retorna à faixa segura.

---

## Componente `SVGControlChart`

Implementado como classe JS pura em `diagram-adapter.js`, sem dependências externas. Cria e gerencia um `<svg>` filho ancorado ao `#diagram-container`, posicionado via `getBoundingClientRect()` do elemento semântico de ancoragem.

### Interface

```js
new SVGControlChart({
  id:         string,   // ex: 'ctrl-reactor-temp'
  anchor:     string,   // data-cell-id do sensor de ancoragem
  placement:  'left' | 'right' | 'above' | 'below',
  offsetPx:   number,
  widthPx:    number,
  heightPx:   number,
  bufferSize: number,   // ring buffer — pontos mantidos em memória
  series: [{
    key:      string,
    label:    string,   // usado no tour
    color:    string,   // CSS var ou hex
    dashed:   boolean,  // true → XMV (atuador)
    hiLimit?: number,
    loLimit?: number,
  }],
})
```

### Estrutura SVG gerada

```
<svg id="ctrl-{id}" class="svg-control-chart">
  <rect class="chart-bg" />
  <line class="chart-hi-limit" />      ← se configurado
  <line class="chart-lo-limit" />      ← se configurado
  <polyline class="chart-series-0" /> ← XMEAS (sólida)
  <polyline class="chart-series-1" /> ← XMV   (tracejada)
</svg>
```

### Comportamento

- `push(seriesKey, value)` — adiciona ao ring buffer, recalcula `min/max` e atualiza `points`.
- Auto-escala dinâmica sobre o buffer visível (sem eixos numéricos).
- Cor muda para `--hmi-warning` / `--hmi-alarm` ao ultrapassar limites.
- `ResizeObserver` no container reposiciona o chart ao redimensionar.
- Cada instância registra-se em `window._svgCharts[id]` com metadados para o tour.

---

## Gráficos estratégicos — 5 instâncias

### Chart 1 — Temperatura do Reator

|               |                                                             |
| ------------- | ----------------------------------------------------------- |
| **ID**        | `ctrl-reactor-temp`                                         |
| **Anchor**    | `sensor-xmeas-09`                                           |
| **Placement** | `left`                                                      |
| **Séries**    | XMEAS(9) Temp °C (sólida) + XMV(10) CWS % (tracejada)       |
| **Limites**   | Hi 150°C · Hi-Hi 165°C                                      |
| **Pergunta**  | "O reator está aquecendo? O resfriamento está respondendo?" |

### Chart 2 — Pressão do Reator

|               |                                                                |
| ------------- | -------------------------------------------------------------- |
| **ID**        | `ctrl-reactor-press`                                           |
| **Anchor**    | `sensor-xmeas-07`                                              |
| **Placement** | `left`                                                         |
| **Séries**    | XMEAS(7) Pressão kPa (sólida) + XMV(6) Purga % (tracejada)     |
| **Limites**   | Hi 2800 kPa                                                    |
| **Pergunta**  | "A pressão está sob controle? A purga está removendo inertes?" |

### Chart 3 — Nível do Separador

|               |                                                                     |
| ------------- | ------------------------------------------------------------------- |
| **ID**        | `ctrl-separator-level`                                              |
| **Anchor**    | `sensor-xmeas-12`                                                   |
| **Placement** | `right`                                                             |
| **Séries**    | XMEAS(12) Nível % (sólida) + XMV(7) Underflow % (tracejada)         |
| **Limites**   | Hi 90% · Lo 10%                                                     |
| **Pergunta**  | "O separador está acumulando? A válvula de underflow está abrindo?" |

### Chart 4 — Nível e Temperatura do Stripper

|               |                                                                  |
| ------------- | ---------------------------------------------------------------- |
| **ID**        | `ctrl-stripper`                                                  |
| **Anchor**    | `sensor-xmeas-15`                                                |
| **Placement** | `right`                                                          |
| **Séries**    | XMEAS(15) Nível % · XMV(8) Produto % · XMEAS(18) Temp °C         |
| **Limites**   | Hi nível 90% · Hi temp 80°C                                      |
| **Pergunta**  | "O stripper está operando? Produto saindo? Temperatura estável?" |

### Chart 5 — Reciclo e Purga

|               |                                                                     |
| ------------- | ------------------------------------------------------------------- |
| **ID**        | `ctrl-recycle-purge`                                                |
| **Anchor**    | `sensor-xmeas-10`                                                   |
| **Placement** | `above`                                                             |
| **Séries**    | XMEAS(5) Reciclo kscmh · XMEAS(10) Purga kscmh                      |
| **Limites**   | Nenhum fixo — referência visual pelo comportamento nominal          |
| **Pergunta**  | "O reciclo está em equilíbrio? A purga está mantendo o loop limpo?" |

---

## Compatibilidade com `graph-tour`

Cada instância registrada em `window._svgCharts` carrega:

```js
{
  instance: SVGControlChart,
  label:    string,   // nome legível para o tour
  tep:      string,   // narrativa operacional completa
  anchor:   string,   // data-cell-id do sensor
}
```

Um futuro `'graph-tour'` no `DEMO_REGISTRY` pode iterar sobre essas instâncias, injetar dados de distúrbio sintético e narrar o laço de controle em tempo real — usando a mesma infraestrutura do alarm-tour e do flow-path-tour já implementados.

---

## Arquivos afetados

| Arquivo               | Mudança                                              |
| --------------------- | ---------------------------------------------------- |
| `diagram-adapter.js`  | Classe `SVGControlChart`                             |
| `diagram-animator.js` | 5 instâncias, chamadas `push()` em `updateDiagram`   |
| `style.css`           | `.svg-control-chart`, `.chart-bg`, `.chart-hi-limit` |

---

# Decisões para Implementação — Gráficos de Controle Embutidos no SVG

Este documento define o mínimo necessário para iniciar a implementação dos mini-gráficos operacionais embutidos no SVG da planta Tennessee Eastman.

## 1. Tipo de componente

- Será implementado um componente próprio em **SVG + JavaScript puro**.
- Não usar ECharts dentro do SVG.
- Nome sugerido do componente: `SVGControlChart`

A função do componente é criar pequenos gráficos operacionais diretamente sobre o diagrama da planta, com foco em consciência operacional, não análise profunda.

## 2. Formato visual esperado

Cada gráfico deve ser um mini-card no estilo ISA-101/HMI, contendo:

- gráfico de tendência à esquerda;
- barra vertical de valor atual à direita;
- valor numérico atual;
- unidade da variável;
- tag curta do controlador ou variável, quando aplicável;
- limites/faixa segura quando fizer sentido.

Referência visual desejada:

```txt
[mini tendência histórica] + [barra vertical de valor atual] + [valor/unidade]
```

## 3. Onde os gráficos devem ficar

Os gráficos devem ser posicionados próximos aos elementos críticos do SVG, sem poluir o diagrama.

Pontos estratégicos:

1. perto do reator;
2. perto do PI/TI do reator;
3. perto do separador vapor/líquido;
4. perto do stripper;
5. perto do sistema recycle/purge.

A posição final pode ser ajustada depois visualmente, mas cada gráfico deve possuir um `anchor` semântico no SVG.

## 4. Gráficos do baseline

Implementar inicialmente cinco gráficos:

| ID sugerido            | Tema                  | Objetivo operacional                                                |
| ---------------------- | --------------------- | ------------------------------------------------------------------- |
| `ctrl-reactor-temp`    | Temperatura do reator | Mostrar aquecimento/resfriamento e resposta da água de resfriamento |
| `ctrl-reactor-press`   | Pressão do reator     | Mostrar pressão e resposta da purga                                 |
| `ctrl-separator-level` | Nível do separador    | Mostrar acúmulo/esvaziamento e atuação no underflow                 |
| `ctrl-stripper`        | Stripper              | Mostrar estabilidade do stripper e saída de produto                 |
| `ctrl-recycle-purge`   | Reciclo/purga         | Mostrar equilíbrio do loop de gás                                   |

## 5. Variáveis de cada gráfico

### 5.1 Reactor Temperature

```txt
XMEAS(9)  = Reactor Temperature [°C]
XMV(10)   = Reactor Cooling Water Flow [%]
```

Pergunta operacional:

```txt
O reator está aquecendo? O resfriamento está respondendo?
```

### 5.2 Reactor Pressure

```txt
XMEAS(7)  = Reactor Pressure [kPa]
XMV(6)   = Purge Valve [%]
```

Pergunta operacional:

```txt
A pressão está sob controle? A purga está reagindo?
```

### 5.3 Separator Level

```txt
XMEAS(12) = Separator Level [%]
XMV(7)   = Separator Liquid Outlet / Underflow [%]
```

Pergunta operacional:

```txt
O separador está acumulando? A válvula de underflow está abrindo?
```

### 5.4 Stripper

Opção inicial recomendada:

```txt
XMEAS(15) = Stripper Level [%]
XMV(8)   = Stripper Liquid Product Outlet [%]
XMEAS(18)= Stripper Temperature [°C]
```

Pergunta operacional:

```txt
O stripper está estável? O produto está saindo? A temperatura está dentro da faixa?
```

Se ficar visualmente poluído, simplificar para:

```txt
XMEAS(15) + XMV(8)
```

### 5.5 Recycle/Purge

```txt
XMEAS(5)  = Recycle Flow [kscmh]
XMEAS(10) = Purge Rate [kscmh]
XMV(6)   = Purge Valve [%]  // opcional
```

Pergunta operacional:

```txt
O gás está sendo reciclado ou purgado? O loop está equilibrado?
```

## 6. Escala dos mini-gráficos

Decisão inicial sugerida:

- Não usar autoescala pura como regra geral.
- Preferir normalização por faixa operacional ou faixa esperada.
- O objetivo é percepção operacional, não ajuste fino.

Critério sugerido:

```txt
variável de processo → normalizar por faixa operacional conhecida
atuador XMV          → normalizar 0–100%
```

Motivo:

- autoescala destaca variações pequenas demais e pode enganar visualmente;
- escala fixa é mais honesta para operação;
- normalização permite misturar variável de processo e atuador no mesmo mini-card.

## 7. Janela temporal

Decisão inicial sugerida:

```txt
bufferSize = 60 pontos
```

Interpretação depende da taxa de atualização:

- se a atualização for ~1 ponto/s → mostra ~1 minuto;
- se houver downsample para 1 ponto/5s → mostra ~5 minutos;
- se houver downsample para 1 ponto/30s → mostra ~30 minutos.

Para primeira entrega, usar o buffer simples. Refinar depois com downsample se necessário.

## 8. Limites operacionais

Priorizar limites visuais nos gráficos mais críticos:

| Gráfico             | Limites iniciais                                                |
| ------------------- | --------------------------------------------------------------- |
| Reactor Temperature | Hi 150 °C, Hi-Hi 165 °C                                         |
| Reactor Pressure    | Hi 2800 kPa ou referência próxima ao limite operacional         |
| Separator Level     | Lo 10%, Hi 90%                                                  |
| Stripper Level      | Lo 10%, Hi 90%                                                  |
| Recycle/Purge       | sem limite fixo inicial; usar referência nominal/comportamental |

A representação visual pode usar:

- linha horizontal de limite;
- marcador triangular;
- mudança de cor da série ao ultrapassar limite;
- faixa sombreada, se não poluir.

## 9. Integração técnica

A implementação deve seguir esta estrutura:

```txt
diagram-adapter.js
  → classe SVGControlChart

 diagram-animator.js
  → criação das 5 instâncias
  → alimentação dos gráficos dentro de updateDiagram(xmeas, xmv)

style.css
  → estilos dos mini-cards, linhas, barras e limites
```

O componente deve:

- localizar o `anchor` semântico no SVG;
- posicionar o mini-card próximo ao anchor;
- manter ring buffer por série;
- redesenhar polyline e barra de valor atual;
- reposicionar quando o container/SVG for redimensionado.

## 10. Compatibilidade com tour futuro

Cada gráfico deve se registrar em:

```js
window._svgCharts
```

Com metadados mínimos:

```js
{
  id: 'ctrl-reactor-temp',
  label: 'Reactor Temperature',
  anchor: 'sensor-xmeas-09',
  variables: ['xmeas[8]', 'xmv[9]'],
  tep: 'Narrativa operacional para o tour'
}
```

Isso prepara um futuro:

```txt
graph-tour
```

O tour poderá:

- destacar cada mini-gráfico;
- explicar a variável controlada;
- explicar o atuador associado;
- injetar dados sintéticos;
- narrar a sequência: desvio → atuação → retorno à faixa segura.

## 11. Mínimo para começar

Para iniciar a implementação, considerar fechado:

1. componente próprio em SVG/JS;
2. cinco gráficos do baseline;
3. variáveis associadas a cada gráfico;
4. anchor semântico de cada gráfico;
5. escala inicial por normalização/faixa operacional;
6. buffer inicial de 60 pontos;
7. registro em `window._svgCharts` para tour futuro.

O refinamento visual fino deve ser feito depois de ver os gráficos renderizados sobre o SVG real.
