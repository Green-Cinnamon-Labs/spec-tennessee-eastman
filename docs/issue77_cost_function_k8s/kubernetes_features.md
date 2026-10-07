# Kubernetes features — cost function J observable by Kubernetes (Issue #77)

**Epic:** https://github.com/Green-Cinnamon-Labs/spec-tennessee-eastman/issues/77
**Sub-issues:** #78 (tep-historian), #79 (tep-operator), #80 (tep-supervisor), #81 (tep-ihm), #82 (experiment)
**Date:** 2026-10-07 (updated after merging #78–#81)

---

Everything built on the Kubernetes side for the epic, with a link to where each piece lives. Links are relative to this file and open in VS Code when the sibling repos (`tep-operator`, `tep-supervisor`, `tep-ihm`, `tep-historian`) are checked out on `main` next to `spec-tennessee-eastman` (everything below is merged). On GitHub, links into another repo don't resolve. The reasoning behind the design is in [tep-plant/docs/18-sobre-k8s-e-funcao-custo.md](../../../tep-plant/docs/18-sobre-k8s-e-funcao-custo.md).

```
tep-plant ──OPC-UA──▶ tep-historian ◀──HTTP── tep-operator (Pod in Kind) ──▶ Plant.status ──▶ kubectl / tep-ihm
```

## Status

| Issue | What                            | Merged                     | State  |
| ----- | ------------------------------- | -------------------------- | ------ |
| #78   | Historian                       | `tep-historian` main, PR #1 | Closed |
| #79   | Operator: CRDs and J evaluation | tep-operator#1             | Closed |
| #80   | TEP manifests and Kind infra    | tep-supervisor#25          | Closed |
| #81   | IHM verdict panel               | tep-ihm#2                  | Closed |
| #82   | Experiment under disturbance    | —                          | Open, not started |

The epic #77 stays open until #82 is done. #64 (operator gRPC → OPC-UA) was closed as absorbed by #79: the operator no longer talks to the plant at all. The design note [tep-plant/docs/18](../../../tep-plant/docs/18-sobre-k8s-e-funcao-custo.md) was merged with tep-plant#2.

### What's next — #82

The experiment that produces thesis evidence: switch on a disturbance (e.g. IDV6, A feed loss) and watch J rise and `PolicyCompliant` flip. Open point: IDV6 takes hours of simulated time to reach the plant's limits, and the plant runs at about 2× real time, so the run length and/or simulation speed need deciding first. Also worth recording: J at nominal operation comes out around 166 $/h against the paper's 170.6 $/h (−2.5 %), a model-validation finding related to #19.

## New object types (CRDs) — group `supervision.greenlabs.io/v1alpha1`

- **`CostFunction`** (`kubectl get cf`) — the cost function J, declared in YAML as a list of terms, each `coefficient × signal(s)`. Type: [costfunction_types.go:72](../../../tep-operator/api/v1alpha1/costfunction_types.go#L72); one term: [CostTerm, line 27](../../../tep-operator/api/v1alpha1/costfunction_types.go#L27); short name `cf`: [line 66](../../../tep-operator/api/v1alpha1/costfunction_types.go#L66).
- **`OperatingPolicy`** (`kubectl get op`) — one way of operating the plant: cost budget (`maxCost`), targets with ±% tolerance, min/max constraints, averaging window and the persistence rule. Type: [operatingpolicy_types.go:95](../../../tep-operator/api/v1alpha1/operatingpolicy_types.go#L95); fields: [OperatingPolicySpec, line 49](../../../tep-operator/api/v1alpha1/operatingpolicy_types.go#L49).
- **`Plant`** (`kubectl get plants`) — the plant, pointing at the historian and the active policy. Type: [plant_types.go:149](../../../tep-operator/api/v1alpha1/plant_types.go#L149); what the user declares: [PlantSpec, line 24](../../../tep-operator/api/v1alpha1/plant_types.go#L24).
- **The verdict** — `Plant.status`: J, the contribution of each term, the result of each target and constraint, phase `Compliant` / `NonCompliant` / `Pending`. [PlantStatus, line 107](../../../tep-operator/api/v1alpha1/plant_types.go#L107).
- **5 conditions** — `DataAvailable`, `CostWithinBudget`, `TargetsMet`, `ConstraintsSatisfied`, `PolicyCompliant`. [plant_types.go:57](../../../tep-operator/api/v1alpha1/plant_types.go#L57).
- **`kubectl get` columns** — e.g. `kubectl get plants` shows Policy, Cost, Unit, Phase. [plant_types.go:143](../../../tep-operator/api/v1alpha1/plant_types.go#L143).
- **Validation in the CRD** — e.g. a cost function needs at least one term, a term needs at least one signal. [costfunction_types.go:51](../../../tep-operator/api/v1alpha1/costfunction_types.go#L51).
- **Generated CRD YAMLs** — produced from the types by `make manifests`: [config/crd/bases/](../../../tep-operator/config/crd/bases/).
- **Generic samples** (not TEP) — [config/samples/](../../../tep-operator/config/samples/).

## The operator (controller running in Kind)

- **Generic** — no TEP knowledge in the Go code; everything plant-specific is in YAML.
- **Evaluation loop** — Plant → policy → cost function → averages from the historian → J, targets, constraints → `status`, every 30 s. [Reconcile, plant_controller.go:65](../../../tep-operator/internal/controller/plant_controller.go#L65).
- **The arithmetic** — pure functions, no Kubernetes: J, targets, constraints. [Evaluate, evaluate.go:86](../../../tep-operator/internal/evaluate/evaluate.go#L86); which signals to ask for: [RequiredSignals, line 51](../../../tep-operator/internal/evaluate/evaluate.go#L51).
- **Persistence rule** (CLPM, Bradu 2018) — the verdict only flips after N failing evaluations in a row; the counter restarts on a policy change. [NextViolations, evaluate.go:130](../../../tep-operator/internal/evaluate/evaluate.go#L130), [NonCompliant, line 142](../../../tep-operator/internal/evaluate/evaluate.go#L142).
- **No data → `Pending` with the reason** (historian unreachable, plant disconnected, missing signal, policy/cost function not found); verdict conditions become `Unknown` instead of keeping a stale value. [pending, plant_controller.go:155](../../../tep-operator/internal/controller/plant_controller.go#L155).
- **Immediate re-evaluation** when a policy or cost function is edited, and own status writes are ignored so the operator doesn't retrigger itself. [SetupWithManager, plant_controller.go:242](../../../tep-operator/internal/controller/plant_controller.go#L242).
- **Historian client** — HTTP `POST /aggregate`. [client.go:78](../../../tep-operator/internal/historian/client.go#L78).
- **Minimal RBAC** — read policies and cost functions, write the Plant status. Markers: [plant_controller.go:60](../../../tep-operator/internal/controller/plant_controller.go#L60); generated role: [config/rbac/role.yaml](../../../tep-operator/config/rbac/role.yaml).

## Tests

- **Downs & Vogel base case** — J = 170.6 $/h (Table 9). [TestDownsVogelBaseCaseCost, evaluate_test.go:84](../../../tep-operator/internal/evaluate/evaluate_test.go#L84).
- **Targets, constraints, persistence** — [evaluate_test.go:98](../../../tep-operator/internal/evaluate/evaluate_test.go#L98), [line 161](../../../tep-operator/internal/evaluate/evaluate_test.go#L161).
- **Controller against a real Kubernetes API (envtest)** — Compliant; flip after persistence; over budget; historian down; missing signal; policy not found. [plant_controller_test.go:117](../../../tep-operator/internal/controller/plant_controller_test.go#L117).
- **End to end in Kind against the real plant** — `Compliant` at J ≈ 166 $/h; lowering `maxCost` to 150 flipped to `NonCompliant` on the 3rd evaluation and back on restore. (Manual run, 2026-10-02.)

## TEP manifests — what makes the generic operator about TEP

- **Cost function** — the 12 terms of Downs & Vogel Table 9, each coefficient's derivation commented. [cost-function-downs-vogel.yaml](../../../tep-supervisor/local/k8s/tep/cost-function-downs-vogel.yaml).
- **Mode 1 policy** — product flow and G/H targets (±5 %), Table 6 constraints, budget 179 $/h, persistence 3. [policy-mode1.yaml](../../../tep-supervisor/local/k8s/tep/policy-mode1.yaml).
- **The plant** — `Plant tep`, historian at `host.docker.internal:8090`. [plant.yaml](../../../tep-supervisor/local/k8s/tep/plant.yaml).

## Cluster infrastructure (Kind)

- **The 3 CRDs** bundled for the cluster — [crd.yaml](../../../tep-supervisor/local/k8s/crd.yaml).
- **Operator Deployment, ServiceAccount, RBAC** — [operator-deployment.yaml](../../../tep-supervisor/local/k8s/operator-deployment.yaml).
- **One-command setup** — creates `tep-lab`, loads the image, installs CRDs and operator, applies the TEP manifests. [setup.sh](../../../tep-supervisor/local/setup.sh); TEP step: [line 66](../../../tep-supervisor/local/setup.sh#L66).
- **Compose for plant + historian + IHM** — [docker-compose.yml](../../../tep-supervisor/local/docker-compose.yml).
- **How to run, step by step** — [local/README.md](../../../tep-supervisor/local/README.md).

## Around Kubernetes

- **Historian** — collects every OPC-UA signal, serves window statistics: [api.py:69 (`/aggregate`)](../../../tep-historian/src/tep_historian/api.py#L69), [buffer.py:43](../../../tep-historian/src/tep_historian/buffer.py#L43), [collector.py:60](../../../tep-historian/src/tep_historian/collector.py#L60).
- **IHM reads the verdict from the Kubernetes API** (a watch on `plants`), not from the operator — [server.py:335](../../../tep-ihm/src/server.py#L335); panel: [app.js:180](../../../tep-ihm/static/dashboard/app.js#L180).

## Removed

- `PLCMachine`, the gRPC client and the `.proto` files; the Makefile `proto` target, the Codespace notes and the `plc-operator` name.

## Documentation in tep-operator

- [01 — Overview](../../../tep-operator/docs/01-visao-geral.md), [02 — Project anatomy](../../../tep-operator/docs/02-anatomia-do-projeto.md), [03 — CRDs](../../../tep-operator/docs/03-crds.md), [04 — Reconciliation](../../../tep-operator/docs/04-reconciliacao.md).
