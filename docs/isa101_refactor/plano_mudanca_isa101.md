# Plano de Mudança — Dashboard TEP para ISA-101

**Issue:** #51  
**Guia normativo:** `docs/isa101_refactor/guia-claude-ihm-isa101.md`  
**Referência PDF:** `ISA-101-III-Simpósio-ISA-São-Paulo-Sabesp-Nov2016.pdf`  
**Tela atual:** `tep-ihm/static/index.html` + `plant-diagram.svg` + `app.js`

---

## 1. Enquadramento da tela atual

**Qual nível é essa tela?**

A tela atual mistura dois níveis em uma única superfície:

| Região                       | Nível ISA-101          | O que deveria ser                    |
| ---------------------------- | ---------------------- | ------------------------------------ |
| P&ID (esquerda)              | Nível 2 — área/unidade | Diagnóstico de unidade de processo   |
| Gráficos (direita)           | Nível 3 — detalhe      | Drill-down de malha ou loop          |
| Tabela XMEAS/XMV (baixo)     | Nível 4 — engenharia   | Configuração, debug, análise técnica |
| Painel de Distúrbios (baixo) | Nível 3                | Entrada de ação operacional          |

**Problema:** o operador está numa única tela vendo diagnóstico de área, trends detalhados e tabela de 41 variáveis ao mesmo tempo. Isso viola o princípio de redução de carga cognitiva (guia §4.2) e mistura drill-downs que deveriam exigir navegação consciente.

---

## 2. Resposta à pergunta: os gráficos entram na planta?

**Sim e não — depende do tipo de gráfico.**

O guia §15.2 diz que Nível 2 deve ter **mini trends** das variáveis-chave embutidos próximos às unidades. O guia §18.2–18.4 especifica quais variáveis cada área deve exibir com tendência curta.

Os **gráficos atuais** (Pressure, Temperature, Level, Feed Flow com janela longa, múltiplas séries, legenda) são Nível 3 — pertencem a uma tela de detalhe acessível por drill-down a partir do P&ID.

**Regra prática para este projeto:**

| Tipo                                                  | Onde fica                                            |
| ----------------------------------------------------- | ---------------------------------------------------- |
| Mini trend (janela curta, 1 variável, limite visível) | Dentro do P&ID, ancorado na unidade                  |
| Trend detalhado (múltiplas séries, janela longa)      | Painel lateral colapsável OU tela separada (Nível 3) |
| Tabela completa XMEAS 1–41                            | Removida da tela operacional; acessível via Nível 4  |

---

## 3. Violações atuais catalogadas

### 3.1 Cores — violações críticas (guia §7)

| Elemento                | Comportamento atual        |                                              Regra violada | Prioridade |
| ----------------------- | -------------------------- | ---------------------------------------------------------: | ---------- |
| Fundo do SVG            | `#1e4d7f` azul escuro      |             Fundo deve ser cinza médio `--hmi-bg: #D9DEE2` | 🔴          |
| Reator (vessel)         | Laranja/marrom contínuo    |               Cor forte em estado normal — proibido (§7.4) | 🔴          |
| Condensador / Separador | Azul contínuo              |                                                       Idem | 🔴          |
| Gráficos de trends      | Paleta arco-íris (6 cores) | "Não usar paleta arco-íris para dados operacionais" (§7.4) | 🔴          |
| Labels de sensores      | `#00e5ff` ciano constante  |                Cor de ênfase usada em estado normal (§7.3) | 🟡          |
| Fundo geral da tela     | Preto / dark               |                            Deve ser `--hmi-bg` cinza claro | 🔴          |

### 3.2 Hierarquia e organização (guia §5, §8)

| Problema                                                    | Regra violada                                        |
| ----------------------------------------------------------- | ---------------------------------------------------- |
| Nível 2 + Nível 3 + Nível 4 na mesma tela                   | §5 — cada tela tem um nível exato                    |
| Tabela XMEAS 1–41 como lista numérica                       | §8.3 — "Exemplo ruim: XMEAS 1, XMEAS 2, ..."         |
| Sem hierarquia visual entre unidades críticas e secundárias | §8.2 — hierarquia por tamanho, posição e agrupamento |
| Sem breadcrumb ou indicação de nível                        | §6.1 — toda tela tem título e localização            |

### 3.3 Tendências (guia §15)

| Problema                                                | Regra                                                        |
| ------------------------------------------------------- | ------------------------------------------------------------ |
| Trends grandes ao lado do P&ID sem drill-down explícito | §15.2 — Nível 2 usa mini trends                              |
| Sem indicação de limite operacional nas séries          | §15.2 — "faixa normal e limite operacional quando relevante" |
| Sem indicação de subida/descida por variável            | §15.2 — "indicação de subida/descida"                        |

### 3.4 Representação numérica (guia §13)

| Problema                                                | Regra                                                          |
| ------------------------------------------------------- | -------------------------------------------------------------- |
| Labels de sensores sem nome operacional                 | §13.1 — estrutura obrigatória: nome + valor + unidade + estado |
| Analisadores mostram `XX.X%` sem identificar componente | §13.1 — toda variável precisa de nome operacional              |
| Tabela usa `XMEAS(N)` como label principal              | §13.2 — tag técnica não substitui nome operacional             |

### 3.5 Posicionamento de labels SVG (guia §19.5)

| Problema                                                                            | Regra                                                               |
| ----------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `getOrCreateAnalyzerText` calcula posição dinamicamente por `getBoundingClientRect` | §19.5 — "posição do label vem de metadado, não de cálculo genérico" |
| `getOrCreateValueText` usa `getBBox()` para posicionar                              | Idem                                                                |
| Sem `preferredSide` declarado por sinal no SVG                                      | §19.5 — cada medição deve declarar lado preferido                   |

---

## 4. Plano de mudança por etapas

As etapas estão ordenadas por impacto/risco. Cada uma é independente — pode ser entregue em PR separado.

---

### Etapa 1 — Paleta ISA e fundo (baixo risco, alto impacto visual)

**Arquivos:** `tep-ihm/static/index.html`, `diagram-animator.js`

Implementar as variáveis CSS do guia §25 e aplicar ao fundo geral e ao SVG:

```css
/* index.html — :root */
--hmi-bg:       #D9DEE2;
--hmi-panel:    #EEF1F3;
--hmi-line:     #6F767D;
--hmi-text:     #1F252A;
--hmi-muted:    #6B7278;
--hmi-data:     #263238;
--hmi-warning:  #B7791F;
--hmi-alarm:    #B00020;
--hmi-invalid:  #7A3E9D;
--hmi-manual:   #1F5F8B;
--hmi-selected: #005A9C;
--hmi-disabled: #9AA1A6;
```

```js
// diagram-animator.js — initDiagramInteraction()
// ANTES:
if (bgRect) bgRect.setAttribute('fill', '#1e4d7f');
// DEPOIS:
if (bgRect) bgRect.setAttribute('fill', '#D9DEE2');
```

Labels de sensores: trocar `#00e5ff` → `var(--hmi-data)` (`#263238`) em estado normal.

---

### Etapa 2 — Vasos: estado normal cinza, cor apenas em alarme

**Arquivo:** `diagram-animator.js` → `colorizeVessel()`

```js
// ANTES: gradiente contínuo decorativo
const color = tempC < 100 ? '#4fc3f7' : tempC < 150 ? '#ffb74d' : '#ef5350';

// DEPOIS: cinza normal, cor apenas em condição anormal
// Limites por unidade a definir em tep-svg-mapping.json (campo alarm_limits)
function colorizeVessel(vesselId, tempC, limits = {}) {
    const wrapper = document.querySelector(`[data-cell-id="${vesselId}"]`);
    if (!wrapper) return;

    const { hi_hi = 175, hi = 160 } = limits;
    const color = tempC > hi_hi ? 'var(--hmi-alarm)'    // #B00020
                : tempC > hi    ? 'var(--hmi-warning)'  // #B7791F
                :                 'var(--hmi-line)';     // #6F767D normal

    wrapper.querySelectorAll('path, ellipse, rect').forEach(el => {
        el.style.fill        = color;
        el.style.fillOpacity = tempC > hi ? '0.55' : '0.25';
    });
}
```

Adicionar campo `alarm_limits` por unidade em `tep-svg-mapping.json`.

---

### Etapa 3 — Labels de sensores via metadado (substitui cálculo dinâmico)

**Arquivo:** `diagram-animator.js` — substituir `getOrCreateAnalyzerText` e `getOrCreateValueText`

Criar `SIGNAL_LAYOUT` conforme §19.5 do guia, com `anchorId` e `preferredSide` para cada sinal:

```js
const SIGNAL_LAYOUT = {
    'sensor-xmeas-07': { name: 'Reactor Pressure',     unit: 'kPa',   preferredSide: 'right' },
    'sensor-xmeas-08': { name: 'Reactor Level',        unit: '%',     preferredSide: 'right' },
    'sensor-xmeas-09': { name: 'Reactor Temp',         unit: '°C',    preferredSide: 'right' },
    'sensor-xmeas-12': { name: 'Separator Level',      unit: '%',     preferredSide: 'left'  },
    // ... demais sinais
};
```

Função `placeSignalLabel(signalId, value, state)` que:
1. Lê `SIGNAL_LAYOUT[signalId].preferredSide`
2. Encontra o `drawable` via `getDrawablePath`
3. Posiciona com offset fixo por lado (não calculado por `getBoundingClientRect` a cada tick)
4. Aplica classe CSS de estado: `hmi-state-normal`, `hmi-state-warning`, `hmi-state-alarm`

---

### Etapa 4 — Reestruturação de layout: mini trends no P&ID

**Conceito:**

Substituir os 4 gráficos grandes (Pressure, Temperature, Level, Feed Flow) por:

- **Mini trends** embutidos no P&ID, ancorados nas unidades: Reator, Separador, Stripper
- **Painel colapsável** lateral para trend detalhado (acessível via clique na unidade = drill-down Nível 3)

```
┌─────────────────────────────────┬──────────────────────────────────┐
│  PROCESS DIAGRAM (Level 2)      │  [collapsed or open: Level 3]    │
│                                 │                                  │
│  ┌─Reactor──────────────────┐   │  Reactor Pressure — 30min        │
│  │ P: 2705 kPa  ↑           │   │  ████████████████                │
│  │ T: 120.4°C   →           │   │  SP: 2705  HH: 3000              │
│  │ L: 75.0%     ↓           │   │                                  │
│  │ [mini trend P ▁▂▃▂▁▂▃]  │   │  Reactor Temperature — 30min     │
│  └──────────────────────────┘   │  ...                             │
└─────────────────────────────────┴──────────────────────────────────┘
```

A tabela XMEAS 1–41 sai da tela operacional e vai para uma aba/tela Nível 4 acessível por botão "Engineering View".

---

### Etapa 5 — Alarmes estruturados (integração com payload WebSocket)

Requer mudança no backend (`tep-plant` ou `tep-ihm`): adicionar campo `alarms` no payload WebSocket.

```json
{
  "xmeas": [...],
  "xmv": [...],
  "alarms": [
    { "id": "xmeas-7-hi-hi", "signal": "xmeas-7", "severity": 2, "state": "unacknowledged" }
  ]
}
```

No frontend: `updateAlarmState(alarmId, severity, state)` aplica classes do guia §14:
- `hmi-state-warning` — contorno âmbar + texto `WARN`
- `hmi-state-alarm` — vermelho escuro + ícone + texto `ALARM`
- `hmi-state-unacknowledged-alarm` — idem + pulso CSS (ver §25 do guia)

---

## 5. Desvios aceitáveis documentados

Conforme §26 do guia: uma tela é aceita se o operador consegue detectar, diagnosticar, responder e valorar. Os desvios abaixo não comprometem esses objetivos:

| Desvio                                                        | Justificativa                                                                                                               |
| ------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| Fundo do P&ID pode ser cinza escuro (não o `#D9DEE2` do guia) | Diagrama P&ID industrial usa fundo escuro para reduzir reflexo em sala de controle — prática aceita em implementações reais |
| Simbologia de vasos não é ISA 5.1 puro                        | Draw.io sem biblioteca ISA nativa; símbolos customizados documentados                                                       |
| Tags internas `sensor-xmeas-N` em vez de `TI-09`              | IDs semânticos para JS; labels ISA visíveis são camada separada (Etapa 3)                                                   |
| Sem Nível 1 (Overview)                                        | Escopo: um único processo contínuo, não planta multiproduto                                                                 |
| Sem sistema de ACK de alarmes                                 | Backend não tem persistência de estado de alarme ainda (Etapa 5 depende de issue separada)                                  |

---

## 6. Checklist ISA-101 (do guia §22) — estado atual

| #   | Pergunta                                          | Estado                                           |
| --- | ------------------------------------------------- | ------------------------------------------------ |
| 1   | Qual é o nível da tela?                           | ✗ Mistura Nível 2, 3 e 4                         |
| 2   | Qual decisão operacional a tela suporta?          | ✗ Não está explícita                             |
| 3   | O normal está visualmente calmo?                  | ✗ Vasos coloridos em estado normal               |
| 4   | O anormal se destaca sem depender só de cor?      | ✗ Nenhum alarme visual implementado              |
| 5   | Existem unidades em todos os valores?             | ✓ Parcial                                        |
| 6   | Há tendência onde direção importa?                | ✓ Trends existem, mas são Nível 3 na tela errada |
| 7   | Botões têm verbo + objeto?                        | ✗ "Pause", "+" não têm objeto                    |
| 8   | O layout funciona em tons de cinza?               | ✗ Fundo escuro + texto ciano falham              |
| 9   | Labels SVG vêm de metadado?                       | ✗ Calculados dinamicamente                       |
| 10  | A tela evita 3D, gradiente e animação sem função? | ✓ Sem 3D. Gradiente parcial nos vasos            |

---

## 7. Arquivos a modificar por etapa

| Arquivo                                             | Etapa   | Mudança                                             |
| --------------------------------------------------- | ------- | --------------------------------------------------- |
| `tep-ihm/static/index.html`                         | 1, 4    | Variáveis CSS, estrutura de layout                  |
| `tep-ihm/static/diagram-animator.js`                | 1, 2, 3 | Paleta, `colorizeVessel`, `SIGNAL_LAYOUT`           |
| `tep-ihm/static/diagram-adapter.js`                 | 3       | `placeSignalLabel` substitui `getOrCreateValueText` |
| `tep-ihm/static/app.js`                             | 4, 5    | Mini trends, alarmes, drill-down                    |
| `tep-ihm/static/plant-diagram.svg`                  | 3       | Labels ISA visíveis nos círculos de sensor          |
| `spec/docs/dashboard_refactor/tep-svg-mapping.json` | 2, 3    | Campos `alarm_limits`, `preferredSide`, `isa_tag`   |
| `tep-plant` (backend)                               | 5       | Campo `alarms` no payload gRPC/WS                   |
