# Registro: Protobuf e Regeneração para tep-ihm

Eu adicionei dois novos métodos gRPC para controlar distúrbios e simulação em tempo real na planta.
O objetivo era permitir ativar/desativar distúrbios e pausar/retomar a simulação sem reiniciar.

## O que é Protocol Buffers

Protocol Buffers (protobuf) é um formato de serialização de dados criado pelo Google em 2008.
Ele define uma forma compacta, eficiente e agnóstica de linguagem para serializar dados estruturados.

**Por que Google criou:** Internamente, o Google precisava de um formato mais eficiente que XML e JSON para comunicação entre serviços em larga escala. XML era muito verboso, e não havia um padrão industrial neutro na época.

**Como funciona:** Você define uma estrutura de dados em um arquivo `.proto` com sintaxe simples.
Depois, um compilador (`protoc`) lê esse arquivo e gera código em linguagens como Rust, Python, Go, Java, etc.
Cada linguagem recebe uma biblioteca que sabe serializar/desserializar os dados automaticamente.

## Por que usamos protobuf neste projeto

Neste lab, temos três componentes em linguagens diferentes:
- **tep-plant**: Rust (simulação + servidor gRPC)
- **tep-ihm**: Python (dashboard web)
- **tep-operator**: Go (controller Kubernetes)

Todos precisam conversar sobre o mesmo contrato de dados (métricas, alarmes, distúrbios, etc).

**Protobuf resolve isso porque:**

1. **Um único `.proto` como fonte de verdade** — defina a estrutura uma vez, gere código para todas as 3 linguagens
2. **Cada linguagem tem gerador próprio** — Rust usa `tonic_build`, Python usa `grpc_tools.protoc`, Go usa `protoc` com plugins Go
3. **Compatibilidade automática** — se o `.proto` mudar, regenera-se o código e as linguagens entendem a nova estrutura
4. **gRPC embutido** — protobuf define não só estruturas de dados, mas também serviços RPC (métodos remotos), que gRPC implementa

## Fluxo da regeneração protobuf

Quando você modifica `plant.proto` e quer que as mudanças façam efeito, precisa regenerar os stubs em cada linguagem.

### 1. Modificar o `.proto`

No nosso caso, adicionei dois novos RPC methods ao `PlantService`:

```proto
// No arquivo: tep-plant/tennessee-eastman-service/service/proto/tep/v1/plant.proto

service PlantService {
  // ... métodos existentes ...
  
  rpc UpdateDisturbances(UpdateDisturbancesRequest) returns (UpdateDisturbancesResponse);
  rpc ControlSimulation(ControlSimulationRequest) returns (ControlSimulationResponse);
}

// Mensagens para os novos métodos
message UpdateDisturbancesRequest {
  repeated uint32 active_idv = 1;  // Lista de IDVs a ativar (1-20)
}

message UpdateDisturbancesResponse {
  bool success = 1;
  string message = 2;
  repeated uint32 active_idv = 3;  // Estado resultante
}

message ControlSimulationRequest {
  enum Action {
    PAUSE = 0;
    RESUME = 1;
    RESET = 2;
  }
  Action action = 1;
}

message ControlSimulationResponse {
  bool success = 1;
  string message = 2;
  bool paused = 3;  // Estado atual da simulação
}
```

### 2. Regenerar stubs em Rust (tep-plant)

O projeto Rust usa `tonic_build` dentro do `build.rs`.
Ao rodar `cargo build`, ele automaticamente regenera os stubs Rust a partir do `.proto`:

```bash
cd c:\Projetos\tep\tep-plant\tennessee-eastman-service
cargo build
```

**O que acontece internamente:**
- Rust lê o arquivo `build.rs`
- `build.rs` chama `tonic_build::compile_protos("proto/tep/v1/plant.proto")`
- O compilador vendored protoc (`protoc_bin_vendored`) regenera os arquivos `.rs` dentro do workspace
- Os novos métodos `UpdateDisturbances` e `ControlSimulation` aparecem na trait `PlantService`

**Implementação Rust dos novos métodos** (adicione em `grpc_server.rs`):

```rust
async fn update_disturbances(
    &self,
    request: Request<UpdateDisturbancesRequest>,
) -> Result<Response<UpdateDisturbancesResponse>, Status> {
    let req = request.into_inner();
    let mut state = self.shared.lock().unwrap();
    
    let new_active: Vec<usize> = req.active_idv
        .iter()
        .filter_map(|&v| {
            let n = v as usize;
            if n >= 1 && n <= 20 { Some(n) } else { None }
        })
        .collect();
    
    state.active_idv = new_active.clone();
    
    Ok(Response::new(UpdateDisturbancesResponse {
        success: true,
        message: format!("disturbances updated: {:?}", new_active),
        active_idv: new_active.iter().map(|&v| v as u32).collect(),
    }))
}
```

### 3. Copiar `.proto` para tep-ihm

O Rust já regenerou tudo; agora Python precisa.
Primeiro, copie o `.proto` atualizado para o diretório de proto do IHM:

```bash
# Copiar usando PowerShell
Copy-Item `
  "C:\Projetos\tep\tep-plant\tennessee-eastman-service\service\proto\tep\v1\plant.proto" `
  -Destination "C:\Projetos\tep\tep-ihm\proto\tep\v1\plant.proto" `
  -Force
```

Ou usando `cp` no bash/WSL:

```bash
cp /mnt/c/Projetos/tep/tep-plant/tennessee-eastman-service/service/proto/tep/v1/plant.proto \
   /mnt/c/Projetos/tep/tep-ihm/proto/tep/v1/plant.proto
```

### 4. Regenerar stubs em Python (tep-ihm)

No diretório `tep-ihm`, use `grpc_tools.protoc` para gerar os stubs Python:

```bash
cd c:\Projetos\tep\tep-ihm

poetry run python -m grpc_tools.protoc \
  -I proto \
  --python_out=gen \
  --grpc_python_out=gen \
  proto/tep/v1/plant.proto
```

**O que cada flag faz:**
- `-I proto` — diretório onde protoc procura por imports (inclusive submódulos)
- `--python_out=gen` — gera `plant_pb2.py` em `gen/tep/v1/`
- `--grpc_python_out=gen` — gera `plant_pb2_grpc.py` em `gen/tep/v1/`
- `proto/tep/v1/plant.proto` — arquivo `.proto` de entrada

**Resultado:**
- `gen/tep/v1/plant_pb2.py` — classes das mensagens (serialização/desserialização)
- `gen/tep/v1/plant_pb2_grpc.py` — cliente e servidor gRPC em Python

### 5. Implementar endpoints em Python (tep-ihm/src/server.py)

Adicione os dois novos endpoints que chamam os métodos gRPC da planta:

```python
@app.post("/disturbances/update")
async def update_disturbances(payload: dict):
    """Atualiza a lista de distúrbios ativos em tempo real."""
    global ACTIVE_IDV
    try:
        import grpc
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "gen"))
        from tep.v1 import plant_pb2, plant_pb2_grpc

        new_active = payload.get("active_idv", [])
        ACTIVE_IDV = sorted([int(x) for x in new_active if isinstance(x, int)])

        # Atualiza planta via gRPC (não-blocking)
        if not CSV_REPLAY:
            async def update_plant_disturbances():
                try:
                    channel = grpc.aio.insecure_channel(PLANT_ADDRESS)
                    stub = plant_pb2_grpc.PlantServiceStub(channel)
                    request = plant_pb2.UpdateDisturbancesRequest(
                        active_idv=[int(x) for x in ACTIVE_IDV]
                    )
                    response = await stub.UpdateDisturbances(request)
                    await channel.close()
                    print(f"[ihm] disturbios atualizados na planta: {ACTIVE_IDV}")
                except Exception as plant_err:
                    print(f"[ihm] aviso: {plant_err}")

            asyncio.create_task(update_plant_disturbances())

        return {"status": "ok", "active_idv": ACTIVE_IDV}
    except Exception as e:
        return Response(f"Erro: {e}", status_code=400)


@app.post("/simulation/control")
async def control_simulation(payload: dict):
    """Controla simulação (pause, resume)."""
    try:
        import grpc
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "gen"))
        from tep.v1 import plant_pb2, plant_pb2_grpc

        action_str = payload.get("action", "").lower()
        action_map = {
            "pause": 0,   # plant_pb2.ControlSimulationRequest.Action.PAUSE
            "resume": 1,  # plant_pb2.ControlSimulationRequest.Action.RESUME
            "reset": 2,   # plant_pb2.ControlSimulationRequest.Action.RESET
        }

        if action_str not in action_map:
            return Response(f"Ação inválida: {action_str}", status_code=400)

        # Envia comando para planta via gRPC (não-blocking)
        if not CSV_REPLAY:
            async def send_control_command():
                try:
                    channel = grpc.aio.insecure_channel(PLANT_ADDRESS)
                    stub = plant_pb2_grpc.PlantServiceStub(channel)
                    request = plant_pb2.ControlSimulationRequest(
                        action=action_map[action_str]
                    )
                    response = await stub.ControlSimulation(request)
                    await channel.close()
                    print(f"[ihm] simulação {action_str}: {response.message}")
                except Exception as plant_err:
                    print(f"[ihm] aviso: {plant_err}")

            asyncio.create_task(send_control_command())

        return {"status": "ok", "action": action_str}
    except Exception as e:
        return Response(f"Erro: {e}", status_code=400)
```

### 6. Atualizar runtime da planta (runtime.rs)

Modifique o loop principal para respeitar pause e atualizar distúrbios:

```rust
loop {
    // Verifica pause e atualiza distúrbios da shared state
    {
        let state = shared.lock().unwrap();

        if state.paused {
            if config.real_time {
                std::thread::sleep(std::time::Duration::from_secs_f64(config.step_delay_secs));
            }
            continue;  // Pula a iteração se pausado
        }

        // Atualiza dv a partir de shared state (permite toggle em tempo real)
        if !state.active_idv.is_empty() && disturbances_restored {
            for i in 0..plant.bus.inputs.dv.len() {
                plant.bus.inputs.dv[i] = 0.0;
            }
            for &idv in &state.active_idv {
                if idv >= 1 && idv <= plant.bus.inputs.dv.len() {
                    plant.bus.inputs.dv[idv - 1] = 1.0;
                }
            }
        }
    }

    // Resto da simulação segue normal...
    if !isd_active {
        plant.step(config.dt);
        // ...
    }
}
```

## Resumo do fluxo

```
User clica em toggle IDV
    ↓
Frontend chama POST /disturbances/update
    ↓
IHM Python chama plant.UpdateDisturbances(new_list) via gRPC
    ↓
Rust recebe chamada, atualiza state.active_idv
    ↓
Loop da planta lê state.active_idv a cada iteração
    ↓
Distúrbio ativado/desativado SEM RESTART
```

Similar para pause:

```
User clica em pause button
    ↓
Frontend chama POST /simulation/control { "action": "pause" }
    ↓
IHM Python chama plant.ControlSimulation(PAUSE) via gRPC
    ↓
Rust recebe chamada, seta state.paused = true
    ↓
Loop da planta verifica paused, skipa plant.step()
    ↓
Simulação pausa SEM RESTART
```

## Validação

Depois de regenerar e reiniciar os serviços:

```bash
# Terminal 1: Rust planta
cd c:\Projetos\tep\tep-plant\tennessee-eastman-service
cargo run -p service

# Terminal 2: Python IHM
cd c:\Projetos\tep\tep-ihm
poetry run python src/server.py

# Browser
http://localhost:8080
```

Testa no dashboard:
1. Clica em um botão de IDV — deve ativar a distúrbio (se começou com ACTIVE_IDV vazio)
2. Clica no botão pause — simulação pausa, métricas congelam
3. Clica no botão resume — simulação volta a rodar

Se tudo funciona sem erros no terminal, a regeneração foi bem-sucedida.

