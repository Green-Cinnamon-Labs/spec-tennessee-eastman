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
| [`tep-plant`](https://github.com/Green-Cinnamon-Labs/tep-plant) | Plant simulator/service in Rust (gRPC :50051 on `main`; `composite` branch, WIP, already migrated to run on top of `monjolo` and exposed via OPC-UA). Contains the process dynamics, numerical integrators, 3 embedded P-controllers, and the state snapshots. |
| [`monjolo`](https://github.com/Green-Cinnamon-Labs/monjolo) | Generic framework for dynamic system simulation (Rust), extracted from `tep-plant`. Knows nothing about TEP — provides dynamic model composition, numerical integration (RK4), reusable blocks (actuator/sensor/disturbance), and the OPC-UA adapter that `tep-plant` (`composite` branch) uses to expose the plant. |
| [`tep-ihm`](https://github.com/Green-Cinnamon-Labs/tep-ihm) | Web dashboard for the plant (HMI). Consumes the real-time gRPC XMEAS/XMV stream and exposes visualization on :8080. |
| [`tep-operator`](https://github.com/Green-Cinnamon-Labs/tep-operator) | Kubernetes operator (Go/Kubebuilder) acting as the supervisory controller. Reads XMEAS via gRPC, evaluates the policy declared in the `PLCMachine` CRD, and adjusts controllers when variables leave their range. |
| [`tep-supervisor`](https://github.com/Green-Cinnamon-Labs/tep-supervisor) | Local lab infrastructure: `docker-compose` (plant + HMI), Kind cluster (`setup.sh`), K8s manifests, and cloud configurations (AWS/Azure/GCP). |


---

## Documents in this repository

- [`CONTRIBUTING.md`](CONTRIBUTING.md) — Main guide to the lab's architecture and development decisions, in numbered articles (pattern described in `docs/padrao_documentacao.md`). Mandatory entry point before touching `tep-plant`/`monjolo`.
- [`experimentos.md`](experimentos.md) — Scientific log of experiments on the integrated system (plant + supervisor). Most recent entries on top.
- Open tasks and pending items are tracked via this repository's GitHub Issues (not a `tarefas.md` file — discontinued), following the rectification flow described in `docs/ai/ISSUE_PROTOCOL.md`.
