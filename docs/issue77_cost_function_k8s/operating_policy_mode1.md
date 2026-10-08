# The TEP Mode 1 policy — `policy-mode1.yaml` explained (Issue #77)

**File:** [tep-lab/local/k8s/tep/policy-mode1.yaml](../../../tep-lab/local/k8s/tep/policy-mode1.yaml)
**Sources:** Downs & Vogel (1993), Tables 4, 5 and 6 (base case and operating constraints)
**Date:** 2026-10-07

---

This file is the policy the plant is judged against. Where the cost function says *how to measure* the cost (see [cost_function_downs_vogel.md](cost_function_downs_vogel.md)), the policy says *what counts as operating well*: what the plant must deliver, which limits it must respect, how much it may cost, and how patient the verdict should be.

It is a Kubernetes object of type `OperatingPolicy` (one of the three CRDs created in #79). Writing a policy is the control engineer's job: it is the place where operating knowledge — a production mode, an operating envelope, an economic budget — becomes something Kubernetes can check. The supervisor never invents any of these numbers; it only compares the plant against what is declared here.

## Why a policy is separate from the cost function

Downs & Vogel define one cost function but six **operating modes** (combinations of production rate and G/H product ratio). The mode is not derived from J: it is a business decision ("this week we produce this much, at this ratio"), and J is what you try to keep low *within* that mode. The design mirrors that: one `CostFunction` can be used by several `OperatingPolicy` objects, and the `Plant` points to whichever policy is active. Switching mode means switching policy, without touching the formula.

## Field by field

### `costFunctionRef: tep-downs-vogel` — [line 13](../../../tep-lab/local/k8s/tep/policy-mode1.yaml#L13)

Which cost function judges this policy, by name. It must be a `CostFunction` in the same namespace. This is the only required field: without it the supervisor would have no J to compute. If the name doesn't exist, the plant goes to `Pending` with the reason `CostFunctionNotFound`.

### `description` — [line 14](../../../tep-lab/local/k8s/tep/policy-mode1.yaml#L14)

Free text for humans. It has no effect on the verdict; it exists so that `kubectl get op -o yaml` tells you what the policy is meant to represent.

### `windowSeconds: 60` — [line 15](../../../tep-lab/local/k8s/tep/policy-mode1.yaml#L15)

How much time each signal is averaged over before it is judged. The supervisor asks the historian for the mean of each signal over the last 60 seconds, and everything below (J, targets, limits) is computed on those means. Averaging exists to filter measurement noise and fast oscillations, so the verdict reacts to the process, not to a single sample.

The window is in **wall-clock** time. The plant runs at about 2× real time, so 60 s covers about 2 simulated minutes. That is short compared to the TEP's slow dynamics (levels and compositions take hours of simulated time to settle), which is one of the decisions to revisit below.

### `maxCost: 179.0` — [line 16](../../../tep-lab/local/k8s/tep/policy-mode1.yaml#L16)

The **budget** for J, in the cost function's unit ($/h). If the averaged J goes above it, the condition `CostWithinBudget` becomes `False`. This is the economic part of the verdict: the plant may be producing the right thing within its limits and still be operating too expensively.

179 is **not** a number from the paper. It is a policy choice: about 5 % above the paper's base-case reference of 170.6 $/h. The field is optional; without it J is still computed and shown, but never judged.

### `persistenceEvaluations: 3` — [line 17](../../../tep-lab/local/k8s/tep/policy-mode1.yaml#L17)

How many failing evaluations **in a row** are needed before the plant is declared `NonCompliant`. One bad evaluation only increments a counter (visible as "Violações" in the IHM); a passing one resets it. With the Plant evaluated every 30 s, 3 means the problem has to last about 90 s.

The idea comes from control-loop performance monitoring (Bradu et al. 2018, Cap 2): an alarm should mean a sustained problem, not a transient. Without it, a single noisy window during a disturbance would flip the verdict back and forth.

### `targets` — [lines 18–27](../../../tep-lab/local/k8s/tep/policy-mode1.yaml#L18)

What the plant must **deliver**. Each target is a signal, a value and a tolerance in percent: the averaged signal must stay within `value ± value × tolerance / 100`. If any target is missed, `TargetsMet` becomes `False`.

| Signal | Meaning | Value | Tolerance | Accepted range |
|---|---|---|---|---|
| `xmeas.stream11.flow_rate` (XMEAS 17) | Product flow leaving the stripper | 22.949 m³/h | ±5 % | 21.80 – 24.10 m³/h |
| `xmeas.stream11.component.g` (XMEAS 40) | Fraction of G in the product | 53.724 mol % | ±5 % | 51.04 – 56.41 mol % |
| `xmeas.stream11.component.h` (XMEAS 41) | Fraction of H in the product | 43.828 mol % | ±5 % | 41.64 – 46.02 mol % |

These are the base-case values of Tables 4 and 5, i.e. Mode 1's "order": produce this much product at a 50/50 G/H mass ratio. The ±5 % comes from the paper's statement that product flow variability above ±5 % is harmful downstream.

Mode 1's G/H ratio is not one signal, so it is expressed as two separate targets on G and H. This is an approximation: the ratio can drift a little while each component stays inside its own band.

### `constraints` — [lines 28–41](../../../tep-lab/local/k8s/tep/policy-mode1.yaml#L28)

The **operating envelope**: signals that must stay inside `[min, max]`. Either bound can be omitted. If any limit is broken, `ConstraintsSatisfied` becomes `False`.

| Signal | Meaning | Limit | Why it exists (Table 6) |
|---|---|---|---|
| `xmeas.reactor.pressure` (XMEAS 7) | Reactor pressure | ≤ 2895 kPa | Equipment protection; the shutdown limit is 3000 kPa |
| `xmeas.reactor.level` (XMEAS 8) | Reactor liquid level | 50 – 100 % | Keeps the cooling coils covered; shutdown below 2 m³ / above 24 m³ |
| `xmeas.reactor.temperature` (XMEAS 9) | Reactor temperature | ≤ 150 °C | Equipment protection; shutdown at 175 °C |
| `xmeas.separator.level` (XMEAS 12) | Product separator level | 30 – 100 % | Normal operating range; shutdown below 1 m³ / above 12 m³ |
| `xmeas.stripper.level` (XMEAS 15) | Stripper base level | 30 – 100 % | Normal operating range; shutdown below 1 m³ / above 8 m³ |

These are the **normal** operating limits of Table 6, deliberately not the shutdown limits. The policy's job is to say "the plant has left its normal envelope" before the plant's own interlock has to stop it; the shutdown itself is a separate mechanism in tep-plant (#70).

### `controlLoops` and the loop settings — the second observation level (#85)

> **Status:** since block 4 of #85 (tep-lab#27), `policy-mode1.yaml` declares the three loops below, with **provisional** thresholds (`minPredictability: 0.1`, `minOutputStd: 0.05`) that will be calibrated in block 6. At nominal operation in Kind: separator level PI 0.34 and stripper level PI 0.32, both judged and healthy; reactor pressure below the variability gate (valve σ 0.009 %), not judged.

Besides the economic criteria above, a policy can declare the plant's **control loops** whose *quality* must be watched. This is the second observation level: not "is the plant operating cheaply and inside its envelope?", but "are the controllers doing their job well?". The index is the Predictability Index of Bradu et al. (2017): an autoregressive model is fitted to each loop's error `SP − PV` and asked how much of it it can predict a little ahead. A regular, predictable error gives PI near 1; an erratic error, like white noise, gives PI near 0. The historian computes the index; the supervisor judges it.

The result is a **separate verdict** — the condition `ControlLoopsHealthy` — that never changes the plant's `phase` or `PolicyCompliant`. That is deliberate: a plant can be economically fine with a badly tuned loop, or the other way round, and the experiment (#82) wants to show the two levels side by side.

Each loop ([ControlLoop, operatingpolicy_types.go:50](../../../plant-supervisor/api/v1alpha1/operatingpolicy_types.go#L50)) declares:

| Field | What it is | Why |
|---|---|---|
| `name` | Loop name in the status | To tell the loops apart in `kubectl` and the IHM |
| `pv` | Historian key of the measured variable | The error is `setpoint − pv` |
| `setpoint` | The controller's setpoint | In the TEP it is a constant inside the plant's Rust code, so it has to be declared here |
| `op` | Historian key of the controller output (the valve position) | Used by the variability gate |
| `timeConstantSeconds` | Closed-loop settling time `T` | Sets the prediction horizon `b = ceil(T / t_s)` — the article's rule |
| `minPredictability` | Threshold `PI_L` | Below it, the loop is considered poorly tuned |
| `minOutputStd` | Variability gate `σ̄_y` | The loop is only judged if its valve actually moves; a saturated, idle or manual loop says nothing about tuning |

And three settings shared by all loops ([lines 127–146](../../../plant-supervisor/api/v1alpha1/operatingpolicy_types.go#L127)):

- **`loopWindowSeconds`** (default 300) — the window `t_W` over which each index is computed. It is longer than the economic `windowSeconds` because the index needs a time series of several loop time constants, not just a mean.
- **`loopSampleIntervalSeconds`** (default 1) — the sampling `t_s`; the historian resamples the series to it before fitting the model.
- **`loopPersistenceEvaluations`** (default 3) — Bradu's `N`: how many evaluations in a row with an unhealthy loop before `ControlLoopsHealthy` turns `False`. It has its own counter, separate from the economic one.

The three TEP loops declared in the file are the plant's three proportional controllers, the classic Downs & Vogel ones:

| `name` | `pv` | `op` | `setpoint` |
|---|---|---|---|
| `reactor_pressure` | `xmeas.reactor.pressure` | `valve.purge.position` | 2705 kPa |
| `separator_level` | `xmeas.separator.level` | `valve.separator_underflow.position` | 50 % |
| `stripper_level` | `xmeas.stripper.level` | `valve.stripper_product.position` | 50 % |

Two things already measured on the running plant (with sensor noise, #66) shape how these will be read; both are discussed in #87. First, these controllers are proportional and keep a constant offset (the reactor pressure sits a few kPa below 2705), so the index is computed on the error's **fluctuation around its mean**, and the offset is reported apart. Second, at nominal operation the level errors are dominated by sensor noise, so their PI is low (≈ 0.2) without the tuning being bad — Bradu's own "Noise" category — and the reactor pressure valve barely moves (σ ≈ 0.008 %), so the gate may leave that loop unjudged (#86). The article's thresholds (`PI_L` = 0.4, `σ̄_y` = 1 %) come from CERN's plant and will not be used as they are.

## How the supervisor turns this into a verdict

Every evaluation, for the active policy:

1. Ask the historian for the 60 s mean of every signal named in the cost function, the targets and the constraints.
2. Compute J from the cost function; check it against `maxCost` → `CostWithinBudget`.
3. Check each target against its tolerance → `TargetsMet`.
4. Check each constraint against its bounds → `ConstraintsSatisfied`.
5. If any of the three failed, increment the violation counter; otherwise reset it.
6. If the counter reached `persistenceEvaluations`, the plant is `NonCompliant` (`PolicyCompliant = False`); otherwise `Compliant`.

The result is what you see in the IHM's K8S SUPERVISOR panel and in `kubectl describe plant tep`. The code is [Evaluate](../../../plant-supervisor/internal/evaluate/evaluate.go#L86) and the persistence rule [NextViolations](../../../plant-supervisor/internal/evaluate/evaluate.go#L130).

When the policy declares control loops, the same evaluation then runs the second level, independently of the first:

7. Ask the historian for the Predictability Index of each loop over `loopWindowSeconds` (`POST /loop-performance`).
8. For each loop: if the valve's standard deviation is not above `minOutputStd`, the loop is **not judged**; otherwise it is unhealthy when its PI is below `minPredictability` ([EvaluateLoops](../../../plant-supervisor/internal/evaluate/loops.go#L42)).
9. If at least one judged loop is unhealthy, increment the loop violation counter; otherwise reset it. After `loopPersistenceEvaluations` in a row, `ControlLoopsHealthy` turns `False`. If no loop could be judged, it is `Unknown` (`NoLoopEvaluated`).

A historian failure on step 7 leaves only `ControlLoopsHealthy` as `Unknown`; the economic verdict of steps 1–6 stands.

## Decisions to revisit

These are engineering choices, not facts from the paper, and several of them decide whether the #82 experiment will show the verdict flipping.

1. **The budget of 179 $/h is arbitrary.** The simulated plant runs at about 166 $/h, so a disturbance has to raise J by about 8 % before the budget fails. A tighter budget makes the cost condition more sensitive; a looser one makes it mostly about the limits.
2. **±5 % applied to everything.** The paper's ±5 % is about product *flow*. For composition, ±5 % of 53.7 mol % is ±2.7 mol %, which may be too loose to detect a product-quality problem.
3. **G/H ratio as two separate targets.** Checking the ratio itself would need a new feature in the policy format (a target on the ratio of two signals).
4. **A 60 s wall-clock window.** It covers about 2 simulated minutes. An economic cost is usually judged over much longer periods; a longer window (or a window in simulated time, using the plant's `clock.t_h` signal) would make J steadier.
5. **Only normal limits.** Shutdown limits are left to the plant's interlock (#70). Whether the policy should also warn when the plant gets *close* to a shutdown limit is an open choice.
6. **What the format can't express yet.** Rate-of-change limits, and limits on the controllers' own outputs (e.g. a valve saturated at 0 % or 100 %).
7. **Loop thresholds.** `minPredictability` and `minOutputStd` for the three loops have to be calibrated on this plant (block 6 of #85); the article's values do not transfer (#87). Whether the proportional controllers should become PI controllers is an open question in #87.

## How to change it

Edit the file and re-apply it: `kubectl apply -f tep-lab/local/k8s/tep/policy-mode1.yaml`, or change a single field in place, e.g. `kubectl patch operatingpolicy tep-mode1 --type merge -p '{"spec":{"maxCost":150}}'`. The supervisor re-evaluates immediately and the violation counter starts counting from the new rules. To try another mode, create a second `OperatingPolicy` with a different name and point the Plant to it (`policyRef` in [plant.yaml](../../../tep-lab/local/k8s/tep/plant.yaml)); the counter restarts when the policy changes.
