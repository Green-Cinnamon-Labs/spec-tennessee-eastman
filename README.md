# Tennessee Eastman Digital Twin — Specification

This repository defines the architectural, numerical, and structural  
specifications of the Tennessee Eastman Digital Twin project.

It serves as the authoritative source of engineering decisions,  
design principles, and system evolution.

---

## Objective

Build a deterministic, extensible, and physically grounded  
digital twin of the Tennessee Eastman process,  
capable of long-horizon simulation and future supervisory control integration.

---

## Core Principles

- Separation of model and integration.
- Deterministic time architecture.
- Explicit physical accumulation modeling.
- Actuator-mediated control inputs.
- Numerical invariance across simulation horizon.

---

## Related Repositories

- `te-engine` — Core simulation engine (Rust implementation).
- `te-supervisor` — Kubernetes-based supervisory control layer.
- `te-experiments` — Numerical and control experiments (future).

---

## Document Structure

- `/premises.md` — Foundational assumptions.
- `/architecture.md` — Structural design.
- `/decisions/` — Recorded engineering decisions.
- `/numerics/` — Numerical analysis and convergence tests.
- `/validation/` — Model validation procedures.
