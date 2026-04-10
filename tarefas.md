# Tarefas — TEP Digital Twin Lab

Pendências abertas com vínculo às issues de [spec-tennessee-eastman](https://github.com/Green-Cinnamon-Labs/spec-tennessee-eastman).

---

## Em andamento

### Conectividade operator → planta
Corrigido o `plantAddress` de `te-plant.default.svc:50051` para `host.docker.internal:50051`.
Aguardando confirmação nos logs que o PLCMachine sai de `Pending` → `Monitoring`.
> Ver [Exp 1](experimentos.md)

---

## Issues abertas — foco atual (42–45)

| Issue | Título | Status |
|---|---|---|
| [#42](https://github.com/Green-Cinnamon-Labs/spec-tennessee-eastman/issues/42) | Dashboard de observabilidade (planta + operator) | Em andamento — IHM ok, painel K8s placeholder |
| [#43](https://github.com/Green-Cinnamon-Labs/spec-tennessee-eastman/issues/43) | Baseline da planta (documentar estado estável, faixas normais) | Pendente — precisa do Exp 2 |
| [#44](https://github.com/Green-Cinnamon-Labs/spec-tennessee-eastman/issues/44) | Lógica supervisória do operator (avaliação e resposta a distúrbios) | Pendente — operator conectando |
| [#45](https://github.com/Green-Cinnamon-Labs/spec-tennessee-eastman/issues/45) | Ciclos de distúrbio (cenários iterativos, testar respostas) | Pendente — após #43 e #44 |

---

## Issues abertas — backlog técnico

| Issue | Título |
|---|---|
| [#27](https://github.com/Green-Cinnamon-Labs/spec-tennessee-eastman/issues/27) | Clarify Control Inputs vs Disturbances in TEP Model Interface |
| [#19](https://github.com/Green-Cinnamon-Labs/spec-tennessee-eastman/issues/19) | Validate Model Against Reference Dataset `(data/d00.dat)` |
| [#1](https://github.com/Green-Cinnamon-Labs/spec-tennessee-eastman/issues/1) | Runtime-Switchable DynamicModel |
| [#2](https://github.com/Green-Cinnamon-Labs/spec-tennessee-eastman/issues/2) | Steady-State Solver (Equilibrium Computation) |
| [#3](https://github.com/Green-Cinnamon-Labs/spec-tennessee-eastman/issues/3) | Jacobian Evaluation Engine |
| [#4](https://github.com/Green-Cinnamon-Labs/spec-tennessee-eastman/issues/4) | Local Stability Analyzer |
| [#5](https://github.com/Green-Cinnamon-Labs/spec-tennessee-eastman/issues/5) | Parameter Sweep & Bifurcation Detection |
| [#10](https://github.com/Green-Cinnamon-Labs/spec-tennessee-eastman/issues/10) | Introduce Base `AccumulationUnit` Abstraction |
| [#13](https://github.com/Green-Cinnamon-Labs/spec-tennessee-eastman/issues/13) | Introduce Base `Actuator` Abstraction |
| [#14](https://github.com/Green-Cinnamon-Labs/spec-tennessee-eastman/issues/14) | Introduce Base `Sensor` Abstraction |

---

## Sequência de experimentos pendentes

| Exp | Descrição | Depende de |
|---|---|---|
| Exp 1 | Fechar resultado/conclusão após confirmar conexão do operator | Conectividade acima |
| Exp 2 | Baseline limpo: t=20→40h sem IDV — std(XMEAS[6,11,14]) | Exp 1 concluído → fecha [#43](https://github.com/Green-Cinnamon-Labs/spec-tennessee-eastman/issues/43) |
| Exp 3 | IDV(4) sozinho em t=25h — pico de pressão, tempo de recovery | Exp 2 |
| Exp 4 | IDV(1) sozinho em t=25h | Exp 2 |
| Exp 5 | IDV(1)+IDV(4) simultâneos — pior caso dos P-controllers | Exp 3 e 4 → inicia [#45](https://github.com/Green-Cinnamon-Labs/spec-tennessee-eastman/issues/45) |
| Exp 6 | IDV(1)+IDV(4) com supervisor ativo — testar H1 | Exp 5 + operator conectado → fecha [#44](https://github.com/Green-Cinnamon-Labs/spec-tennessee-eastman/issues/44) |
