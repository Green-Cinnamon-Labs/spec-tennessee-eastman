# Tennessee Eastman Digital Twin — Specification

This repository is the lab's entry point. It contains no code —
it holds the experiment log, the architecture decisions, and the
tracking of open tasks that span the other repositories.

**Note:** this repository's own documentation (`docs/`, `experimentos.md`) is still written in Portuguese; only the root `README.md`/`CONTRIBUTING.md` files across the lab's repos have been translated so far. English is the project's official language going forward.

---

## Objective

Build a deterministic, extensible digital twin of the Tennessee Eastman process,
capable of long-horizon simulation with supervisory control integrated via Kubernetes.

---

## Lab Repositories

| Repository | Role |
|---|---|
| [`tep-plant`](https://github.com/Green-Cinnamon-Labs/tep-plant) | Plant simulator in Rust, running on top of `monjolo` and exposed via **OPC-UA** (`opc.tcp://0.0.0.0:4840/tep/server/`). The `composite` branch was merged into `main` on 2026-07-17 — there is no gRPC server in this repo anymore, and no supervisory Controller/`ControllerBank` layer either (see Status in `tep-plant`'s own README). Contains the process dynamics, numerical integrators, and the state snapshots. |
| [`monjolo`](https://github.com/Green-Cinnamon-Labs/monjolo) | Generic framework for dynamic system simulation (Rust), extracted from `tep-plant`. Knows nothing about TEP — provides dynamic model composition, numerical integration (RK4), reusable blocks (actuator/sensor/disturbance), and the OPC-UA adapter that `tep-plant` uses to expose the plant. |
| [`tep-ihm`](https://github.com/Green-Cinnamon-Labs/tep-ihm) | Web dashboard for the plant (HMI). Still built against the old **gRPC** XMEAS/XMV stream (:8080) — ⚠️ incompatible with `tep-plant`'s current `main`, which no longer serves gRPC. Migration to OPC-UA is issue [#55](https://github.com/Green-Cinnamon-Labs/spec-tennessee-eastman/issues/55)'s unchecked "tep-ihm integration" item. |
| [`tep-operator`](https://github.com/Green-Cinnamon-Labs/tep-operator) | Kubernetes operator (Go/Kubebuilder) acting as the supervisory controller. Still built against the old **gRPC** interface to read XMEAS and adjust controllers — ⚠️ same incompatibility as `tep-ihm` above, and there is no controller layer left in `tep-plant` to adjust either way. Migration is issue [#55](https://github.com/Green-Cinnamon-Labs/spec-tennessee-eastman/issues/55)'s unchecked "tep-operator integration" item. |
| [`tep-supervisor`](https://github.com/Green-Cinnamon-Labs/tep-supervisor) | Local lab infrastructure: `docker-compose` (plant + HMI), Kind cluster (`setup.sh`), K8s manifests, and cloud configurations (AWS/Azure/GCP). |


---

## Documents in this repository

- [`CONTRIBUTING.md`](CONTRIBUTING.md) — Main guide to the lab's architecture and development decisions, in numbered articles (pattern described in `docs/padrao_documentacao.md`). Mandatory entry point before touching `tep-plant`/`monjolo`.
- [`experimentos.md`](experimentos.md) — Scientific log of experiments on the integrated system (plant + supervisor). Most recent entries on top.
- Open tasks and pending items are tracked via this repository's GitHub Issues (not a `tarefas.md` file — discontinued), following the rectification flow described in `docs/ai/ISSUE_PROTOCOL.md`.
