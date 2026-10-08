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

- [ ] Confirmar que o Claude parou a planta e o historian que estavam rodando em background (as portas 4840, 8090 e 8080 precisam estar livres).
- [ ] Confirmar que o Kind está de pé: `kubectl get pods` mostra `plant-supervisor-...` em `Running`.

### 6.1 Ferramentas (Claude prepara, você revisa)

- [ ] Ler o script de gravação [`tep-lab/local/scripts/record_run.py`](../../../tep-lab/local/scripts/record_run.py): a cada N segundos grava numa linha de CSV o tempo simulado (`clock.t_h`), J, a fase, as conditions e, por malha, PI, offset, σ da válvula e se foi julgada.
- [ ] Ler o script de resumo [`tep-lab/local/scripts/summarize_run.py`](../../../tep-lab/local/scripts/summarize_run.py): lê o CSV e mostra, por malha, a distribuição do PI e do σ da válvula, e a média e a dispersão de J.

### 6.2 Subir tudo (você)

- [ ] F5 no tep-plant: **"tep-plant (com adaptador OPC-UA)"**.
- [ ] F5 no tep-historian: **"Historian: planta local (OPC-UA)"**. Conferir `http://localhost:8090/healthz` → `"connected": true`.
- [ ] F5 no tep-ihm: **"IHM: planta local (plant OPC-UA + k8s)"**. Abrir `http://localhost:8080` e o painel ⬡ K8S SUPERVISOR.
- [ ] Conferir: `kubectl get plants` mostra a coluna `LOOPS`, e o painel mostra a linha "Malhas" e a tabela das 3 malhas.

### 6.3 Escolher a velocidade da simulação (decisão sua)

As janelas do historian são em **tempo de relógio**, mas a planta roda mais rápido que o tempo real. Na velocidade atual (~2×), a janela de 300 s das malhas cobre ~10 min simulados; a 10×, cobriria ~50 min. A constante de tempo `T` das malhas (30 s) também é de relógio, então muda de significado com a velocidade.

- [ ] Decidir a velocidade (botões 1× / 2× / 5× / 10× / Max da IHM) — **a mesma** que será usada no experimento #82.
- [ ] Decidir se `loopWindowSeconds`, `timeConstantSeconds` e `windowSeconds` mudam para essa velocidade.
- [ ] Registrar a decisão e o porquê (abaixo, em "Decisões").

### 6.4 Rodada de calibração (você roda, observamos juntos)

- [ ] Ajustar a velocidade escolhida na IHM.
- [ ] Deixar a planta estabilizar alguns minutos depois de subir.
- [ ] Iniciar a gravação, num terminal na pasta `C:\Projetos	ep`:
  ```bash
  python tep-lab/local/scripts/record_run.py --interval 10 --out tep-lab/data/experiment_82/calibracao_2026-10-08.csv
  ```
  Cada leitura imprime uma linha (`t=` tempo simulado, J, fase, veredito das malhas e o PI de cada uma). Se `t=None`, o historian não está respondendo.
- [ ] Deixar rodar **20–30 min de relógio**, sem ligar nenhum distúrbio.
- [ ] Enquanto roda, observar no painel: o PI das malhas oscilando, a pressão como "não julgada", J em torno de ~166–169 $/h.
- [ ] Parar a gravação com Ctrl+C.

### 6.5 Ler os dados e escolher os limiares (decisão sua, com o Claude)

- [ ] Rodar o resumo: `python tep-lab/local/scripts/summarize_run.py tep-lab/data/experiment_82/calibracao_2026-10-08.csv`.
- [ ] **`minPredictability`** por malha: ficar abaixo do menor PI visto em operação nominal (com margem), para que o normal nunca dispare. Hoje o stripper chegou a 0.096.
- [ ] **`minOutputStd`**: decidir entre o σ da válvula de purga (~0.009 %) e o dos níveis (~0.3 %). Decidir também se a malha de pressão continua fora do julgamento (#86) ou sai da política.
- [ ] **`maxCost`**: rever a partir da média e da dispersão de J (hoje ~166–169 $/h contra orçamento de 179).
- [ ] Editar `tep-lab/local/k8s/tep/policy-mode1.yaml` com os valores e aplicar: `kubectl apply -f tep-lab/local/k8s/tep/policy-mode1.yaml`.
- [ ] Conferir no painel, por alguns minutos, que a operação nominal fica estável em `Compliant` e "Malhas: saudáveis".

### 6.6 Fechamento (Claude)

- [ ] Registrar os parâmetros escolhidos e o raciocínio em `experiment_82.md` e na #85.
- [ ] Commitar o CSV da calibração em `tep-lab/data/experiment_82/` e a política atualizada.

### Decisões (preencher durante o bloco)

| Decisão | Valor escolhido | Por quê |
|---|---|---|
| Velocidade da simulação | | |
| `windowSeconds` / `loopWindowSeconds` / `timeConstantSeconds` | | |
| `minPredictability` (por malha) | | |
| `minOutputStd` | | |
| Malha de pressão: julgar ou não | | |
| `maxCost` | | |
