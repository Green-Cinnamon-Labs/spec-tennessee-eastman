# Tennessee Eastman Digital Twin — Architecture

---

## 1. Architectural Layers

The system is structured in strictly separated layers:

1. Physical Model Layer
2. Numerical Integration Layer
3. Execution Engine Layer
4. Signal & Actuation Layer
5. Supervisory Layer (future)

Each layer has explicit responsibilities and must not leak abstractions.

---

## 2. Physical Model Layer

Defines:

- State variables
- Parameters
- Balance equations
- dx/dt computation

Interface concept:

DynamicModel:
    derivatives(state, inputs, params) -> dx/dt

Rules:

- Must be independent of integration strategy.
- Must not depend on execution timing logic.
- Must represent only physical behavior.

---

## 3. Numerical Integration Layer

Responsible for:

- Advancing state by Δt.
- Calling model derivatives.
- Applying integration scheme (e.g., RK4).

Interface concept:

Integrator:
    step(model, state, inputs, params, dt) -> new_state

Rules:

- Must not embed plant logic.
- Must not control simulation time.
- Must operate purely on state and model interface.

---

## 4. Execution Engine Layer

Responsible for:

- Governing simulation time.
- Orchestrating loop order.
- Maintaining deterministic execution.
- Coordinating signals and actuators.

Deterministic Loop:

1. Read actuators
2. Integrate Δt
3. Update state
4. Update sensors
5. Publish signal bus
6. Advance clock

Rules:

- Time is engine-driven.
- Δt is fixed.
- Execution order is explicit.

---

## 5. Signal & Actuation Layer

Defines mediation between controller and plant:

Controller → Control Signal → Actuator → Applied Input → Plant

Responsibilities:

- Transform control signals into physical inputs.
- Optionally model actuator dynamics.
- Maintain separation between hardware behavior and plant physics.

---

## 6. State Representation

State must be:

- Structurally defined.
- Deterministically flattened.
- Explicitly mapped.
- Validated at initialization.

State layout must never be implicit.

---

## 7. Determinism Constraints

- No solver-driven adaptive time.
- No hidden randomness.
- No non-deterministic iteration order.
- No parallel reduction altering floating-point order.

Reproducibility is mandatory.

---

## 8. Extension Strategy

Future extensions must:

- Respect layer separation.
- Preserve deterministic execution.
- Not introduce hidden coupling.
- Maintain validation guarantees.

Architecture evolves, but invariants remain.
