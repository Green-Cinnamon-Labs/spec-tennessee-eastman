# Contrato semântico do SVG — Tennessee Eastman Process

Este documento define a tabela-mestra para construir um SVG semântico da planta Tennessee Eastman Process (TEP).

A ideia central é separar três coisas:

1. **Origem física/modelo TEP**: equipamento, corrente, medição ou atuador conforme o artigo.
2. **Representação SVG**: elemento visual nomeado e organizado em grupos.
3. **Operação via JavaScript**: atributos `data-*` usados para atualizar cores, valores, estados, animações e alarmes.

Este documento **não define coordenadas gráficas**. Ele define a identidade dos elementos.

---

## 1. Estrutura geral recomendada do SVG

```xml
<svg id="tep-diagram" viewBox="0 0 1400 900">
  <g id="background"></g>
  <g id="streams"></g>
  <g id="utilities"></g>
  <g id="units"></g>
  <g id="actuators"></g>
  <g id="measurements"></g>
  <g id="analyzers"></g>
  <g id="labels"></g>
  <g id="alarms"></g>
</svg>
```

Regra prática: o JavaScript deve operar por `id`, `data-unit`, `data-stream`, `data-xmeas`, `data-xmv` e `data-xmeas-range`. Ele não deve depender da posição visual do elemento.

---

## 2. Equipamentos / unidades principais

O artigo define cinco operações principais: reator, condensador, separador vapor-líquido, compressor de reciclo e stripper de produto.

| id SVG            | tipo     | origem TEP             | bind JS                  | pai no SVG | função                                      |
| ----------------- | -------- | ---------------------- | ------------------------ | ---------- | ------------------------------------------- |
| `unit-reactor`    | unidade  | Reactor                | `data-unit="reactor"`    | `#units`   | vaso reativo; recebe feeds e reciclo        |
| `unit-condenser`  | trocador | Product condenser      | `data-unit="condenser"`  | `#units`   | condensa produto do reator                  |
| `unit-separator`  | unidade  | Vapor-liquid separator | `data-unit="separator"`  | `#units`   | separa vapor reciclável/purga e líquido     |
| `unit-compressor` | máquina  | Recycle compressor     | `data-unit="compressor"` | `#units`   | recicla vapor não condensado                |
| `unit-stripper`   | unidade  | Product stripper       | `data-unit="stripper"`   | `#units`   | remove componentes leves do produto líquido |

Exemplo:

```xml
<g id="unit-reactor" class="unit vessel" data-unit="reactor">
  <!-- corpo do reator, serpentinas, agitador, labels etc. -->
</g>
```

---

## 3. Correntes de processo e utilidades

| id SVG                        | tipo      | origem TEP                      | bind JS                                          | pai no SVG   | observação                                                       |
| ----------------------------- | --------- | ------------------------------- | ------------------------------------------------ | ------------ | ---------------------------------------------------------------- |
| `stream-01-a-feed`            | stream    | Stream 1 — A feed               | `data-stream="1" data-xmeas="1" data-xmv="3"`    | `#streams`   | alimentação A                                                    |
| `stream-02-d-feed`            | stream    | Stream 2 — D feed               | `data-stream="2" data-xmeas="2" data-xmv="1"`    | `#streams`   | alimentação D                                                    |
| `stream-03-e-feed`            | stream    | Stream 3 — E feed               | `data-stream="3" data-xmeas="3" data-xmv="2"`    | `#streams`   | alimentação E                                                    |
| `stream-04-ac-feed`           | stream    | Stream 4 — A/C feed             | `data-stream="4" data-xmeas="4" data-xmv="4"`    | `#streams`   | alimentação A + C para stripper                                  |
| `stream-05-stripper-overhead` | stream    | Stream 5 — stripper overhead    | `data-stream="5"`                                | `#streams`   | topo do stripper retorna ao sistema                              |
| `stream-06-reactor-feed`      | stream    | Stream 6 — reactor feed         | `data-stream="6" data-xmeas="6"`                 | `#streams`   | alimentação total do reator; ponto do analisador `XMEAS(23..28)` |
| `stream-07-reactor-product`   | stream    | Stream 7 — reactor product      | `data-stream="7"`                                | `#streams`   | saída do reator para condensador                                 |
| `stream-08-recycle`           | stream    | Stream 8 — recycle              | `data-stream="8" data-xmeas="5" data-xmv="5"`    | `#streams`   | reciclo via compressor                                           |
| `stream-09-purge`             | stream    | Stream 9 — purge                | `data-stream="9" data-xmeas="10" data-xmv="6"`   | `#streams`   | purga; ponto do analisador `XMEAS(29..36)`                       |
| `stream-10-separator-liquid`  | stream    | Stream 10 — separator underflow | `data-stream="10" data-xmeas="14" data-xmv="7"`  | `#streams`   | líquido do separador para stripper                               |
| `stream-11-product`           | stream    | Stream 11 — product             | `data-stream="11" data-xmeas="17" data-xmv="8"`  | `#streams`   | produto final; ponto do analisador `XMEAS(37..41)`               |
| `stream-12-reactor-cw`        | utilidade | Reactor cooling water           | `data-stream="12" data-xmv="10" data-xmeas="21"` | `#utilities` | resfriamento do reator                                           |
| `stream-13-condenser-cw`      | utilidade | Condenser cooling water         | `data-stream="13" data-xmv="11" data-xmeas="22"` | `#utilities` | resfriamento do condensador                                      |

Exemplo:

```xml
<path id="stream-09-purge"
      class="stream gas purge"
      data-stream="9"
      data-xmeas="10"
      data-xmv="6"
      data-phase="vapor" />
```

---

## 4. Atuadores — `XMV(1..12)`

| id SVG            | tipo               | origem TEP                             | bind JS         | pai no SVG   | atua sobre                   |
| ----------------- | ------------------ | -------------------------------------- | --------------- | ------------ | ---------------------------- |
| `actuator-xmv-01` | válvula / flow set | `XMV(1)` D feed flow                   | `data-xmv="1"`  | `#actuators` | `stream-02-d-feed`           |
| `actuator-xmv-02` | válvula / flow set | `XMV(2)` E feed flow                   | `data-xmv="2"`  | `#actuators` | `stream-03-e-feed`           |
| `actuator-xmv-03` | válvula / flow set | `XMV(3)` A feed flow                   | `data-xmv="3"`  | `#actuators` | `stream-01-a-feed`           |
| `actuator-xmv-04` | válvula / flow set | `XMV(4)` A/C feed flow                 | `data-xmv="4"`  | `#actuators` | `stream-04-ac-feed`          |
| `actuator-xmv-05` | válvula            | `XMV(5)` compressor recycle valve      | `data-xmv="5"`  | `#actuators` | `stream-08-recycle`          |
| `actuator-xmv-06` | válvula            | `XMV(6)` purge valve                   | `data-xmv="6"`  | `#actuators` | `stream-09-purge`            |
| `actuator-xmv-07` | válvula            | `XMV(7)` separator liquid flow         | `data-xmv="7"`  | `#actuators` | `stream-10-separator-liquid` |
| `actuator-xmv-08` | válvula            | `XMV(8)` stripper product flow         | `data-xmv="8"`  | `#actuators` | `stream-11-product`          |
| `actuator-xmv-09` | válvula            | `XMV(9)` stripper steam valve          | `data-xmv="9"`  | `#actuators` | steam to stripper            |
| `actuator-xmv-10` | válvula / flow set | `XMV(10)` reactor cooling water flow   | `data-xmv="10"` | `#actuators` | `stream-12-reactor-cw`       |
| `actuator-xmv-11` | válvula / flow set | `XMV(11)` condenser cooling water flow | `data-xmv="11"` | `#actuators` | `stream-13-condenser-cw`     |
| `actuator-xmv-12` | atuador            | `XMV(12)` agitator speed               | `data-xmv="12"` | `#actuators` | `unit-reactor`               |

Exemplo:

```xml
<g id="actuator-xmv-06"
   class="actuator valve"
   data-xmv="6"
   data-stream="9"
   data-target="stream-09-purge">
  <!-- desenho da válvula -->
</g>
```

Uso esperado no JavaScript:

```js
const purgeValve = document.querySelector('[data-xmv="6"]');
purgeValve.dataset.value = snapshot.xmv[5];
purgeValve.classList.toggle('valve-stuck', snapshot.disturbances?.idv14 === true);
```

---

## 5. Medições contínuas — `XMEAS(1..22)`

| id SVG            | tipo               | origem TEP                                            | bind JS           | pai no SVG      | significado                                 |
| ----------------- | ------------------ | ----------------------------------------------------- | ----------------- | --------------- | ------------------------------------------- |
| `sensor-xmeas-01` | sensor fluxo       | `XMEAS(1)` A feed                                     | `data-xmeas="1"`  | `#measurements` | vazão de A                                  |
| `sensor-xmeas-02` | sensor fluxo       | `XMEAS(2)` D feed                                     | `data-xmeas="2"`  | `#measurements` | vazão de D                                  |
| `sensor-xmeas-03` | sensor fluxo       | `XMEAS(3)` E feed                                     | `data-xmeas="3"`  | `#measurements` | vazão de E                                  |
| `sensor-xmeas-04` | sensor fluxo       | `XMEAS(4)` A/C feed                                   | `data-xmeas="4"`  | `#measurements` | vazão da corrente A/C                       |
| `sensor-xmeas-05` | sensor fluxo       | `XMEAS(5)` recycle flow                               | `data-xmeas="5"`  | `#measurements` | vazão de reciclo                            |
| `sensor-xmeas-06` | sensor fluxo       | `XMEAS(6)` reactor feed rate                          | `data-xmeas="6"`  | `#measurements` | vazão total ao reator                       |
| `sensor-xmeas-07` | sensor pressão     | `XMEAS(7)` reactor pressure                           | `data-xmeas="7"`  | `#measurements` | pressão do reator                           |
| `sensor-xmeas-08` | sensor nível       | `XMEAS(8)` reactor level                              | `data-xmeas="8"`  | `#measurements` | nível do reator                             |
| `sensor-xmeas-09` | sensor temperatura | `XMEAS(9)` reactor temperature                        | `data-xmeas="9"`  | `#measurements` | temperatura do reator                       |
| `sensor-xmeas-10` | sensor fluxo       | `XMEAS(10)` purge rate                                | `data-xmeas="10"` | `#measurements` | vazão de purga                              |
| `sensor-xmeas-11` | sensor temperatura | `XMEAS(11)` product separator temperature             | `data-xmeas="11"` | `#measurements` | temperatura do separador                    |
| `sensor-xmeas-12` | sensor nível       | `XMEAS(12)` product separator level                   | `data-xmeas="12"` | `#measurements` | nível do separador                          |
| `sensor-xmeas-13` | sensor pressão     | `XMEAS(13)` product separator pressure                | `data-xmeas="13"` | `#measurements` | pressão do separador                        |
| `sensor-xmeas-14` | sensor fluxo       | `XMEAS(14)` separator underflow                       | `data-xmeas="14"` | `#measurements` | vazão do líquido do separador               |
| `sensor-xmeas-15` | sensor nível       | `XMEAS(15)` stripper level                            | `data-xmeas="15"` | `#measurements` | nível do stripper                           |
| `sensor-xmeas-16` | sensor pressão     | `XMEAS(16)` stripper pressure                         | `data-xmeas="16"` | `#measurements` | pressão do stripper                         |
| `sensor-xmeas-17` | sensor fluxo       | `XMEAS(17)` stripper underflow                        | `data-xmeas="17"` | `#measurements` | vazão do produto final                      |
| `sensor-xmeas-18` | sensor temperatura | `XMEAS(18)` stripper temperature                      | `data-xmeas="18"` | `#measurements` | temperatura do stripper                     |
| `sensor-xmeas-19` | sensor fluxo       | `XMEAS(19)` stripper steam flow                       | `data-xmeas="19"` | `#measurements` | vazão de vapor do stripper                  |
| `sensor-xmeas-20` | sensor potência    | `XMEAS(20)` compressor work                           | `data-xmeas="20"` | `#measurements` | trabalho do compressor                      |
| `sensor-xmeas-21` | sensor temperatura | `XMEAS(21)` reactor CW outlet temperature             | `data-xmeas="21"` | `#measurements` | temperatura de saída da água do reator      |
| `sensor-xmeas-22` | sensor temperatura | `XMEAS(22)` separator/condenser CW outlet temperature | `data-xmeas="22"` | `#measurements` | temperatura de saída da água do condensador |

Exemplo:

```xml
<g id="sensor-xmeas-07"
   class="measurement pressure"
   data-xmeas="7"
   data-unit="reactor">
  <circle class="sensor-symbol" />
  <text class="sensor-label">PI</text>
  <text class="sensor-value" data-bind="xmeas-7">--</text>
</g>
```

---

## 6. Analisadores — `XMEAS(23..41)`

| id SVG                  | tipo       | origem TEP                | bind JS                                     | pai no SVG   | significado                             |
| ----------------------- | ---------- | ------------------------- | ------------------------------------------- | ------------ | --------------------------------------- |
| `analyzer-reactor-feed` | analisador | `XMEAS(23..28)` stream 6  | `data-xmeas-range="23-28" data-stream="6"`  | `#analyzers` | composição A–F da alimentação do reator |
| `analyzer-purge`        | analisador | `XMEAS(29..36)` stream 9  | `data-xmeas-range="29-36" data-stream="9"`  | `#analyzers` | composição A–H da purga                 |
| `analyzer-product`      | analisador | `XMEAS(37..41)` stream 11 | `data-xmeas-range="37-41" data-stream="11"` | `#analyzers` | composição D–H do produto               |

Detalhamento:

| faixa           | localização             | componentes            | frequência de amostragem | dead time |
| --------------- | ----------------------- | ---------------------- | ------------------------ | --------- |
| `XMEAS(23..28)` | Stream 6 — reactor feed | A, B, C, D, E, F       | `0.1 h`                  | `0.1 h`   |
| `XMEAS(29..36)` | Stream 9 — purge gas    | A, B, C, D, E, F, G, H | `0.1 h`                  | `0.1 h`   |
| `XMEAS(37..41)` | Stream 11 — product     | D, E, F, G, H          | `0.25 h`                 | `0.25 h`  |

Exemplo:

```xml
<g id="analyzer-purge"
   class="analyzer"
   data-stream="9"
   data-xmeas-range="29-36"
   data-components="A,B,C,D,E,F,G,H"
   data-sample-period-h="0.1"
   data-dead-time-h="0.1">
  <!-- símbolo do analisador -->
</g>
```

---

## 7. Relação mínima entre SVG e snapshot da simulação

Formato esperado de snapshot do backend/simulador:

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

Função utilitária recomendada:

```js
function getXmeas(snapshot, n) {
  return snapshot.xmeas[n - 1];
}

function getXmv(snapshot, n) {
  return snapshot.xmv[n - 1];
}
```

---

## 8. Atualização visual sugerida

### Streams

- largura da linha: proporcional à vazão medida, quando houver `data-xmeas`;
- opacidade: baixa quando vazão próxima de zero;
- classe de fase: `gas`, `vapor`, `liquid`, `utility`;
- animação de traço: direção do fluxo.

### Atuadores

- cor: abertura/posição da válvula;
- rotação ou preenchimento: valor de `XMV`;
- classe especial: `valve-stuck`, `manual`, `saturated`, `alarm`.

### Sensores

- texto: valor atual formatado;
- cor: normal, warning ou shutdown;
- tooltip: nome, unidade, valor e limite.

### Analisadores

- valor exibido: composição por componente;
- indicador de idade da amostra;
- diferença visual entre medição contínua e medição amostrada.

---

## 9. Exemplo de elemento completo

```xml
<g id="stream-11-product"
   class="stream liquid product"
   data-stream="11"
   data-xmeas="17"
   data-xmv="8"
   data-source="unit-stripper"
   data-destination="external-product">
  <path class="stream-line" d="..." />
  <text class="stream-label">11 Product</text>
</g>

<g id="actuator-xmv-08"
   class="actuator valve"
   data-xmv="8"
   data-stream="11"
   data-target="stream-11-product">
  <path class="valve-symbol" d="..." />
  <text class="valve-label">XMV(8)</text>
</g>

<g id="sensor-xmeas-17"
   class="measurement flow"
   data-xmeas="17"
   data-stream="11">
  <circle class="sensor-symbol" />
  <text class="sensor-label">FI</text>
  <text class="sensor-value" data-bind="xmeas-17">--</text>
</g>

<g id="analyzer-product"
   class="analyzer"
   data-stream="11"
   data-xmeas-range="37-41"
   data-components="D,E,F,G,H"
   data-sample-period-h="0.25"
   data-dead-time-h="0.25">
  <rect class="analyzer-box" />
  <text class="analyzer-label">Product Analyzer</text>
</g>
```

---

## 10. Critério para dizer que o SVG está semanticamente correto

O SVG só deve ser tratado como semanticamente correto quando:

1. Todo `XMV(1..12)` existir como `actuator-xmv-XX`.
2. Todo `XMEAS(1..22)` existir como `sensor-xmeas-XX` ou estar explicitamente agrupado.
3. Os analisadores `XMEAS(23..41)` estiverem nos streams corretos: `6`, `9`, `11`.
4. Toda corrente principal tiver `data-stream`.
5. Toda corrente manipulada tiver `data-xmv`.
6. Toda corrente medida tiver `data-xmeas`.
7. Os equipamentos principais estiverem agrupados em `#units`.
8. O JavaScript conseguir atualizar o diagrama sem conhecer coordenadas internas do desenho.

---

## 11. Observação importante

Não confundir:

- **modelo matemático da planta**: estados internos, balanços, equações diferenciais;
- **interface operacional do benchmark**: `XMEAS`, `XMV`, `IDV`;
- **SVG semântico**: representação navegável e manipulável dessa interface;
- **layout visual**: coordenadas, formas, curvas e estética.

O SVG deve refletir a interface operacional. Ele não precisa expor todos os estados internos da planta.
