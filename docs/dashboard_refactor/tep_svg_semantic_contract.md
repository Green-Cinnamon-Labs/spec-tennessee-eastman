# Contrato semântico do SVG — Tennessee Eastman Process

Este documento define a tabela-mestra do SVG semântico da planta Tennessee Eastman Process (TEP).

A ideia central é separar três coisas:

1. **Origem física/modelo TEP**: equipamento, corrente, medição ou atuador conforme o artigo.
2. **Representação SVG**: elemento visual identificado no draw.io via `data-cell-id`.
3. **Operação via JavaScript**: seleção por `data-cell-id` para atualizar cores, valores, estados e alarmes.

Este documento **não define coordenadas gráficas**. Ele define a identidade dos elementos.

---

## 0. Padrão de endereçamento — draw.io SVG

O SVG é exportado pelo draw.io como `.drawio.svg`. Nesse formato:

- O atributo de endereçamento semântico é **`data-cell-id`**, não `id`.
- O `id` do elemento SVG é gerado automaticamente pelo draw.io e **não deve ser usado** como referência.
- O JavaScript deve usar `querySelector` ou `querySelectorAll`:

```js
// Correto — busca por data-cell-id:
document.querySelector('[data-cell-id="sensor-xmeas-07"]')
document.querySelectorAll('[data-cell-id^="stream-08-"]')  // todos os segmentos da corrente 8

// Errado — id gerado pelo draw.io, não é semântico:
document.getElementById('sensor-xmeas-07')
```

Regra prática: o JavaScript deve operar por `data-cell-id`. Ele não deve depender da posição visual do elemento.

---

## 1. Estrutura do SVG draw.io

O draw.io gerencia a estrutura interna do SVG. Não há grupos fixos como `#streams` ou `#units`. O endereçamento é feito **exclusivamente** pelo atributo `data-cell-id`.

Para animações que agrupam múltiplos segmentos de uma corrente, use seleção por prefixo:

```js
// Todos os segmentos visuais da corrente 8 (reciclo + bypass):
document.querySelectorAll('[data-cell-id^="stream-08-"]')
```

---

## 2. Equipamentos / unidades principais

| data-cell-id            | tipo       | origem TEP                     | função                                                |
| ----------------------- | ---------- | ------------------------------ | ----------------------------------------------------- |
| `unit-reactor`          | vaso       | Reactor                        | Reator; recebe feeds e reciclo                        |
| `unit-condenser`        | trocador   | Product condenser              | Condensador do produto do reator                      |
| `unit-separator`        | vaso       | Vapor-liquid separator         | Separador flash; separa vapor de reciclo e líquido    |
| `unit-compressor-1`     | máquina    | Recycle compressor (estágio 1) | Compressor de reciclo — estágio 1                     |
| `unit-compressor-2`     | máquina    | Recycle compressor (estágio 2) | Compressor de reciclo — estágio 2                     |
| `unit-compressor-3`     | máquina    | Recycle compressor (estágio 3) | Compressor de reciclo — estágio 3                     |
| `unit-stripper`         | coluna     | Product stripper               | Stripper; remove leves do produto líquido             |
| `unit-stripper-boiler`  | trocador   | Stripper reboiler              | Reboiler da base do stripper; aquecido por XMV(9)     |
| `node-reactor-feed-mixer` | nó       | Feed mixing point              | Nó de mistura das alimentações do reator              |

---

## 3. Correntes de processo e utilidades

### 3.1 Alimentações externas — streams 1–4

Cada feed tem: um elemento `data-0X-*` (rótulo/fonte externa) e dois segmentos de tubo `stream-0X-*-up/down`.  
Para JS de binding, use o sensor (`sensor-xmeas-0X`) e o atuador (`actuator-xmv-0X`) como pontos de atualização primários.

| data-cell-id             | papel        | stream TEP | XMEAS | XMV |
| ------------------------ | ------------ | ---------- | ----- | --- |
| `data-01-a-feed`         | fonte/label  | Stream 1   | —     | —   |
| `stream-01-a-feed-up`    | segmento     | Stream 1   | 1     | 3   |
| `stream-01-a-feed-down`  | segmento     | Stream 1   | 1     | 3   |
| `data-02-d-feed`         | fonte/label  | Stream 2   | —     | —   |
| `stream-02-d-feed-up`    | segmento     | Stream 2   | 2     | 1   |
| `stream-02-d-feed-down`  | segmento     | Stream 2   | 2     | 1   |
| `data-03-e-feed`         | fonte/label  | Stream 3   | —     | —   |
| `stream-03-e-feed-up`    | segmento     | Stream 3   | 3     | 2   |
| `stream-03-e-feed-down`  | segmento     | Stream 3   | 3     | 2   |
| `data-04-c-feed`         | fonte/label  | Stream 4   | —     | —   |
| `stream-04-c-feed-up`    | segmento     | Stream 4   | 4     | 4   |
| `stream-04-c-feed-down`  | segmento     | Stream 4   | 4     | 4   |

### 3.2 Correntes internas de processo — streams 5–11

Correntes com um único segmento têm `data-cell-id` direto como âncora primária.  
Correntes com múltiplos segmentos têm uma **âncora primária** indicada e segmentos visuais auxiliares.

| data-cell-id                  | papel         | stream TEP | XMEAS | XMV | observação                                    |
| ----------------------------- | ------------- | ---------- | ----- | --- | --------------------------------------------- |
| `stream-05-stripper-mixer`    | âncora        | Stream 5   | —     | —   | overhead do stripper → nó de mistura          |
| `stream-06-mixer-reactor`     | âncora        | Stream 6   | 6     | —   | nó de mistura → reator; ponto XMEAS 23–28     |
| `stream-07-reactor-condenser` | âncora        | Stream 7   | —     | —   | reator → condensador → separador              |
| `stream-08-up`                | segmento      | Stream 8   | 5     | 5   | reciclo — trecho superior                     |
| `stream-08-down`              | segmento      | Stream 8   | 5     | 5   | reciclo — trecho inferior                     |
| `stream-08-bypass-up`         | segmento      | Stream 8   | —     | 5   | bypass do reciclo — trecho superior           |
| `stream-08-bypass-down`       | segmento      | Stream 8   | —     | 5   | bypass do reciclo — trecho inferior           |
| `stream-09-purge`             | **âncora**    | Stream 9   | 10    | 6   | purga; ponto XMEAS 29–36                      |
| `stream-09-up`                | segmento      | Stream 9   | —     | —   | trecho superior                               |
| `stream-09-down`              | segmento      | Stream 9   | —     | —   | trecho inferior                               |
| `stream-10-in`                | segmento      | Stream 10  | 14    | 7   | underflow separador — entrada                 |
| `stream-10-out`               | segmento      | Stream 10  | —     | —   | underflow separador — saída                   |
| `stream-10-up`                | segmento      | Stream 10  | —     | —   | trecho superior                               |
| `stream-10-down`              | segmento      | Stream 10  | —     | —   | trecho inferior                               |
| `stream-11-product`           | **âncora**    | Stream 11  | 17    | 8   | produto final; ponto XMEAS 37–41              |
| `stream-11-up`                | segmento      | Stream 11  | —     | —   | trecho superior                               |
| `stream-11-down`              | segmento      | Stream 11  | —     | —   | trecho inferior                               |
| `product-stream`              | saída         | Stream 11  | —     | —   | ponto de saída final do produto               |

### 3.3 Correntes de utilidade — água de resfriamento e vapor

| data-cell-id                  | tipo       | XMV | XMEAS | observação                                  |
| ----------------------------- | ---------- | --- | ----- | ------------------------------------------- |
| `stream-cws-reactor-in`       | CWS in     | 10  | —     | água fria entrando no reator                |
| `stream-cws-reactor-out`      | CWS out    | —   | 21    | água quente saindo do reator                |
| `stream-cws-reactor-up`       | segmento   | —   | —     | trecho vertical — circuito CWS reator       |
| `stream-cws-condenser-in`     | CWS in     | 11  | —     | água fria entrando no condensador           |
| `stream-cws-condenser-out`    | CWS out    | —   | 22    | água quente saindo do condensador           |
| `stream-stm-boiler-in`        | vapor in   | 9   | 19    | vapor de aquecimento → boiler do stripper   |
| `stream-stm-boiler-down`      | segmento   | —   | —     | trecho descendente do vapor                 |
| `stream-stripper-boiler-in`   | processo   | —   | —     | líquido entrando no boiler                  |
| `stream-stripper-boiler-out`  | processo   | —   | —     | líquido saindo do boiler                    |
| `stream-cond-boiler-out`      | condensado | —   | —     | condensado saindo do boiler                 |

---

## 4. Atuadores — `XMV(1..12)`

Os `data-cell-id` dos atuadores estão alinhados com o contrato original. Sem mudanças de nome.

| data-cell-id           | tipo               | origem TEP                              | XMV | stream alvo                  |
| ---------------------- | ------------------ | --------------------------------------- | --- | ----------------------------- |
| `actuator-xmv-01`      | válvula            | `XMV(1)` D feed flow                   | 1   | stream-02 (D feed)            |
| `actuator-xmv-02`      | válvula            | `XMV(2)` E feed flow                   | 2   | stream-03 (E feed)            |
| `actuator-xmv-03`      | válvula            | `XMV(3)` A feed flow                   | 3   | stream-01 (A feed)            |
| `actuator-xmv-04`      | válvula            | `XMV(4)` A/C feed flow                 | 4   | stream-04 (C feed)            |
| `actuator-xmv-05`      | válvula            | `XMV(5)` compressor recycle valve      | 5   | stream-08 (reciclo)           |
| `actuator-xmv-06`      | válvula            | `XMV(6)` purge valve                   | 6   | stream-09-purge               |
| `actuator-xmv-07`      | válvula            | `XMV(7)` separator liquid flow         | 7   | stream-10 (underflow)         |
| `actuator-xmv-08`      | válvula            | `XMV(8)` stripper product flow         | 8   | stream-11-product             |
| `actuator-xmv-09`      | válvula            | `XMV(9)` stripper steam valve          | 9   | stream-stm-boiler-in          |
| `actuator-xmv-10`      | válvula            | `XMV(10)` reactor cooling water flow   | 10  | stream-cws-reactor-in         |
| `actuator-xmv-10-coil` | decoração visual   | Serpentina do reator                   | —   | auxiliar visual de XMV(10)   |
| `actuator-xmv-11`      | válvula            | `XMV(11)` condenser cooling water flow | 11  | stream-cws-condenser-in       |
| `actuator-xmv-12`      | atuador            | `XMV(12)` agitator speed              | 12  | unit-reactor                  |

Exemplo de uso JS:

```js
const valve = document.querySelector('[data-cell-id="actuator-xmv-06"]');
valve.style.fill = `hsl(${snapshot.xmv[5] * 1.2}, 80%, 50%)`;
```

---

## 5. Medições contínuas — `XMEAS(1..22)`

Os `data-cell-id` dos sensores estão alinhados com o contrato original. Sem mudanças de nome.

| data-cell-id        | tipo               | XMEAS | unidade | significado                                 |
| ------------------- | ------------------ | ----- | ------- | ------------------------------------------- |
| `sensor-xmeas-01`   | sensor fluxo       | 1     | kscmh   | Vazão de A                                  |
| `sensor-xmeas-02`   | sensor fluxo       | 2     | kg/hr   | Vazão de D                                  |
| `sensor-xmeas-03`   | sensor fluxo       | 3     | kg/hr   | Vazão de E                                  |
| `sensor-xmeas-04`   | sensor fluxo       | 4     | kscmh   | Vazão da corrente A/C                       |
| `sensor-xmeas-05`   | sensor fluxo       | 5     | kscmh   | Vazão de reciclo                            |
| `sensor-xmeas-06`   | sensor fluxo       | 6     | kscmh   | Vazão total ao reator                       |
| `sensor-xmeas-07`   | sensor pressão     | 7     | kPa     | Pressão do reator (**crítica**)             |
| `sensor-xmeas-08`   | sensor nível       | 8     | %       | Nível do reator (**crítica**)               |
| `sensor-xmeas-09`   | sensor temperatura | 9     | °C      | Temperatura do reator (**crítica**)         |
| `sensor-xmeas-10`   | sensor fluxo       | 10    | kscmh   | Vazão de purga                              |
| `sensor-xmeas-11`   | sensor temperatura | 11    | °C      | Temperatura do separador                    |
| `sensor-xmeas-12`   | sensor nível       | 12    | %       | Nível do separador (**crítica**)            |
| `sensor-xmeas-13`   | sensor pressão     | 13    | kPa     | Pressão do separador                        |
| `sensor-xmeas-14`   | sensor fluxo       | 14    | m³/hr   | Vazão do líquido do separador               |
| `sensor-xmeas-15`   | sensor nível       | 15    | %       | Nível do stripper (**crítica**)             |
| `sensor-xmeas-16`   | sensor pressão     | 16    | kPa     | Pressão do stripper                         |
| `sensor-xmeas-17`   | sensor fluxo       | 17    | m³/hr   | Vazão do produto final                      |
| `sensor-xmeas-18`   | sensor temperatura | 18    | °C      | Temperatura do stripper                     |
| `sensor-xmeas-19`   | sensor fluxo       | 19    | kg/hr   | Vazão de vapor do stripper                  |
| `sensor-xmeas-20`   | sensor potência    | 20    | kW      | Trabalho do compressor                      |
| `sensor-xmeas-21`   | sensor temperatura | 21    | °C      | Temperatura de saída da CWS do reator       |
| `sensor-xmeas-22`   | sensor temperatura | 22    | °C      | Temperatura de saída da CWS do condensador  |

Exemplo:

```js
const temp = document.querySelector('[data-cell-id="sensor-xmeas-09"]');
temp.querySelector('text').textContent = `${snapshot.xmeas[8].toFixed(1)} °C`;
```

---

## 6. Analisadores — `XMEAS(23..41)`

**Mudança de nome:** os IDs seguem o padrão `analyzer-{stream}-{localização}`.

| data-cell-id          | XMEAS  | stream | componentes             | período  |
| --------------------- | ------ | ------ | ----------------------- | -------- |
| `analyzer-06-feed`    | 23–28  | 6      | A, B, C, D, E, F        | 0.1 h    |
| `analyzer-09-purge`   | 29–36  | 9      | A, B, C, D, E, F, G, H  | 0.1 h    |
| `analyzer-11-product` | 37–41  | 11     | D, E, F, G, H           | 0.25 h   |

Detalhamento:

| faixa           | data-cell-id          | componentes            | período  | dead time |
| --------------- | --------------------- | ---------------------- | -------- | --------- |
| `XMEAS(23..28)` | `analyzer-06-feed`    | A, B, C, D, E, F       | `0.1 h`  | `0.1 h`   |
| `XMEAS(29..36)` | `analyzer-09-purge`   | A, B, C, D, E, F, G, H | `0.1 h`  | `0.1 h`   |
| `XMEAS(37..41)` | `analyzer-11-product` | D, E, F, G, H          | `0.25 h` | `0.25 h`  |

---

## 7. Relação mínima entre SVG e snapshot da simulação

Formato esperado de snapshot:

```json
{
  "time_h": 12.345,
  "xmeas": [/* 41 valores */],
  "xmv": [/* 12 valores */],
  "idv": [/* 20 flags */],
  "alarms": []
}
```

Regra de indexação:

```txt
XMEAS(1)  -> snapshot.xmeas[0]
XMEAS(7)  -> snapshot.xmeas[6]
XMEAS(41) -> snapshot.xmeas[40]

XMV(1)  -> snapshot.xmv[0]
XMV(12) -> snapshot.xmv[11]
```

Funções utilitárias:

```js
const getXmeas = (snap, n) => snap.xmeas[n - 1];
const getXmv   = (snap, n) => snap.xmv[n - 1];
const getIdv   = (snap, n) => snap.idv[n - 1];
```

---

## 8. Atualização visual sugerida

### Streams

- largura de traço: proporcional à vazão medida (XMEAS associado);
- opacidade: baixa quando vazão próxima de zero;
- animação de traço: direção do fluxo;
- para múltiplos segmentos: `querySelectorAll('[data-cell-id^="stream-08-"]')`.

### Atuadores

- cor de preenchimento: proporcional à abertura (`XMV`);
- stroke vermelho quando válvula travada (IDV 14, 16–20);
- `actuator-xmv-10-coil` é visual auxiliar — atualizar junto com `actuator-xmv-10`.

### Sensores

- texto: valor atual formatado com unidade;
- cor: normal → warning → shutdown;
- tooltip: nome, valor, unidade, limites.

### Analisadores

- composição por componente;
- indicador de idade da amostra (0.1 h ou 0.25 h de período);
- opacidade reduzida até receber primeira amostra.

---

## 9. Exemplo de binding JavaScript (draw.io SVG)

```js
function updateStream11(snap) {
  const flow = getXmeas(snap, 17); // XMEAS(17) = Stripper Underflow

  // Âncora primária
  const anchor = document.querySelector('[data-cell-id="stream-11-product"]');
  anchor.style.strokeWidth = `${1 + flow * 0.05}px`;

  // Todos os segmentos visuais
  document.querySelectorAll('[data-cell-id^="stream-11-"]').forEach(seg => {
    seg.style.opacity = flow < 0.1 ? '0.2' : '0.8';
  });

  // Sensor de vazão
  document.querySelector('[data-cell-id="sensor-xmeas-17"]')
          .querySelector('text').textContent = `${flow.toFixed(2)} m³/hr`;

  // Analisador de composição do produto
  const az = document.querySelector('[data-cell-id="analyzer-11-product"]');
  if (az) az.dataset.lastUpdate = Date.now();
}
```

---

## 10. Critério para dizer que o SVG está semanticamente correto

O SVG só deve ser tratado como semanticamente correto quando:

1. Todo `XMV(1..12)` existir como `actuator-xmv-XX` (12 elementos).
2. Todo `XMEAS(1..22)` existir como `sensor-xmeas-XX` (22 elementos).
3. Os analisadores `analyzer-06-feed`, `analyzer-09-purge` e `analyzer-11-product` existirem.
4. As unidades `unit-reactor`, `unit-separator`, `unit-condenser`, `unit-stripper`, `unit-stripper-boiler`, `unit-compressor-1`, `unit-compressor-2`, `unit-compressor-3` existirem.
5. As âncoras primárias das correntes 5–11 existirem (`stream-05-stripper-mixer` a `stream-11-product`).
6. O JavaScript conseguir atualizar o diagrama sem conhecer coordenadas internas do desenho.

---

## 11. Observação importante

Não confundir:

- **modelo matemático da planta**: estados internos, balanços, equações diferenciais;
- **interface operacional do benchmark**: `XMEAS`, `XMV`, `IDV`;
- **SVG semântico**: representação navegável dessa interface via `data-cell-id`;
- **layout visual**: coordenadas, formas, curvas e estética (gerenciadas pelo draw.io).

O SVG reflete a interface operacional. Ele não expõe estados internos da planta.
