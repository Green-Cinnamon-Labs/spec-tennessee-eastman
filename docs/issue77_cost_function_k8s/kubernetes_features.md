# Kubernetes features — cost function J observable by Kubernetes (Issue #77)

**Epic:** https://github.com/Green-Cinnamon-Labs/spec-tennessee-eastman/issues/77
**Sub-issues:** #78 (tep-historian), #79 (plant-supervisor), #80 (tep-lab), #81 (tep-ihm), #82 (experiment)
**Date:** 2026-10-07 (updated after merging #78–#81)

---

This document lists everything that was built on the Kubernetes side of the epic, explains why each piece exists, and links to where it lives. The thesis behind it is simple to state: Kubernetes should be able to follow the plant's economic state — the operating cost J from Downs & Vogel (1993) — against a policy that someone declared, and say whether the plant is complying. The reasoning that led to this design, written as a conversation, is in [tep-plant/docs/18-sobre-k8s-e-funcao-custo.md](../../../tep-plant/docs/18-sobre-k8s-e-funcao-custo.md).

**Naming:** the component that evaluates the plant was built as `tep-operator` and renamed to **`plant-supervisor`** in #83 (and the infrastructure repo `tep-supervisor` became **`tep-lab`**). Technically it is built with the Kubernetes *Operator* pattern, but in industrial automation an "operator" acts on the plant and this component never does, so this document calls it **the supervisor**.

Links are relative to this file and open in VS Code when the sibling repos (`plant-supervisor`, `tep-lab`, `tep-ihm`, `tep-historian`) are checked out on `main` next to `spec-tennessee-eastman`. On GitHub, links into another repo don't resolve.

```
tep-plant ──OPC-UA──▶ tep-historian ◀──HTTP── plant-supervisor (Pod in Kind) ──▶ Plant.status ──▶ kubectl / tep-ihm
```

Read the diagram as a chain of translations. The plant only produces raw signals; the historian turns raw signals into averages over a time window; the supervisor turns averages into a verdict ("the plant complies / does not comply"); Kubernetes stores that verdict and notifies whoever is watching (you with `kubectl`, or the IHM dashboard). Kubernetes itself never sees a raw signal.

## Kubernetes in one minute — the words used below

- **Cluster** — a running Kubernetes: a database of objects plus an API to read and change them. Here the cluster is **Kind** ("Kubernetes in Docker"), a whole cluster packed into one Docker container on your machine, named `tep-lab`.
- **Object / manifest** — everything in Kubernetes is an object described in YAML (the manifest). You `kubectl apply -f file.yaml` to create or change it, and `kubectl get` to read it back.
- **`spec` and `status`** — every object has two halves. `spec` is what *you* want (declared by a person), `status` is what is *observed* (written by a program). This split is the core of the thesis: the policy goes in `spec`, the verdict comes back in `status`.
- **CRD (Custom Resource Definition)** — Kubernetes only knows built-in object types (Pods, Deployments…). A CRD teaches it a new type, with its fields and validation. We created three: `CostFunction`, `OperatingPolicy` and `Plant`.
- **Controller** — a program running inside the cluster that watches objects and acts on them in a loop (the *reconcile* loop). When a controller manages its own custom object types for a specific domain, Kubernetes calls it an *operator* (the "Operator pattern"). Ours is **`plant-supervisor`**: it reads the policy, evaluates the plant and writes the verdict, so in the lab's vocabulary it is the supervisor.
- **Condition** — a standard way of writing facts in `status`: a type (e.g. `PolicyCompliant`), a value (`True` / `False` / `Unknown`), a reason and a message. Tools and dashboards know how to read them.
- **RBAC** — Kubernetes' permission system. A program running in the cluster can only read or write what its role allows.
- **Kubebuilder / controller-gen** — the tooling that generates the boilerplate: from Go types it produces the CRD YAMLs, the permission files and some copy code. That is why some files in `plant-supervisor` are "generated, don't edit".

## Status

| Issue | What                            | Merged                      | State             |
| ----- | ------------------------------- | --------------------------- | ----------------- |
| #78   | Historian                       | `tep-historian` main, PR #1 | Closed            |
| #79   | Supervisor: CRDs and J evaluation | plant-supervisor#1              | Closed            |
| #80   | TEP manifests and Kind infra    | tep-lab#25           | Closed            |
| #81   | IHM verdict panel               | tep-ihm#2                   | Closed            |
| #82   | Experiment under disturbance    | —                           | Open, not started |

The epic #77 stays open until #82 is done. #64 (`tep-operator` gRPC → OPC-UA) was closed as absorbed by #79: the supervisor no longer talks to the plant at all, so there was nothing left to migrate. The design note [tep-plant/docs/18](../../../tep-plant/docs/18-sobre-k8s-e-funcao-custo.md) was merged with tep-plant#2.

### What's next — #82

This is the experiment that produces evidence for the thesis: switch on a disturbance (e.g. IDV6, loss of the A feed) and watch J rise and `PolicyCompliant` flip to `False`. The open point is time: IDV6 takes hours of *simulated* time to push the plant to its limits, and the plant runs at about 2× real time, so the run length and/or simulation speed must be decided first.

Also worth recording: at nominal operation J comes out around 166 $/h, against 170.6 $/h in the paper (−2.5 %). That gap is a finding about how close the simulated plant is to the original, and it relates to #19 (validation against reference data).

## New object types (CRDs) — group `supervision.greenlabs.io/v1alpha1`

These are the three new kinds of object Kubernetes learned. They are deliberately generic: nothing in them says "TEP". The TEP-specific content goes into YAML files that use these types (see *TEP manifests* below), so the same supervisor could follow another plant with different YAML.

- **`CostFunction`** (`kubectl get cf`) — the cost function J, declared in YAML as a list of terms, each `coefficient × signal(s)` — for example "price of A × purge flow × fraction of A in the purge". It exists so the formula is *data you declare*, not code: changing a price or adding a term means editing YAML, not recompiling the supervisor. Type: [costfunction_types.go:72](../../../plant-supervisor/api/v1alpha1/costfunction_types.go#L72); one term: [CostTerm, line 27](../../../plant-supervisor/api/v1alpha1/costfunction_types.go#L27); short name `cf`: [line 66](../../../plant-supervisor/api/v1alpha1/costfunction_types.go#L66).
- **`OperatingPolicy`** (`kubectl get op`) — one way of operating the plant, the equivalent of a Downs & Vogel "mode" plus a cost budget. It holds the budget for J (`maxCost`), targets that a signal must stay close to (±%), limits a signal must stay within (min/max), the time window to average over, and the persistence rule. It is separate from the cost function because the same J can be judged by different policies — "base case", "maximum production" — and switching policy should not touch the formula. Type: [operatingpolicy_types.go:95](../../../plant-supervisor/api/v1alpha1/operatingpolicy_types.go#L95); fields: [OperatingPolicySpec, line 49](../../../plant-supervisor/api/v1alpha1/operatingpolicy_types.go#L49).
- **`Plant`** (`kubectl get plants`) — the plant as Kubernetes sees it. Its `spec` is small on purpose: where the historian is and which policy is active right now. It is the object that ties everything together, and switching the plant to another policy is just changing one field (`policyRef`). Type: [plant_types.go:149](../../../plant-supervisor/api/v1alpha1/plant_types.go#L149); what you declare: [PlantSpec, line 24](../../../plant-supervisor/api/v1alpha1/plant_types.go#L24).
- **The verdict — `Plant.status`** — what the supervisor writes back: the value of J, how much each term contributed to it, the result of each target and each limit, and an overall phase `Compliant` / `NonCompliant` / `Pending`. This is the "observed state" half of the thesis: it is stored by Kubernetes, so anyone can read it without talking to the supervisor, and it survives the supervisor restarting. [PlantStatus, line 107](../../../plant-supervisor/api/v1alpha1/plant_types.go#L107).
- **5 conditions** — `DataAvailable`, `CostWithinBudget`, `TargetsMet`, `ConstraintsSatisfied` and `PolicyCompliant`. They split the verdict into separate questions, so when the plant is non-compliant you can see *why* (over budget? a limit broken? no data?). Using the standard condition format means generic Kubernetes tools can read them too. [plant_types.go:57](../../../plant-supervisor/api/v1alpha1/plant_types.go#L57).
- **`kubectl get` columns** — `kubectl get plants` shows Policy, Cost, Unit and Phase directly in the table. Without this you would only see the name and age and would have to dump the whole YAML to find the verdict. [plant_types.go:143](../../../plant-supervisor/api/v1alpha1/plant_types.go#L143).
- **Validation in the CRD** — Kubernetes rejects malformed objects at `kubectl apply` time, e.g. a cost function with no terms or a term with no signal. Catching the mistake when you apply the YAML is much clearer than the supervisor failing later with an odd error. [costfunction_types.go:51](../../../plant-supervisor/api/v1alpha1/costfunction_types.go#L51).
- **Generated CRD YAMLs** — the actual files Kubernetes needs to learn the new types, produced from the Go types by `make manifests`. You don't edit them by hand; you change the Go type and regenerate, so code and cluster never disagree. [config/crd/bases/](../../../plant-supervisor/config/crd/bases/).
- **Generic samples** (not TEP) — a tiny made-up plant (a pump, a heater, a tank) using the three types. They exist to show the supervisor is plant-agnostic and as a minimal example of the YAML shape. [config/samples/](../../../plant-supervisor/config/samples/).

## The supervisor (controller running in Kind)

The supervisor is the program that turns the declared policy into a verdict. It runs as a Pod inside the Kind cluster, reads the three object types, asks the historian for data and writes `Plant.status`. It never writes anything to the plant: this milestone is observation only.

- **Generic** — there is no TEP knowledge in the Go code: no signal names, no prices, no limits. That knowledge lives only in the YAML, which is what lets the thesis claim "Kubernetes can follow an industrial plant", not just "this program follows the TEP".
- **Evaluation loop** — every 30 s the supervisor reads the Plant, finds its policy, finds the policy's cost function, asks the historian for the averages of the signals they need, computes J, checks targets and limits, and writes the result in `status`. This is the standard Kubernetes reconcile loop: compare what was declared with what is observed, and record the outcome. [Reconcile, plant_controller.go:65](../../../plant-supervisor/internal/controller/plant_controller.go#L65).
- **The arithmetic** — J, the targets and the limits are computed by plain functions that know nothing about Kubernetes or HTTP. Keeping the math separate means it can be tested directly against the paper's numbers, and the Kubernetes part is just plumbing around it. [Evaluate, evaluate.go:86](../../../plant-supervisor/internal/evaluate/evaluate.go#L86); which signals to ask the historian for: [RequiredSignals, line 51](../../../plant-supervisor/internal/evaluate/evaluate.go#L51).
- **Persistence rule** — the verdict only flips to `NonCompliant` after N failing evaluations in a row (3 in the TEP policy), and the counter restarts when the policy changes. The idea comes from control-loop performance monitoring (Bradu et al. 2018, cited in Cap 2): a short transient should not raise an alarm, only a sustained problem. [NextViolations, evaluate.go:130](../../../plant-supervisor/internal/evaluate/evaluate.go#L130), [NonCompliant, line 142](../../../plant-supervisor/internal/evaluate/evaluate.go#L142).
- **No data → `Pending`, with the reason** — if the historian is down, the plant is disconnected, a signal has no samples, or the policy/cost function doesn't exist, the plant goes to `Pending` and the reason is written in `DataAvailable`. The verdict conditions become `Unknown` instead of keeping the last `True`/`False`, because a stale "compliant" while blind would be a lie. [pending, plant_controller.go:155](../../../plant-supervisor/internal/controller/plant_controller.go#L155).
- **Immediate re-evaluation, without looping on itself** — when you edit a policy or a cost function (`kubectl edit` / `kubectl patch`), every Plant is re-evaluated right away instead of waiting up to 30 s. At the same time, the supervisor ignores changes to `status` only, otherwise each verdict it writes would trigger yet another evaluation forever. [SetupWithManager, plant_controller.go:242](../../../plant-supervisor/internal/controller/plant_controller.go#L242).
- **Historian client** — the supervisor gets data with one HTTP call, `POST /aggregate`, asking "average of these signals over the last N seconds". This is why the supervisor doesn't need to speak OPC-UA or know how the plant is built; any plant with a historian that answers this call could be followed. [client.go:78](../../../plant-supervisor/internal/historian/client.go#L78).
- **Minimal permissions (RBAC)** — the supervisor may read policies and cost functions and write the Plant's status, nothing else. The permissions are declared next to the code that needs them and the role file is generated from them, so they can't drift apart. Markers: [plant_controller.go:60](../../../plant-supervisor/internal/controller/plant_controller.go#L60); generated role: [config/rbac/role.yaml](../../../plant-supervisor/config/rbac/role.yaml).

## Tests

- **Downs & Vogel base case** — the test feeds the base-case values from the paper into the cost function and checks that J comes out at 170.6 $/h, the number in Table 9. It is the guarantee that the 12 terms and their unit conversions are right before any real plant is involved. [TestDownsVogelBaseCaseCost, evaluate_test.go:84](../../../plant-supervisor/internal/evaluate/evaluate_test.go#L84).
- **Targets, limits and persistence** — tests that a signal outside its tolerance or limit fails, that missing bounds are allowed, and that the persistence counter flips, resets and restarts as intended. These are the rules the verdict depends on, so they are checked in isolation. [evaluate_test.go:98](../../../plant-supervisor/internal/evaluate/evaluate_test.go#L98), [line 161](../../../plant-supervisor/internal/evaluate/evaluate_test.go#L161).
- **Controller against a real Kubernetes API (envtest)** — envtest starts a real Kubernetes API locally (without a full cluster) and the tests run the supervisor against it with a fake historian. They cover: compliant plant, flip after persistence, cost over budget, historian down, missing signal and missing policy. This checks the part the pure-math tests can't: that the right `status` and conditions actually get written. [plant_controller_test.go:117](../../../plant-supervisor/internal/controller/plant_controller_test.go#L117).
- **End to end in Kind against the real plant** — the whole chain running: plant → historian → supervisor in Kind → `kubectl get plants`. Result: `Compliant` at J ≈ 166 $/h; lowering `maxCost` to 150 flipped the verdict to `NonCompliant` on the 3rd evaluation, and restoring it brought it back. (Manual run, 2026-10-02.)

## TEP manifests — what makes the generic supervisor about TEP

Because the supervisor is generic, all of the TEP lives in these three YAML files. They are the only place where Downs & Vogel's numbers appear.

- **Cost function** — the 12 terms of Downs & Vogel's Table 9: raw material lost in the purge (7 components), raw material lost in the product (3), compressor power and steam. Each coefficient has a comment showing how it was derived (price × unit conversion), so anyone can check it against the paper. [cost-function-downs-vogel.yaml](../../../tep-lab/local/k8s/tep/cost-function-downs-vogel.yaml).
- **Mode 1 policy** — the base case: product flow and G/H composition must stay within ±5 % of the paper's values, the normal operating limits of Table 6 must hold (reactor pressure, temperature, vessel levels), J must stay under 179 $/h, and persistence is 3. The budget of 179 is a choice, about 5 % above the paper's 170.6, not a number from the paper. [policy-mode1.yaml](../../../tep-lab/local/k8s/tep/policy-mode1.yaml).
- **The plant** — the `Plant tep` object: points at the historian (`host.docker.internal:8090`, which is how a Pod inside Kind reaches your machine) and sets Mode 1 as the active policy. To try another policy, you change `policyRef` here. [plant.yaml](../../../tep-lab/local/k8s/tep/plant.yaml).

## Cluster infrastructure (Kind)

- **The 3 CRDs, bundled** — one file with the three generated CRDs, so the cluster can be taught the new types with a single `kubectl apply`. If the Go types change, this file is regenerated by copying from plant-supervisor. [crd.yaml](../../../tep-lab/local/k8s/crd.yaml).
- **Supervisor Deployment, ServiceAccount, RBAC** — what makes the supervisor run inside the cluster: the Deployment keeps one Pod alive (and recreates it if it crashes), the ServiceAccount gives it an identity, and the RBAC rules give that identity its permissions. [plant-supervisor-deployment.yaml](../../../tep-lab/local/k8s/plant-supervisor-deployment.yaml).
- **One-command setup** — `bash setup.sh` creates the `tep-lab` cluster if it doesn't exist, loads the supervisor image into it, installs the CRDs and the supervisor, and applies the TEP manifests. It exists so the whole Kubernetes side can be rebuilt from scratch in one step, e.g. after `kind delete cluster`. [setup.sh](../../../tep-lab/local/setup.sh); TEP step: [line 66](../../../tep-lab/local/setup.sh#L66).
- **Compose for plant + historian + IHM** — an alternative way to run the three non-Kubernetes pieces as containers instead of from VS Code. On Windows, running them natively (F5) is simpler, because the plant's Docker image expects a Linux binary. [docker-compose.yml](../../../tep-lab/local/docker-compose.yml).
- **How to run, step by step** — the practical guide: what to start, in which order, what to expect from `kubectl get plants`, and how to change the budget to see the verdict flip. [local/README.md](../../../tep-lab/local/README.md).

## Around Kubernetes

- **Historian** — a small Python service that reads every signal from the plant over OPC-UA, keeps the last hour in memory, and answers "average / std / min / max of these signals over the last N seconds". It is the translator between the plant's world (protocols, raw values) and Kubernetes' world (verdicts), and it knows nothing about TEP either. [api.py:69 (`/aggregate`)](../../../tep-historian/src/tep_historian/api.py#L69), [buffer.py:43](../../../tep-historian/src/tep_historian/buffer.py#L43), [collector.py:60](../../../tep-historian/src/tep_historian/collector.py#L60).
- **IHM reads the verdict from the Kubernetes API** — the dashboard's ⬡ K8S SUPERVISOR panel watches the `Plant` object directly in Kubernetes, not the supervisor. This is on purpose: Kubernetes is the single source of truth for the verdict, and the supervisor could be restarted or replaced without the dashboard noticing. [server.py:335](../../../tep-ihm/src/server.py#L335); panel: [app.js:180](../../../tep-ihm/static/dashboard/app.js#L180).

## Removed

- **`PLCMachine`, the gRPC client and the `.proto` files** — the previous design, where `tep-operator` talked to the plant over gRPC and tried to retune controllers. That gRPC server no longer exists in tep-plant (which now speaks OPC-UA), so the old design could not work anymore.
- **Leftovers of that design** — the Makefile `proto` target, the Codespace notes and the old `plc-operator` name. They were removed so nothing in the repo points to a design that is gone.

## Documentation in plant-supervisor

- [01 — Overview](../../../plant-supervisor/docs/01-visao-geral.md): what the supervisor is and where it fits. [02 — Project anatomy](../../../plant-supervisor/docs/02-anatomia-do-projeto.md): which files you edit and which are generated. [03 — CRDs](../../../plant-supervisor/docs/03-crds.md): the three types field by field, with examples. [04 — Reconciliation](../../../plant-supervisor/docs/04-reconciliacao.md): one evaluation step by step.
