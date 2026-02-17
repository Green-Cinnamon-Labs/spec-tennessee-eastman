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

- [`fork-tennesseeEastman`](https://github.com/Green-Cinnamon-Labs/fork-tennesseeEastman)  
  Core simulation engine (Rust implementation) of the Tennessee Eastman Digital Twin.  
  Contains plant dynamics, numerical integration framework, and deterministic execution engine.

- [`lab-k8s-supervisor`](https://github.com/Green-Cinnamon-Labs/lab-k8s-supervisor)  
  Experimental supervisory control layer integrating Kubernetes control concepts with the digital twin.

- [`cluster-api-provider-plc`](https://github.com/Green-Cinnamon-Labs/cluster-api-provider-plc)  
  Custom Kubernetes controller (kubebuilder-based) implementing a reconciliation loop  
  to declaratively manage plant control state through CRDs.



---

## Document Structure

- `/premises.md` — Foundational assumptions.
- `/architecture.md` — Structural design.
- `/decisions/` — Recorded engineering decisions.
- `/numerics/` — Numerical analysis and convergence tests.
- `/validation/` — Model validation procedures.
