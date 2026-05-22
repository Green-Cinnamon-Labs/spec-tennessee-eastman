# Alarmes TEP — Inventário e Mapeamento ISA-101

**Referência:** `plano_mudanca_isa101.md` Etapa 5 · `guia-claude-ihm-isa101.md` §14  
**Status:** rascunho para discussão — nenhuma implementação feita ainda

---

## 1. Princípio ISA-101 para alarmes (§14)

> "A condição anormal deve se destacar sem depender apenas de cor.  
>  O estado normal deve ser visualmente calmo."

Consequências práticas para este projeto:

| O que NÃO fazer (atual)             | O que fazer (ISA-101)                                     |
| ----------------------------------- | --------------------------------------------------------- |
| Pintar o vaso de vermelho/âmbar     | Manter o vaso em cinza; colocar badge numerado sobre ele  |
| Usar cor de ênfase em estado normal | Cor de ênfase reservada a alarme não-reconhecido          |
| Alarme só distinguível por cor      | Badge com número + forma geométrica (sem depender de cor) |

**Hierarquia visual de badges (referência Elipse screenshot):**

| Prioridade          | Forma                       | Cor       | Quando                            |
| ------------------- | --------------------------- | --------- | --------------------------------- |
| 1 — Alarm (hi_hi)   | Quadrado vermelho `▣`       | `#B00020` | Valor acima do limite de shutdown |
| 2 — Warning (hi/lo) | Triângulo âmbar `⚠`         | `#B7791F` | Valor acima do limite operacional |
| 3 — Advisory        | Triângulo laranja invertido | `#D4580A` | Desvio moderado                   |

---

## 2. Alarmes expostos pelo gRPC (payload WebSocket `alarms[]`)

Estes chegam do backend `tep-plant` via WebSocket no campo `alarms`:

| #   | Nome (`variable`)        | Fonte XMEAS | Índice 0-based | Unidade | SVG element       |
| --- | ------------------------ | ----------- | -------------- | ------- | ----------------- |
| 1   | Reactor High Pressure    | XMEAS(7)    | `xmeas[6]`     | kPa     | `sensor-xmeas-07` |
| 2   | Reactor High Level       | XMEAS(8)    | `xmeas[7]`     | %       | `sensor-xmeas-08` |
| 3   | Reactor High Temperature | XMEAS(9)    | `xmeas[8]`     | °C      | `unit-reactor`    |
| 4   | Separator High Level     | XMEAS(12)   | `xmeas[11]`    | %       | `sensor-xmeas-12` |
| 5   | Stripper High Level      | XMEAS(15)   | `xmeas[14]`    | %       | `sensor-xmeas-15` |
| 6   | Stripper High Underflow  | XMEAS(17)?  | `xmeas[16]`    | —       | `unit-stripper`   |
| 7   | Reactor Low Level        | XMEAS(8)    | `xmeas[7]`     | %       | `sensor-xmeas-08` |
| 8   | Separator Low Level      | XMEAS(12)   | `xmeas[11]`    | %       | `sensor-xmeas-12` |
| 9   | Stripper Low Level       | XMEAS(15)   | `xmeas[14]`    | %       | `sensor-xmeas-15` |

> **Problema #1:** os campos `variable` acima são strings exatas do gRPC. Se mudar no backend, o mapeamento frontend quebra silenciosamente.  
> **Problema #2:** itens 4 e 8 mapeiam para o mesmo `sensor-xmeas-12` — badges de hi e lo apareceriam sobrepostos.

---

## 3. Alarmes locais (derivados dos limites em `diagram-animator.js`)

Estes são calculados pelo frontend a partir dos XMEAS — **não vêm do gRPC**.  
Usados atualmente para colorir os vasos (o que viola ISA-101).

| Vessel ID               | Variável de controle | XMEAS     | Hi (warning) | Hi-Hi (alarm) | Unidade |
| ----------------------- | -------------------- | --------- | ------------ | ------------- | ------- |
| `unit-reactor`          | Temperatura          | XMEAS(9)  | 150          | 165           | °C      |
| `unit-separator`        | Temperatura          | XMEAS(11) | 100          | 115           | °C      |
| `unit-stripper`         | Temperatura          | XMEAS(18) | 80           | 90            | °C      |
| `unit-condenser`        | Temperatura          | XMEAS(11) | 55           | 65            | °C      |
| `unit-stripper-boiler`  | Temperatura          | XMEAS(18) | 80           | 90            | °C      |
| `unit-compressor-1/2/3` | Trabalho             | XMEAS(20) | 400          | 450           | kW      |

> **Problema #3:** `colorizeVessel()` pinta o corpo do vaso de vermelho/âmbar — viola ISA-101 §7.  
> O vaso deve permanecer cinza. A indicação de alarme deve ser o badge.

---

## 4. Discrepâncias a resolver

### 4.1 Demo mode não dispara badges

O demo sobe `xmeas[8]` (temperatura do reator, XMEAS 9) para 172°C.  
`_deriveDemoAlarms` verifica `x[8] > 150` → deveria ser `true`.  
**Suspeita:** `renderAlarmBadges` é chamado, mas `getDrawablePath('unit-reactor')` retorna `null` porque o SVG pode não estar ainda no DOM quando o primeiro step roda. Verificar com `console.log`.

### 4.2 Colisão de badges hi/lo no mesmo sensor

Alarmes 4+8 (Separator High/Low Level) e 5+9 (Stripper High/Low Level) apontam para o mesmo elemento.  
**Proposta:** empilhar verticalmente (badge hi acima, badge lo abaixo do elemento).

### 4.3 XMEAS de "Stripper High Underflow" é incerto

O nome sugere `XMEAS(17)` (Stripper Underflow) mas precisa confirmação no código Rust do `tep-plant`.  
**Ação:** verificar `src/alarms.rs` em `tep-plant`.

### 4.4 Compressores não têm alarme no gRPC

`VESSEL_ALARM_LIMITS` define limites para os compressores (XMEAS 20, kW), mas nenhum  
`Compressor High Work` aparece no `ALARM_NAMES` do WebSocket.  
**Opção A:** alarme local no frontend (badge sem confirmação do backend).  
**Opção B:** pedir ao backend para adicionar o alarme.

---

## 5. Proposta de implementação

### 5.1 Remover colorização dos vasos

```js
// diagram-animator.js — colorizeVessel()
// REMOVER: qualquer atribuição de fill vermelho/âmbar no corpo do vaso
// MANTER: apenas cinza neutro
function colorizeVessel(vesselId) {
    const vessel = document.querySelector(`[data-cell-id="${vesselId}"]`);
    if (!vessel) return;
    vessel.querySelectorAll('path, ellipse, rect').forEach(el => {
        el.style.fill        = '#6F767D';  // --hmi-line (normal)
        el.style.fillOpacity = '0.20';
    });
}
```

### 5.2 Badge estruturado por severidade

```js
// app.js — renderAlarmBadges()
// Badge quadrado vermelho = alarm (hi_hi)
// Badge triângulo âmbar = warning (hi/lo)
// Forma geométrica diferente por severidade → não depende só de cor
```

### 5.3 Tabela de alarmes unificada

Unificar `ALARM_NAMES` (gRPC) + limites locais em uma única fonte:

```js
const ALARM_CATALOG = [
    { id: 'reactor-pressure-hi',  variable: 'Reactor High Pressure',   element: 'sensor-xmeas-07', severity: 'alarm'   },
    { id: 'reactor-level-hi',     variable: 'Reactor High Level',       element: 'sensor-xmeas-08', severity: 'alarm'   },
    { id: 'reactor-temp-hi',      variable: 'Reactor High Temperature', element: 'unit-reactor',    severity: 'alarm'   },
    { id: 'reactor-level-lo',     variable: 'Reactor Low Level',        element: 'sensor-xmeas-08', severity: 'warning', badgeOffset: 'below' },
    { id: 'separator-level-hi',   variable: 'Separator High Level',     element: 'sensor-xmeas-12', severity: 'alarm'   },
    { id: 'separator-level-lo',   variable: 'Separator Low Level',      element: 'sensor-xmeas-12', severity: 'warning', badgeOffset: 'below' },
    { id: 'stripper-level-hi',    variable: 'Stripper High Level',      element: 'sensor-xmeas-15', severity: 'alarm'   },
    { id: 'stripper-level-lo',    variable: 'Stripper Low Level',       element: 'sensor-xmeas-15', severity: 'warning', badgeOffset: 'below' },
    { id: 'stripper-underflow-hi',variable: 'Stripper High Underflow',  element: 'unit-stripper',   severity: 'alarm'   },
];
```

---

## 6. Perguntas em aberto

1. **Confirmar XMEAS do "Stripper High Underflow"** — verificar `tep-plant/src/alarms.rs`
2. **Compressores** — adicionar alarme gRPC ou manter local?
3. **ACK de alarmes** — o operador precisa reconhecer? Backend não tem persistência de ACK ainda.
4. **Badge visível em zoom out?** — badges de 14px SVG podem desaparecer com zoom < 0.5×. Usar tamanho fixo em CSS (`position: fixed`) em vez de SVG user-space?

---

## 7. Próximos passos sugeridos

- [ ] Remover `colorizeVessel` (ou reduzir a cinza fixo) — **não pintar vasos**
- [ ] Corrigir `renderAlarmBadges` para funcionar no demo (debug `getDrawablePath`)
- [ ] Implementar badge com forma geométrica por severidade (quadrado vs triângulo)
- [ ] Unificar `ALARM_NAMES` + limites locais em `ALARM_CATALOG`
- [ ] Verificar XMEAS do Stripper Underflow no Rust
