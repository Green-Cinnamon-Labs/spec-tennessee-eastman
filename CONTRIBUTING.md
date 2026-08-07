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
Actuator              → Art. 3.5, 12.1–12.3, 12.8
BootCatalogs (repealed 2026-08-07) → Art. 12.4
Composite             → Art. 2.5, 2.6
Valve/Agitator        → Art. 2.2, 2.6, 12.8 (tep-plant, not monjolo, since 2026-08-07)
IoImage (repealed 2026-07-29)     → Art. 10.1–10.4
CommandSink (repealed 2026-07-29) → Art. 10.4
CommandQueue (repealed 2026-07-29) → Art. 10.6.2, 11.4
SnapshotBus (repealed 2026-07-15) → Art. 11.4
Simulation            → Art. 9, 9.1–9.9, 11, 11.1–11.10
AdapterConfig         → Art. 11.10
NumericalMethod/RK4   → Art. 9.9, 11.10
OPC-UA Adapter        → Art. 10.6, 10.6.1–10.6.4, 12.5–12.7
Flows/Heat/Measurements → Art. 2.6, §1
Controller            → Art. 3.5, 3.5.1 §2
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

**Art. 2.5.** ~~There is no reusable generic `Composite` implementation. A generic `struct Composite` (`children`/`sizes`) was considered and rejected: in the whole system there is only **one** actual composite node — `TennesseeEastmanModel`. `TennesseeEastmanModel` implements `DynamicModel` + `CompositeDynamicModel` directly, owning its own `Vec<Box<dyn DynamicModel>>` (the `models` field).~~ **Note (2026-08-07):** reversed. `monjolo::dynamic_model::Composite` is now the reusable generic implementation this article originally rejected — the "only one composite node in the whole system" premise stopped holding once a second composite scenario made hand-writing the same struct/`Vec`/two-trait-impl boilerplate again look ridiculous rather than proportionate. `Composite` holds `models: Vec<Box<dyn DynamicModel>>` + `name: String`, implements both `DynamicModel` and `CompositeDynamicModel` itself, and exposes a builder, `Composite::new().named(impl Into<String>)`, for the display name (`DynamicModel::name()` — Art. 2.1 — changed its return type from `&'static str` to `&str` specifically so `Composite` could return a reference into its own owned `name: String`). Whoever assembles a plant no longer declares a struct, a `Vec` field, or the two trait impls (Art. 2.6) — they call `Composite::new().named("...")` and `add_dynamic()` (Art. 2.3) the components in, same as any other `CompositeDynamicModel` always did.

**Art. 2.6.** ~~The TEP constructor (`TennesseeEastmanModel::new()`) contains no composition logic of its own — just a sequence of `add_dynamic` (Art. 2.3) calls registering each component, in the order they must be evaluated.~~ **Note (2026-08-07):** there is no `TennesseeEastmanModel` struct anymore either (Art. 2.5) — once `Composite` supplies both trait impls for free, nothing TEP-specific was left to justify a struct declaration. `tep-plant/src/model.rs` is now a single free function, `pub fn new(registry: &mut StateRegistry, initial: &Snapshot) -> Composite`, that builds `Composite::new().named("TennesseeEastmanModel")` (the *string* survives as the display name even though the *type* is gone) and `add_dynamic`-registers each component, in evaluation order: `Reactor`, `Separator`, `Stripper`, `Compressor` (all consuming their initial condition via `Snapshot`, Art. 11.9), plus `Valve` ("cooling_water") and `Agitator` (2026-07-30, Art. 12.8) — the latter two don't take a `Snapshot`, their position/speed just starts at the slot default (`0.0`). `Valve`/`Agitator` themselves live in `tep-plant/src/subsystems/actuators.rs`, not in `monjolo` (Art. 12.8) — they're TEP-specific physical components, not generic framework building blocks.

§1 (open item, identified on 2026-07-12 — partially resolved 2026-07-30, see Item I) `Flows`, `Heat`, and `Measurements` — the three subsystems that would close the calculation (Blocks 19-36 of `teprob.f`) — exist only as empty `struct`s with `evaluate() { todo!() }` (`tep-plant/src/subsystems/{flows,heat,measurements}.rs`) and are not `add_dynamic`'d here: they are not just "unimplemented," they are dead code, never instantiated even in the `tep-plant` binary. The original physics is preserved, commented out, in `tep-plant/docs/_deprecated_2.rs`: `TepFlows` (Blocks 19-31), `TepHeat` (Blocks 32-34), `TepMeasurements` (Blocks 35-36).

Item I — Consequence: `Flows` is the one that would compute the actual derivative (`yp`) of the `own_state` for Reactor/Separator/Stripper/Compressor. Without it, none of the four offers the companion `.derivative` key, and `model::new()`'s `Composite` (Art. 2.5/2.6) does not declare any `state_keys()` for them (Art. 9.9, it stays at the empty default) — the Integrator (Art. 9) has nothing to integrate for the chemical core, and `own_state` stays frozen at the value seeded by `Snapshot` (Art. 11.9). `evaluate()` only recomputes derived thermodynamic quantities (temperature, pressure, composition) on top of that stalled state. ~~The integration machinery itself works and is tested (`Valve`/`Agitator` already use it correctly).~~ **Note (2026-07-30):** no longer just tested in isolation — `Valve`/`Agitator` are now `add_dynamic`'d into the composite for real (this article's caput). **Note (2026-08-07):** the "each consuming its own `Arc<Actuator>`" part of the 2026-07-30 note is no longer accurate — `Actuator` stopped being a mailbox object (Art. 12.1, 12.2); `Valve`/`Agitator` implement the `Actuator` trait directly on themselves now. Either way, their position/speed genuinely integrates via `add_dynamic` — but nothing in `Simulation` exposes that externally today (Art. 11's note) — and Item III still applies: it has no effect on the chemical core until `Flows` exists.

Item II — Porting requires deciding each one's `needs` against the current `StateRegistry` (`Flows` needs all four chemical subsystems + valve positions + disturbance flags at once) and rewriting the logic on top of `Proxy`/`ReadProxy` (Art. 7), not positional `&[f64]`.

Item III — Dependency order: `Flows` (depends only on the 4 chemical subsystems) → `Heat` (depends on Reactor+Stripper+Flows) → `Measurements` (depends on all of them+Flows+Heat). ~~Wiring up an actuator (Art. 11.2, §1) only produces a real effect on the plant once `Flows` exists.~~ **Note (2026-07-30):** an actuator *is* wired now (Art. 2.6, Art. 12.8) — this sentence's point still holds exactly as stated, just reworded to not read as a future conditional: `valve.cooling_water.position` evolves for real and is readable/writable from outside, but produces no effect elsewhere in the plant until `Flows` exists to consume it. **Note (2026-08-07):** "readable/writable from outside" no longer holds — `valve.cooling_water.position` still evolves for real (`Valve` still `add_dynamic`'d, still implements `Actuator`), but `Simulation` no longer exposes anything to an actual outside caller (no `add_sensor`/`add_actuator`/`set_adapter`, no adapter thread — Art. 11's note). Today "outside" means a test, or a future `DynamicModel`/`Controller` holding a direct handle — not a network client.

**Art. 2.7.** `get_state_template()`/`StateTemplate` do not exist — they were replaced by subscription (Art. 6.2). A `DynamicModel` subscribes to the `StateRegistry`, gets `Proxy`s back, and operates with them. `DynamicModel`'s real methods are `evaluate()` and `subscribe()` (the special subscription method, Art. 6.2.1).

## Relationship with the outside world (Outside ↔ DynamicModel)

**Art. 3.1.** Name of the relationship: `AcquisitionLayer`. Considered and rejected before: "Process Image" (automation/PLC connotation, deemed confusing).

**Art. 3.2.** Role of the `AcquisitionLayer`: querying, not evaluation. Something external (e.g. 4-20mA, Modbus, OPC-UA adapters) queries the parent `DynamicModel` to obtain the raw state and transforms it for a specific protocol — pure reading, after the model has already resolved everything, without taking part in `evaluate()`.

**Art. 3.3.** `Sensor` is not a `DynamicModel` in the composition tree — it stays outside `add_dynamic` (Art. 2.3) because it does not take part in evaluation: it only reads the state after it has been resolved.

**Art. 3.4.** `Disturbance` is not a `DynamicModel` in the composition tree — it doesn't belong to a single component, it cuts across several at once (reaction in the Reactor, condenser UA and flow in Flows, exchange coefficients in Heat). Treated as an injected input, associated with each component that consumes it.

**Art. 3.5.** There are exactly three objects that give the simulated physics any interaction with the outside world: **Sensor** (exposes an observed value), **Actuator** (allows action on the plant), and **Controller** (allows closing a control loop over the plant). Outside these three, there is no other entry/exit door between the simulated dynamics and the outside world.

**Art. 3.5.1.** The detailed design of Actuator and Controller (Art. 3.5) was handled after Sensor's. Art. 3.6 through 3.9 specify only `Sensor`.

§1 Actuator got a concrete design: ~~`CommandSink` (Art. 10.4), channel (Art. 11.4)~~ `Actuator` (Art. 12.1, 12.2), 2026-07-29 — no longer a pending item.

§2 (open item) Controller is not yet modeled. ~~Design already anticipated: reads via `IoImage.read()` (Art. 10.3), writes via `IoImage.write()` (Art. 10.4) — without requiring any shape change in `IoImage`.~~ **Note (2026-07-29):** the anticipated mechanism changed along with `IoImage`'s elimination — the direct precedent now is `Sensor`/`Actuator` (Art. 3.6.6, 12.1-12.2): a `Send + Sync` object exported once via `Arc` in the boot handshake, combining a read path (mirroring `Sensor`) and a write path (mirroring `Actuator`). Not implemented because there is no Controller yet to test it against. **Note (2026-08-07):** the anticipated mechanism changed again, and the premise itself is gone. `Actuator` (Art. 12.1) is a bare trait now, `fn write(&self, value: f64)`, the same one-method shape as `Sensor` (Art. 3.6) — mirrored, not a shared base type, and neither is `Send + Sync` by any framework guarantee (that's on whatever implements them). There is also no boot handshake left to export anything through (Art. 11's note) — `Simulation` doesn't catalog sensors/actuators for an adapter thread anymore, because it doesn't have an adapter thread anymore. Whatever eventually exposes a `Controller` to the outside is an open question again, not a solved-but-unbuilt one — see Art. 11.8's note.

**Art. 3.6.** `Sensor` has no relationship with `evaluate()`/`EvaluationState` (Art. 8) — those are written to by the `DynamicModel`s resolving their own physics, at each RK4 sub-step. `Sensor` reads from `StateRegistry.CurrentState` (Art. 1.3): the already-committed store, after `set_current_state()` has closed the step. `Sensor` is never a participant in evaluation, it only observes what is already final.

**Art. 3.6.1.** `Sensor` may have its own internal state — without being a `DynamicModel`. Problems like hysteresis/dead band or noise don't require integrated dynamics: a function `(raw_value, sensor_state) -> output`, updated as a side effect of each read, without entering the vector that the `Integrator`/RK4 advances. Implemented as a `trait SensorBehavior` (`monjolo/src/sensor/model.rs`), with `Ideal`, `Noisy`, and `Hysteresis` as pluggable behaviors on `Sensor`.

**Art. 3.6.2.** ~~`current_state` is `Rc<RefCell<Vec<Cell<f64>>>>` — same shape as `evaluation_state` (Art. 8), mutated cell-by-cell by `commit()`, never replaced wholesale.~~ **Note (2026-07-15):** `current_state` became `Arc<RwLock<CurrentState>>`, where `CurrentState { generation: u64, values: Vec<f64> }` — it no longer has the same shape as `evaluation_state` (which remains `Rc<RefCell<Vec<Cell<f64>>>>`, thread-local, Art. 8). Reason: `current_state` needs to cross threads (Art. 1.3, §1) — `Rc`/`Cell` aren't `Sync`, there's no way to share them safely. `commit()` (Art. 9.8) now takes the `write()` lock exactly once per call, writing all values and advancing `generation` in the same critical section — never cell-by-cell. `StateRegistry::read_proxy(key) -> Option<ReadProxy>` resolves the key exactly once against this buffer — that's what `Sensor` (Art. 3.6.3, 3.6.6) uses, now via `ReadProxy::get_versioned() -> (u64, f64)` (generation + value, same lock). `StateRegistry::read(key) -> Option<f64>` still exists, but as a one-off debug/inspection read, not the path `Sensor` uses.

**Art. 3.6.3.** `Sensor` is, in practice, a pipe: it observes a key, applies a `SensorBehavior` (Art. 3.6.1), and exposes the result — it never writes back to the `StateRegistry`. `Sensor` holds a `ReadProxy` (Art. 3.6.2), resolved exactly once in `Sensor::new()` — `read()` is just `self.proxy.get()`, with no string lookup. `RegistryView` (a read-only facade over `Rc<RefCell<StateRegistry>>`, without `subscribe()`/`resolve()`/`commit()`) is the factory that produces this `ReadProxy` (`RegistryView::read_proxy(key)`), used exactly once when the Sensor is constructed.

**Art. 3.6.4.** `ReadProxy` is a type separate from `Proxy` (Art. 7) — it must not be confused with a hypothetical value. `Proxy` addresses `EvaluationState`, which may hold a hypothetical value from an iterative solver in progress (Art. 7.2). `ReadProxy` only exists over `CurrentState` — always the last confirmed value. Two distinct `struct`s (same shape: buffer + index) by design: with separate types, mistakenly handing a `Sensor` a `Proxy` resolved against `EvaluationState` fails to compile. `ReadProxy` is born already resolved — it's only created after the general `resolve()` has already run (Art. 3.8) — and it has no `set()`.

**Art. 3.6.5.** `StateSlot` (Art. 5) no longer holds the current state — it is rebuilt on demand by `StateRegistry::snapshot() -> Vec<StateSlot>`, zipping `index` (the operational source of truth for `key -> position`) with the current buffer. It only serves as metadata/catalog: inspection, debugging, signal listing, named export — never the path `Proxy`/`ReadProxy` use to read or write.

**Art. 3.6.6.** (2026-07-15) `Sensor` is the measurement layer over `CurrentState` (Art. 1.3, §1) — no external consumer (an OPC-UA client, a future Controller, Art. 3.5.1 §2) reads the raw state directly when the signal in question is a sensor; all of them go through `Sensor::read()`, which applies `SensorBehavior` (scaling, noise, hysteresis, failure, 4-20mA transformation, etc. — a property of the instrument, not of the plant) before exposing it.

§1 `Sensor` became `Send + Sync` — shareable via `Arc<Sensor>` between the plant thread, the Adapter thread, and a future Controller, all pointing at the same instrument, with no copy. `read()` became `&self` (not `&mut self`): `SensorBehavior` mutation sits behind an internal `Mutex`. **Note (2026-08-07):** the "Adapter thread" part of that sentence describes a consumer that no longer exists — `Simulation` doesn't spawn one anymore, and there's no boot handshake exporting `Arc<Sensor>` to anything (Art. 11.8's note). `Sensor` being `Send + Sync` is still true and still the reason it *could* be shared via `Arc` — there's just nothing today that actually does the sharing besides whoever constructs one directly and keeps a clone.

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

§1 (open item, identified on 2026-07-07) Subscription shouldn't depend on someone remembering to explicitly call `subscribe()`/`add_dynamic()` inside ~~`TennesseeEastmanModel::new()`~~ `tep-plant::model::new()` (Art. 2.6 — no `TennesseeEastmanModel` type exists anymore, same correction as Art. 9.1). In Python this would be solved with an import side effect; in Rust, being compiled, the idea is to use compilation itself to pre-register this, without depending on an imperative sequence of calls. The concrete mechanism is still open — candidates: registration via a linker section (`inventory`/`linkme`-style), or `ctor` to run code before `main()`.

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

**Art. 9.1.** `Simulation` is the high-level object that instantiates the TEP (~~`TennesseeEastmanModel`~~ **Note (2026-08-07):** built by `tep-plant::model::new()`, a free function — no `TennesseeEastmanModel` type exists anymore, Art. 2.5/2.6) and the `Integrator` (RK4). It's the one that knows what needs to be passed to the integrator — neither the TEP nor the `Integrator` know this on their own.

**Art. 9.2.** After the TEP (and every `DynamicModel` it registered via `add_dynamic`, Art. 2.3) has already run its `subscribe()` (Art. 6.2) on the `StateRegistry`, `Simulation` calls `registry.resolve()` (Art. 6.3) exactly once.

**Art. 9.3.** `Simulation` passes a list of derivative names to the `StateRegistry`, which returns the corresponding vector of `Proxy`s — resolved exactly once, stored, in the same order as the state vector the `Integrator` uses.

**Art. 9.4.** The `Integrator` still receives a raw `state: Vec<f64>` — it just sums vectors, knowing nothing about `Proxy`, `EvaluationState`, or `StateRegistry`.

**Art. 9.5.** `Integrator::step()` receives a closure/callback, supplied by `Simulation`, called internally at each sub-step (k1..k4) — it no longer receives `model: &mut dyn DynamicModel`.

**Art. 9.6.** The closure from Art. 9.5 writes the perturbed state (`s2`, `s3`, `s4` of RK4) into `EvaluationState`, via the state slots' own `Proxy`s, and triggers `evaluate()` for the whole `DynamicModel` tree.

**Art. 9.7.** The closure from Art. 9.5 acts directly on the subset of derivatives (Art. 9.3) — it doesn't extract and return an isolated copy.

**Art. 9.8.** After `step()`, `Simulation` writes the entire `EvaluationState` into the real slots — not just the derivative subset, but also the algebraic values computed as a side effect (e.g. `reactor.temperature`), available for whoever needs them later (e.g. the `AcquisitionLayer`, Art. 3.2) at no extra cost.

**Art. 9.9.** Implemented in `monjolo/src/method/{integrator.rs,rk4.rs}` + `Simulation::run()`. Decisions that Art. 9.1-9.8 didn't fix:

Item I — the list of derivative names (Art. 9.3) comes from `DynamicModel::state_keys(&self) -> Vec<String>` (empty default — the only one of these declaration-style methods `DynamicModel` still has; ~~same pattern as `sensors()`, Art. 11.8~~ **Note (2026-08-07):** `sensors()`/`actuators()` never existed as a permanent fixture and are gone now, Art. 11.8's note — `state_keys()` stands alone); the derivative key is always `<key>.derivative` by convention. `Simulation::set_model()` captures `state_keys()` while the model's concrete type is still known, before it becomes `Box<dyn DynamicModel>`. Inside `run()`'s `spawn_plant_thread` (Art. 11.3), each `(key, key.derivative)` pair becomes two `need`s in `subscribe(&[], ...)`.

Item II — `tick_interval` (wall-clock pacing) ≠ `dt_hours` (simulated physical step): `Simulation` has both fields, independent (`set_dt_hours`/`set_tick_interval`).

Item III — after `Integrator::step()` returns the combined state (`y_new`), `EvaluationState` still reflects the last `k4` sub-step (a hypothetical point) — `run()` does one extra write + `evaluate()` with the final state before committing, so that algebraic values (e.g. `reactor.temperature`) stay consistent with the state actually committed.

§1 Real state of the TEP's chemical core integration today: see Art. 2.6, §1.

§2 (2026-07-10) RK4 stopped being hardcoded: `Simulation::set_numerical_method(NumericalMethod)` (item I) started being genuinely consumed inside `spawn_plant_thread` via `NumericalMethod::integrator() -> Box<dyn Integrator>` — before, the field existed but `run()` ignored it and used a fixed RK4.

## About the I/O Image — minimal external boundary

**Art. 10.1.** ~~`IoImage` (`monjolo/src/io_image.rs`) is a central catalog of named signals — the single place where `Sensor`s (read) and Actuator commands (write) are available by name. Naming convention (not enforced by the type): `sensors/<something>` for reads, `actuators/<something>` for writes.~~ **Note (2026-07-29):** `IoImage` was eliminated. There is no longer a dedicated name→object catalog type at all — `Sensor` and `Actuator` are exported directly, by name, in a plain data-only struct (`BootCatalogs`, Art. 12.4) built by a private helper. See Art. 12.1.

**Art. 10.2.** ~~`io_image.rs` doesn't import `state_registry` — it only knows `Sensor` (Art. 3) as the read type, and its own `CommandSink` trait as the write type. `IoImage` never needs to know that `StateRegistry`/`Proxy`/`ReadProxy`/`EvaluationState` exist.~~ **Note (2026-07-29):** moot — there is no `io_image.rs` anymore. The property this article described (the boundary code never needing to know about `StateRegistry`/`Proxy`/`ReadProxy`/`EvaluationState`) still holds for `adapter/opcua.rs` today — it only imports `Sensor` and `Actuator` (Art. 12.1).

**Art. 10.3.** ~~`IoImage` holds a `HashMap<String, Sensor>` — publishing is just inserting an already-built `Sensor` under a name (`register_sensor(name, sensor)`). `read(name)` calls `Sensor::read()` under the hood (Art. 3.6.1), returning `None` if the name doesn't exist.~~ **Note (2026-07-29):** superseded by `BootCatalogs`/`build_catalogs` (Art. 12.4) — the catalog is assembled once, inside `spawn_plant_thread`, and handed to the adapter thread whole; there is no `register_sensor`/`read(name)` API left anywhere to call at runtime.

§1 (open item — moot, see Note above, 2026-07-29) It's not settled whether `IoImage.read()` should become push/observer instead of in-process pull, nor whether `commit()` should notify subscribers — the adapter (Art. 10.6) works around this with a 500ms `interval` that just re-reads everything each tick, not a real notification mechanism.

**Art. 10.4.** (repealed design, kept verbatim below as historical record — see the Note that follows for what replaced it):
```rust
pub trait CommandSink {
    fn write(&mut self, value: f64);
}
```
Any `FnMut(f64)` implements `CommandSink` for free — `Valve::set_command`/`Agitator::set_command` become a write signal just via closure: `io.register_actuator("actuators/cooling_water.command", move |v| valve.set_command(v))`. `IoImage` never needs to know `Valve` as a type — only the `CommandSink` behind it.

**Note (2026-07-29):** `CommandSink` was eliminated along with `IoImage`. There is no trait a closure can satisfy anymore — `add_actuator` takes a concrete `Arc<Actuator>` (Art. 12.1-12.3) that the caller constructs itself; wiring it to something like `Valve::set_command` (if/when a real actuator exists) is the caller's own responsibility, done by reading `Actuator::take()` inside its own `evaluate()`, not by handing a closure to the framework.

§1 See Art. 3.5.1, §2, for the (still pending) Controller design over the mechanism that replaced this one.

**Art. 10.6.** The first network adapter is `monjolo/src/adapter/opcua.rs` (`pub async fn serve(...)`), behind the `opcua` feature (pulls in `async-opcua` + `tokio`). It spins up a real OPC-UA server: one read-only node per sensor in ~~`io.sensor_names()` (Art. 10.6.4)~~ the `sensors` catalog it receives (Art. 12.4, 12.7), 2026-07-29, updated by push (`node_manager.set_values()`) every tick, after each `Simulation::run()` (Art. 9.9) — never via `add_read_callback`, because the value is already ready.

**Note (2026-08-07):** this whole article now describes a code path nothing calls. `Simulation` stopped spawning an adapter thread at all (Art. 11's note) — `serve()` has no caller anywhere in the workspace. The file itself is still there, still feature-gated behind `opcua` (a feature nothing in the workspace turns on), and it does not currently compile if that feature *were* turned on: it imports `crate::actuator::model::Actuator`, a path that stopped existing once `Actuator` became a flat trait directly in `actuator/mod.rs` (Art. 12.1) with no `model` submodule. Left broken on purpose rather than patched — the whole exposure layer (Art. 11's note, Art. 12.4-12.7) is pending a redesign, not a one-line fix, since there is no catalog-building mechanism left to feed it a `HashMap<String, Arc<Sensor>>`/`HashMap<String, Arc<Actuator>>` in the first place.

**Art. 10.6.1.** `opcua_adapter::serve()` knows nothing about TEP — it just iterates ~~`simulation.io().sensor_names()`/`actuator_names()`, names~~ the `sensors`/`actuators` catalogs it receives (Art. 12.4, 12.7), 2026-07-29, already declared from outside. The declarer is the application's real binary, `tep-plant/src/bin/tep_plant.rs` (`[[bin]] name = "tep-plant"`, ~~previously an `examples/opcua_server.rs`, back when `tep-plant` was still a workspace with a subcrate~~ → 2026-07-10) — `cargo run --bin tep-plant`, not a demo. The OPC-UA name (`"TEP/Reactor/Temperature"`) and the `StateRegistry` key (`"reactor.temperature"`) are the exclusive decision of whoever assembles the `Simulation` — the adapter only ever sees the first one.

**Art. 10.6.2.** ~~Actuators have a complete write path: `SimpleNodeManager::add_write_callback` requires `Fn(...) + Send + Sync + 'static`, and `Simulation`/`IoImage`/`StateRegistry` are deliberately `Rc<RefCell<_>>` (Art. 11.1) — not `Send`. The registered callback never touches `Simulation` directly: it just pushes `(name, value)` onto a channel, `tokio::sync::mpsc::UnboundedSender` → `CommandQueue` (Art. 11.4) — the channel mechanism survived, the concrete type and the receiving side changed with the split into threads.~~ **Note (2026-07-29):** the channel is gone entirely now, not just its concrete type. `SimpleNodeManager::add_write_callback` still requires `Fn(...) + Send + Sync + 'static`, but the registered callback now captures its own bound `Arc<Actuator>` (Art. 12.1, 12.2) directly and calls `actuator.write(value)` — `Actuator` is `Send + Sync` on its own, so nothing needs to bridge it across threads. See Art. 12.6.

**Art. 10.6.3.** (repealed, see Art. 11, 2026-07-10)

**Art. 10.6.4.** ~~`IoImage` gained `sensor_names()`/`actuator_names()` — needed so the generic adapter can tell, without knowing about TEP, which names become read-only nodes and which become writable nodes.~~ **Note (2026-07-29):** `IoImage` is gone (Art. 12.1); the adapter now receives two already-typed catalogs directly (`HashMap<String, Arc<Sensor>>`, `HashMap<String, Arc<Actuator>>`, Art. 12.4) and iterates each one's keys itself — which collection a name came from already tells the adapter whether it becomes a read-only or writable node, no dedicated name-listing methods needed anymore. See Art. 12.5, 12.7.

## About `Simulation` as a builder — "plant thread" separate from the "OPC-UA thread"

**Art. 11.1.** `Simulation` stopped building everything up front (`new(build) -> Result<Self, String>`) and became a builder that only stores definitions until `run()` — the terminal call that actually creates `StateRegistry`/model and spawns the plant thread. Reason: `Simulation` (once assembled) always holds something rooted in `Rc<RefCell<StateRegistry>>` — impossible to move into a new thread once it already exists. The real construction needs to happen *inside* the thread that will run the tick loop; that's why `set_model` only packages what it needs into a `Box<dyn FnOnce(...) + Send>` — what the closure *produces* (the model) never needs to be `Send`, because it never leaves the thread that created it.

**Note (2026-08-07):** the builder's surface shrank a lot since this article was written. There is no `IoImage`, no sensor/actuator catalog, no `build_catalogs`, no adapter thread, no `add_sensor`/`add_actuator`/`set_adapter` — `Simulation`'s public API today is exactly five things: `new()`, `set_model()`, `set_dt_hours()`, `set_tick_interval()`, `set_numerical_method()`, and `run()`. The `Rc<RefCell<StateRegistry>>`-can't-cross-threads reasoning above is unchanged and is still why it's a builder at all — everything downstream of it (catalogs, an adapter, a second thread) was removed, not the builder pattern itself.

**Art. 11.2.**
```rust
let initial = Snapshot::from_file("src/snapshots/te_exp3_snapshot.toml")
    .unwrap_or_else(|e| panic!("failed to load initial condition: {e}"));

let mut simulation = Simulation::new();
simulation.set_model(move |registry| model::new(registry, &initial));
simulation.set_numerical_method(NumericalMethod::RK4);
simulation.run().expect("run ended with an error");
```
(current real usage, `tep-plant/src/bin/tep_plant.rs` — `model::new`, Art. 2.6, needs a `&Snapshot` and so can't be passed directly as a function pointer, hence the closure.) The caller never sees `StateRegistry` or `thread::spawn` — that's internal to `run()`. ~~`add_sensor`...~~ **Note (2026-08-07):** `add_sensor`/`set_adapter` don't exist to call — see this chapter's note on Art. 11.1. A panic while constructing the model still becomes an `Err` in `run()` via the supervisor (Art. 11.10).

§1 (open item — resolved, see Art. 12.3 §1, 2026-07-29) ~~`add_actuator(name, sink: impl CommandSink + Send + 'static)` works for sinks that only capture external `Send` data...~~ **Note (2026-08-07):** moot on top of resolved — `add_actuator` doesn't exist at all anymore (Art. 12.3's note), so the ordering problem this paragraph described has no API left to apply to.

**Art. 11.3.** `run(self) -> Result<(), String>` consumes `Simulation` by value. ~~Inside `std::thread::spawn`: it creates `StateRegistry::shared()`, calls the stored `model_factory`, `resolve()`s (Art. 6.3), builds each `Sensor`/registers each `CommandSink` in the `IoImage`... Loop: drain pending commands → `model.evaluate()` + `registry.commit()` → publish each sensor to the `SnapshotBus`... If `set_adapter()` was called, a second thread comes up.~~ **Note (2026-08-07):** rewritten to match the real, much simpler `spawn_plant_thread` (`monjolo/src/simulation.rs`) — a single `std::thread::Builder::new().name("plant")`, its whole body inside `panic::catch_unwind`:

1. `StateRegistry::shared()`, then the stored `model_factory` runs, producing `(model, model_state_keys)` — `model_state_keys` is what `DynamicModel::state_keys()` (Art. 9.9, Item I) returned while the model's concrete type was still known.
2. For each key in `model_state_keys`, both `key` and `key.derivative` are requested as `need`s in one `subscribe(&[], ...)` call; `registry.resolve()` (Art. 6.3) runs exactly once, right after.
3. `let integrator = numerical_method.integrator();` (Art. 9.9, §2) — the `RK4`/`Integrator` the constructor picked.
4. The tick loop: if there are no declared state keys, it just calls `model.evaluate()` every tick (nothing to integrate). Otherwise it runs the RK4 step described in Art. 9.5-9.8 — the closure writes each perturbed sub-state via `Proxy::set`, calls `model.evaluate()`, and reads the derivative `Proxy`s back — then writes the combined final state and calls `evaluate()` once more so `EvaluationState` reflects what's about to be committed, not the last hypothetical sub-step.
5. `registry.commit()` (Art. 1.3 §1, 9.8), then `std::thread::sleep(tick_interval)`.

There is no catalog build step, no publish step, no per-tick drain step, and no second thread — none of `IoImage`/`SnapshotBus`/`CommandQueue`/`BootCatalogs` exist to build or drain, and there is no `set_adapter()` to have called (Art. 11's note on Art. 11.1). A panic anywhere in this body is caught by the outer `catch_unwind` and turned into `ServiceEvent::Panicked` (Art. 11.10).

**Art. 11.4.** ~~`SnapshotBus` and `CommandQueue` are the only two thread-safe bridges, with no tokio dependency (only `std::sync`):~~
- ~~**`SnapshotBus`** (`Arc<RwLock<HashMap<String, f64>>>`): the "plant thread" publishes each sensor's value every tick; any outside reader only reads.~~
- ~~**`CommandQueue`** (`Arc<Mutex<std::sync::mpsc::Sender<(String, f64)>>>`): whatever is outside pushes `(name, value)`; the plant drains it at the start of each tick. The `Mutex` exists because an OPC-UA write callback requires `Fn(...) + Send + Sync` and `Sender` alone isn't `Sync`. It doesn't know what OPC-UA, TEP, or `StateRegistry` are.~~ → see Art. 12.1, 12.2, 2026-07-29.

**Note (2026-07-15):** `SnapshotBus` was eliminated. `CurrentState` (Art. 1.3 §1, 3.6.2) explicitly took on the role of "last confirmed physical state" — no more intermediate publishing needed: `Sensor` (Art. 3.6.6) became `Send + Sync` and is exported, exactly once, via `Arc<Sensor>` in the boot handshake (Art. 11.8); any consumer (adapter, future Controller) calls `sensor.read()` directly, with no channel in between. ~~`CommandQueue` is unaffected — its reason to exist is different (external writes, not read coherence) and it stays as is.~~ → see Art. 12.1, 2026-07-29 (`CommandQueue` was eliminated too, once the same reasoning was applied to writes).

**Note (2026-07-29):** `CommandQueue` was eliminated — `Actuator` (Art. 12.1, 12.2) applies the exact same fix to writes that `Sensor` (Art. 3.6.6) and this article's 2026-07-15 note already applied to reads: instead of a bridge object relaying `(name, value)` pairs to the plant thread, `Actuator` is itself `Send + Sync` and is written to directly by the adapter thread. Nothing bridges threads anymore, in either direction.

**Note (2026-08-07):** one layer further — there is no adapter thread left to write from (Art. 11's note), so the "written to directly by the adapter thread" half of the note above no longer has a writer on the other end. `Actuator` (Art. 12.1) is now just a bare trait a component implements on itself — not even an object something external hands a value to; see Art. 12.1-12.3.

§1 (2026-07-14, historical — about the now-repealed `SnapshotBus` above) Found during a discussion about simplifying the read bridge, then verified directly in the code: the original implementation of `SnapshotBus::publish(name, value)` took the `write()` lock **once per sensor**, inside the `for name in &sensor_names` loop in the tick loop (`Simulation::spawn_plant_thread`). Since the lock was released between one sensor and the next, a concurrent reader (the "OPC-UA thread") could — in theory — read the `HashMap` in the middle of that sequence and see a mix of values from different ticks across distinct variables: there wasn't, in fact, an atomic "snapshot" of the whole tick, contrary to what the name `SnapshotBus` suggests. Fixed at the time by swapping `publish()` for `publish_all(...)` (single lock per tick) — the whole change was superseded by `SnapshotBus`'s elimination the following day; kept here only as a historical record of the reasoning that led to that elimination.

**Art. 11.5.** (moot, 2026-08-07) This article described `spawn_adapter_thread` — the second thread `run()` used to spin up when `set_adapter()` was called, and the `opcua_adapter::serve(...)` signature it invoked at each point in that mechanism's history. `Simulation` doesn't spawn a second thread anymore, in any configuration (Art. 11's note on Art. 11.1) — there is no `spawn_adapter_thread` function left in `monjolo/src/simulation.rs` to describe. `monjolo/src/adapter/opcua.rs` still physically exists, still exports a `serve()` function with roughly the shape this article once tracked, but nothing calls it and it doesn't currently compile under its own `opcua` feature (Art. 10.6's note). Kept as a repealed article, not deleted, so the article numbering and every cross-reference into it (Art. 12.5) stay stable.

§1 (moot, 2026-08-07) The `tokio::runtime::Builder::new_current_thread()` reasoning this paragraph recorded was specific to `spawn_adapter_thread`, which no longer exists (this article's note) — there is no runtime being created anywhere in `Simulation` today, current-thread or otherwise. Kept as historical record of a decision that applied to code since removed.

**Art. 11.6.** `tep-plant/src/bin/tep_plant.rs`: `main()` is synchronous — no `#[tokio::main]`, no `async fn main()`, no `.await`. `Simulation::run()` is the only thing that creates a runtime, internally. `tep-plant`'s `Cargo.toml` doesn't depend on `tokio` directly.

**Art. 11.8.** ~~`DynamicModel` gained `sensors(&self) -> Vec<(String, String)>`...~~ **Note (2026-08-07):** `DynamicModel` never kept this method — it's back to exactly `name()`, `evaluate()`, `state_keys()` (Art. 1.1, 2.1). There is no model-declared sensor concept, no `add_sensor()` to merge it with, and no handshake (`std::sync::mpsc::channel`, in any of the three payload shapes this article tracked over time — `Vec<String>`, then `HashMap<String, Arc<Sensor>>`, then `BootCatalogs`) exporting anything from the plant thread to a second thread, because there is no second thread (Art. 11.5's note). A `Sensor` is still perfectly constructible — `Sensor::new(registry, key, behavior)` (Art. 3.6.3) — just not through any framework-provided declaration/export path; whoever wants one builds it themselves and holds onto it (a test, a future `Controller`), same as any other value.

**Art. 11.9.** `tep-plant/src/initial_state.rs` (a rigid struct, one Rust field per TOML key, matching position-by-position with `teprob.f`'s `YY(1..50)`) was deleted — replaced by `monjolo::snapshot::Snapshot`, generic: it loads any TOML file and flattens the nested tables into dotted keys (`[state.reactor_vapor] A = 1.0` becomes `"state.reactor_vapor.A" -> 1.0`) in a `HashMap<String, f64>`. `Snapshot::get(key) -> Option<f64>`; `Snapshot::from_pairs(&[(&str, f64)])` for testing. `Reactor::new(registry, initial: &Snapshot)` fetches only the keys it cares about, a missing key becomes `0.0`. ~~`TennesseeEastmanModel::new(registry, initial: &Snapshot)`~~ **Note (2026-08-07):** `tep-plant::model::new(registry, initial: &Snapshot) -> Composite` (Art. 2.5/2.6) — passes the same `&Snapshot` on to the four subsystems — ~~only `Reactor` uses it so far; `Separator`/`Stripper`/`Compressor` are still born without an initial condition~~ → all four consume `Snapshot` today, 2026-07-12. `tep_plant.rs` loads the `Snapshot` (~~`Snapshot::from_file("src/cases/te_exp3_snapshot.toml")`~~ **Note (2026-08-07):** path is `"src/snapshots/te_exp3_snapshot.toml"` today) and passes it through a closure to `set_model`, since `model::new` doesn't fit as a direct function pointer (two parameters).

**Art. 11.10.** ~~`Simulation` is the lifecycle manager/supervisor: `run()` orchestrates 0/1/2 services depending on what was configured — it spawns the "plant thread" only if `set_model()` was called, spawns the "adapter thread" only if `set_adapter()` was called (`AdapterConfig`...), and returns `Err` without spawning anything if neither was configured. Supervisor (`ServiceEvent`/`ServiceKind`, private in `simulation.rs`)...~~ **Note (2026-08-07):** simpler now — there is exactly one possible service, the plant thread, not 0/1/2. `run()` requires `set_model()` to have been called (`Err` otherwise, no thread spawned) and always spawns exactly the plant thread when it has been — there is no `set_adapter()`/`AdapterConfig` consumption left in `Simulation` at all (`AdapterConfig` still exists as a type in `monjolo/src/adapter/mod.rs`, feature-gated behind `opcua`, but nothing constructs or passes one to anything). `ServiceKind` never existed to distinguish between services, because there's only ever the one; the private `enum ServiceEvent { Stopped, Failed(String), Panicked(String) }` (`simulation.rs`) is otherwise unchanged — the plant thread runs inside `std::panic::catch_unwind` and sends exactly one `ServiceEvent` over a lifecycle channel before returning. `run()` still blocks on `events_rx.recv()` — tested (`run_returns_err_instead_of_hanging_when_plant_panics`).

§1 (open item, left explicit on purpose) There is no cooperative cancellation — neither the plant thread nor the adapter thread checks for a stop signal; when one dies, the other (if any) is not notified, and `run()` just stops waiting for it. It's up to whoever called `run()` to decide to end the process. True graceful shutdown is the next step.

## About `Actuator` — the write-side mirror of `Sensor`

**Art. 12.1.** ~~(2026-07-29) `IoImage`, `CommandSink`, and `CommandQueue` were eliminated. `Actuator` (`monjolo/src/actuator/model.rs`) now mirrors `Sensor`'s design (Art. 3.6.6) on the write side: `Send + Sync`, holding its state behind an internal `Mutex`, exported exactly once via `Arc<Actuator>` in the same boot handshake that already exported `Arc<Sensor>` (Art. 11.8). No bridge object exists for either direction anymore — reads and writes are now symmetric.~~ **Note (2026-08-07):** the mailbox design this article and the next two described was itself short-lived. `Actuator` is now a bare trait, `monjolo/src/actuator/mod.rs`:
```rust
pub trait Actuator {
    fn write(&self, value: f64);
}
```
Symmetric with `Sensor` (`monjolo/src/sensor/mod.rs`, `trait Sensor { fn read(&self) -> f64; }`) in shape — one method each — but the two are unrelated traits, not a shared base type, and there is no boot handshake exporting either one anymore (Art. 11's note on Art. 11.8) — see Art. 3.5.1 §2's note. A component becomes actuable by implementing `Actuator` on itself directly; see Art. 12.8 (`Valve`/`Agitator`).

**Art. 12.2.** ~~`Actuator` is a mailbox, not a queue: `write(&self, value: f64)` overwrites any not-yet-consumed pending value...; `take(&self) -> Option<f64>` consumes it...~~ **Note (2026-08-07):** there is no `take()`, no mailbox, no separate `Actuator` object at all — `write(&self, value: f64)` is the entire trait (Art. 12.1). How a command is held between one `write()` and the next `evaluate()` is entirely up to whoever implements the trait. `Valve`/`Agitator` (Art. 12.8) hold it in a `Cell<f64>`, overwritten (last-write-wins) on every `write()` and read directly at the top of `evaluate()` — no "already consumed" tracking, no `None` case, just whatever the cell currently holds. `&self`, not `&mut self`, for the same reason as before: `write()`/`evaluate()` can't take `&mut self` on a component that might be shared, so mutation needs to happen through interior mutability regardless of which concrete cell type ends up holding it.

**Art. 12.3.** ~~`Actuator` does not know about `DynamicModel`, `Valve`, or `Agitator`... `Simulation::add_actuator(name: &str, actuator: Arc<Actuator>)` only catalogs the `Arc` for export to the adapter thread...~~ **Note (2026-08-07):** `add_actuator` doesn't exist — `Simulation` has no notion of `Actuator` at all anymore, catalogs it nothing, exports it nowhere. `Actuator` is purely a trait a `DynamicModel` can also implement on itself (Art. 12.8) — whoever holds a handle to that component (a test, a future `Controller`) calls `.write(value)` on it directly, no framework mediation, no catalog, no adapter thread to route through (Art. 11's note).

§1 ~~(2026-07-29) This resolves the pending item from Art. 11.2 §1...~~ **Note (2026-08-07):** moot along with `add_actuator` itself (this article's note) — there is no ordering problem to resolve when there is no separate registration call at all. `Valve`/`Agitator` are built and `add_dynamic`'d in the same place, at the same time — see Art. 12.8.

**Art. 12.4.** (repealed 2026-08-07) ~~`Simulation`'s boot handshake (Art. 11.8) exports both catalogs at once via a private `BootCatalogs { sensors: HashMap<String, Arc<Sensor>>, actuators: HashMap<String, Arc<Actuator>> }`...~~ There is no boot handshake left to export anything through (Art. 11's note on Art. 11.8) — `BootCatalogs` and `Simulation::build_catalogs()` don't exist. Kept as a repealed article so the numbering and cross-references into it (Index, Art. 10.1/10.3/11.3) stay stable.

**Art. 12.5.** (moot, 2026-08-07) ~~Current `opcua_adapter::serve()` signature: `serve(sensors: HashMap<String, Arc<Sensor>>, actuators: HashMap<String, Arc<Actuator>>, endpoint: &str) -> Result<(), String>`...~~ This signature is still literally what's in `monjolo/src/adapter/opcua.rs` today, but nothing calls it (Art. 10.6's note) and it wouldn't even compile under the `opcua` feature — its own `use crate::actuator::model::Actuator;` points at a module path that stopped existing once Art. 12.1 flattened `Actuator` into a bare trait.

**Art. 12.6.** (moot, 2026-08-07) ~~The OPC-UA write callback... captures its own bound `Arc<Actuator>` per node directly...~~ Same status as Art. 12.5 — describes a code path with no caller and a broken import, not a currently exercised mechanism.

**Art. 12.7.** (moot, 2026-08-07) ~~There is no `sensor_names()`/`actuator_names()` method anywhere anymore...~~ Still true as a narrow fact (no such methods exist), but the article's context — an adapter receiving live catalogs — no longer applies (Art. 12.4).

**Art. 12.8.** ~~(2026-07-30) `DynamicModel` gained `actuators(&self) -> Vec<(String, Arc<Actuator>)>`... `Valve`/`Agitator` (`monjolo/src/actuator/dynamic.rs`) each gained a field holding their own `Arc<Actuator>`, consumed via `incoming.take()`...~~ **Note (2026-08-07):** superseded by a simpler design. `DynamicModel` never kept an `actuators()` method (Art. 11.8's note applies the same way on the write side — there's nothing left to declare it to). `Valve`/`Agitator` moved out of `monjolo` entirely — they're TEP-specific physical components, not generic framework building blocks, so they now live in `tep-plant/src/subsystems/actuators.rs` (Art. 2.6's note) — and each `impl`s both `DynamicModel` and `Actuator` (Art. 12.1) *directly on itself*, with no intermediary `Arc<Actuator>` field:

```rust
pub struct Valve {
    tau: f64,
    command: Cell<f64>,
    position: Proxy,
    derivative: Proxy,
}

impl Actuator for Valve {
    fn write(&self, value: f64) {
        self.command.set(value);
    }
}

impl DynamicModel for Valve {
    fn evaluate(&self) {
        let position = self.position.get();
        self.derivative.set((self.command.get() - position) / self.tau);
    }
    // ...
}
```

`command: Cell<f64>` (not a plain field) for the same reason as before: `write(&self, ...)` and `evaluate(&self)` are both `&self`, so mutating the pending command needs interior mutability regardless of which type holds it (Art. 12.2's note). `write()` just overwrites `command`; `evaluate()` reads it straight off `self`, no `take()`, no separate object anyone hands a value to. `Agitator` is the identical pattern, one field down (no `name` parameter — it's a singleton in the plant).

§1 (2026-07-30, still accurate) `tep-plant::model::new()` (Art. 2.6, itself renamed/moved from `TennesseeEastmanModel::new()`) builds this for real: one `Valve` (name `"cooling_water"`, τ from `VTAU(10)` in `teprob.f`, 5s) and the plant's one `Agitator` (τ from `VTAU(12)`, also 5s), both `add_dynamic`'d into the composite alongside the four chemical subsystems. ~~each constructed with its own `Arc<Actuator>` — one clone `add_dynamic`'d into the component, the other clone handed to `actuators()`'s returned list under `"TEP/Reactor/CoolingWaterValve/Command"`/`"TEP/Reactor/Agitator/Command"`. Each is paired with a companion `Sensor`...~~ **Note (2026-08-07):** the `Arc<Actuator>`/companion-`Sensor`/named-export part no longer applies — there is no export mechanism left to hand either one to (Art. 11's note, Art. 12.4). Position/speed still genuinely integrate via the first-order lag (Art. 12.2's note) and are still directly writable through `Actuator::write()`/readable through the `StateRegistry` by anything holding a handle (a test, today) — just not published to an outside client by name anymore. Not all 12 real TEP valves (XMV 1-11) are wired, only this one plus the agitator (XMV-12) — same "representative subset" scope already used for sensors (Art. 2.6, §1, only 4 of 41 XMEAS exposed).
