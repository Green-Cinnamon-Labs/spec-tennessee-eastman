# The TEP plant object — `plant.yaml` explained (Issue #77)

**File:** [tep-lab/local/k8s/tep/plant.yaml](../../../tep-lab/local/k8s/tep/plant.yaml)
**Type:** [Plant, plant_types.go:149](../../../plant-supervisor/api/v1alpha1/plant_types.go#L149)
**Date:** 2026-10-07

---

This file creates the `Plant tep` object: the TEP plant as Kubernetes sees it. It is the smallest of the three TEP manifests, but it is the one that makes everything happen. The cost function ([cost_function_downs_vogel.md](cost_function_downs_vogel.md)) says *how to measure* the cost, the policy ([operating_policy_mode1.md](operating_policy_mode1.md)) says *what operating well means*; `plant.yaml` says *which plant, measured where, judged by which policy right now*.

```yaml
apiVersion: supervision.greenlabs.io/v1alpha1
kind: Plant
metadata:
  name: tep
spec:
  historianURL: "http://host.docker.internal:8090"
  policyRef: tep-mode1
  evaluationIntervalSeconds: 30
```

## Why this object exists

The supervisor works **per Plant**. Applying a cost function and a policy alone does nothing: they are definitions that sit in the cluster until a `Plant` points to them. Each `Plant` object is one plant being supervised, and the supervisor runs one evaluation loop for each. With a second plant, you would create a second `Plant` with its own historian and its own policy, and the same supervisor would follow both.

The `Plant` is also where the **verdict lives**. Like every Kubernetes object it has two halves: the `spec`, which you write (the three fields above), and the `status`, which only the supervisor writes (J, targets, limits, `Compliant` / `NonCompliant`). That split is the core of the thesis: what you declare goes in, what is observed comes back, in the same object.

## Field by field

### `metadata.name: tep` — [line 8](../../../tep-lab/local/k8s/tep/plant.yaml#L8)

The object's name. It is how you refer to the plant everywhere else: `kubectl get plant tep`, `kubectl describe plant tep`, and the IHM, which watches the Plant named by its `K8S_CR_NAME` setting (default `tep`). If you rename it, the IHM must be told the new name.

### `historianURL: "http://host.docker.internal:8090"` — [line 10](../../../tep-lab/local/k8s/tep/plant.yaml#L10)

Where the supervisor gets data from. The supervisor never talks to the plant itself; it asks the historian "give me the average of these signals over the last N seconds" with `POST /aggregate`. This field is that historian's address.

`host.docker.internal` is a special name Docker provides so that a container (here, the supervisor's Pod inside Kind) can reach services running on your own machine, where the historian runs (from VS Code or docker compose) on port 8090. If the historian were deployed inside the cluster instead, this would become a cluster address such as `http://tep-historian:8090`.

If the historian can't be reached, or answers but isn't connected to the plant, the plant goes to `Pending` with the reason `HistorianUnreachable` or `PlantDisconnected`. The supervisor gives the historian 5 seconds to answer, so a slow historian shows up as `Pending` instead of freezing the supervisor ([client.go:69](../../../plant-supervisor/internal/historian/client.go#L69)).

### `policyRef: tep-mode1` — [line 11](../../../tep-lab/local/k8s/tep/plant.yaml#L11)

Which `OperatingPolicy` is active right now, by name. From it the supervisor follows the chain **Plant → OperatingPolicy → CostFunction**: the policy names its cost function (`tep-downs-vogel`), so the Plant doesn't need to.

This field is the **switch between operating modes**. To run the plant under a different policy, create another `OperatingPolicy` and change this one field (`kubectl edit plant tep`). The supervisor re-evaluates immediately, and the violation counter restarts, because failures under the old policy say nothing about the new one. If the name doesn't exist, the plant goes to `Pending` with the reason `PolicyNotFound`.

### `evaluationIntervalSeconds: 30` — [line 12](../../../tep-lab/local/k8s/tep/plant.yaml#L12)

How often the supervisor re-evaluates the plant. Every 30 s it fetches fresh averages and writes a new verdict. If omitted, the default is 30 s ([plant_controller.go:73](../../../plant-supervisor/internal/controller/plant_controller.go#L73)).

This interval works together with two fields of the policy:

- **`windowSeconds`** (60 s in Mode 1) — each evaluation looks at the last 60 s of data. With a 30 s interval, consecutive evaluations overlap by half: they are sliding windows, not separate blocks.
- **`persistenceEvaluations`** (3 in Mode 1) — the plant is declared `NonCompliant` only after 3 failing evaluations in a row, so a problem has to last about 3 × 30 s = 90 s.

A shorter interval makes the verdict react faster but writes to Kubernetes more often; a longer one is calmer but slower. Note that the persistence time scales with it: at 60 s, 3 evaluations would mean 3 minutes.

## What the supervisor writes back — the `status`

You never write the `status`; the supervisor fills it on every evaluation. This is what `kubectl get plant tep -o yaml` shows, and what the IHM's K8S SUPERVISOR panel displays ([PlantStatus, plant_types.go:107](../../../plant-supervisor/api/v1alpha1/plant_types.go#L107)):

| Field | What it holds | In the IHM panel |
|---|---|---|
| `phase` | `Compliant`, `NonCompliant` or `Pending` | Phase |
| `activePolicy` | The policy this verdict refers to | Política |
| `cost` | J, its unit, the cost function's reference and the policy's budget | Custo J |
| `terms` | How much each of the 12 terms contributed to J | — |
| `targets` | For each target: the observed average and whether it was met | Metas e restrições (meta) |
| `constraints` | For each limit: the observed average and whether it held | Metas e restrições (restrição) |
| `consecutiveViolations` | Failing evaluations in a row so far | Violações |
| `lastEvaluationTime` | When the last evaluation ran | Avaliação |
| `conditions` | `DataAvailable`, `CostWithinBudget`, `TargetsMet`, `ConstraintsSatisfied`, `PolicyCompliant`, each with a reason and message | Motivo |

The three phases mean:

- **`Compliant`** — every check passes, or checks are failing but fewer than `persistenceEvaluations` times in a row.
- **`NonCompliant`** — checks failed `persistenceEvaluations` times in a row.
- **`Pending`** — no verdict is possible: the policy or cost function doesn't exist, the historian is unreachable, the plant is disconnected, or a signal has no samples. The verdict conditions become `Unknown` rather than keeping a stale `True`/`False`, and `DataAvailable` says why.

Because the verdict is stored by Kubernetes, anyone can read it without talking to the supervisor, and it survives the supervisor restarting.

## How to use it

```bash
kubectl apply -f tep-lab/local/k8s/tep/plant.yaml   # create or update the Plant
kubectl get plants                                         # one line: policy, J, unit, phase
kubectl describe plant tep                                 # conditions with reason and message
kubectl get plant tep -o yaml                              # the whole status, including each term of J
kubectl edit plant tep                                     # change policyRef, interval or historian
```

`setup.sh` applies this file together with the cost function and the policy ([setup.sh:66](../../../tep-lab/local/setup.sh#L66)), so after a fresh setup the Plant already exists. The order of applying the three files doesn't matter: if the Plant arrives before its policy, it stays `Pending` (`PolicyNotFound`) and becomes `Compliant` or `NonCompliant` as soon as the policy appears.
