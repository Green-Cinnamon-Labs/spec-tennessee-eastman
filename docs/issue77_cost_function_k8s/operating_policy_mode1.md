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

## How the supervisor turns this into a verdict

Every evaluation, for the active policy:

1. Ask the historian for the 60 s mean of every signal named in the cost function, the targets and the constraints.
2. Compute J from the cost function; check it against `maxCost` → `CostWithinBudget`.
3. Check each target against its tolerance → `TargetsMet`.
4. Check each constraint against its bounds → `ConstraintsSatisfied`.
5. If any of the three failed, increment the violation counter; otherwise reset it.
6. If the counter reached `persistenceEvaluations`, the plant is `NonCompliant` (`PolicyCompliant = False`); otherwise `Compliant`.

The result is what you see in the IHM's K8S SUPERVISOR panel and in `kubectl describe plant tep`. The code is [Evaluate](../../../plant-supervisor/internal/evaluate/evaluate.go#L86) and the persistence rule [NextViolations](../../../plant-supervisor/internal/evaluate/evaluate.go#L130).

## Decisions to revisit

These are engineering choices, not facts from the paper, and several of them decide whether the #82 experiment will show the verdict flipping.

1. **The budget of 179 $/h is arbitrary.** The simulated plant runs at about 166 $/h, so a disturbance has to raise J by about 8 % before the budget fails. A tighter budget makes the cost condition more sensitive; a looser one makes it mostly about the limits.
2. **±5 % applied to everything.** The paper's ±5 % is about product *flow*. For composition, ±5 % of 53.7 mol % is ±2.7 mol %, which may be too loose to detect a product-quality problem.
3. **G/H ratio as two separate targets.** Checking the ratio itself would need a new feature in the policy format (a target on the ratio of two signals).
4. **A 60 s wall-clock window.** It covers about 2 simulated minutes. An economic cost is usually judged over much longer periods; a longer window (or a window in simulated time, using the plant's `clock.t_h` signal) would make J steadier.
5. **Only normal limits.** Shutdown limits are left to the plant's interlock (#70). Whether the policy should also warn when the plant gets *close* to a shutdown limit is an open choice.
6. **What the format can't express yet.** Rate-of-change limits, and limits on the controllers' own outputs (e.g. a valve saturated at 0 % or 100 %).

## How to change it

Edit the file and re-apply it: `kubectl apply -f tep-lab/local/k8s/tep/policy-mode1.yaml`, or change a single field in place, e.g. `kubectl patch operatingpolicy tep-mode1 --type merge -p '{"spec":{"maxCost":150}}'`. The supervisor re-evaluates immediately and the violation counter starts counting from the new rules. To try another mode, create a second `OperatingPolicy` with a different name and point the Plant to it (`policyRef` in [plant.yaml](../../../tep-lab/local/k8s/tep/plant.yaml)); the counter restarts when the policy changes.
