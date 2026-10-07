# The TEP cost function — `cost-function-downs-vogel.yaml` explained (Issue #77)

**File:** [tep-supervisor/local/k8s/tep/cost-function-downs-vogel.yaml](../../../tep-supervisor/local/k8s/tep/cost-function-downs-vogel.yaml)
**Source:** Downs & Vogel (1993), *A plant-wide industrial process control problem*, Table 9, p. 251
**Date:** 2026-10-07

---

This file is where the TEP's operating cost J lives. The operator in Kubernetes is generic and knows nothing about the TEP, so this YAML is the only place where Downs & Vogel's prices and formula appear. If you want to change how the plant's cost is measured — a new price, a new term, a different plant — this is the file you edit, not Go code.

It is a Kubernetes object of type `CostFunction` (one of the three CRDs created in #79). It only *declares* the formula. The operator reads it, asks the historian for the signals it mentions, and computes J every evaluation (see [kubernetes_features.md](kubernetes_features.md)).

## What J measures

Downs & Vogel give the TEP an explicit economic objective: the operating cost in dollars per hour. Their argument (p. 251) is that the cost of running this plant is dominated by **raw material that is lost** instead of becoming product. Raw material leaves the process in three ways, and the formula charges for each, plus two utilities:

1. **The purge (stream 9).** The purge exists to bleed the inert B and the byproduct F out of the recycle loop, otherwise they would accumulate. But it also throws away whatever else is in that gas: unreacted A, C, D, E and even product G and H. Every kgmol that leaves through the purge is money lost.
2. **The product stream (stream 11).** The product should be G and H. Any D, E or F that leaves with it is raw material (or byproduct) sold as if it were product, so it is charged as a loss.
3. **The byproduct F.** Forming F consumes reactants without producing anything sellable. The paper charges F through the purge and product terms above (F has its own price per kgmol).
4. **Compressor power.** The recycle compressor consumes electricity.
5. **Stripper steam.** The stripper uses steam to separate the product.

So J is **not** a physical law of the plant, it is a design choice: a way of saying "this is what operating well means in money". The thesis uses it because it is the objective the TEP benchmark itself proposes, which gives the supervisory layer a criterion everybody can agree on.

## The formula

```
J [$/h] = (Σ price_i · x_purge,i) · (44.79 · F_purge)        purge: kscmh → kgmol/h
        + (Σ price_i · x_product,i) · (9.21 · F_product)     product (only D, E, F): m³/h → kgmol/h
        + 0.0536 · W_compressor + 0.0318 · F_steam
```

- `price_i` — cost of component *i* in $/kgmol (Table 9): A 2.206, C 6.177, D 22.06, E 14.56, F 17.89, G 30.44, H 22.94. B is inert and has no cost.
- `x_purge,i`, `x_product,i` — the mole fraction of component *i* in the purge or the product, as measured by the plant's analyzers (in mol %).
- `F_purge` — purge flow in kscmh (thousands of standard cubic meters per hour). The factor **44.79** converts it to kgmol/h.
- `F_product` — product flow in m³/h of liquid. The factor **9.21** converts it to kgmol/h.
- `W_compressor` — compressor power in kW, priced at 0.0536 $/kWh.
- `F_steam` — stripper steam in kg/h, priced at 0.0318 $/kg.

This header is also written as a comment at the top of the file: [lines 1–13](../../../tep-supervisor/local/k8s/tep/cost-function-downs-vogel.yaml#L1).

## How the formula becomes YAML terms

The `CostFunction` type only understands one shape: a sum of terms, each `coefficient × signal × signal …`. The paper's formula fits that shape once the brackets are expanded: "Σ price × fraction × (factor × flow)" is the same as one term per component, `(price × factor / 100) × flow × fraction`. The `/100` is there because the analyzers report mol %, and the formula needs a fraction.

So every term folds **the price, the unit conversion and the % → fraction step into a single coefficient**, and keeps only the measured signals as variables. Worked example, purge A ([lines 24–26](../../../tep-supervisor/local/k8s/tep/cost-function-downs-vogel.yaml#L24)):

```yaml
- name: purge.a
  coefficient: 0.9880674    # 2.206 × 44.79 / 100
  signals: [xmeas.stream9.flow_rate, xmeas.stream9.component.a]
```

- `2.206` is the price of A, `44.79` the kscmh → kgmol/h factor, `/100` the mol % → fraction step, giving `0.9880674`.
- The two signals are the purge flow (XMEAS 10) and the fraction of A in the purge (XMEAS 29).
- At the paper's base case (purge 0.3371 kscmh, 32.958 mol % A) this term is `0.9880674 × 0.3371 × 32.958 ≈ 10.98 $/h`.

The signal names are the OPC-UA browse names published by tep-plant, the same keys the historian uses. Units are whatever the plant publishes, which is why the conversion factors matter: they assume the plant's units match the paper's (kscmh, m³/h, mol %, kW, kg/h).

## The 12 terms

| Term | What it charges | Coefficient (derivation) | Signals | Base case ($/h) |
|---|---|---|---|---|
| [`purge.a`](../../../tep-supervisor/local/k8s/tep/cost-function-downs-vogel.yaml#L24) | A lost in the purge | 0.9880674 (2.206 × 44.79 / 100) | purge flow × A in purge | 10.98 |
| [`purge.c`](../../../tep-supervisor/local/k8s/tep/cost-function-downs-vogel.yaml#L27) | C lost in the purge | 2.7666783 (6.177 × 44.79 / 100) | purge flow × C in purge | 22.36 |
| [`purge.d`](../../../tep-supervisor/local/k8s/tep/cost-function-downs-vogel.yaml#L30) | D lost in the purge | 9.880674 (22.06 × 44.79 / 100) | purge flow × D in purge | 4.19 |
| [`purge.e`](../../../tep-supervisor/local/k8s/tep/cost-function-downs-vogel.yaml#L33) | E lost in the purge | 6.521424 (14.56 × 44.79 / 100) | purge flow × E in purge | 40.84 |
| [`purge.f`](../../../tep-supervisor/local/k8s/tep/cost-function-downs-vogel.yaml#L36) | F (byproduct) in the purge | 8.012931 (17.89 × 44.79 / 100) | purge flow × F in purge | 6.11 |
| [`purge.g`](../../../tep-supervisor/local/k8s/tep/cost-function-downs-vogel.yaml#L39) | Product G lost in the purge | 13.634076 (30.44 × 44.79 / 100) | purge flow × G in purge | 22.26 |
| [`purge.h`](../../../tep-supervisor/local/k8s/tep/cost-function-downs-vogel.yaml#L42) | Product H lost in the purge | 10.274826 (22.94 × 44.79 / 100) | purge flow × H in purge | 7.96 |
| [`product.d`](../../../tep-supervisor/local/k8s/tep/cost-function-downs-vogel.yaml#L46) | D leaving with the product | 2.031726 (22.06 × 9.21 / 100) | product flow × D in product | 0.84 |
| [`product.e`](../../../tep-supervisor/local/k8s/tep/cost-function-downs-vogel.yaml#L49) | E leaving with the product | 1.340976 (14.56 × 9.21 / 100) | product flow × E in product | 25.73 |
| [`product.f`](../../../tep-supervisor/local/k8s/tep/cost-function-downs-vogel.yaml#L52) | F leaving with the product | 1.647669 (17.89 × 9.21 / 100) | product flow × F in product | 3.74 |
| [`compressor`](../../../tep-supervisor/local/k8s/tep/cost-function-downs-vogel.yaml#L56) | Compressor electricity | 0.0536 $/kWh | compressor power | 18.30 |
| [`steam`](../../../tep-supervisor/local/k8s/tep/cost-function-downs-vogel.yaml#L59) | Stripper steam | 0.0318 $/kg | steam flow | 7.32 |
| | | | **Total J** | **170.6** |

Totals at the base case: purge 114.7 $/h, product 30.3 $/h, compressor 18.3 $/h, steam 7.3 $/h. Two things stand out: **the purge is two thirds of the whole cost**, and inside it the largest single loss is E (40.8 $/h). That is why the purge is where a supervisory policy would look first if J goes up.

The base-case column is the same check the operator's unit test does: [TestDownsVogelBaseCaseCost](../../../tep-operator/internal/evaluate/evaluate_test.go#L84) feeds the paper's numbers into these 12 terms and expects 170.6 $/h.

## The other fields

- **`unit: "$/h"`** ([line 19](../../../tep-supervisor/local/k8s/tep/cost-function-downs-vogel.yaml#L19)) — just a label, copied into `Plant.status` and shown by `kubectl get plants` and the IHM. The operator doesn't convert anything; it is there so whoever reads J knows what the number means.
- **`reference: 170.6`** ([line 20](../../../tep-supervisor/local/k8s/tep/cost-function-downs-vogel.yaml#L20)) — J at nominal operation according to the paper. It is not a limit and doesn't affect the verdict; it is shown next to the current J so you can see at a glance how far the plant is from the paper's base case. The limit lives in the policy (`maxCost`), see [operating_policy_mode1.md](operating_policy_mode1.md).
- **`source`** ([line 21](../../../tep-supervisor/local/k8s/tep/cost-function-downs-vogel.yaml#L21)) — free text citing where the formula comes from. It exists because a cost function is a design choice, and anyone reading the cluster should be able to trace it back to the paper.

## Things to keep in mind

- **A typo in the paper.** In Table 9's purge breakdown, the line printed as "D 0.04844 30.44" is actually component G (D already appears above it, and 30.44 is G's price). The file uses the correct G price.
- **Average of a product vs product of averages.** The operator computes `coefficient × mean(flow) × mean(fraction)`, not `mean(flow × fraction)`. They are the same when the signals are steady over the window, which is the regime an economic cost describes; during a strong transient (a disturbance) they can differ a little. If that ever matters, the historian can be taught to average the product directly.
- **The simulated plant vs the paper.** At nominal operation the operator measures J ≈ 166 $/h, about 2.5 % below the paper's 170.6. The formula is verified against the paper's numbers, so the gap comes from the simulated plant's operating point (for example, its purge flow is ≈ 0.328 kscmh instead of 0.337). That is a model-validation finding, related to #19.
- **Analyzers.** In the original TEP, compositions come from sampled analyzers (every 0.1 h or 0.25 h, with dead time). How tep-plant models those sensors affects how noisy and how delayed the composition terms of J are.

## How to change it

Edit the file and re-apply it: `kubectl apply -f tep-supervisor/local/k8s/tep/cost-function-downs-vogel.yaml`. The operator re-evaluates every Plant using this cost function immediately, without restarting anything. For example, to study a scenario where steam is twice as expensive, change the `steam` coefficient to `0.0636` and watch J in `kubectl get plants` or in the IHM panel. Kubernetes validates the file on apply: a cost function with no terms, or a term with no signal, is rejected.
