# Design notes

Design notes written along the project, one folder per GitHub issue. They record why things were built the way they are; the code in each repository is the reference for how they work today. Most notes are in Portuguese.

## Supervision with Kubernetes

| Folder | What it covers |
|---|---|
| [`issue77_cost_function_k8s/`](issue77_cost_function_k8s/) | The core of the thesis. The three Kubernetes resources explained file by file ([cost function](issue77_cost_function_k8s/cost_function_downs_vogel.md), [Mode 1 policy](issue77_cost_function_k8s/operating_policy_mode1.md), [plant](issue77_cost_function_k8s/plant_tep.md)), [what each piece of the lab does](issue77_cost_function_k8s/kubernetes_features.md), and the plan that added the control-loop quality level and ran the disturbance experiment. |

## Plant and simulation framework

| Folder | What it covers |
|---|---|
| [`issue55_opcua_refactor/`](issue55_opcua_refactor/) | The evaluations behind the rewrite of the plant on top of a named state registry and its exposure over OPC UA: naming standard, sensor/actuator boundary, nature of the disturbances, derivatives. The decisions that came out of them are in [`CONTRIBUTING.md`](../CONTRIBUTING.md). |
| [`issue61_runtime_supervisor/`](issue61_runtime_supervisor/) | Why the `monjolo` runtime outlives the simulation: the OPC UA server stays up across plant resets. |
| [`issue91_steady_state_optimization/`](issue91_steady_state_optimization/) | Parallel line of work: the plant evaluated as a function, without time, so an optimizer can call it ([`tep-optimizer`](https://github.com/Green-Cinnamon-Labs/tep-optimizer)). |

## HMI

| Folder | What it covers |
|---|---|
| [`issue49_dashboard_refactor/`](issue49_dashboard_refactor/) | The process diagram drawn in draw.io and its semantic contract: every relevant shape carries a meaningful `data-cell-id`, which the browser uses to animate it. Includes the draw.io sources. |
| [`issue51_isa101_refactor/`](issue51_isa101_refactor/) | Moving the HMI to the ISA-101 style: change plan, alarm inventory, the symposium material it was based on. |
| [`issue51_etapa4a_refactor/`](issue51_etapa4a_refactor/) | Trend charts drawn inside the diagram and the analysis page with capture sessions stored in SQLite. |
| [`notes/`](notes/) | Short guides: [how the diagram goes from draw.io to the browser](notes/nota_svg_diagram_pipeline.md) and [how to use the analysis page](notes/nota_analytics_panel.md). |

## Conventions and references

- [`padrao_documentacao.md`](padrao_documentacao.md): the numbered-article style (Art./§) used in `CONTRIBUTING.md`.
- [`padroes/`](padroes/): design pattern references (Composite, Proxy, Builder, Facade, Singleton) used while designing the framework.

## Archive

[`archive/`](archive/) keeps notes from the phase when the plant served gRPC. They no longer describe the system.
