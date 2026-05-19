# Dashboard Redesign — Análise de Gráficos e Novo SVG Semântico

**Objetivo:** Documentar os 4 gráficos atuais, identificar lacunas de observabilidade, e especificar a estrutura semântica de um novo diagrama SVG interativo que permita visualizar o estado térmico, fluxos e falhas do Tennessee Eastman Process.

**Data:** 2026-05-19  
**Contexto:** Exp 14 (IDV(4) — validação de distúrbio de temperatura CW do reator)

---

## 1. Os 4 Gráficos Atuais

### Gráfico 1: Pressure (kPa)

**Localização no código:** `tep-ihm/static/app.js`, linhas 109–113

```javascript
const chartPressure = new Chart(document.getElementById('chart-pressure'), {
    type: 'line',
    data: { labels: timeLabels, datasets: [
        ds('Reactor (7)', 0),
        ds('Separator (13)', 1),
        ds('Stripper (16)', 2)
    ]},
    options: chartOpts('Pressure (kPa)'),
});
```

| Série | XMEAS     | Nome                     | Descrição                                     |
| ----- | --------- | ------------------------ | --------------------------------------------- |
| 1     | XMEAS(7)  | Reactor Pressure (PTR)   | Pressão total na fase líquida+vapor do reator |
| 2     | XMEAS(13) | Separator Pressure (PTS) | Pressão no separador de produtos              |
| 3     | XMEAS(16) | Stripper Pressure (PTC)  | Pressão na coluna de stripping                |

**O que observa:**
- Estabilidade dos três vasos
- Dinâmica de equilíbrio P-V-T após ramp-up
- Sobre-pressão no reator → alarme crítico (ISD trigger)

**Sensível a (IDVs):**
- IDV(3): D feed frio → reação mais rápida → P sobe em R
- IDV(4): CW reator quente → TCR sobe → Taxa reação ↑ → PTR ↑ (este é o Exp 14)
- IDV(7): Drop no header C → afeta reciclo → PTR cai

**Limitação:** Não mostra *por que* a pressão muda — precisa cruzar com temperatura e taxa de reação.

---

### Gráfico 2: Temperature (°C)

**Localização:** `tep-ihm/static/app.js`, linhas 115–119

```javascript
const chartTemp = new Chart(document.getElementById('chart-temperature'), {
    type: 'line',
    data: { labels: timeLabels, datasets: [
        ds('Reactor (9)', 3),
        ds('Separator (11)', 4),
        ds('Stripper (18)', 5)
    ]},
    options: chartOpts('Temperature (°C)'),
});
```

| Série | XMEAS     | Nome                        | Descrição                                   |
| ----- | --------- | --------------------------- | ------------------------------------------- |
| 1     | XMEAS(9)  | Reactor Temperature (TCR)   | Temperatura do líquido no reator (critical) |
| 2     | XMEAS(11) | Separator Temperature (TCS) | Temperatura no separador                    |
| 3     | XMEAS(18) | Stripper Temperature (TCC)  | Temperatura na coluna de stripping          |

**O que observa:**
- Exotermia da reação (TCR sobe com conversão)
- Efeito de resfriamento do coolant jacket (XMV10)
- Eficácia da troca térmica dos trocadores

**Sensível a (IDVs):**
- **IDV(3):** D feed frio → TCR cai inicialmente → reação endotérmica compensação
- **IDV(4):** CW inlet quente (+5°C) → TCR sobe (Exp 14)
- **IDV(5):** Condenser CW quente → TCS sobe
- **IDV(11):** Ruído rand. em CW reator → TCR oscila
- **IDV(12):** Ruído rand. em CW condenser → TCS oscila

**Problema em Exp 14:** TCR deve subir visualmente quando IDV(4) ativa. Se não subir, ou se subir muito pouco, há problema:
- Controlador de temperatura não está funcionando
- Entrada de CW não é efetiva
- Modelo de transferência térmica está errado

---

### Gráfico 3: Level (%)

**Localização:** `tep-ihm/static/app.js`, linhas 121–125

```javascript
const chartLevels = new Chart(document.getElementById('chart-levels'), {
    type: 'line',
    data: { labels: timeLabels, datasets: [
        ds('Reactor (8)', 0),
        ds('Separator (12)', 1),
        ds('Stripper (15)', 2)
    ]},
    options: chartOpts('Level (%)'),
});
```

| Série | XMEAS     | Nome                  | Descrição                                 |
| ----- | --------- | --------------------- | ----------------------------------------- |
| 1     | XMEAS(8)  | Reactor Level (VLR)   | Volume de líquido acumulado no reator (%) |
| 2     | XMEAS(12) | Separator Level (VLS) | Volume de líquido no separador (%)        |
| 3     | XMEAS(15) | Stripper Level (VLC)  | Volume de líquido na coluna stripping (%) |

**O que observa:**
- Balanço molar em cada vaso
- Efetividade dos controladores P (XMV6 sep, XMV8 stri)
- Dinâmica de inventário acumulado

**Sensível a (IDVs):**
- IDV(6): A feed loss → VLR cai (menos entrada)
- IDV(14): Reactor CW valve stuck → afeta troca térmica → pode afetar Flash dynamics → VLS ↑
- IDV(16): D feed valve stuck → afeta V_LR e V_LS

**Problema crítico:** Níveis altos → alarme; níveis baixos → perda de controle. Indicadores diretos de falha operacional.

---

### Gráfico 4: Feed Flows (kscmh / kg/hr)

**Localização:** `tep-ihm/static/app.js`, linhas 127–131

```javascript
const chartFlows = new Chart(document.getElementById('chart-flows'), {
    type: 'line',
    data: { labels: timeLabels, datasets: [
        ds('A (1)', 0),
        ds('D (2)', 1),
        ds('E (3)', 2),
        ds('A&C (4)', 3)
    ]},
    options: chartOpts('Feed Flows (kscmh / kg/hr)'),
});
```

| Série | XMEAS    | Nome              | Descrição                      |
| ----- | -------- | ----------------- | ------------------------------ |
| 1     | XMEAS(1) | A Feed (gasoso)   | Fluxo molar de matéria-prima A |
| 2     | XMEAS(2) | D Feed (líquido)  | Fluxo molar de matéria-prima D |
| 3     | XMEAS(3) | E Feed (líquido)  | Fluxo molar de matéria-prima E |
| 4     | XMEAS(4) | A&C Feed (gasoso) | Fluxo molar misturado A+C      |

**O que observa:**
- Ramp-up das válvulas de entrada durante cold-start (0% → nominais em ~30 min sim)
- Constância em operação normal (alimentação estável)
- Efeito de distúrbios nas entradas

**Sensível a (IDVs):**
- **IDV(1):** A/C ratio na stream 4 → muda composição, não fluxo (não aparece aqui)
- **IDV(2):** B composition em stream 4 → idem
- **IDV(3):** D feed temp → não afeta fluxo direto
- **IDV(6):** A feed loss (stream 1 → 0) → XMEAS(1) → 0
- **IDV(16):** D feed valve stuck → XMEAS(2) fica constante
- **IDV(17):** A&C valve stuck → XMEAS(4) fica constante

---

## 2. Gap Análise — O que Está Faltando

### Crítico: Composições (XMEAS 23–41)

**Problema:** Você vê fluxos (A, D, E) mas **não vê se os produtos estão sendo formados**. Composições são o diagnóstico essencial:

| XMEAS | O quê                                        | Por quê é crítico                                |
| ----- | -------------------------------------------- | ------------------------------------------------ |
| 23–28 | Composição no reator (A, B, C, D, E, F mol%) | Mostra taxa de reação real; A decai, D/E crescem |
| 29–34 | Composição na purga (A–H)                    | Indica reciclo e balanço                         |
| 37–41 | Composição no produto (D, E, F, G, H)        | Prova de separação e conversão                   |

**Exemplo prático — Exp 14 (IDV(4)):**
- Você vê TCR subir? Ótimo.
- Mas **A está decaindo no reator?** (XMEAS 23 caindo)
  - Se sim → reação acelerou, como esperado.
  - Se não → temperatura subiu mas reação não; possível problema no modelo cinético.

---

### Importante: Reciclo e Purga

| XMEAS     | O quê                                                  |
| --------- | ------------------------------------------------------ |
| XMEAS(5)  | Recycle Flow (kscmh) — volta do compressor para reator |
| XMEAS(10) | Purge Rate (kscmh) — vent para remover inertes         |

**Por que faltam:**
- XMEAS(5) → Controlado por P-controller (XMV5). Indica saúde do loop de reciclo.
- XMEAS(10) → Afeta inventário de vapor. Falta = falha do controle de purga.

---

### Secundário: Underflow e CW Outlet

| XMEAS     | O quê                         | Atual   |
| --------- | ----------------------------- | ------- |
| XMEAS(14) | Separator Underflow (m³/hr)   | Ausente |
| XMEAS(17) | Stripper Underflow (m³/hr)    | Ausente |
| XMEAS(19) | Stripper Steam Flow (kg/hr)   | Ausente |
| XMEAS(20) | Compressor Work (kW)          | Ausente |
| XMEAS(21) | Reactor CW Outlet Temp (°C)   | Ausente |
| XMEAS(22) | Separator CW Outlet Temp (°C) | Ausente |

Estes são informativos (diagnóstico de eficiência), não críticos para observar distúrbios básicos.

---

## 3. Estrutura Semântica do SVG

### 3.1 Nomenclatura Base (segue `tep-plant/docs/02-glossario.md`)

**Abreviaturas de Unidades:**
- **R** — Reactor (reator)
- **S** — Separator (separador)
- **C** — Stripper Column (coluna de stripping)
- **V** — Vapor/Compressor (fase vapor no compressor)

**Abreviaturas de Grandezas:**
- **PT** — Pressure Total (kPa)
- **TC** — Temperature Celsius (°C)
- **VL** — Volume Liquid (%)
- **UC** — Unit Contents (molar, mol)
- **FTM** — Flow Total Molar (kscmh, kg/hr)
- **XST** — Composition STream (fração molar)
- **VPOS** — Valve POSition (%)

**Exemplo de Leitura:**
- `PTR` = Pressão total do reator = XMEAS(7)
- `TCR` = Temperatura Celsius do reator = XMEAS(9)
- `VLR` = Volume líquido do reator = XMEAS(8)

---

### 3.2 Hierarquia SVG Proposta

```xml
<svg id="plant-diagram" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 800">
  
  <!-- Definições: cores, gradientes, marcadores -->
  <defs>
    <style>
      .vessel { stroke: #333; stroke-width: 2; }
      .vessel-R { fill: url(#grad-R); }
      .vessel-S { fill: url(#grad-S); }
      .vessel-C { fill: url(#grad-C); }
      .vessel-V { fill: url(#grad-V); }
      
      .stream { fill: none; stroke: #666; stroke-width: 2; }
      .stream-gaseous { stroke-dasharray: 5,5; }
      
      .valve { fill: #ccc; stroke: #333; stroke-width: 1; }
      .valve-open { fill: #90EE90; }
      .valve-stuck { fill: #FF6B6B; }
      
      .sensor { fill: #666; stroke: #333; stroke-width: 1; }
      .analyzer { fill: #FFD700; stroke: #333; stroke-width: 1; }
      
      .label { font-family: Consolas, monospace; font-size: 10px; }
      .xmeas-label { fill: #000; }
      .xmv-label { fill: #fff; font-weight: bold; }
      
      .alarm-ok { filter: drop-shadow(0 0 3px #4fc3f7); }
      .alarm-warning { filter: drop-shadow(0 0 5px #ffa726); }
      .alarm-active { filter: drop-shadow(0 0 8px #ef5350); }
    </style>
    
    <!-- Gradientes de cores para vasos (T simulado) -->
    <linearGradient id="grad-R" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#3498db;stop-opacity:0.3" />
      <stop offset="100%" style="stop-color:#e74c3c;stop-opacity:0.3" />
    </linearGradient>
    <!-- idem para S, C, V -->
  </defs>
  
  <!-- ─────────────────────────────────────────────────────────────── -->
  <!-- VASOS (Vessels) — núcleos de operação -->
  <!-- ─────────────────────────────────────────────────────────────── -->
  <g id="vessels">
    
    <!-- Reactor (R) -->
    <g id="vessel-R" data-unit="R" data-xmeas-base="7,8,9,23-28">
      <rect class="vessel vessel-R" x="300" y="200" width="150" height="120" rx="5" 
            data-pt="7" data-vl="8" data-tc="9" />
      <text class="label xmeas-label" x="310" y="215">REACTOR (R)</text>
      <text class="label xmeas-label" x="310" y="230" data-bind="xmeas-7">PT: --</text>
      <text class="label xmeas-label" x="310" y="245" data-bind="xmeas-9">TC: --</text>
      <text class="label xmeas-label" x="310" y="260" data-bind="xmeas-8">VL: --</text>
    </g>
    
    <!-- Separator (S) -->
    <g id="vessel-S" data-unit="S" data-xmeas-base="13,12,11,29-34">
      <rect class="vessel vessel-S" x="600" y="200" width="150" height="120" rx="5"
            data-pt="13" data-vl="12" data-tc="11" />
      <text class="label xmeas-label" x="610" y="215">SEPARATOR (S)</text>
      <text class="label xmeas-label" x="610" y="230" data-bind="xmeas-13">PT: --</text>
      <text class="label xmeas-label" x="610" y="245" data-bind="xmeas-11">TC: --</text>
      <text class="label xmeas-label" x="610" y="260" data-bind="xmeas-12">VL: --</text>
    </g>
    
    <!-- Stripper (C) -->
    <g id="vessel-C" data-unit="C" data-xmeas-base="16,15,18,35-41">
      <rect class="vessel vessel-C" x="800" y="200" width="150" height="120" rx="5"
            data-pt="16" data-vl="15" data-tc="18" />
      <text class="label xmeas-label" x="810" y="215">STRIPPER (C)</text>
      <text class="label xmeas-label" x="810" y="230" data-bind="xmeas-16">PT: --</text>
      <text class="label xmeas-label" x="810" y="245" data-bind="xmeas-18">TC: --</text>
      <text class="label xmeas-label" x="810" y="260" data-bind="xmeas-15">VL: --</text>
    </g>
    
    <!-- Compressor (V) -->
    <g id="vessel-V" data-unit="V" data-xmeas-base="5">
      <circle class="vessel vessel-V" cx="450" cy="450" r="60"
              data-flow="5" />
      <text class="label xmeas-label" x="430" y="450">COMP (V)</text>
      <text class="label xmeas-label" x="425" y="470" data-bind="xmeas-5">Recycle: --</text>
    </g>
  </g>
  
  <!-- ─────────────────────────────────────────────────────────────── -->
  <!-- CORRENTES (Streams) — conexões de material -->
  <!-- ─────────────────────────────────────────────────────────────── -->
  <g id="streams">
    <!-- Cada corrente é uma PATH com animação de largura/opacidade dinamica -->
    
    <!-- Feed Streams (entradas) -->
    <path id="stream-feed-A" class="stream" 
          d="M 100 220 Q 200 220 300 220" 
          data-xmeas="1" data-type="gas" data-source="A" stroke-width="2" />
    
    <path id="stream-feed-D" class="stream" 
          d="M 100 260 Q 200 240 300 260" 
          data-xmeas="2" data-type="liquid" data-source="D" stroke-width="2" />
    
    <path id="stream-feed-E" class="stream" 
          d="M 100 300 Q 200 260 300 300" 
          data-xmeas="3" data-type="liquid" data-source="E" stroke-width="2" />
    
    <path id="stream-feed-AC" class="stream" 
          d="M 100 340 Q 200 280 300 340" 
          data-xmeas="4" data-type="gas" data-source="AC" stroke-width="2" />
    
    <!-- Recycle (Compressor → Reactor) -->
    <path id="stream-recycle" class="stream stream-gaseous" 
          d="M 450 520 Q 400 300 380 260" 
          data-xmeas="5" data-type="gas" stroke-width="2" />
    
    <!-- Purge (Reactor → Vent) -->
    <path id="stream-purge" class="stream stream-gaseous" 
          d="M 380 200 L 350 100" 
          data-xmeas="10" data-type="gas" stroke-width="2" />
    
    <!-- Reactor → Separator (vapor) -->
    <path id="stream-vapor-R-to-S" class="stream stream-gaseous" 
          d="M 450 260 Q 530 260 600 260" 
          data-type="vapor" stroke-width="2" />
    
    <!-- Separator → Stripper (liquid) -->
    <path id="stream-liquid-S-to-C" class="stream" 
          d="M 750 300 Q 770 300 800 300" 
          data-type="liquid" stroke-width="2" />
    
    <!-- Product Overhead (vapor out) -->
    <path id="stream-product-overhead" class="stream stream-gaseous" 
          d="M 675 200 L 700 100" 
          data-type="gas" stroke-width="2" />
    
    <!-- Product Bottoms (liquid out) -->
    <path id="stream-product-bottoms" class="stream" 
          d="M 875 320 L 900 400" 
          data-type="liquid" stroke-width="2" />
  </g>
  
  <!-- ─────────────────────────────────────────────────────────────── -->
  <!-- VÁLVULAS (Valves) — atuadores XMV -->
  <!-- ─────────────────────────────────────────────────────────────── -->
  <g id="valves">
    <!-- Válvulas de feed (XMV 1-4) — retângulos pequenos, altura proporcional a VPOS -->
    <rect id="valve-XMV1" class="valve" x="280" y="200" width="15" height="30"
          data-xmv="1" data-stream="feed-D" />
    <text class="label xmv-label" x="260" y="185">XMV(1)</text>
    
    <!-- ... idem XMV(2), XMV(3), XMV(4) ... -->
    
    <!-- Válvulas de controle (XMV 5-9) — maiores, posição no pipeline -->
    <rect id="valve-XMV5" class="valve" x="420" y="500" width="30" height="30"
          data-xmv="5" data-stream="recycle" title="Compressor Recycle" />
    <text class="label xmv-label" x="400" y="545">XMV(5)</text>
    
    <!-- CW flows (XMV 10, 11) — círculos, fluxo em legenda -->
    <circle id="valve-XMV10" class="valve" cx="280" cy="140" r="15"
            data-xmv="10" data-stream="CW-reactor" title="Reactor CW Flow" />
    <text class="label xmv-label" x="270" y="160">XMV(10)</text>
    
    <!-- Agitator (XMV 12) — disco giratório -->
    <circle id="valve-XMV12" class="valve" cx="375" cy="270" r="12"
            data-xmv="12" title="Agitator Speed %" />
    <text class="label xmv-label" x="360" y="290">XMV(12)</text>
  </g>
  
  <!-- ─────────────────────────────────────────────────────────────── -->
  <!-- SENSORES INLINE (Sensors) — medições de fluxo/composição nas correntes -->
  <!-- ─────────────────────────────────────────────────────────────── -->
  <g id="sensors">
    <!-- Sensores de fluxo (XMEAS 1-22) nas correntes -->
    <circle class="sensor" cx="150" cy="220" r="6" data-xmeas="1" />
    <text class="label" x="140" y="235">XMEAS(1)</text>
    
    <!-- ... idem para todos os feeds ... -->
  </g>
  
  <!-- ─────────────────────────────────────────────────────────────── -->
  <!-- ANALISADORES (Analyzers) — medições periódicas XMEAS 23-41 -->
  <!-- ─────────────────────────────────────────────────────────────── -->
  <g id="analyzers">
    <!-- Dentro de cada vaso, losangos com composição -->
    
    <!-- Reactor composition (XMEAS 23-28) -->
    <g id="analyzer-reactor-comp" data-xmeas="23-28">
      <polygon class="analyzer" points="375,260 385,270 375,280 365,270" />
      <text class="label" x="360" y="275" title="Reactor composition">XMEAS(23-28)</text>
    </g>
    
    <!-- Separator composition (XMEAS 29-34) -->
    <g id="analyzer-sep-comp" data-xmeas="29-34">
      <polygon class="analyzer" points="675,260 685,270 675,280 665,270" />
      <text class="label" x="660" y="275" title="Separator/Purge composition">XMEAS(29-34)</text>
    </g>
    
    <!-- Product composition (XMEAS 35-41) -->
    <g id="analyzer-product-comp" data-xmeas="35-41">
      <polygon class="analyzer" points="875,270 885,280 875,290 865,280" />
      <text class="label" x="860" y="285" title="Product composition">XMEAS(35-41)</text>
    </g>
  </g>
  
  <!-- ─────────────────────────────────────────────────────────────── -->
  <!-- LEGENDA E STATUS -->
  <!-- ─────────────────────────────────────────────────────────────── -->
  <g id="legend" transform="translate(50, 600)">
    <text class="label" x="0" y="0" font-weight="bold">Legenda:</text>
    <circle class="alarm-ok" cx="10" cy="20" r="5" />
    <text class="label" x="25" y="25">Normal</text>
    
    <circle class="alarm-warning" cx="150" cy="20" r="5" />
    <text class="label" x="165" y="25">Aviso</text>
    
    <circle class="alarm-active" cx="280" cy="20" r="5" />
    <text class="label" x="295" y="25">Alarme</text>
  </g>
</svg>
```

---

### 3.3 Atributos Data para Animação JavaScript

Cada elemento SVG carrega metadados que permitem atualização dinâmica:

| Atributo                        | Tipo       | Uso                                                           |
| ------------------------------- | ---------- | ------------------------------------------------------------- |
| `data-xmeas`                    | int, range | Qual(is) XMEAS este elemento representa                       |
| `data-xmv`                      | int        | Qual XMV controla                                             |
| `data-unit`                     | char       | R, S, C, ou V                                                 |
| `data-pt`, `data-vl`, `data-tc` | int        | IDs de XMEAS para PT, VL, TC                                  |
| `data-type`                     | string     | gas, liquid, vapor                                            |
| `data-stream`                   | string     | Nome da corrente (feed-A, recycle, etc)                       |
| `data-bind`                     | string     | Selector CSS para atualizar texto (ex: `data-bind="xmeas-7"`) |

**Exemplo de uso em JavaScript:**

```javascript
// Ao receber update do WebSocket
function updateSVG(xmeas, xmv, alarms) {
  
  // Atualizar cores dos vasos por temperatura
  ['R', 'S', 'C'].forEach(unit => {
    const vessel = document.querySelector(`g[data-unit="${unit}"]`);
    const tempXmeas = vessel.dataset.tc;
    const temp = xmeas[tempXmeas - 1]; // XMEAS é 1-indexed
    const hue = mapTemp(temp); // azul frio → vermelho quente
    vessel.style.filter = `hue-rotate(${hue}deg)`;
  });
  
  // Atualizar largura de correntes por fluxo
  const recycle = document.querySelector('path[data-xmeas="5"]');
  const ftm5 = xmeas[4]; // XMEAS(5)
  recycle.style.strokeWidth = Math.max(1, ftm5 / 50); // escala arbitrária
  
  // Atualizar posição de válvulas
  document.querySelectorAll('[data-xmv]').forEach(valve => {
    const xmvIdx = parseInt(valve.dataset.xmv);
    const vpos = xmv[xmvIdx - 1]; // XMV é 1-indexed
    // Para válvulas de entrada, altura = VPOS%
    // Para CW, opacidade = VPOS%
  });
  
  // Adicionar classe de alarme se in_range === false
  document.querySelectorAll('[data-xmeas]').forEach(elem => {
    const xmeasList = elem.dataset.xmeas.split(',');
    const hasAlarm = xmeasList.some(idx => {
      return alarms.some(a => a.xmeas_index === parseInt(idx));
    });
    elem.classList.toggle('alarm-active', hasAlarm);
  });
}
```

---

## 4. Nomenclatura Proposta

### 4.1 IDs e Classes SVG (convenção)

```
Vasos:     vessel-{R|S|C|V}        ex: vessel-R
Correntes: stream-{source}-to-{dest}  ex: stream-reactor-to-separator
Válvulas:  valve-XMV{1..12}        ex: valve-XMV5
Sensores:  sensor-XMEAS{1..41}     ex: sensor-XMEAS7
Analisadores: analyzer-{unit}-comp ex: analyzer-reactor-comp
```

### 4.2 Cores (não muda com T)

| Elemento       | Cor            | Hex     |
| -------------- | -------------- | ------- |
| Reactor (R)    | Azul base      | #3498db |
| Separator (S)  | Verde base     | #2ecc71 |
| Stripper (C)   | Laranja base   | #e67e22 |
| Compressor (V) | Cinza base     | #95a5a6 |
| Stream gasoso  | Tracejado      | —       |
| Stream líquido | Linha contínua | —       |

### 4.3 Animações Dinâmicas

| Propriedade        | Evento           | Mudança                                    |
| ------------------ | ---------------- | ------------------------------------------ |
| `fill` / `filter`  | Temperatura sobe | Gradiente azul → vermelho                  |
| `stroke-width`     | Fluxo aumenta    | Proporcional a FTM                         |
| `opacity`          | Alarme           | Normal 0.8 → Alarme 1.0                    |
| `drop-shadow`      | Alarme           | Ok azul → Aviso laranja → Crítico vermelho |
| Animação giratória | Agitador ativo   | Disco XMV(12) gira se VPOS > 0             |

---

## 5. Próximos Passos de Implementação

### 5.1 Curto Prazo (Semana 1)

1. **Criar `tep-ihm/static/plant-diagram.svg`** com o SVG base (desenho)
2. **Integrar no `index.html`:**
   ```html
   <object id="plant-diagram-obj" data="plant-diagram.svg" type="image/svg+xml"></object>
   ```
3. **Escrever funções em `app.js`:**
   - `updatePlantDiagram(xmeas, xmv, alarms)` — chama map funções
   - `mapTemperatureToColor(temp)` — XMEAS(7,9,11,13,16,18) → hue CSS
   - `mapFlowToWidth(ftm)` — XMEAS(1,2,3,4,5,10) → stroke-width

### 5.2 Médio Prazo (Semana 2)

4. **Adicionar composições dinâmicas** (XMEAS 23-41):
   - Exibir percentuais de A, D, E dentro dos vasos
   - Fazer losango analyzer piscar/mudar cor quando fração molar muda
   
5. **Adicionar tooltips** com valores instantâneos (ex: "TCR: 68.2°C, PTR: 2800 kPa")

### 5.3 Longo Prazo (Se necessário)

6. **Animações avançadas:**
   - Partículas fluindo nas correntes (GSAP/SVG animation)
   - Reação visual (moléculas A → D no reator)

---

## 6. Validação em Exp 14

**Cenário:** Ativar IDV(4) (CW reator quente +5°C) e observar:

| Aspecto               | Esperado no SVG                  | Diagnóstico                                 |
| --------------------- | -------------------------------- | ------------------------------------------- |
| **Cor do vaso R**     | Azul escuro → Vermelho           | TCR sobe (XMEAS 9)                          |
| **Pressão em R**      | Ícone ganha drop-shadow vermelho | PTR sobe (XMEAS 7)                          |
| **Composição A no R** | Losango analyzer mostra ↓ A%     | Taxa reação ↑                               |
| **Nível R**           | Sem alarme                       | VLR estável (balanço mantido)               |
| **Reciclo**           | Linha mais grossa                | XMEAS(5) aumenta (compressor trabalha mais) |

Se alguma dessas observações **não ocorrer**, a distúrbio não está sendo aplicado corretamente.

---

## Referências

- `tep-plant/docs/01-premissas.md` — Vetor de estados, ordem de operação
- `tep-plant/docs/02-glossario.md` — Nomenclatura de unidades e grandezas
- `tep-plant/docs/05-disturbios.md` — Definição dos 20 IDVs
- `tep-ihm/static/app.js` — XMEAS_META, XMV_META (linhas 12–70)
- `tep-supervisor/local/docker-compose.yml` — STEP_DELAY_MS para validação experimental

---

**Autor:** Claude Code  
**Status:** Proposta pronta para implementação  
**Bloqueador:** Nenhum — proceder com SVG base
