# Experimentos — TEP Digital Twin Lab

Registro científico dos experimentos sobre o sistema integrado (planta + IHM + supervisor).

Estrutura de cada entrada: **Observação → Hipótese → Intervenção → Resultado → Conclusão**

O experimento mais recente aparece primeiro.

---

## Exp 1 — Validação da stack integrada e conectividade do operator

**Data:** 2026-04-10

### Observação

Ao aplicar o CR `tep-baseline` via `kubectl apply`, o operator entrou em loop de erro:

```
failed to connect to plant
address: "te-plant.default.svc:50051"
error: dial plant at te-plant.default.svc:50051: context deadline exceeded
```

A planta estava rodando como container Docker standalone (fora do cluster Kind),
mas o `plantAddress` no sample apontava para um Service Kubernetes inexistente.
A IHM (`localhost:8080`) estava acessível e exibindo XMEAS/XMV em tempo real via stream gRPC.

Estado observado no momento da falha (leitura da IHM):

| Variável | Valor | Observação |
|---|---|---|
| XMEAS(7) Reactor Pressure | 2705 kPa | No setpoint |
| XMEAS(8) Reactor Level | 75.5% | Acima da faixa do PLCMachine (max: 60%) |
| XMEAS(12) Sep Level | 49.6% | Normal |
| XMEAS(15) Stripper Level | 49.5% | Normal |

### Hipótese

O Kind cria uma rede Docker interna isolada. Containers fora do cluster
não são endereçáveis via `<nome>.default.svc`. Para alcançar a planta
(que roda no host Docker), o operator precisa usar `host.docker.internal:50051`.

### Intervenção

Arquivo modificado: `tep-operator/config/samples/infrastructure_v1alpha1_plcmachine.yaml`

```yaml
# antes
plantAddress: "te-plant.default.svc:50051"

# depois
plantAddress: "host.docker.internal:50051"
```

Reaplicado via `kubectl apply -f infrastructure_v1alpha1_plcmachine.yaml`.

### Resultado

A ser preenchido após confirmação da conexão nos logs do operator.

### Conclusão

A ser preenchida.

---
