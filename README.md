# Tennessee Eastman Digital Twin — Specification

Este repositório é o ponto de entrada do lab. Ele não contém código —
contém o registro dos experimentos, as decisões de arquitetura, e o
rastreamento de tarefas abertas que atravessam os demais repositórios.

---

## Objetivo

Construir um digital twin determinístico e extensível do processo Tennessee Eastman,
capaz de simulação de longo horizonte com controle supervisório integrado via Kubernetes.

---

## Repositórios do Lab

| Repositório | Papel |
|---|---|
| [`fork-tennesseeEastman`](https://github.com/Green-Cinnamon-Labs/fork-tennesseeEastman) | Simulador da planta em Rust (RK4, 8 componentes, gRPC :50051). Contém a dinâmica do processo, integradores numéricos, 3 P-controllers embutidos e os snapshots de estado. |
| [`tep-ihm`](https://github.com/Green-Cinnamon-Labs/tep-ihm) | Dashboard web da planta (IHM). Consome o stream gRPC de XMEAS/XMV em tempo real e expõe visualização em :8080. |
| [`cluster-api-provider-plc`](https://github.com/Green-Cinnamon-Labs/cluster-api-provider-plc) | Operator Kubernetes (Go/Kubebuilder) que atua como controlador supervisório. Lê XMEAS via gRPC, avalia a política declarada no CRD `PLCMachine` e ajusta controladores quando variáveis saem da faixa. |
| [`lab-k8s-supervisor`](https://github.com/Green-Cinnamon-Labs/lab-k8s-supervisor) | Infraestrutura local do lab: `docker-compose` (planta + IHM), cluster Kind (`setup.sh`), manifests K8s e configurações de cloud (AWS/Azure/GCP). |

---

## Princípios de Engenharia

- Separação entre modelo e integração numérica.
- Arquitetura de tempo determinística.
- Modelagem explícita de acúmulo físico.
- Entradas de controle mediadas por atuadores.
- Invariância numérica ao longo do horizonte de simulação.

---

## Documentos deste repositório

- [`experimentos.md`](experimentos.md) — Registro científico dos experimentos sobre o sistema integrado (planta + supervisor). Mais recente em cima.
- [`tarefas.md`](tarefas.md) — Tarefas abertas, pendências e vínculos com issues dos repositórios.
