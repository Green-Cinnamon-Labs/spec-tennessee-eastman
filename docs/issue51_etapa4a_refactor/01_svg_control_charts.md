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

## Questões em aberto

- Tamanho padrão dos charts (px): depende de testes visuais no SVG real.
- Escala Y: auto-scaling puro ou banda fixa por variável? Auto-scaling pode confundir se a variação for pequena.
- Janela temporal: 60 pontos a ~1 ponto/30s = 30 min. Adequado?
