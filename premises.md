# Tennessee Eastman Digital Twin — Technical Premises

---

## 1. Nature of the Model

- The plant is described by a system of nonlinear ODEs: ẋ = f(x, u).
- No closed-form analytical solution exists; numerical integration is mandatory.
- The physical model follows the original Tennessee Eastman formulation
  (mass balances, energy balances, Arrhenius kinetics, VLE).
- No distributed spatial dynamics are introduced at this stage.

---

## 2. Mandatory Conceptual Separation

- Mathematical model ≠ Integrator
- Plant dynamics ≠ Execution architecture
- Physical states ≠ Signals (XMEAS/XMV)
- Physical fidelity ≠ Numerical method

Architecture must prevent coupling between physics and discretization.

---

## 3. Platform Objectives

- Deterministic digital twin.
- Long-horizon continuous execution.
- Numerical invariance across simulation time.
- Prepared for hardware-in-the-loop.
- Prepared for external controllers.
- Evolutive: benchmark → robust infrastructure.

---

## 4. Simulation Time Architecture

- Architectural discrete time.
- Fixed Δt.
- Engine governs time.
- Integrator does not govern time.
- Determinism is an explicit requirement.

---

## 5. Integration Strategy

- Explicit Euler is abandoned.
- RK4 with fixed Δt is the initial integration method.
- Integrator must be pluggable via abstraction.
- Δt must be configurable.
- Step-convergence testing is mandatory.

---

## 6. Numerical Requirements

- Sensitivity to Δt must be measurable.
- Mass/energy drift must be monitored.
- Dynamic responses must converge under step refinement.
- System behavior must be property of the model, not the solver.

---

## 7. Execution Architecture

Deterministic loop:

1. Read actuators
2. Integrate Δt (RK4)
3. Update states
4. Update sensors
5. Publish signal bus
6. Advance clock

---

## 8. Formal Definition of State

The project must explicitly define:

- Physical state variables
- Algebraic variables
- Signals
- Parameters

State representation must be:

- Structurally defined
- Deterministically flattened
- Explicitly mapped to internal vector layout

---

## 9. Structural Conservation Principles

The model must explicitly respect:

- Conservation of mass
- Conservation of energy

Numerical integration must not silently violate structural balances.

---

## 10. Determinism Requirements

- Execution must be reproducible.
- Evaluation order must be fixed.
- No parallelism that alters numerical outcome.
- Identical initial state must produce identical trajectory.

---

## 11. Validation and Acceptance Criteria

The system must support:

- Validation against reference article responses.
- Validation against steady-state balances.
- Step convergence testing as acceptance requirement.
- Explicit numerical comparison across integrators.

Without measurable validation, there is no engineering — only intention.
