## Comandos

### tep-plant (Rust)

```bash
cd tep-plant/tennessee-eastman-service

cargo build                  # build do workspace (core + service)
cargo run -p service         # roda simulação + gRPC server
cargo run -p service -- --headless  # sem CSV logger nem dashboard terminal
cargo test                   # todos os testes
cargo test -p te-core        # testes só do core

# Variáveis de ambiente da planta:
# STEP_DELAY_MS=36   → 100× tempo real  (0 = máximo da CPU, padrão)
# ACTIVE_IDV=4       → ativar distúrbio IDV 4 (pode ser lista: "1,4")
```

### tep-ihm (Python / FastAPI)

```bash
cd tep-ihm
poetry install

# Gerar stubs gRPC (obrigatório na 1ª vez e quando o .proto mudar):
poetry run python -m grpc_tools.protoc \
  -I proto \
  --python_out=gen \
  --grpc_python_out=gen \
  proto/tep/v1/plant.proto

# Rodar o backend (planta precisa estar acessível em :50051):
poetry run python src/server.py

# Variáveis de ambiente:
# PLANT_ADDRESS=localhost:50051
# STREAM_INTERVAL_MS=500
# PORT=8080
```

### tep-operator (Go / Kubebuilder)

```bash
cd tep-operator

make build              # compila o binário em bin/manager
make run                # roda o controller localmente (sem Docker)
make test               # testes unitários (requer setup-envtest)
make fmt vet            # formatar + verificar o código
make lint               # golangci-lint (baixa automaticamente se ausente)
make proto              # gera stubs Go a partir de proto/tep/v1/plant.proto

# Apenas em Linux / GitHub Codespace:
make generate manifests # gera DeepCopy + CRDs (controller-gen requer Linux)
```

### Docker (builds de imagem)

```bash
docker build -t te-plant:latest    tep-plant/
docker build -t tep-ihm:latest     tep-ihm/
docker build -t plc-operator:latest tep-operator/
```

### Lab completo (subir tudo)

```bash
# 1. Subir planta + IHM:
docker compose -f tep-supervisor/local/docker-compose.yml up -d

# 2. Criar cluster Kind + carregar operator + deployar:
bash tep-supervisor/local/setup.sh
```

### Retomar após reinício do Docker

```bash
docker start tep-lab-control-plane
docker compose -f tep-supervisor/local/docker-compose.yml up -d
```

### Atualizar imagem no cluster existente

```bash
# Operator:
kind load docker-image plc-operator:latest --name tep-lab
kubectl rollout restart deployment/plc-operator

# IHM:
docker compose -f tep-supervisor/local/docker-compose.yml up -d --force-recreate tep-ihm
```

### Diagnóstico rápido

```bash
docker ps                                          # deve mostrar te-plant, tep-ihm, tep-lab-control-plane
kubectl get pods                                   # pod plc-operator-* deve ser Running
kubectl get plcmachine tep-baseline                # phase: Stable
kubectl logs -f deploy/plc-operator                # logs do operator
kubectl get plcmachine tep-baseline -o jsonpath='{.status}' | python -m json.tool
```

### Análise de dados (Python)

```bash
cd tep-plant/analysis
poetry install
poetry run plot --csv ../tennessee-eastman-service/simulation_log.csv
```