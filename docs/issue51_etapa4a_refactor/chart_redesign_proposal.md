# Etapa 4A — Índice: Redesign dos Gráficos

**Vinculado:** issue #49 (Dashboard charts audit and redesign) e, principalmente, issue #51 (Standardize dashboard UI to ISA-101/ANSI ISA-101 conventions)  
**Contexto:** Refactor ISA-101 removeu os gráficos da tela principal. Esta etapa define onde e como eles voltam, distinguindo dois tipos conceituais fundamentais.

---

## Documentos desta etapa

| Documento                                            | Escopo                                                       | Complexidade |
| ---------------------------------------------------- | ------------------------------------------------------------ | ------------ |
| [01_svg_control_charts.md](01_svg_control_charts.md) | Mini-gráficos operacionais embutidos no SVG (`tep-ihm` only) | Média        |
| [02_analytical_panel.md](02_analytical_panel.md)     | Painel analítico com persistência, ECharts e variable picker | Alta         |

As duas entregas são independentes e podem ser implementadas em ordem. A seção abaixo preserva a distinção conceitual e o mapa de responsabilidades para referência rápida.

---

---

## 1. Distinção conceitual

| Dimensão                  | Gráfico de controle (SVG inline)                        | Gráfico analítico (painel drill-down)         |
| ------------------------- | ------------------------------------------------------- | --------------------------------------------- |
| **Usuário alvo**          | Operador — consciência operacional imediata             | Engenheiro — diagnóstico, sintonia, histórico |
| **ISA-101 Level**         | Level 2 — Overview                                      | Level 3 — Detail / Faceplate                  |
| **Pergunta que responde** | "A planta está sob controle agora?"                     | "O que aconteceu e por quê?"                  |
| **Janela temporal**       | Curta — últimos ~30 min                                 | Toda a sessão                                 |
| **Eixos / escala**        | Implícitos — apenas a forma da curva importa            | Explícitos, com limites HH/LL rotulados       |
| **Interação**             | Nenhuma — passivo, sempre visível                       | Zoom, hover, toggle de séries                 |
| **Implementação**         | Componente `SVGControlChart` — SVG nativo, reutilizável | Chart.js em painel colapsável                 |

---

## 2. Gráficos de controle embutidos no SVG — estratégia de consciência operacional

### 2.1 Objetivo e narrativa

O objetivo **não** é análise profunda. É demonstrar, durante experimentos e perturbações (IDV), que a planta está sendo mantida sob controle:

> Variável crítica desvia → atuador responde → sistema retorna à faixa segura.

Esse padrão é especialmente importante para a narrativa do laboratório: mostrar que o operador Kubernetes (`tep-operator`) e os controladores PID estão intervindo ativamente. O mini-gráfico torna essa intervenção visível sem que o observador precise olhar tabelas ou consoles.

Cada gráfico de controle deve mostrar **ao menos duas séries complementares** quando existir uma malha de controle clara: a variável controlada (XMEAS) e a variável manipulada (XMV). Isso transforma o mini-gráfico de um indicador passivo em evidência visual de uma malha fechada funcionando.

### 2.2 Componente `SVGControlChart` — especificação

O componente deve ser implementado como uma classe ou função de fábrica em JavaScript puro, sem dependências externas. Ele cria e gerencia um elemento `<svg>` filho ancorado ao `#diagram-container`, posicionado via `getBoundingClientRect()` do elemento semântico referenciado.

**Interface de configuração:**

```js
SVGControlChart({
  id:        string,            // ID único desta instância (ex: 'ctrl-reactor-temp')
  anchor:    string,            // data-cell-id do elemento SVG de ancoragem
  placement: 'left' | 'right' | 'above' | 'below',
  offsetPx:  number,           // afastamento extra do anchor em px de tela
  widthPx:   number,           // largura do chart em px de tela
  heightPx:  number,           // altura do chart em px de tela
  bufferSize: number,          // tamanho do ring buffer (pontos)
  series: [
    {
      key:       string,       // identificador interno da série
      label:     string,       // rótulo para o tour
      color:     string,       // CSS var ou hex
      dashed:    boolean,      // true para XMV (linha tracejada = atuador)
      hiLimit?:  number,       // desenha linha horizontal de alarme Hi
      loLimit?:  number,
    }
  ],
})
```

**Renderização interna:**

```
<svg id="ctrl-{id}" class="svg-control-chart" ...>
  <rect class="chart-bg" />                  ← fundo semitransparente
  <line class="chart-hi-limit" ... />        ← limite Hi (se configurado)
  <line class="chart-lo-limit" ... />        ← limite Lo (se configurado)
  <polyline class="chart-series-0" ... />    ← XMEAS (linha sólida)
  <polyline class="chart-series-1" ... />    ← XMV   (linha tracejada)
</svg>
```

**Comportamento:**

- `push(seriesKey, value)` — adiciona valor ao ring buffer e atualiza o `<polyline>` correspondente via `setAttribute('points', ...)`.
- Normalização Y: `min/max` calculados dinamicamente sobre o buffer visível (auto-escala suave).
- Cor muda para `--hmi-warning` ou `--hmi-alarm` se valor ultrapassa `hiLimit`/`loLimit`.
- Reposicionamento automático se o diagrama for redimensionado (listener em `ResizeObserver` no container).
- Cada instância registra-se em `window._svgCharts = {}` pelo seu `id`, permitindo que um tour futuro itere sobre eles.

### 2.3 Gráficos estratégicos — seleção e justificativa

Critério de inclusão: a variável é crítica para segurança ou controle, existe uma malha de controle explícita no TEP, e o mini-gráfico responde a uma pergunta operacional concreta.

---

#### Chart 1 — Temperatura do Reator

| Campo                    | Valor                                                                  |
| ------------------------ | ---------------------------------------------------------------------- |
| **ID**                   | `ctrl-reactor-temp`                                                    |
| **Anchor**               | `sensor-xmeas-09`                                                      |
| **Placement**            | `left`                                                                 |
| **Séries**               | XMEAS(9) Temperatura °C · XMV(10) CWS %                                |
| **Pergunta operacional** | "O reator está aquecendo? O sistema de resfriamento está respondendo?" |
| **Limites**              | Hi: 150°C · Hi-Hi: 165°C (shutdown)                                    |

**Justificativa:** A temperatura do reator é a variável de segurança mais crítica do TEP. Sob distúrbio de reação exotérmica (IDV), o operador/K8s deve aumentar XMV(10) para compensar. Mostrar as duas curvas em paralelo evidencia a ação de controle.

---

#### Chart 2 — Pressão do Reator

| Campo                    | Valor                                                          |
| ------------------------ | -------------------------------------------------------------- |
| **ID**                   | `ctrl-reactor-press`                                           |
| **Anchor**               | `sensor-xmeas-07`                                              |
| **Placement**            | `left`                                                         |
| **Séries**               | XMEAS(7) Pressão kPa · XMV(6) Purga %                          |
| **Pergunta operacional** | "A pressão está sob controle? A purga está removendo inertes?" |
| **Limites**              | Hi: 2800 kPa                                                   |

**Justificativa:** Pressão alta indica acúmulo de inertes. A resposta correta é aumentar a purga (XMV-6). Mostrar pressão + abertura da válvula de purga demonstra diretamente essa relação.

---

#### Chart 3 — Nível e Produto do Separador

| Campo                    | Valor                                                                       |
| ------------------------ | --------------------------------------------------------------------------- |
| **ID**                   | `ctrl-separator-level`                                                      |
| **Anchor**               | `sensor-xmeas-12`                                                           |
| **Placement**            | `right`                                                                     |
| **Séries**               | XMEAS(12) Nível % · XMV(7) Underflow %                                      |
| **Pergunta operacional** | "O separador está acumulando líquido? A válvula de underflow está abrindo?" |
| **Limites**              | Hi: 90% · Lo: 10%                                                           |

**Justificativa:** Nível do separador sem resposta indica falha de controle de inventário. A malha XMV(7) é direta e visível no diagrama.

---

#### Chart 4 — Nível e Produto do Stripper

| Campo                    | Valor                                                                                  |
| ------------------------ | -------------------------------------------------------------------------------------- |
| **ID**                   | `ctrl-stripper-level`                                                                  |
| **Anchor**               | `sensor-xmeas-15`                                                                      |
| **Placement**            | `right`                                                                                |
| **Séries**               | XMEAS(15) Nível % · XMV(8) Produto % · XMEAS(18) Temperatura °C                        |
| **Pergunta operacional** | "O stripper está operando? Produto está saindo? A temperatura de coluna está estável?" |
| **Limites**              | Hi nível: 90% · Hi temp: 80°C                                                          |

**Justificativa:** Três variáveis interdependentes — nível, saída de produto e temperatura de coluna — que juntas descrevem o estado completo do stripper. Um dos poucos gráficos com 3 séries justificadas.

---

#### Chart 5 — Reciclo e Purga

| Campo                    | Valor                                                               |
| ------------------------ | ------------------------------------------------------------------- |
| **ID**                   | `ctrl-recycle-purge`                                                |
| **Anchor**               | `sensor-xmeas-10`                                                   |
| **Placement**            | `above`                                                             |
| **Séries**               | XMEAS(5) Reciclo kscmh · XMEAS(10) Purga kscmh                      |
| **Pergunta operacional** | "O reciclo está em equilíbrio? A purga está mantendo o loop limpo?" |
| **Limites**              | nenhum fixo — referência visual pelo comportamento nominal          |

**Justificativa:** Reciclo e purga são variáveis acopladas: reciclo alto com purga baixa acumula inertes. Ver as duas curvas juntas revela desequilíbrios que nenhuma delas indica individualmente.

---

### 2.4 Compatibilidade com tour futuro — `'graph-tour'`

Cada instância registrada em `window._svgCharts` carrega metadados suficientes para um tour narrativo:

```js
window._svgCharts['ctrl-reactor-temp'] = {
  instance: chart,
  label:    'Reactor Temperature Control',
  tep:      'XMEAS(9) vs XMV(10): temperatura do reator e abertura da válvula de CWS. ...',
  anchor:   'sensor-xmeas-09',
}
```

Um futuro `'graph-tour'` no `DEMO_REGISTRY` (demo.js) pode:
1. Iterar sobre `Object.values(window._svgCharts)`.
2. Para cada chart, injetar dados de um distúrbio sintético (`patch` como no alarm-tour).
3. Mostrar a variável desviando e o atuador respondendo em tempo real.
4. Narrar no console o significado operacional (`tep` field).

---

## 3. Gráficos analíticos — painel colapsável

### Posição no layout

Painel lateral direito que **empurra** (push) o `#diagram-container` quando aberto.  
Toggle: botão `📈` no header, ao lado do botão Demo.  
Estado persistido em `localStorage`.

```
┌─ header ──────────────────────────────────────────────────────────┐
│  TEP-IHM  [status]  [▶ Demo]  [📈 Charts]  [alarms]              │
└───────────────────────────────────────────────────────────────────┘
┌─ diagram (flex) ──────────────┐ ┌─ charts-panel (320px) ─────────┐
│                               │ │  [1] Pressure                   │
│  SVG plant diagram            │ │  [2] Temperature                │
│  (com SVGControlCharts)       │ │  [3] Level                      │
│                               │ │  [4] Feed Flows                 │
│                               │ │  [5] Recycle / Purge            │
│                               │ │  [6] Compressor Work            │
│                               │ │  [7] Actuators — Feeds          │
│                               │ │  [8] Actuators — Process        │
│                               │ │  [9] Actuators — Utilities      │
└───────────────────────────────┘ └─────────────────────────────────┘
```

### Gráficos do painel analítico

| #   | Título                | Séries                       | Variáveis               | Unidade |
| --- | --------------------- | ---------------------------- | ----------------------- | ------- |
| 1   | Pressure              | Reactor, Separator, Stripper | XMEAS(7), (13), (16)    | kPa     |
| 2   | Temperature           | Reactor, Separator, Stripper | XMEAS(9), (11), (18)    | °C      |
| 3   | Level                 | Reactor, Separator, Stripper | XMEAS(8), (12), (15)    | %       |
| 4   | Feed Flows            | A, D, E, A/C                 | XMEAS(1), (2), (3), (4) | misto   |
| 5   | Recycle / Purge       | Recycle, Purge, Reactor Feed | XMEAS(5), (10), (6)     | kscmh   |
| 6   | Compressor            | Work                         | XMEAS(20)               | kW      |
| 7   | Actuators — Feeds     | XMV 1–4                      | xmv[0..3]               | %       |
| 8   | Actuators — Process   | XMV 5–9                      | xmv[4..8]               | %       |
| 9   | Actuators — Utilities | XMV 10–12                    | xmv[9..11]              | %       |

Gráficos 7–9 (XMV) são novos — não existem hoje. Permitem ver a posição de válvulas ao longo do tempo, essencial para diagnóstico de IDV.

### Especificação técnica

```
Biblioteca: Chart.js (já presente)
Paleta ISA: --hmi-line (#4fc3f7) · --hmi-warning (#ffd54f) · --hmi-alarm (#ef5350)
  → sem arco-íris; cada série tem cor fixa por variável
Limites HH/LL: linha de dataset com borderDash (sem plugin externo)
Histórico: MAX_POINTS = 300 (aumentar de 200)
Lazy update: chart.update() só chamado se painel estiver visível
```

---

## 4. Separação de responsabilidades

```
diagram-adapter.js   → SVGControlChart (classe/fábrica, ancoragem, polyline)
diagram-animator.js  → instâncias dos 5 charts, chamadas push() em updateDiagram
app.js               → charts analíticos, toggle do painel, pushData lazy
style.css            → layout push, .charts-panel, .svg-control-chart
index.html           → estrutura do painel analítico, botão toggle
```

---

## 5. Ordem de implementação

**Fase 1 — Painel analítico** (impacto imediato, resolve #49):
1. Toggle + layout push no header
2. Paleta ISA nos charts existentes (remover arco-íris)
3. Linhas de limite HH/LL como datasets tracejados
4. Charts novos: Recycle/Purge, Compressor, XMV grupos (7–9)

**Fase 2 — SVGControlChart** (consciência operacional, narrativa K8s):
1. Implementar classe `SVGControlChart` em `diagram-adapter.js`
2. Instanciar Chart 1 (Reactor Temperature) — variável mais crítica
3. Validar ancoragem, auto-escala e troca de cor por limite
4. Instanciar os demais 4 charts estratégicos
5. Registrar metadados em `window._svgCharts` para o futuro `graph-tour`
