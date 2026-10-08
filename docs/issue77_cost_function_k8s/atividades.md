# Plan: second observation level (control-loop quality) + run experiment #82

## Context

Epic #77 delivered the first observation level: Kubernetes (`plant-supervisor`) evaluates the plant's operating cost J against a declared policy. The user wants the #82 experiment to show **two** levels side by side: (1) economic — J and the policy verdict, (2) **control quality** — health of the plant's control loops, using Bradu et al.'s Predictability Index (Cap 2, art2). Decisions taken: loop health is a **separate verdict** (`ControlLoopsHealthy`, not folded into `PolicyCompliant`); plant excitation is **sensor noise only** (#66), no random IDVs; index is **Bradu's PI only** (Harris later).

Why work is needed before running: the PI is variance-based and degenerates on today's noise-free plant (all sensors `Ideal`, only deterministic step IDVs); the historian only serves window means; the CRDs have no notion of a control loop.

Existing pieces to reuse:
- 3 P loops in `tep-plant/src/controllers/` — PV/OP already published over OPC-UA: reactor pressure → `valve.purge.position` (SP 2705), separator level → `valve.separator_underflow.position` (SP 50), stripper level → `valve.stripper_product.position` (SP 50). SPs are Rust consts → declared in the manifest (no plant change).
- `monjolo::sensor::model::Noisy` already exists (`monjolo/monjolo/sensor/model.rs:108`); real std devs in `tep-plant/docs/06-ruidos.md`.
- Runtime speed already controllable (`monjolo/monjolo/runtime_control.rs` `set_speed`; IHM `POST /simulation/speed`) — no #69 work needed.
- Historian buffer keeps raw samples (`tep-historian/src/tep_historian/buffer.py`), all keys sampled at the same timestamp.

## Steps

### 0. Spec
- New issue in spec-tennessee-eastman: "Qualidade das malhas no supervisor (Predictability Index)" — sub-items per repo below; link #66, #82, #84. Update `docs/issue77_cost_function_k8s/experiment_82.md` decisions as they are taken.

### 1. Sensor noise — monjolo + tep-plant (#66)
- `monjolo-macros`: extend `#[monjolo::sensor(key = "...")]` with optional `noise = <std_dev>` (and seed) → `Noisy::new(...)` instead of `Ideal` (`monjolo-macros/macros/lib.rs` ~line 270–278). No `noise` → `Ideal` (deterministic default unchanged).
- `tep-plant/src/sensors/*.rs`: apply std devs from `docs/06-ruidos.md`, at least to the 3 loop PVs and the signals used by J; ideally all 41 XMEAS. Update the `sensors/mod.rs` note.
- Rust comment style: `/* */`, max 100 chars/line.

### 2. Historian — loop performance (#new)
- `buffer.py`: method returning the raw window series for given keys (aligned by timestamp).
- New module `loop_performance.py` (numpy): per loop, `e = SP − PV`; with sampling `t_s`, window `T_W`, time constant `T`: `n = ⌈T_W/t_s⌉`, `b = ⌈T/t_s⌉`, `m = 2b`; least-squares AR fit `ê(t+b) = a0 + Σ a_i e(t−i)`; `PI = σ²_r / mse` (verify exact definition against art2 while implementing); also `σ_OP` for the variability gate. Guard degenerate cases (too few samples, mse≈0 → report `null`, not a number).
- `api.py`: `POST /loop-performance {loops:[{name, pv, sp, op, time_constant_s}], window_s}` → per loop `{pi, mse, sigma_op, count}`. Keep endpoints `async def`.
- pytest with synthetic series (white noise vs AR process vs constant) + API test. Add `numpy` to pyproject.

### 3. plant-supervisor — loops in the policy, separate verdict
- `api/v1alpha1/operatingpolicy_types.go`: `controlLoops[]{name, pv, setpoint, op, timeConstantSeconds, minPredictability (PI_L), minOutputStd (σ̄_y)}` + `loopPersistenceEvaluations`.
- `api/v1alpha1/plant_types.go`: `status.loops[]{name, pi, sigmaOp, healthy, reason}`, `consecutiveLoopViolations`, condition `ControlLoopsHealthy` (separate from `PolicyCompliant`; phase unchanged).
- `internal/historian/client.go`: `LoopPerformance(...)`.
- `internal/evaluate`: pure `EvaluateLoops` — loop unhealthy if `PI < minPredictability` **and** `σ_OP > minOutputStd` (Bradu's gate); separate persistence counter. Unit tests.
- `internal/controller/plant_controller.go`: call it when the policy has loops; set the condition; historian errors on loops don't block the J verdict.
- Tests: decided earlier to swap the `Historian` interface for `httptest.Server` — do it here (removes interface/`NewHistorian`/`if`, adds coverage of `client.go`).
- `make generate manifests`; docs 03/04 updated.

### 4. tep-lab — manifests and setup
- Regenerate `local/k8s/crd.yaml` (cat of `config/crd/bases`).
- `local/k8s/tep/policy-mode1.yaml`: the 3 loops with SPs 2705/50/50, time constants and **provisional** thresholds (set in step 6).
- Rebuild image, `kind load`, `rollout restart` (via `setup.sh`).

### 5. IHM — show loop health
- `tep-ihm/src/server.py` (`_k8s_watch_sync`): map `status.loops` and the new condition.
- `static/dashboard/app.js` / `index.html`: a "Malhas de controle" table in the supervisor panel (PI, σ_OP, ok/degradada).

### 6. Experiment infrastructure + calibration
- Recording script (tep-lab, e.g. `local/scripts/record_verdict.py`): every N s, `kubectl get plant tep -o json` + historian `clock.t_h` → CSV (J, terms, conditions, per-loop PI).
- Decide simulation speed (e.g. 10× via `/simulation/speed`) and window/interval so the window covers meaningful simulated time; keep historian sampling adequate for `t_s`.
- Calibration run (nominal, with noise): record baseline J and PI per loop; set `minPredictability`/`minOutputStd` and revisit `maxCost` (doc: operating_policy_mode1.md "Decisions to revisit").

### 7. Run #82
- Nominal stretch → IDV6 on (OPC-UA `disturbance.idv6 = 1`) → observe both levels → IDV6 off → recovery; repeat with IDV1 for contrast.
- Record in `experimentos.md` (new Exp) and update `experiment_82.md` with results; feeds the thesis (Cap 4).

## Order and pacing
Strictly **block by block** (user request): 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7. At the end of each block, stop and report to the user (what changed, files, test results, anything surprising) and **wait for the go-ahead** before starting the next block. No parallel blocks.

## Verification
- monjolo/tep-plant: existing tests pass with no `noise` (deterministic unchanged); a sensor with `noise` shows the declared std dev over many samples; plant runs and historian `/aggregate` shows `std > 0` on noisy signals.
- historian: pytest — white noise → low PI, strongly autocorrelated AR series → high PI, constant series → `null`.
- plant-supervisor: unit tests for `EvaluateLoops` + persistence; envtest controller tests (httptest historian) for healthy / degraded / gated-by-σ_OP / historian loop error not blocking J.
- End to end in Kind: `kubectl describe plant tep` shows `ControlLoopsHealthy` and per-loop PI; IHM panel shows the loop table; recording script produces a CSV covering a full #82 run.

---

## Bloco 6 — suas atividades (calibração, feita junto)

Objetivo do bloco: medir como a planta se comporta em **operação nominal** (com ruído, sem distúrbio) e, a partir dos números, escolher os limiares definitivos das malhas (`minPredictability`, `minOutputStd`) e revisar o orçamento de custo (`maxCost`). Sem isso, o experimento #82 não tem com o que comparar: não dá para dizer que algo "piorou" sem saber como é o "normal".

Divisão: **você** sobe e opera a planta e toma as decisões; **Claude** prepara os scripts (passo 6.1) e ajuda a ler os dados. Marque cada item ao concluir.

### 6.0 Antes de começar

- [x] Confirmar que o Claude parou a planta e o historian que estavam rodando em background (as portas 4840, 8090 e 8080 precisam estar livres).
- [x] Confirmar que o Kind está de pé: `kubectl get pods` mostra `plant-supervisor-...` em `Running`.

### 6.1 Ferramentas (Claude prepara, você revisa)

- [x] Ler o script de gravação [`tep-lab/local/scripts/record_run.py`](../../../tep-lab/local/scripts/record_run.py): a cada N segundos grava numa linha de CSV o tempo simulado (`clock.t_h`), J, a fase, as conditions e, por malha, PI, offset, σ da válvula e se foi julgada.
- [x] Ler o script de resumo [`tep-lab/local/scripts/summarize_run.py`](../../../tep-lab/local/scripts/summarize_run.py): lê o CSV e mostra, por malha, a distribuição do PI e do σ da válvula, e a média e a dispersão de J.

### 6.2 Subir tudo (você)

- [x] F5 no tep-plant: **"tep-plant (com adaptador OPC-UA)"**.
- [x] F5 no tep-historian: **"Historian: planta local (OPC-UA)"**. Conferir `http://localhost:8090/healthz` → `"connected": true`.
- [x] F5 no tep-ihm: **"IHM: planta local (plant OPC-UA + k8s)"**. Abrir `http://localhost:8080` e o painel ⬡ K8S SUPERVISOR.
- [x] Conferir: `kubectl get plants` mostra a coluna `LOOPS`, e o painel mostra a linha "Malhas" e a tabela das 3 malhas.

### 6.3 Escolher a velocidade da simulação (decisão sua)

As janelas do historian são em **tempo de relógio**, mas a planta roda mais rápido que o tempo real. Na velocidade atual (~2×), a janela de 300 s das malhas cobre ~10 min simulados; a 10×, cobriria ~50 min. A constante de tempo `T` das malhas (30 s) também é de relógio, então muda de significado com a velocidade.

- [x] Decidir a velocidade — **a mesma** que será usada no experimento #82. Sugestão: **5** (≈ 10× o tempo real). A velocidade só muda a pausa entre ticks, não a física: o passo simulado é sempre 1 s, então os resultados são os mesmos em qualquer velocidade.
- [x] Decidir se `loopWindowSeconds`, `timeConstantSeconds` e `windowSeconds` mudam para essa velocidade.
- [x] Registrar a decisão e o porquê (abaixo, em "Decisões").

### 6.4 Rodada de calibração (você roda, observamos juntos)

- [x] Ajustar a velocidade no **UaExpert**: chamar o método `control.set_speed` com o argumento escolhido (Double; `1` = 2× o tempo real, `N` = 2N×, `0` = o mais rápido possível). Os botões de velocidade da IHM não funcionam (o backend ignora). Conferir: a 5, `clock.t_h` avança ~0.0028 h por segundo de relógio.
- [x] Deixar a planta estabilizar alguns minutos depois de subir.
- [x] Iniciar a gravação, num terminal na pasta `C:\Projetos	ep`:
  ```bash
  python tep-lab/local/scripts/record_run.py --interval 10 --out tep-lab/data/experiment_82/calibracao_2026-10-08.csv
  ```
  Cada leitura imprime uma linha (`t=` tempo simulado, J, fase, veredito das malhas e o PI de cada uma). Se `t=None`, o historian não está respondendo.
- [x] Deixar rodar **20–30 min de relógio**, sem ligar nenhum distúrbio.
- [x] Enquanto roda, observar no painel: o PI das malhas oscilando, a pressão como "não julgada", J em torno de ~166–169 $/h.
- [x] Parar a gravação com Ctrl+C.

### 6.5 Ler os dados e escolher os limiares (decisão sua, com o Claude)

- [x] Rodar o resumo: `python tep-lab/local/scripts/summarize_run.py tep-lab/data/experiment_82/calibracao_2026-10-08.csv`.
- [x] **`minPredictability`** por malha: ficar abaixo do menor PI visto em operação nominal (com margem), para que o normal nunca dispare. Hoje o stripper chegou a 0.096.
- [x] **`minOutputStd`**: decidir entre o σ da válvula de purga (~0.009 %) e o dos níveis (~0.3 %). Decidir também se a malha de pressão continua fora do julgamento (#86) ou sai da política.
- [x] **`maxCost`**: rever a partir da média e da dispersão de J (hoje ~166–169 $/h contra orçamento de 179).
- [x] Editar `tep-lab/local/k8s/tep/policy-mode1.yaml` com os valores e aplicar: `kubectl apply -f tep-lab/local/k8s/tep/policy-mode1.yaml`.
- [x] Conferir no painel, por alguns minutos, que a operação nominal fica estável em `Compliant` e "Malhas: saudáveis". **Conferido no início do bloco 7** (2026-10-08): `Compliant`, `LOOPS True`, "budget 170.60".

### 6.6 Fechamento (Claude)

- [x] Registrar os parâmetros escolhidos e o raciocínio em `experiment_82.md` e na #85.
- [x] Commitar o CSV da calibração em `tep-lab/data/experiment_82/` e a política atualizada.

### Decisões (preencher durante o bloco)

| Decisão | Valor escolhido | Por quê |
|---|---|---|
| Velocidade da simulação | **5** (≈ 10× o tempo real), via `control.set_speed` no UaExpert | O IDV6 (~7 h simuladas) cabe em ~40 min de relógio. A velocidade só muda a pausa entre ticks, não a física. Historian ajustado para ler a cada 100 ms e reter 900 s (tep-historian#6, tep-lab#30) |
| `windowSeconds` / `loopWindowSeconds` / `timeConstantSeconds` | **60 / 300 / 30 s** (mantidos) | Na velocidade 5 cobrem ~10 / ~50 / ~5 min de processo. J ficou estável (σ 0.18 $/h) com a janela de 60 s |
| `minPredictability` | **0.12** (0.1 → 0.12) | PI nominal dos níveis entre 0.147 e 0.40 em 41 avaliações: 0.12 fica abaixo do mínimo, com margem, para o normal nunca disparar |
| `minOutputStd` | **0.05 %** (mantido) | σ das válvulas de nível 0.28–0.34 % passa folgado; o da purga, 0.012–0.015 %, não |
| Malha de pressão: julgar ou não | **Não julgar** (continua na política, fica abaixo do portão) | A válvula de purga quase não se mexe; baixar o portão para 0.01 a faria entrar e sair do julgamento a cada flutuação. Achado registrado na #86 |
| `maxCost` | **170.6 $/h** (179 → 170.6) | É o custo do caso base de Downs & Vogel. J nominal = 166.83 ± 0.18 $/h, então J precisa subir ~2.3 % para estourar — sensível o bastante para o IDV6 |

**Gravação da calibração:** `tep-lab/data/experiment_82/calibracao_2026-10-08.csv` — `clock.t_h` 1.75 → 5.06 h (~3.3 h simuladas, 20 min de relógio), 41 avaliações, 100 % `Compliant` e `LOOPS True`.

---

## Bloco 7 — suas atividades (rodada do #82 com IDV6)

Objetivo: mostrar que o Kubernetes percebe a planta se degradando **com as regras fixas** — a política calibrada no bloco 6 não muda durante a rodada. Liga-se um distúrbio, e observa-se os dois níveis lado a lado: o econômico (J, `PolicyCompliant`) e o da qualidade das malhas (`ControlLoopsHealthy`).

Distúrbio: **IDV6**, perda total da alimentação de A (Downs & Vogel, Tabela 8). É lento e severo: no TEP original leva horas de processo para levar a planta aos limites. Por isso a rodada é longa (~1 h de relógio na velocidade 5).

Divisão: **você** opera (planta, UaExpert, gravação) e anota os marcos; **Claude** gera o gráfico e o resumo e ajuda a ler.

### 7.0 Subir e conferir (inclui a pendência do bloco 6)

- [x] F5 no tep-plant, no tep-historian e no tep-ihm (mesmas configurações do bloco 6).
- [x] No UaExpert: `control.set_speed(5.0)`. Anotar o `clock.t_h` desse momento.
- [x] Esperar ~5 min de relógio (`clock.t_h` ≈ momento do set_speed + 0.85), para a janela das malhas ficar toda na velocidade 5.
- [x] Conferir a política calibrada (pendência do bloco 6): `kubectl get plants` mostra `Compliant` e `LOOPS True`, e `kubectl describe plant tep` mostra `CostWithinBudget` com "budget 170.60".

### 7.1 Gravar e registrar o trecho nominal

- [x] Iniciar a gravação, num terminal em `C:\Projetos\tep`:
  ```bash
  python tep-lab/local/scripts/record_run.py --interval 10 --out tep-lab/data/experiment_82/idv6_2026-10-08.csv
  ```
- [x] Deixar ~5 min de relógio sem distúrbio (~0.8 h simulada) — é a referência "antes".

### 7.2 Ligar o IDV6

- [x] No UaExpert, escrever **`1`** em `disturbance.idv6`.
- [x] **Anotar o `clock.t_h` do momento** (T₀) na tabela abaixo.
- [x] Conferir que pegou: `xmeas.stream1.flow_rate` (alimentação de A) cai para ~0.

### 7.3 Observar (até o veredito virar, ou ~T₀ + 7 h)

No painel ⬡ K8S SUPERVISOR, acompanhar e anotar na tabela:

- [x] J subindo — quando passa de 170.6 (`CostWithinBudget` vira False).
- [x] Qual condition cai **primeiro**: custo, metas (`TargetsMet`) ou limites (`ConstraintsSatisfied`).
- [x] Quando `PolicyCompliant` vira False e a fase vira `NonCompliant` (depois de 3 avaliações ruins seguidas).
- [x] O que acontece com o PI das malhas de nível e com `ControlLoopsHealthy` — sai da faixa nominal (0.15–0.40)?
- [x] Se a pressão do reator passa a ser julgada (a válvula de purga começa a se mexer?).
- [x] Se `status.shutdown_detected` vira 1 no UaExpert (a planta continua rodando mesmo assim; o shutdown é só diagnóstico, #70).
- [x] Parar de observar quando o veredito tiver virado e ficado estável, ou em `clock.t_h` ≈ T₀ + 7.

### 7.4 Desligar o IDV6 e ver a recuperação

- [x] No UaExpert, escrever **`0`** em `disturbance.idv6`. **Anotar o `clock.t_h`** (T₁).
- [x] Deixar ~10 min de relógio (~1.7 h simulada) e observar se o veredito volta a `Compliant` e as malhas a saudáveis.
- [x] Parar a gravação com Ctrl+C.

### 7.5 Ler o resultado (Claude, com você)

- [x] Gráfico no tempo, com os marcos (Claude roda; de dentro de `tep-lab/analysis`):
  ```bash
  poetry run run-timeline ../data/experiment_82/idv6_2026-10-08.csv --mark T₀:"IDV6 ligado" --mark T₁:"IDV6 desligado"
  ```
- [x] Resumo: `python tep-lab/local/scripts/summarize_run.py tep-lab/data/experiment_82/idv6_2026-10-08.csv`.
- [x] Registrar como novo experimento em `experimentos.md`, atualizar `experiment_82.md` e a #82/#85; commitar CSV e PNG em `tep-lab/data/experiment_82/`.

### Anotações (preencher durante a rodada)

| Marco | `clock.t_h` | Observação |
|---|---|---|
| `control.set_speed(5.0)` | não anotado | Velocidade confirmada antes da gravação: ~9.5 s simulados por segundo |
| Início da gravação | 1.39 | `Compliant`, `LOOPS True`, budget 170.60 (pendência do bloco 6 conferida) |
| T₀ — IDV6 ligado | **2.31** | Alimentação de A cai a ~0 |
| J passa de 170.6 (`CostWithinBudget` False) | 3.46 | J 171.6 |
| Primeira condition a cair | 3.29 | qual: **`TargetsMet`** — vazão de produto 21.48 < 21.80 |
| `PolicyCompliant` False / `NonCompliant` | **3.46** | 3ª avaliação ruim seguida (persistência 3) |
| `ControlLoopsHealthy` muda? | — | **Não**: True o tempo todo; PI da pressão vai a ≈ 1.0 com offset de −131 kPa (#87) |
| `shutdown_detected` = 1? | — | Não (pressão chegou a ~2840, limite 2895; nível do reator ~90 %) |
| T₁ — IDV6 desligado | **3.84** | Alimentação de A volta a 0.25 kscmh |
| Volta a `Compliant` | — | **Não voltou**: pressão, nível e J continuaram subindo (J 218 no fim) |
| Fim da gravação | 5.00 | 44 avaliações gravadas |
