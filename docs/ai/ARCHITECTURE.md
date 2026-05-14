## Overview

**Tennessee Eastman Digital Twin Lab** — simulação executável da planta química Tennessee Eastman (Downs & Vogel, 1993) com controle supervisório via Kubernetes. Este workspace reúne cinco repositórios com linguagens e papéis distintos.

| Pasta                    | Linguagem        | Papel                                                           |
| ------------------------ | ---------------- | --------------------------------------------------------------- |
| `spec-tennessee-eastman` | — (sem código)   | Especificações, registro de experimentos, tarefas abertas       |
| `tep-plant`              | Rust + Python    | Simulador da planta + servidor gRPC `:50051` + análise de dados |
| `tep-ihm`                | Python (FastAPI) | Dashboard web em tempo real `:8080`                             |
| `tep-operator`           | Go (Kubebuilder) | Operator Kubernetes para controle supervisório                  |
| `tep-supervisor`         | Shell + YAML     | Infraestrutura local (Docker Compose + Kind)                    |


## Arquitetura

```
Browser ──WebSocket──► tep-ihm (FastAPI :8080)
                            │
                          gRPC StreamMetrics
                            │
                       tep-plant (Rust :50051)  ◄── gRPC UpdateController ── plc-operator (Go / Kind)
                            │
                         RK4 loop
                            │
                       Plant model (te-core)
                          + ControllerBank (3 P-controllers embutidos)
```

**Fluxo de dados:**
1. A planta Rust avança o tempo via RK4 (dt = 0,001 h/step), com 3 P-controllers embutidos (pressão do reator, nível do separador, nível do stripping).
2. O servidor gRPC (tonic `:50051`) expõe `StreamMetrics`, `GetPlantStatus`, `ListControllers`, `UpdateController`.
3. O operator K8s lê XMEAS via gRPC, avalia a política declarada no CRD `PLCMachine`, e chama `UpdateController` quando variáveis saem da faixa.
4. A IHM consome `StreamMetrics` via gRPC, converte para JSON e faz broadcast via WebSocket para o navegador (Chart.js).




---

---

## Regras arquiteturais

### 1. Conectividade entre componentes

- A IHM acessa a planta pelo service name do Docker Compose:
  - `te-plant:50051`
- O operator, quando roda dentro do cluster Kind, acessa a planta pelo host Docker:
  - `host.docker.internal:50051`

### 2. Contrato gRPC

- O arquivo `.proto` canônico fica em:
  - `tep-plant`
- Cópias manuais devem ser mantidas em:
  - `tep-operator/proto/`
  - `tep-ihm/proto/`
- Quando o `.proto` mudar:
  - regenerar stubs no `tep-plant`;
  - regenerar stubs no `tep-operator`;
  - regenerar stubs no `tep-ihm`.

### 3. Estado da simulação

- A simulação inicia a partir de:
  - `cases/te_exp3_snapshot.toml`
- O snapshot de destino da execução é:
  - `cases/te_exp11_snapshot.toml`

### 4. Logging e artefatos de execução

- O CSV logger é desativado com:
  - `--headless`
- O arquivo `simulation_log.csv` é criado na raiz de onde o binário é executado.
- Stubs gRPC gerados em `gen/` são artefatos locais e não devem ir para o Git.

### 5. Kubernetes e operator

- `make generate manifests` só deve ser executado em Linux.
- Em ambiente Windows, usar GitHub Codespace para gerar manifests e depois fazer pull das alterações.
- No CRD `PLCMachine`:
  - `.spec` define a política supervisória;
  - `.status` armazena a memória operacional do operator.