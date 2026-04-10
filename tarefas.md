# Tarefas — TEP Digital Twin Lab

Pendências abertas com vínculo às issues dos repositórios.
Tarefas sem issue associada ainda não foram formalizadas.

---

## Em andamento

### Conectividade operator → planta
Corrigido o `plantAddress` de `te-plant.default.svc:50051` para `host.docker.internal:50051`.
Aguardando confirmação nos logs que o PLCMachine sai de `Pending` → `Monitoring`.
> Ver [Exp 1](experimentos.md)

---

## Pendente — cluster-api-provider-plc

| # | Descrição | Issue |
|---|---|---|
| — | Reconciler com gRPC client | [#38](https://github.com/Green-Cinnamon-Labs/cluster-api-provider-plc/issues/38) |
| — | Setup Kind cluster | [#39](https://github.com/Green-Cinnamon-Labs/cluster-api-provider-plc/issues/39) |
| — | Deploy planta + operator | [#40](https://github.com/Green-Cinnamon-Labs/cluster-api-provider-plc/issues/40) |
| — | Teste E2E: CR → distúrbio → reconciliação | [#41](https://github.com/Green-Cinnamon-Labs/cluster-api-provider-plc/issues/41) |

---

## Pendente — tep-ihm

| # | Descrição | Issue |
|---|---|---|
| — | Painel OPERATOR K8S: exibir fase e última ação do PLCMachine | [#44](https://github.com/Green-Cinnamon-Labs/tep-ihm/issues/44) |

---

## Pendente — experimentos

| Exp | Descrição | Depende de |
|---|---|---|
| Exp 1 | Fechar resultado/conclusão após confirmar conexão do operator | Conectividade acima |
| Exp 2 | Baseline limpo: t=20→40h sem IDV, capturar std(XMEAS[6,11,14]) | Exp 1 concluído |
| Exp 3 | IDV(4) sozinho em t=25h — medir pico de pressão e tempo de recovery | Exp 2 concluído |
| Exp 4 | IDV(1) sozinho em t=25h | Exp 2 concluído |
| Exp 5 | IDV(1)+IDV(4) simultâneos — "pior caso" dos P-controllers | Exp 3 e 4 concluídos |
| Exp 6 | IDV(1)+IDV(4) com supervisor ativo — testar H1 | Exp 5 + operator conectado |

---

## Decisões abertas

- O `plcmachine-sample.yaml` em `lab-k8s-supervisor/local/k8s/` deve ser mantido
  sincronizado com o sample de `cluster-api-provider-plc/config/samples/`.
  Hoje estão divergentes — o do lab ainda usa o endereço antigo?
