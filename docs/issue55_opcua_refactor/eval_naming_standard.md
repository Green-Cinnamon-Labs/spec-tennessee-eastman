# TEP Naming Standard

Padrão canônico de nomenclatura para todos os repositórios do lab (IHM, plant, operator, supervisor).
A fonte de verdade é o SVG do diagrama (`tep-ihm/static/assets/plant-diagram.svg`).

---

## Padrão geral

```
{tipo}-{número}-{descrição}
```

- `tipo` — categoria do elemento (ver tabela abaixo)
- `número` — dois dígitos zero-padded (`01`, `09`, `12`)
- `descrição` — kebab-case em inglês, opcional para atuadores e sensores

| Tipo       | Prefixo    | Exemplos                                |
| ---------- | ---------- | --------------------------------------- |
| Unidade    | `unit`     | `unit-reactor`, `unit-separator`        |
| Stream     | `stream`   | `stream-01-a-feed`, `stream-09-purge`   |
| Atuador    | `actuator` | `actuator-xmv-01` … `actuator-xmv-12`   |
| Sensor     | `sensor`   | `sensor-xmeas-01` … `sensor-xmeas-41`   |
| Analisador | `analyzer` | `analyzer-06-feed`, `analyzer-09-purge` |
| Nó/junção  | `node`     | `node-reactor-feed-mixer`               |

---

## Unidades de processo

| ID                     | Nome físico             |
| ---------------------- | ----------------------- |
| `unit-reactor`         | Reator (CSTR)           |
| `unit-separator`       | Separador vapor/líquido |
| `unit-condenser`       | Condensador             |
| `unit-compressor`      | Compressor de reciclo   |
| `unit-stripper`        | Stripper                |
| `unit-stripper-boiler` | Reboiler do stripper    |

---

## Streams (ftm[i] no FORTRAN → índice base-0 no Rust)

| ID                            | ftm idx | Descrição                                        |
| ----------------------------- | ------- | ------------------------------------------------ |
| `stream-01-a-feed`            | 0       | Feed A (gás puro)                                |
| `stream-02-d-feed`            | 1       | Feed D (líquido)                                 |
| `stream-03-e-feed`            | 2       | Feed E (líquido)                                 |
| `stream-04-c-feed`            | 3       | Feed A/C (gás)                                   |
| `stream-05-stripper-mixer`    | 4       | Reciclo stripper → mixer de feed                 |
| `stream-06-mixer-reactor`     | 5       | Feed do reator (saída do mixer/compressor)       |
| `stream-07-reactor-separator` | 6       | Efluente do reator → separador (via condensador) |
| `stream-08-recycle`           | 7       | Vapor do separador → compressor (reciclo)        |
| `stream-09-purge`             | 8       | Purga (vapor topo separador → saída)             |
| `stream-10-separator-liquid`  | 9       | Líquido separador → stripper                     |
| `stream-11-stripper-feed`     | 10      | Feed do stripper (do mixer)                      |
| `stream-12-cws-reactor`       | 11      | Água de resfriamento do reator                   |
| `stream-13-cws-condenser`     | 12      | Água de resfriamento do condensador              |
| `stream-14-stripper-steam`    | —       | Vapor/condensado do stripper (utilitário)        |
| `stream-15-stripper-boiler`   | —       | Circuito do reboiler                             |

---

## Atuadores (XMV — manipulated variables)

| ID                | XMV | vpos idx | Descrição                                |
| ----------------- | --- | -------- | ---------------------------------------- |
| `actuator-xmv-01` | 1   | 0        | Válvula feed A                           |
| `actuator-xmv-02` | 2   | 1        | Válvula feed D                           |
| `actuator-xmv-03` | 3   | 2        | Válvula feed E                           |
| `actuator-xmv-04` | 4   | 3        | Válvula feed A/C                         |
| `actuator-xmv-05` | 5   | 4        | Válvula reciclo (anti-surge compressor)  |
| `actuator-xmv-06` | 6   | 5        | Válvula líquido separador → stripper     |
| `actuator-xmv-07` | 7   | 6        | Válvula purga                            |
| `actuator-xmv-08` | 8   | 7        | Válvula produto (saída stripper)         |
| `actuator-xmv-09` | 9   | 8        | Válvula água resfriamento condensador    |
| `actuator-xmv-10` | 10  | 9        | Válvula água resfriamento reator         |
| `actuator-xmv-11` | 11  | 10       | Válvula vapor stripper                   |
| `actuator-xmv-12` | 12  | —        | Agitador do reator (Agitator, não Valve) |

> **Nota:** XMV-12 é modelado como `Agitator` em `actuator/dynamic.rs`, não como `Valve`.
> O seu estado vive em `state[49]`, separado das 11 válvulas em `state[38..49]`.

---

## Sensores (XMEAS — measured variables)

Os sensores seguem o padrão `sensor-xmeas-NN` onde NN é o índice 1-based do vetor XMEAS (base-0 no Rust: `xmeas[NN-1]`).

Sensores especiais:
- `sensor-sc-reactor` — shutdown criterion do reator (não é XMEAS, é flag interna)
- `analyzer-06-feed` / `analyzer-09-purge` / `analyzer-11-product` — analisadores de composição (XMEAS 23–41)

---

## Mapeamento para Rust

O objetivo de curto prazo é substituir índices numéricos por nomes semânticos nos structs de output:

| Hoje (FORTRAN/numérico) | Meta (semântico)                   |
| ----------------------- | ---------------------------------- |
| `ftm[0]`                | `flows.a_feed`                     |
| `ftm[4]`                | `flows.recycle`                    |
| `ftm[8]`                | `flows.purge`                      |
| `vpos[4]`               | `recycle_valve.position`           |
| `vpos[8]`               | `condenser_cooling_valve.position` |
| `xmeas[6]`              | `xmeas.reactor_pressure`           |

Os nomes em Rust devem usar snake_case com a mesma raiz descritiva dos IDs do SVG
(ex: `a_feed`, `d_feed`, `purge`, `reactor`, `separator`, `stripper`).
