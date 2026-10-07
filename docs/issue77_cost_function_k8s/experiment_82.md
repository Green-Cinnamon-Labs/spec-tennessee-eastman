# Experiment #82 — J under disturbance, observed by Kubernetes

**Issue:** https://github.com/Green-Cinnamon-Labs/spec-tennessee-eastman/issues/82
**Epic:** #77
**Date:** 2026-10-07 (not started)

---

The epic #77 built the chain plant → historian → `plant-supervisor` → `Plant.status`, and showed it working at nominal operation: J ≈ 166 $/h, `Compliant`. It also showed the verdict flipping, but only by *changing the rule* (lowering `maxCost` to 150 with `kubectl patch`). What has not been shown yet is the case that matters for the thesis: the **plant itself** degrading while the rules stay fixed, and Kubernetes noticing. Experiment #82 is that test — it is the evidence that the supervisory layer actually observes the plant's economic state, not just the numbers someone typed into a policy.

The procedure is simple to state. With the plant running at the Mode 1 base case and the Mode 1 policy active, first record a stretch of nominal operation (J, targets and limits all fine). Then switch on a TEP disturbance by writing its OPC-UA node — e.g. `disturbance.idv6 = 1`, loss of the A feed, the same switch already tested on 2026-10-02 — and keep the policy untouched. From then on, watch `Plant.status` over time: J should drift away from its nominal value, some target or limit should eventually fail, and after `persistenceEvaluations` (3) failing evaluations in a row `PolicyCompliant` should flip to `False` and the phase to `NonCompliant`.

What gets measured is the *observation*, not the disturbance itself (characterizing each IDV is #47). The questions are: how J evolves after the disturbance and which of its 12 terms move; which condition fails first — cost (`CostWithinBudget`), product (`TargetsMet`) or the operating envelope (`ConstraintsSatisfied`); how long it takes from switching the disturbance on to the verdict flipping, split into the plant's own response time and the delay added by the supervisor (60 s averaging window, 30 s evaluation interval, persistence of 3); and whether the verdict comes back to `Compliant` when the disturbance is switched off. A second disturbance with a different signature (e.g. IDV1, a step in the A/C feed ratio) would show whether the verdict distinguishes an economic problem from a limit problem.

The main obstacle is time. IDV6 is a slow, severe disturbance: in the original TEP it takes hours of *simulated* time to push the plant to its limits, and the simulated plant currently runs at about 2× real time, so a full run could take hours of wall-clock time — and the supervisor's 60 s window is in wall-clock time too, covering only about 2 simulated minutes. Before running, a few things have to be decided, listed below. The result is meant to go into `experimentos.md` as a new experiment and into the thesis as the main piece of evidence for the supervisory layer.

## Decisions before running

- **Simulation speed** — run the plant faster than 2× real time (making `tick_interval` configurable is #69), or accept a long run.
- **Window and interval** — keep 60 s / 30 s, or lengthen the window so J is judged over a meaningful slice of simulated time (or move the window to simulated time using the plant's `clock.t_h` signal).
- **Budget** — with `maxCost: 179` and J ≈ 166, J must rise about 8 % before the cost condition fails; decide whether that is the intended sensitivity (see [operating_policy_mode1.md](operating_policy_mode1.md), "Decisions to revisit").
- **Recording** — `Plant.status` only holds the latest verdict, so the run needs a time series: a script polling `kubectl get plant tep -o json` (with the plant's `clock.t_h`), the supervisor's own log (one line per evaluation), or the IHM's SQLite sessions.
- **Which disturbances** — IDV6 alone, or IDV6 plus a faster one (IDV1) for contrast; and whether to let the plant reach its shutdown limits (the plant's shutdown is only a diagnostic today, #70).
