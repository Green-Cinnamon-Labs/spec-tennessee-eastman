# CONTRIBUTING — Architecture and development definitions

This is the lab's main guide to architecture and development decisions — the mandatory entry point for anyone about to touch the technical repositories (`tep-plant`, `monjolo`, and eventually `tep-ihm`/`tep-operator` once they migrate to OPC-UA). It records, in numbered articles, the decisions currently in force for the `tep-plant`/`monjolo` modeling. It follows the structure defined in `docs/padrao_documentacao.md` — read that first if the notation (Art./§/Item) isn't familiar. That document itself is still in Portuguese.

It started out as the plan for the Composite + semantic Registry refactor (issue #55), but it stopped being a document specific to that issue: it now covers the lab's architecture as a whole, and keeps receiving new/amended articles as the architecture evolves. `docs/issue55_opcua_refactor/eval_refactor.md` keeps the evaluation/history that led here.

**Methodological note on this document's origin (not normative content):** the article numbering inherited from the earlier, unnumbered version (`plan_refactor.md`, today referenced only by historical docs in `docs/issue55_opcua_refactor/`) was preserved wherever possible — old cross-references (`section X.Y`) still match `Art. X.Y` here. Using `git blame` on the original file, two cases were separated, both sharing the same look (`~~text~~ **Note:**`): (a) pairs where the struck-through text and the correction were written on the same day — not a real change, just the author documenting "considered X, decided Y" in a single act of writing; these became direct article bodies, with no strike-through/date apparatus. (b) pairs with a real time gap between the struck-through text and the correction — these keep the strike-through (Art. 4) or became a repeal (Art. 2), with a date. Missing article numbers (Art. 6.5, 10.5, 10.7, 11.7, and the old chapter 12) were not deleted by mistake — the content that occupied those addresses was a pending item mis-filed as its own article; it was reclassified as a paragraph of the article it actually qualifies (the index below points to where).

## Index

```
StateRegistry        → Art. 1.3, 3.6, 6, 6.1–6.4
Snapshot              → Art. 11.9
CurrentState          → Art. 1.3, 3.6, 3.6.2
EvaluationState       → Art. 1.2, 1.3, 8, 8.1–8.4
Proxy                 → Art. 1.1, 7, 7.1, 7.2
ReadProxy             → Art. 3.6.2, 3.6.4
DynamicModel          → Art. 1 (chapter), 1.1, 2.1, 2.2
CompositeDynamicModel → Art. 2, 2.1, 2.3, 2.3.1
add_dynamic           → Art. 2.3, 2.3.1, 2.6
Sensor                → Art. 3.3, 3.5, 3.5.1, 3.6–3.9
SensorBehavior        → Art. 3.6.1
IoImage               → Art. 10, 10.1–10.4
CommandSink           → Art. 10.4
CommandQueue          → Art. 10.6.2, 11.4
SnapshotBus (repealed 2026-07-15) → Art. 11.4
Simulation            → Art. 9, 9.1–9.9, 11, 11.1–11.10
AdapterConfig         → Art. 11.10
NumericalMethod/RK4   → Art. 9.9, 11.10
OPC-UA Adapter        → Art. 10.6, 10.6.1–10.6.4
Flows/Heat/Measurements → Art. 2.6, §1
Controller            → Art. 3.5, 3.5.1 §2, 10.4 §1
DAG/DAE               → Art. 4, 4.1–4.5
StateSlot             → Art. 3.6.5, 5, 5.1–5.4
tep-plant (binary)    → Art. 10.6.1, 11.6, 11.9
```

## Integration Contract (Integrator ↔ DynamicModel)

**Art. 1.1.** The relationship between the `Integrator` (RK4) and a `DynamicModel` has exactly one real phase: `evaluate()`, the integration loop. There is no construction phase via `get_state_template()`/`StateTemplate` — it was replaced by each `DynamicModel` subscribing directly to the `StateRegistry` (`subscribe()`, Art. 6.2), which returns `Proxy`s (Art. 7). There is no `set_state()` as a `DynamicModel` method — persistence is done by `StateRegistry.set_current_state()` (Art. 1.3).

**Art. 1.1.1.** The RK4 never assumes anything about the model beyond the contract in Art. 1.1: it doesn't know how many states exist, doesn't know how derivatives are computed internally, doesn't know how the new state is persisted — that's the `DynamicModel`'s exclusive responsibility.

**Art. 1.2.** `evaluate()` does not mutate the `self` of the component running it. With `EvaluationState` (Art. 8), `evaluate()` has a mutation effect on an external buffer — it writes its outputs (values and derivatives) via `Proxy`, using interior mutability (`Cell`). What gets mutated is the shared `EvaluationState` (Art. 8.2), never the component's `self`.

§1 This design eliminates a bug present in the code before this refactor, where `dynamics()` mutated fields like `self.mole_fractions`/`self.stream_temperatures` as a side effect, even though it was called 4 times per RK4 step (k1..k4) — intermediate states silently went out of sync.

**Art. 1.3.** `StateRegistry` holds two internal stores: **`CurrentState`** (the official slots, the persisted/confirmed state) and **`EvaluationState`** (the working buffer for one evaluation round, Art. 8, where the `DynamicModel`s' `evaluate()` calls write via `Proxy`). `set_current_state()` is the procedure — implemented in `StateRegistry`, never per-component in `DynamicModel` — that loads `EvaluationState` → `CurrentState`, closing the evolution loop; `Simulation` (Art. 9) is the one that calls this after `step()` (Art. 9.8).

§1 (2026-07-15) `CurrentState` explicitly takes on the role of **the plant's last confirmed physical state** — not just an internal store, but the read boundary for everything outside the plant thread (the OPC-UA Adapter thread, a future Controller). `EvaluationState` remains thread-local, without exception — it is never read from outside. See Art. 3.6.2 (internal type) and Art. 3.6.6 (what this implies for `Sensor`).

## Composition Contract (DynamicModel ↔ DynamicModel)

**Art. 2.1.** `trait CompositeDynamicModel: DynamicModel` — Rust has no class inheritance, only trait inheritance (supertrait). Implementing `CompositeDynamicModel` also requires implementing `DynamicModel`.

**Art. 2.2.** Only composite nodes implement `CompositeDynamicModel`. Leaf components (`Valve`, `Agitator`, and eventually Reactor/Separator/Stripper/Compressor, if they ever become true leaves) do not implement this trait — trying to compose them becomes a compile-time error, not a runtime one.

**Art. 2.3.** `add_dynamic` is a `CompositeDynamicModel` method that adds the `DynamicModel` being registered to the composite's evaluation sequence, in the order it was inserted — it declares no slots and merges no template. Slots are declared by each `DynamicModel`'s direct subscription to the `StateRegistry` (Art. 6).

**Art. 2.3.1.** Default body of `add_dynamic`: `self.models_mut().push(component)` — just the `models_mut()` getter over its own `Vec<Box<dyn DynamicModel>>` (the `models` field, Art. 2.5).

**Art. 2.4.** Delegating evaluation to each child — calling each one's `evaluate()`, in the order `add_dynamic` (Art. 2.3) registered them — is the only part each composite writes from scratch. This only works because the TEP is a DAG (Art. 4.1): a single pass, in fixed insertion order, resolves the composite because there is no algebraic cycle between the components.

§1 For a DAE case (Art. 4.3, strong algebraic coupling), a single pass doesn't close — an object analogous to the `Integrator`, but for the algebraic dimension (an "`Interator`"), would be needed, running the cyclic subset via Newton/tearing (Art. 4.4) until convergence. It doesn't exist and isn't needed for the current TEP — a registered future extension, not an immediate implementation pending item.

**Art. 2.5.** There is no reusable generic `Composite` implementation. A generic `struct Composite` (`children`/`sizes`) was considered and rejected: in the whole system there is only **one** actual composite node — `TennesseeEastmanModel`. `TennesseeEastmanModel` implements `DynamicModel` + `CompositeDynamicModel` directly, owning its own `Vec<Box<dyn DynamicModel>>` (the `models` field).

**Art. 2.6.** The TEP constructor (`TennesseeEastmanModel::new()`) contains no composition logic of its own — just a sequence of `add_dynamic` (Art. 2.3) calls registering each component, in the order they must be evaluated. Today: `Reactor`, `Separator`, `Stripper`, `Compressor` — all consuming their initial condition via `Snapshot` (Art. 11.9).

§1 (open item, identified on 2026-07-12) `Flows`, `Heat`, and `Measurements` — the three subsystems that would close the calculation (Blocks 19-36 of `teprob.f`) — exist only as empty `struct`s with `evaluate() { todo!() }` (`tep-plant/src/subsystems/{flows,heat,measurements}.rs`) and are not `add_dynamic`'d here: they are not just "unimplemented," they are dead code, never instantiated even in the `tep-plant` binary. The original physics is preserved, commented out, in `tep-plant/docs/_deprecated_2.rs`: `TepFlows` (Blocks 19-31), `TepHeat` (Blocks 32-34), `TepMeasurements` (Blocks 35-36).

Item I — Consequence: `Flows` is the one that would compute the actual derivative (`yp`) of the `own_state` for Reactor/Separator/Stripper/Compressor. Without it, none of the four offers the companion `.derivative` key, and `TennesseeEastmanModel` does not override `state_keys()` (Art. 9.9, it stays at the empty default) — the Integrator (Art. 9) has nothing to integrate for the chemical core, and `own_state` stays frozen at the value seeded by `Snapshot` (Art. 11.9). `evaluate()` only recomputes derived thermodynamic quantities (temperature, pressure, composition) on top of that stalled state. The integration machinery itself works and is tested (`Valve`/`Agitator` already use it correctly).

Item II — Porting requires deciding each one's `needs` against the current `StateRegistry` (`Flows` needs all four chemical subsystems + valve positions + disturbance flags at once) and rewriting the logic on top of `Proxy`/`ReadProxy` (Art. 7), not positional `&[f64]`.

Item III — Dependency order: `Flows` (depends only on the 4 chemical subsystems) → `Heat` (depends on Reactor+Stripper+Flows) → `Measurements` (depends on all of them+Flows+Heat). Wiring up an actuator (Art. 11.2, §1) only produces a real effect on the plant once `Flows` exists.

**Art. 2.7.** `get_state_template()`/`StateTemplate` do not exist — they were replaced by subscription (Art. 6.2). A `DynamicModel` subscribes to the `StateRegistry`, gets `Proxy`s back, and operates with them. `DynamicModel`'s real methods are `evaluate()` and `subscribe()` (the special subscription method, Art. 6.2.1).

## Relationship with the outside world (Outside ↔ DynamicModel)

**Art. 3.1.** Name of the relationship: `AcquisitionLayer`. Considered and rejected before: "Process Image" (automation/PLC connotation, deemed confusing).

**Art. 3.2.** Role of the `AcquisitionLayer`: querying, not evaluation. Something external (e.g. 4-20mA, Modbus, OPC-UA adapters) queries the parent `DynamicModel` to obtain the raw state and transforms it for a specific protocol — pure reading, after the model has already resolved everything, without taking part in `evaluate()`.

**Art. 3.3.** `Sensor` is not a `DynamicModel` in the composition tree — it stays outside `add_dynamic` (Art. 2.3) because it does not take part in evaluation: it only reads the state after it has been resolved.

**Art. 3.4.** `Disturbance` is not a `DynamicModel` in the composition tree — it doesn't belong to a single component, it cuts across several at once (reaction in the Reactor, condenser UA and flow in Flows, exchange coefficients in Heat). Treated as an injected input, associated with each component that consumes it.

**Art. 3.5.** There are exactly three objects that give the simulated physics any interaction with the outside world: **Sensor** (exposes an observed value), **Actuator** (allows action on the plant), and **Controller** (allows closing a control loop over the plant). Outside these three, there is no other entry/exit door between the simulated dynamics and the outside world.

**Art. 3.5.1.** The detailed design of Actuator and Controller (Art. 3.5) was handled after Sensor's. Art. 3.6 through 3.9 specify only `Sensor`.

§1 Actuator got a concrete design: `CommandSink` (Art. 10.4), channel (Art. 11.4) — no longer a pending item.

§2 (open item) Controller is not yet modeled. Design already anticipated: reads via `IoImage.read()` (Art. 10.3), writes via `IoImage.write()` (Art. 10.4) — without requiring any shape change in `IoImage`. Not implemented because there is no Controller yet to test it against.

**Art. 3.6.** `Sensor` has no relationship with `evaluate()`/`EvaluationState` (Art. 8) — those are written to by the `DynamicModel`s resolving their own physics, at each RK4 sub-step. `Sensor` reads from `StateRegistry.CurrentState` (Art. 1.3): the already-committed store, after `set_current_state()` has closed the step. `Sensor` is never a participant in evaluation, it only observes what is already final.

**Art. 3.6.1.** `Sensor` may have its own internal state — without being a `DynamicModel`. Problems like hysteresis/dead band or noise don't require integrated dynamics: a function `(raw_value, sensor_state) -> output`, updated as a side effect of each read, without entering the vector that the `Integrator`/RK4 advances. Implemented as a `trait SensorBehavior` (`monjolo/src/sensor/model.rs`), with `Ideal`, `Noisy`, and `Hysteresis` as pluggable behaviors on `Sensor`.

**Art. 3.6.2.** ~~`current_state` is `Rc<RefCell<Vec<Cell<f64>>>>` — same shape as `evaluation_state` (Art. 8), mutated cell-by-cell by `commit()`, never replaced wholesale.~~ **Note (2026-07-15):** `current_state` became `Arc<RwLock<CurrentState>>`, where `CurrentState { generation: u64, values: Vec<f64> }` — it no longer has the same shape as `evaluation_state` (which remains `Rc<RefCell<Vec<Cell<f64>>>>`, thread-local, Art. 8). Reason: `current_state` needs to cross threads (Art. 1.3, §1) — `Rc`/`Cell` aren't `Sync`, there's no way to share them safely. `commit()` (Art. 9.8) now takes the `write()` lock exactly once per call, writing all values and advancing `generation` in the same critical section — never cell-by-cell. `StateRegistry::read_proxy(key) -> Option<ReadProxy>` resolves the key exactly once against this buffer — that's what `Sensor` (Art. 3.6.3, 3.6.6) uses, now via `ReadProxy::get_versioned() -> (u64, f64)` (generation + value, same lock). `StateRegistry::read(key) -> Option<f64>` still exists, but as a one-off debug/inspection read, not the path `Sensor` uses.

**Art. 3.6.3.** `Sensor` is, in practice, a pipe: it observes a key, applies a `SensorBehavior` (Art. 3.6.1), and exposes the result — it never writes back to the `StateRegistry`. `Sensor` holds a `ReadProxy` (Art. 3.6.2), resolved exactly once in `Sensor::new()` — `read()` is just `self.proxy.get()`, with no string lookup. `RegistryView` (a read-only facade over `Rc<RefCell<StateRegistry>>`, without `subscribe()`/`resolve()`/`commit()`) is the factory that produces this `ReadProxy` (`RegistryView::read_proxy(key)`), used exactly once when the Sensor is constructed.

**Art. 3.6.4.** `ReadProxy` is a type separate from `Proxy` (Art. 7) — it must not be confused with a hypothetical value. `Proxy` addresses `EvaluationState`, which may hold a hypothetical value from an iterative solver in progress (Art. 7.2). `ReadProxy` only exists over `CurrentState` — always the last confirmed value. Two distinct `struct`s (same shape: buffer + index) by design: with separate types, mistakenly handing a `Sensor` a `Proxy` resolved against `EvaluationState` fails to compile. `ReadProxy` is born already resolved — it's only created after the general `resolve()` has already run (Art. 3.8) — and it has no `set()`.

**Art. 3.6.5.** `StateSlot` (Art. 5) no longer holds the current state — it is rebuilt on demand by `StateRegistry::snapshot() -> Vec<StateSlot>`, zipping `index` (the operational source of truth for `key -> position`) with the current buffer. It only serves as metadata/catalog: inspection, debugging, signal listing, named export — never the path `Proxy`/`ReadProxy` use to read or write.

**Art. 3.6.6.** (2026-07-15) `Sensor` is the measurement layer over `CurrentState` (Art. 1.3, §1) — no external consumer (an OPC-UA client, a future Controller, Art. 3.5.1 §2) reads the raw state directly when the signal in question is a sensor; all of them go through `Sensor::read()`, which applies `SensorBehavior` (scaling, noise, hysteresis, failure, 4-20mA transformation, etc. — a property of the instrument, not of the plant) before exposing it.

§1 `Sensor` became `Send + Sync` — shareable via `Arc<Sensor>` between the plant thread, the Adapter thread, and a future Controller, all pointing at the same instrument, with no copy. `read()` became `&self` (not `&mut self`): `SensorBehavior` mutation sits behind an internal `Mutex`.

§2 Idempotency: `read()` is idempotent within the same `CurrentState` `generation` (Art. 3.6.2). `Sensor` holds a `(generation, already_processed_value)` cache — the first call after a `commit()` invokes `SensorBehavior::apply()` for real (advances `Noisy`'s RNG, re-evaluates `Hysteresis`'s dead band) and stores the result; any subsequent call, from any consumer, from any thread, before the next `commit()`, just returns the cached value. This guarantees that OPC-UA and Controller, reading the same sensor on the same tick, always see the same measurement — `SensorBehavior` never advances twice for the same confirmed instant.

§3 Scope consequence: this only applies to signals that are a `Sensor` — a one-off debug/inspection read via `StateRegistry::read(key)` (Art. 3.6.2) still exposes `CurrentState`'s raw value, without `SensorBehavior` or caching; it is not the path OPC-UA/Controller use for sensor signals.

**Art. 3.7.** A `Sensor` tracks exactly one variable — there is no "composite sensor" at this layer. If the user wants to track A, B, and C, they declare three sensors.

**Art. 3.7.1.** `Sensor` is agnostic to the signal's physical type. There is no `FI`/`PI`/`LI`/`TI`/`AI` as distinct types — an approach that existed in the earlier codebase (one struct per physical quantity, all with the same body) and was abandoned. What varies between sensors is the read behavior (Art. 3.6.1), not the physical quantity measured.

**Art. 3.8.** `Sensor` declaration is explicit, done by whoever assembles the plant/simulation — never automatic or implicit in the dynamics itself. It can only be constructed after every `DynamicModel` has called `subscribe()` and the general `StateRegistry::resolve()` has already run (Art. 9.2) — never alongside the `add_dynamic` calls (Art. 2.3) in the model's composition. Reason: `Sensor::new()` resolves the key against `CurrentState` exactly once, on the spot (Art. 3.6.2/3.6.4), with no second resolution phase like `Proxy::unresolved` has for `needs` (Art. 6.2) — if the key doesn't yet exist in `index` at that moment, it's an error (`Result<Self, String>`). This lines up with `Simulation`'s instantiation (Art. 9), not with the composite model's constructor.

**Art. 3.9.** (repealed, see Art. 10.1 and Art. 11.1, 2026-07-09/2026-07-10)

## Architecture feasibility (DAG vs. DAE)

**Art. 4.1.** The TEP is a DAG (directed acyclic graph) today. The dependencies between Reactor → Separator → Stripper/Compressor → Flows → Heat/Measurements → derivatives form an acyclic graph. A fixed order (`EvaluationPlan`) is enough — there is no circular implicit equation in the current code.

**Art. 4.2.** Physical recycle does not imply an algebraic cycle. The TEP has physical recycle (the compressor's output goes back to the reactor), but flows and compositions are computed using already-known states, in explicit causal order. The algebraic problem would only appear if one block's variable `A(t)` needed `B(t)` from another block at the same time *and* `B(t)` needed `A(t)`.

**Art. 4.3.** A simple DAG breaks down for more general plants with hydraulic network equilibrium, coupled flash, strong recycle, or an implicit pressure-flow relation (e.g. `F = Cv·√(PA-PB)`, with `PA`/`PB` depending on `F` at the same instant). This forms an algebraic cycle — it becomes a DAE (`0 = g(y, z, t)`), not solvable by a linear sequence.

**Art. 4.4.** An iterative solver resolves the cycle by guessing a value for the variable that closes the cycle, evaluating the rest of the graph as a DAG from that guess, measuring the residual, adjusting, and repeating until convergence — it turns the cycle into a fixed-point problem.

**Art. 4.4.1.** Newton uses the residual's Jacobian to choose the correction direction, converging in far fewer iterations than successive substitution.

**Art. 4.4.2.** Tearing deliberately isolates the variable(s) that close the cycle and iterates only over them, re-evaluating the rest as a DAG on each attempt — this drastically reduces the size of the iterated system.

**Art. 4.5.** Valid for the TEP's current scope (simple DAG, Art. 4.1). Not the universal architecture for plant simulation in general — plants with strong algebraic coupling would require an iterative solver embedded inside the evaluation phase (Art. 4.4), keeping RK4 only for time advancement.

## About `StateSlot` and the semantic name mesh

**Art. 5.1.** Final structure of `StateSlot`: `key: String` + `value: f64`, with no `index` field. A slot's position within the `Vec` that holds it is its index — it is not redeclared inside the slot.

**Art. 5.1.1.** `index` was removed from `StateSlot` because storing it inside the slot itself creates an invariant nobody guarantees (`slots[3].index == 4`), which can silently drift if anyone filters, reorders, or merges slots. Resolving position at runtime is always the job of the `index: HashMap<String, usize>` (Art. 6), never of scanning a `Vec<StateSlot>`.

**Art. 5.2.** Invariant: append-only. Once a slot is registered, its position never changes or gets reused.

**Art. 5.3.** A component that depends on another's semantic value (e.g. Separator needing `reactor.temperature`) resolves that string against the slot list exactly once, at construction/composition time — not on every `evaluate()`. It stores the resulting `usize` as its own field.

**Art. 5.4.** `EvaluationResult` (`{ derivatives: Vec<f64>, values: Vec<StateSlot> }`, returned by `evaluate()`) was superseded by `EvaluationState`/`Proxy` (Art. 8) — `evaluate()` no longer returns anything.

## About `StateRegistry` as a subscription singleton

**Art. 6.1.** `StateRegistry` is a subscription/resolution singleton service, used during construction — not during the simulation loop. Every `DynamicModel` reports to one and only one `StateRegistry`, even if it isn't part of a composition.

**Art. 6.2.** A `DynamicModel`, at construction time, subscribes to the `StateRegistry` (`subscribe()`): it reserves space for its own slots (outputs), declaring their semantics, and declares which inputs (other components' keys) it needs.

§1 (open item, identified on 2026-07-07) Subscription shouldn't depend on someone remembering to explicitly call `subscribe()`/`add_dynamic()` inside `TennesseeEastmanModel::new()` (Art. 2.6). In Python this would be solved with an import side effect; in Rust, being compiled, the idea is to use compilation itself to pre-register this, without depending on an imperative sequence of calls. The concrete mechanism is still open — candidates: registration via a linker section (`inventory`/`linkme`-style), or `ctor` to run code before `main()`.

**Art. 6.2.1.** `subscribe` is a special method, separate from `add_dynamic` (Art. 2.3) — which serves only structural composition purposes. At initialization, `DynamicModel`s subscribe first, and only afterward are they evaluated — without the subscription resolved, they don't have the indices needed to run `evaluate()`.

**Art. 6.3.** Two-phase resolution: subscription order doesn't need to be respected — everyone subscribes first. Only after that is there an explicit step (`resolve()`), run exactly once, that resolves the index for every slot and every declared input.

**Art. 6.4.** Validation: if a declared input has no matching provider during resolution, it's an error (an exception is raised). If an offered slot (output) is never consumed by anyone, that's fine — the only thing checked is whether all requested inputs were mapped.

## About `Proxy`

**Art. 7.1.** `Proxy` is a handle shared between a `DynamicModel` and the `StateRegistry`, of the "resolved once, used forever" kind (in practice, something like `Rc<Cell<usize>>`). It is born unresolved; the `StateRegistry`, during `resolve()` (Art. 6.3), writes the real index into it. From then on, every clone of that `Proxy` sees the resolved index, with no need to look it up again.

**Art. 7.2.** `Proxy` is agnostic to whether a value is "hypothetical" or "real" — it only addresses a position; what exists *inside* that position (an intermediate guess from an iterative solver/Newton, Art. 4.4, or an already-converged value) is another layer's concern.

## About `EvaluationState`

**Art. 8.1.** `EvaluationState` is a copy initialized from the already-resolved `StateRegistry` — same size, same indices. It's the working buffer for one evaluation round, carrying the real values during the simulation.

**Art. 8.2.** Since `evaluate()` remains `&self` (Art. 1.2) but needs to write to its own outputs, `EvaluationState` needs interior mutability (`Vec<Cell<f64>>`). The external buffer gets mutated, not the component's `self` — the rule from Art. 1.2 still holds.

**Art. 8.3.** Derivatives are also slots addressed by `Proxy` (Art. 7). Each state slot gets, besides its value, its own key for its derivative (e.g. `"Separator.temperature.derivative"`), resolved together in `subscribe()` (Art. 6.2). This unifies derivatives and algebraic values under the same addressing mechanism.

**Art. 8.4.** `EvaluationResult` was eliminated (Art. 5.4). `evaluate()` no longer returns anything — it only writes inside `EvaluationState`, using the output `Proxy`s it has already held since subscription.

## About `Simulation` (orchestration object)

**Art. 9.1.** `Simulation` is the high-level object that instantiates the TEP (`TennesseeEastmanModel`) and the `Integrator` (RK4). It's the one that knows what needs to be passed to the integrator — neither the TEP nor the `Integrator` know this on their own.

**Art. 9.2.** After the TEP (and every `DynamicModel` it registered via `add_dynamic`, Art. 2.3) has already run its `subscribe()` (Art. 6.2) on the `StateRegistry`, `Simulation` calls `registry.resolve()` (Art. 6.3) exactly once.

**Art. 9.3.** `Simulation` passes a list of derivative names to the `StateRegistry`, which returns the corresponding vector of `Proxy`s — resolved exactly once, stored, in the same order as the state vector the `Integrator` uses.

**Art. 9.4.** The `Integrator` still receives a raw `state: Vec<f64>` — it just sums vectors, knowing nothing about `Proxy`, `EvaluationState`, or `StateRegistry`.

**Art. 9.5.** `Integrator::step()` receives a closure/callback, supplied by `Simulation`, called internally at each sub-step (k1..k4) — it no longer receives `model: &mut dyn DynamicModel`.

**Art. 9.6.** The closure from Art. 9.5 writes the perturbed state (`s2`, `s3`, `s4` of RK4) into `EvaluationState`, via the state slots' own `Proxy`s, and triggers `evaluate()` for the whole `DynamicModel` tree.

**Art. 9.7.** The closure from Art. 9.5 acts directly on the subset of derivatives (Art. 9.3) — it doesn't extract and return an isolated copy.

**Art. 9.8.** After `step()`, `Simulation` writes the entire `EvaluationState` into the real slots — not just the derivative subset, but also the algebraic values computed as a side effect (e.g. `reactor.temperature`), available for whoever needs them later (e.g. the `AcquisitionLayer`, Art. 3.2) at no extra cost.

**Art. 9.9.** Implemented in `monjolo/src/method/{integrator.rs,rk4.rs}` + `Simulation::run()`. Decisions that Art. 9.1-9.8 didn't fix:

Item I — the list of derivative names (Art. 9.3) comes from `DynamicModel::state_keys(&self) -> Vec<String>` (empty default, same pattern as `sensors()`, Art. 11.8); the derivative key is always `<key>.derivative` by convention. `Simulation::set_model()` captures `state_keys()` at the same moment it captures `sensors()`. Inside `run()` (Art. 11.10), each `(key, key.derivative)` pair becomes two `need`s in `subscribe(&[], ...)`.

Item II — `tick_interval` (wall-clock pacing) ≠ `dt_hours` (simulated physical step): `Simulation` has both fields, independent (`set_dt_hours`/`set_tick_interval`).

Item III — after `Integrator::step()` returns the combined state (`y_new`), `EvaluationState` still reflects the last `k4` sub-step (a hypothetical point) — `run()` does one extra write + `evaluate()` with the final state before committing, so that algebraic values (e.g. `reactor.temperature`) stay consistent with the state actually committed.

§1 Real state of the TEP's chemical core integration today: see Art. 2.6, §1.

§2 (2026-07-10) RK4 stopped being hardcoded: `Simulation::set_numerical_method(NumericalMethod)` (item I) started being genuinely consumed inside `spawn_plant_thread` via `NumericalMethod::integrator() -> Box<dyn Integrator>` — before, the field existed but `run()` ignored it and used a fixed RK4.

## About the I/O Image — minimal external boundary

**Art. 10.1.** `IoImage` (`monjolo/src/io_image.rs`) is a central catalog of named signals — the single place where `Sensor`s (read) and Actuator commands (write) are available by name. Naming convention (not enforced by the type): `sensors/<something>` for reads, `actuators/<something>` for writes.

**Art. 10.2.** `io_image.rs` doesn't import `state_registry` — it only knows `Sensor` (Art. 3) as the read type, and its own `CommandSink` trait as the write type. `IoImage` never needs to know that `StateRegistry`/`Proxy`/`ReadProxy`/`EvaluationState` exist.

**Art. 10.3.** `IoImage` holds a `HashMap<String, Sensor>` — publishing is just inserting an already-built `Sensor` under a name (`register_sensor(name, sensor)`). `read(name)` calls `Sensor::read()` under the hood (Art. 3.6.1), returning `None` if the name doesn't exist.

§1 (open item) It's not settled whether `IoImage.read()` should become push/observer instead of in-process pull, nor whether `commit()` should notify subscribers — the adapter (Art. 10.6) works around this with a 500ms `interval` that just re-reads everything each tick, not a real notification mechanism.

**Art. 10.4.**
```rust
pub trait CommandSink {
    fn write(&mut self, value: f64);
}
```
Any `FnMut(f64)` implements `CommandSink` for free — `Valve::set_command`/`Agitator::set_command` become a write signal just via closure: `io.register_actuator("actuators/cooling_water.command", move |v| valve.set_command(v))`. `IoImage` never needs to know `Valve` as a type — only the `CommandSink` behind it.

§1 See Art. 3.5.1, §2, for the (still pending) Controller design over this same mechanism.

**Art. 10.6.** The first network adapter is `monjolo/src/adapter/opcua.rs` (`pub async fn serve(...)`), behind the `opcua` feature (pulls in `async-opcua` + `tokio`). It spins up a real OPC-UA server: one read-only node per `io.sensor_names()` (Art. 10.6.4), updated by push (`node_manager.set_values()`) every tick, after each `Simulation::run()` (Art. 9.9) — never via `add_read_callback`, because the value is already ready.

**Art. 10.6.1.** `opcua_adapter::serve()` knows nothing about TEP — it just iterates `simulation.io().sensor_names()`/`actuator_names()`, names already declared from outside. The declarer is the application's real binary, `tep-plant/src/bin/tep_plant.rs` (`[[bin]] name = "tep-plant"`, ~~previously an `examples/opcua_server.rs`, back when `tep-plant` was still a workspace with a subcrate~~ → 2026-07-10) — `cargo run --bin tep-plant`, not a demo. The OPC-UA name (`"TEP/Reactor/Temperature"`) and the `StateRegistry` key (`"reactor.temperature"`) are the exclusive decision of whoever assembles the `Simulation` — the adapter only ever sees the first one.

**Art. 10.6.2.** Actuators have a complete write path: `SimpleNodeManager::add_write_callback` requires `Fn(...) + Send + Sync + 'static`, and `Simulation`/`IoImage`/`StateRegistry` are deliberately `Rc<RefCell<_>>` (Art. 11.1) — not `Send`. The registered callback never touches `Simulation` directly: it just pushes `(name, value)` onto a channel, ~~`tokio::sync::mpsc::UnboundedSender`~~ → `CommandQueue` (Art. 11.4), 2026-07-10 — the channel mechanism survived, the concrete type and the receiving side changed with the split into threads.

**Art. 10.6.3.** (repealed, see Art. 11, 2026-07-10)

**Art. 10.6.4.** `IoImage` gained `sensor_names()`/`actuator_names()` — needed so the generic adapter can tell, without knowing about TEP, which names become read-only nodes and which become writable nodes.

## About `Simulation` as a builder — "plant thread" separate from the "OPC-UA thread"

**Art. 11.1.** `Simulation` stopped building everything up front (`new(build) -> Result<Self, String>`) and became a builder that only stores definitions until `run()` — the terminal call that actually creates `StateRegistry`/model/`IoImage` and spawns the thread(s). Reason: `Simulation` (once assembled) always holds something rooted in `Rc<RefCell<StateRegistry>>` — impossible to move into a new thread once it already exists. The real construction needs to happen *inside* the thread that will run the tick loop; that's why `set_model`/`add_sensor`/`add_actuator` only package what they need into a `Box<dyn FnOnce(...) + Send>` — what the closure *produces* (the model, the `Sensor`s) never needs to be `Send`, because it never leaves the thread that created it.

**Art. 11.2.**
```rust
let mut simulation = Simulation::new();
simulation.set_model(TennesseeEastmanModel::new);
simulation.add_sensor("TEP/Reactor/Temperature", "reactor.temperature", Ideal);
simulation.set_adapter(AdapterConfig::OpcUa { endpoint: "opc.tcp://0.0.0.0:4840/tep/server/".into() });
simulation.run().expect("run ended with an error");
```
The caller never sees `StateRegistry`, `thread::spawn`, a channel, or the tokio runtime — all of that is internal to `run()`. `add_sensor` doesn't return a `Result` (the "does this key exist?" check can only happen after `run()` has already created the `StateRegistry`); if a key doesn't exist, the "plant thread" panics while constructing the `Sensor`, and that becomes an `Err` in `run()` via the supervisor (Art. 11.10).

§1 (open item) `add_actuator(name, sink: impl CommandSink + Send + 'static)` works for sinks that only capture external `Send` data (e.g. a channel, an `Arc<AtomicXxx>`). It doesn't work for something like `move |v| valve.set_command(v)`, because `Valve` only exists *after* the `model_factory` runs inside the "plant thread" — at the moment `add_actuator()` is called (before `run()`), that `Valve` hasn't even been built yet. Today this doesn't block anything because no real actuator (`Valve`/`Agitator`) is wired into `TennesseeEastmanModel` yet (Art. 2.6, §1) — but once one exists, it will need a "key resolved later" mechanism, symmetric to what `add_sensor` already has via `key: &str`, instead of accepting a ready-made closure.

**Art. 11.3.** `run(self) -> Result<(), String>` consumes `Simulation` by value. Inside `std::thread::spawn`: it creates `StateRegistry::shared()`, calls the stored `model_factory`, `resolve()`s (Art. 6.3), builds each `Sensor`/registers each `CommandSink` in the `IoImage` — only now do these objects really exist. Loop: drain pending commands → `model.evaluate()` + `registry.commit()` ~~→ publish each sensor to the `SnapshotBus` (Art. 11.4)~~ → sleep `tick_interval`. **Note (2026-07-15):** there is no longer a publish step — `commit()` is already enough, `Sensor` reads `CurrentState` on demand (Art. 3.6.6). If `set_adapter()` was called, a second thread comes up (Art. 11.5).

**Art. 11.4.** ~~`SnapshotBus` and `CommandQueue` are the only two thread-safe bridges, with no tokio dependency (only `std::sync`):~~
- ~~**`SnapshotBus`** (`Arc<RwLock<HashMap<String, f64>>>`): the "plant thread" publishes each sensor's value every tick; any outside reader only reads.~~
- **`CommandQueue`** (`Arc<Mutex<std::sync::mpsc::Sender<(String, f64)>>>`): whatever is outside pushes `(name, value)`; the plant drains it at the start of each tick. The `Mutex` exists because an OPC-UA write callback requires `Fn(...) + Send + Sync` and `Sender` alone isn't `Sync`. It doesn't know what OPC-UA, TEP, or `StateRegistry` are.

**Note (2026-07-15):** `SnapshotBus` was eliminated. `CurrentState` (Art. 1.3 §1, 3.6.2) explicitly took on the role of "last confirmed physical state" — no more intermediate publishing needed: `Sensor` (Art. 3.6.6) became `Send + Sync` and is exported, exactly once, via `Arc<Sensor>` in the boot handshake (Art. 11.8); any consumer (adapter, future Controller) calls `sensor.read()` directly, with no channel in between. `CommandQueue` is unaffected — its reason to exist is different (external writes, not read coherence) and it stays as is.

§1 (2026-07-14, historical — about the now-repealed `SnapshotBus` above) Found during a discussion about simplifying the read bridge, then verified directly in the code: the original implementation of `SnapshotBus::publish(name, value)` took the `write()` lock **once per sensor**, inside the `for name in &sensor_names` loop in the tick loop (`Simulation::spawn_plant_thread`). Since the lock was released between one sensor and the next, a concurrent reader (the "OPC-UA thread") could — in theory — read the `HashMap` in the middle of that sequence and see a mix of values from different ticks across distinct variables: there wasn't, in fact, an atomic "snapshot" of the whole tick, contrary to what the name `SnapshotBus` suggests. Fixed at the time by swapping `publish()` for `publish_all(...)` (single lock per tick) — the whole change was superseded by `SnapshotBus`'s elimination the following day; kept here only as a historical record of the reasoning that led to that elimination.

**Art. 11.5.** ~~`opcua_adapter::serve(sensor_names, actuator_names, snapshot: SnapshotBus, commands: CommandQueue, endpoint)`~~ **Note (2026-07-15):** the current signature is `opcua_adapter::serve(sensors: HashMap<String, Arc<Sensor>>, actuator_names, commands: CommandQueue, endpoint)` — it doesn't import `Simulation`/`IoImage`/`StateRegistry` — only the sensor catalog (Art. 3.6.6, 11.8) and `CommandQueue` (Art. 11.4). The push loop calls `sensor.read()` directly on each `Arc<Sensor>` every tick (500ms) — `snapshot.read(name)` no longer exists. Each actuator's `add_write_callback` just calls `commands.write(name, value)`. Since nothing here is `!Send`, the push loop runs on a plain `tokio::spawn`. `run()` creates the tokio runtime only inside the "OPC-UA thread" — the rest of the process never sees tokio.

§1 (2026-07-15) The runtime created in `spawn_adapter_thread` is `tokio::runtime::Builder::new_current_thread()`, not `Runtime::new()`/`multi_thread`. Reason: `async-opcua-server`/`async-opcua-core` depend on `tokio` directly (`features = ["full"]`, confirmed in the published `Cargo.toml` of the lib) — there's no swappable async runtime abstraction; and the adapter itself is purely I/O-bound (a `TcpListener`, few connections, one push task every 500ms via `tokio::spawn`/`tokio::time::interval`), with no real parallel work to justify the worker-thread pool (one per logical core) that `multi_thread` creates by default. The swap changes nothing in `opcua_adapter::serve` or in the lib — only the `Builder` used in `spawn_adapter_thread`; validated by bringing up `tep-plant` for real and connecting an actual OPC-UA client (session, `Browse`, the 4 expected nodes), compared side by side against the `multi_thread` baseline to isolate a pre-existing bug (reading `Value` via `ReadAttribute` returns `BadNodeIdUnknown` in both) as a non-regression from this swap.

**Art. 11.6.** `tep-plant/src/bin/tep_plant.rs`: `main()` is synchronous — no `#[tokio::main]`, no `async fn main()`, no `.await`. `Simulation::run()` is the only thing that creates a runtime, internally. `tep-plant`'s `Cargo.toml` doesn't depend on `tokio` directly.

**Art. 11.8.** `DynamicModel` gained `sensors(&self) -> Vec<(String, String)>` (exposure name, `StateRegistry` key) — the model itself declares what it exposes, not whoever assembles the `Simulation`. A method with an empty default body — only whoever orchestrates (`TennesseeEastmanModel`) overrides it. `Simulation::set_model()` calls `model.sensors()` while the type is still concrete, before it becomes `Box<dyn DynamicModel>`. Inside the "plant thread," these "model" sensors are merged with the ones that came from an external `add_sensor()`. ~~A handshake (`std::sync::mpsc::channel::<Vec<String>>()`) guarantees that the "OPC-UA thread" only builds the address space after the "plant thread" has finished registering everything in `IoImage`.~~ **Note (2026-07-15):** the handshake still exists (same purpose: the Adapter thread only builds the address space after the plant thread has finished registering everything), but the channel became `std::sync::mpsc::channel::<HashMap<String, Arc<Sensor>>>()` — it carries the ready-built sensor catalog (`IoImage::sensor_catalog()`), not just the names; it's the same handshake that resolves Art. 3.6.6/11.4 (exporting `Arc<Sensor>` exactly once, at boot). Result in `tep_plant.rs`: the binary no longer mentions `"reactor.temperature"` or `"TEP/Reactor/Temperature"` anywhere.

**Art. 11.9.** `tep-plant/src/initial_state.rs` (a rigid struct, one Rust field per TOML key, matching position-by-position with `teprob.f`'s `YY(1..50)`) was deleted — replaced by `monjolo::snapshot::Snapshot`, generic: it loads any TOML file and flattens the nested tables into dotted keys (`[state.reactor_vapor] A = 1.0` becomes `"state.reactor_vapor.A" -> 1.0`) in a `HashMap<String, f64>`. `Snapshot::get(key) -> Option<f64>`; `Snapshot::from_pairs(&[(&str, f64)])` for testing. `Reactor::new(registry, initial: &Snapshot)` fetches only the keys it cares about, a missing key becomes `0.0`. `TennesseeEastmanModel::new(registry, initial: &Snapshot)` passes the same `&Snapshot` on to the four subsystems — ~~only `Reactor` uses it so far; `Separator`/`Stripper`/`Compressor` are still born without an initial condition~~ → all four consume `Snapshot` today, 2026-07-12. `tep_plant.rs` loads the `Snapshot` (`Snapshot::from_file("src/cases/te_exp3_snapshot.toml")`) and passes it through a closure to `set_model`, since `TennesseeEastmanModel::new` stopped fitting as a direct function pointer (two parameters).

**Art. 11.10.** `Simulation` is the lifecycle manager/supervisor: `run()` orchestrates 0/1/2 services depending on what was configured — it spawns the "plant thread" only if `set_model()` was called, spawns the "adapter thread" only if `set_adapter()` was called (`AdapterConfig`, `monjolo/src/adapter/mod.rs` — a closed enum, today only `OpcUa { endpoint: String }`), and returns `Err` without spawning anything if neither was configured. Supervisor (`ServiceEvent`/`ServiceKind`, private in `simulation.rs`): each internal thread runs inside `std::panic::catch_unwind` and sends exactly one `ServiceEvent` (`Stopped`/`Failed`/`Panicked`) over a lifecycle channel before returning. `run()` blocks on `events_rx.recv()`: the first event from any configured service is already reason enough to return — tested (`run_returns_err_instead_of_hanging_when_plant_panics`).

§1 (open item, left explicit on purpose) There is no cooperative cancellation — neither the plant thread nor the adapter thread checks for a stop signal; when one dies, the other (if any) is not notified, and `run()` just stops waiting for it. It's up to whoever called `run()` to decide to end the process. True graceful shutdown is the next step.
