# Entrega 2 — Painel Analítico com Persistência de Séries Temporais

> **Status: IMPLEMENTADO** — issue #54 fechada em 2026-05-25.  
> Arquivos entregues: `src/persistence.py`, `static/analytics.html`, `static/analytics.js`, rotas em `src/server.py`.  
> Guia de uso: `docs/forDummies/nota_analytics_panel.md`

**Escopo:** `tep-ihm` (storage + display)  
**Complexidade:** Alta — envolve decisão de persistência, nova dependência (ECharts), e possivelmente novo serviço  
**Pré-requisito:** Decisão de arquitetura de storage (seção 2) ✓

---

## Objetivo

Viabilizar análise de dados de processo em séries temporais: o usuário monta os gráficos que quer acompanhar, os dados são persistidos durante (e após) a sessão, e podem ser exportados ou consultados para ciência de dados.

Isso é fundamentalmente diferente dos mini-gráficos operacionais: aqui o dado histórico **tem valor fora da sessão ativa**.

---

## 1. Separação conceitual

```
WebSocket (tempo real) ──► SVGControlCharts (Entrega 1) — memória, descartável
                      └──► Ingestão → Storage → API REST ──► Painel ECharts (esta entrega)
```

O painel analítico **não lê o WebSocket diretamente**. Ele consulta dados históricos via API REST, com janela configurável pelo usuário.

---

## 2. Decisão de storage — opções em aberto

Esta é a decisão mais importante da entrega. Três caminhos possíveis:

### Opção A — InfluxDB (time series database dedicado)
- Protocolo de ingestão nativo (line protocol), cliente Rust disponível.
- Query via Flux ou InfluxQL — poderoso para ciência de dados.
- Docker Compose: adicionar container `influxdb` em `tep-supervisor`.
- **Trade-off:** infraestrutura nova, overhead de operação.

### Opção B — TimescaleDB (PostgreSQL + extensão time series)
- Familiar se o lab já usa SQL; suporte a queries complexas com JOINs.
- Cliente Rust via `sqlx` ou `diesel`.
- **Trade-off:** mais pesado que InfluxDB para ingestão de alta frequência.

### Opção C — SQLite local no `tep-ihm` (ingestão via WebSocket)
- Zero infraestrutura nova — SQLite embutido no processo FastAPI.
- `tep-ihm` assina o WebSocket do plant e persiste cada tick em tabela `(t_h, xmeas_json, xmv_json)`.
- Query via API REST simples (`/api/history?var=xmeas_7&from=0&to=100`).
- **Trade-off:** não escala para múltiplos experimentos simultâneos; dados ficam no container.

### DECISÃO
SQLite (Opção C) para o primeiro ciclo — menor fricção, sem nova infra, viabiliza o painel sem alterar `tep-plant`. Migrar para InfluxDB quando o volume de experimentos justificar. Isso é disctudido na issue [#54](https://github.com/Green-Cinnamon-Labs/spec-tennessee-eastman/issues/54)

---

## 3. Arquitetura da ingestão

### Se Opção C (SQLite no tep-ihm):

```
tep-plant (Rust gRPC)
    │
    ▼ StreamMetrics (WebSocket)
tep-ihm (FastAPI)
    ├── ws_handler.py  ──► persistence.py (SQLite write)
    └── api/history.py ──► SELECT ... WHERE t_h BETWEEN ? AND ?
```

**Tabela:**
```sql
CREATE TABLE metrics (
  id       INTEGER PRIMARY KEY,
  t_h      REAL NOT NULL,
  xmeas    TEXT NOT NULL,  -- JSON array [41 floats]
  xmv      TEXT NOT NULL,  -- JSON array [12 floats]
  ts_wall  INTEGER         -- Unix timestamp (para correlação real)
);
CREATE INDEX idx_t_h ON metrics(t_h);
```

**API REST mínima:**
```
GET /api/history?from=<t_h>&to=<t_h>&vars=xmeas_7,xmeas_9,xmv_10
→ { labels: [...], series: { xmeas_7: [...], xmeas_9: [...] } }

GET /api/sessions        → lista de experimentos gravados
DELETE /api/history      → limpa sessão atual
GET /api/export?format=csv
```

---

## 4. Frontend — ECharts

### Por que ECharts

- Dataset API desacopla dados de configuração: o mesmo dataset alimenta múltiplos charts.
- Toolbox nativo: zoom, brush (seleção de janela), save image, data view.
- Suporte a eixos duplos (Y esquerdo e direito) para séries de unidades diferentes.
- Melhor suporte a grandes volumes de pontos que Chart.js (WebGL renderer opcional).

### Estrutura da aba analítica

```
┌─ aba: Analytics ───────────────────────────────────────────────────┐
│  ┌─ variable picker ──────┐  ┌─ chart canvas ─────────────────────┐│
│  │ XMEAS                  │  │                                     ││
│  │  ☑ (7) Pressure kPa    │  │   [ECharts instance]                ││
│  │  ☑ (9) Temperature °C  │  │   zoom / brush / export nativos     ││
│  │  ☐ (8) Level %         │  │                                     ││
│  │  ...                   │  │                                     ││
│  │ XMV                    │  └─────────────────────────────────────┘│
│  │  ☑ (10) CWS Reactor %  │                                         │
│  │  ...                   │  [+ Add chart slot]                     │
│  │ [Query]  [t_h: 0─100]  │                                         │
│  └────────────────────────┘                                         │
└────────────────────────────────────────────────────────────────────┘
```

### Comportamento do variable picker

- Lista todas as variáveis disponíveis: XMEAS(1–41) com nome e unidade, XMV(1–12).
- Checkboxes para selecionar quais entram no chart ativo.
- Seleção de janela temporal: slider de `t_h` ou inputs numéricos.
- Botão "Query" dispara `GET /api/history` e popula o dataset ECharts.
- Configuração de chart salva em `localStorage` (variáveis selecionadas + janela).

### Múltiplos slots de chart

- O usuário pode abrir até N charts simultâneos (ex: 3–4).
- Cada slot tem seu próprio variable picker e dataset independente.
- Layout: CSS grid, redimensionável via drag.

---

## 5. Questões em aberto — para discussão


- Storage: SQLite vs InfluxDB   → SQLite                                                     
- Frequência de ingestão        → downsampled → 1 ponto/s                                    
- Retenção de dados             → Não gravar tudo automaticamente. Modelar `data_source` como origem dos dados e `capture_session` como uma tomada de dados   iniciada manualmente pelo usuário. Cada captura gera uma sessão listável, com início/fim, descrição, fonte, variáveis registradas  e dados associados.
- Múltiplos experimentos        → tabela com `session_id`.
- Export                        → CSV.
- ECharts: CDN ou bundle local  → CDN simples para começar.
- Eixos duplos                  → ECharts

---

## 6. Arquivos afetados

| Repositório      | Arquivo                      | Mudança                                         |
| ---------------- | ---------------------------- | ----------------------------------------------- |
| `tep-ihm`        | `persistence.py` (novo)      | SQLite write a cada tick WebSocket              |
| `tep-ihm`        | `api/history.py` (novo)      | Endpoint REST de query                          |
| `tep-ihm`        | `main.py`                    | Registrar router de history                     |
| `tep-ihm`        | `templates/index.html`       | Aba Analytics + ECharts                         |
| `tep-ihm`        | `static/analytics.js` (novo) | Variable picker + ECharts setup                 |
| `tep-supervisor` | `docker-compose.yml`         | Volume para SQLite (ou novo container InfluxDB) |

---

## 7. Ordem sugerida de implementação

1. **Decisão de storage** — Opção C.
2. **Ingestão mínima** — `persistence.py` gravando em cada segundo no SQLite.
3. **API REST mínima** — `/api/history` com query por variável e janela temporal.
4. **ECharts básico** — uma aba com um chart, variable picker simples, query funcional.
5. **Variable picker completo** — multi-seleção, janela temporal, localStorage.
6. **Múltiplos slots** — grid de charts configurável pelo usuário.
7. **Export CSV/Parquet** — para ciência de dados fora do IHM.
