# Registro Científico de Intervenções — TEP CPS

Registro científico dos experimentos e intervenções.

Estrutura de cada entrada: **Observação → Hipótese → Intervenção → Resultado → Conclusão**

O experimento mais recente aparece primeiro.



## Experimento 17 — IDV(3): Step na temperatura do D feed (corrente 2)

**Data:** 2026-06-02 — **Planejado**

### Observação

Exp 15 (IDV(1)) e Exp 16 (IDV(2)) mostraram dois modos de colapso: cinético (rápido, 2.5h) e por acúmulo de inerte (lento, dezenas de horas). IDV(3) é qualitativamente diferente: não altera composição nem reatividade — apenas a **entalpia do feed de D**. D é um reagente líquido (corrente 2); temperatura mais alta muda o balanço de calor de entrada no reator sem mudar a estequiometria.

Mecanismo FORTRAN: `TST(1) = TESUB8(3,TIME) + IDV(3)*5.D0` → D feed sobe +5°C em step.
Rust equivalente: `self.tst[0] = eval_disturbance(2, time, ds) + idv[2] as f64 * 5.0` (`model.rs:275`).

### Hipótese

D líquido mais quente entra no reator com maior entalpia específica — a temperatura do reator (XMEAS(9)) sobe. **Crítico: não há controlador de temperatura na planta.** O `ControllerBank` tem apenas 3 malhas P: pressão→purge, nível separador→underflow, nível stripper→produto (`main.rs:62-64`). XMV(10) e XMV(11) (CWS reator e condensador) ficam fixos.

**Mecanismo esperado:**

1. D feed +5°C → entalpia de entrada ↑ → **temperatura do reator sobe sem controle direto**
2. Temperatura mais alta → taxa de reação Arrhenius ↑ → mais consumo de reagentes e produção de G/H
3. Mudança na produção de gás altera o balanço de pressão → XMEAS(7) pode subir ou cair dependendo do balanço líquido das reações
4. Só então `pressure_reactor` age via XMV(6) (purge) — resposta indireta e defasada

Hipótese central: **temperatura sobe monotonicamente (sem malha fechada), pressão segue com algum atraso, e o único atuador que responde é XMV(6) via pressão.** Se a temperatura cruzar o ISD (>175°C) antes de estabilizar, a planta colapsa por temperatura — diferente dos Exp 15 e 16, que colapsaram por pressão.

| Variável           | Baseline  | Esperado após IDV(3)                        |
| ------------------ | --------- | ------------------------------------------- |
| XMEAS(9) Reactor T | ~120 °C   | ↑ sem controle direto — deriva ou ISD       |
| XMEAS(7) Reactor P | ~2699 kPa | ↑ ou ↓ dependendo das reações aceleradas    |
| XMV(10) CWS valve  | ~41 %     | **fixo** — sem controlador de temperatura   |
| XMV(6) Purge valve | ~39 %     | muda apenas se pressão variar               |
| XMEAS(23,24,25)    | ~31/10/26%| pode derivar — cinética alterada por T      |

### Intervenção

**tep-plant:** Debugger config `"Planta: baseline (100x, sem distúrbios)"` com `ACTIVE_IDV=""`

**tep-ihm:** `RECORD_CSV=true`, `RECORD_CSV_PATH=/data/simulation_log_17.0.csv`

**Procedimento:**
1. Iniciar planta com snapshot `te_exp3_snapshot.toml`, aguardar SS (~5h simuladas)
2. Ativar **IDV(3)** no painel "Disturbances" da IHM
3. Observar: XMEAS(9) temperatura, XMEAS(7) pressão, XMV(10) CWS valve
4. Rodar até novo SS ou até ISD — se a temperatura se estabilizar em 20h, o distúrbio é "benigno"
5. Exportar CSV; salvar como `docs/simulations/simulation_log_17.0.csv`
6. Plotar: `python -m tep_analysis.plot --csv docs/simulations/simulation_log_17.0.csv --smooth 11`

**Variáveis a logar no CSV** (verificar se `tep-ihm` está capturando):
- `xmeas_7` (pressão), `xmeas_9` (temperatura), `xmv_10` (CWS valve), `xmeas_2` (D feed flow)

### Resultado

**CSV:** `docs/simulations/simulation_log.csv` | 718 linhas, t = 2.13 → 1102.77 h (~45 dias simulados)

| Variável           | Baseline  | Após IDV(3) — 1100h depois    |
| ------------------ | --------- | ----------------------------- |
| XMEAS(9) Reactor T | 120.43 °C | 120.43 °C — variação < 0.01°C |
| XMEAS(7) Reactor P | 2695 kPa  | 2703 kPa — +8 kPa em 45 dias  |
| XMV(6) Purge valve | 39.1 %    | 39.9 % — +0.8 pp              |

Temperatura absolutamente flat. A variação de pressão de 8 kPa em 1100h simuladas está dentro do ruído de processo. O experimento foi acelerado para 100% logo após o IDV(3) ser ativado (~t=3.7h); a diferença de taxa de amostragem é visível no CSV (dt ≈ 0.003h lento → dt ≈ 8h rápido). Nenhum degrau detectável em nenhuma variável.

### Conclusão

**IDV(3) é numericamente nulo nesta planta.** A análise do código confirmou o mecanismo: a entalpia extra do D feed entra em `yp[35]` (UCVV), diluída pelo reciclo dominante antes de chegar ao reator via `hst[6] = hst[5]`. Com `VRNG[0] = 400` (D feed range) frente ao reciclo de ~26 kscmh, o impacto térmico é imperceptível.

**Implicação para o TCC:** IDV(3) não é um distúrbio útil para exercitar o supervisor. Não gera nenhuma resposta mensurável e não ameaça os limites ISD. O foco deve permanecer em IDV(1) (colapso cinético rápido) e IDV(2) (acúmulo lento de inerte) como os casos de interesse para a lógica supervisória.

---

## Experimento 16 — IDV(2): Step na composição de B no feed (corrente 4)

**Data:** 2026-06-02 — **Concluído**

### Observação

O Exp 15 mostrou que IDV(1) colapsa a planta por sobrepressão em ~2.5h: menos A → reações mais lentas → gás acumula → purge insuficiente. IDV(2) atua sobre um componente **inerte**: B dobra no feed (0.005 → 0.010 mol frac), enquanto A e C mal se movem (−0.5% cada). O mecanismo de colapso do Exp 15 não se aplica aqui — não há alteração de cinética.

### Hipótese

IDV(2)=1 dobra B na corrente 4 (`XST(2,4) = TESUB8(2) + IDV(2)*0.005`). Como B é inerte, ele **não reage**, mas ocupa volume no espaço gasoso do reator e do loop de reciclo. A única saída de B do sistema é a purga (XMV(6)).

**Mecanismo esperado:** mais B entra → B se acumula no vapor do reator e no reciclo → pressão (XMEAS(7)) sobe → controlador P abre XMV(6) → mais B purgado. Um **novo SS estável** deve ser atingido quando a taxa de remoção de B pela purga iguala a taxa de entrada. O sistema não colapsa porque a reatividade não mudou — apenas o inventário de inerte.

Temperatura (XMEAS(9)) não deve se mover: B não participa das reações exotérmicas. Composição de B no reator (XMEAS(24)) e na purga (XMEAS(30)) devem subir e estabilizar no novo SS.

| Variável           | Baseline (Exp 13) | Esperado após IDV(2)          |
| ------------------ | ----------------- | ----------------------------- |
| XMEAS(24) B reator | ~?%               | ↑ — novo SS mais alto         |
| XMEAS(30) B purga  | ~?%               | ↑ — novo SS mais alto         |
| XMEAS(7) Reactor P | ~2699 kPa         | ↑ levemente — novo SS estável |
| XMEAS(9) Reactor T | ~120 °C           | flat — B é inerte             |
| XMV(6) Purge       | ~39 %             | ↑ — remove o B extra          |

### Intervenção

Configuração via VS Code debugger local:

**tep-plant:**
```
Debugger config: "Planta: baseline (100x, sem distúrbios)"
  STEP_DELAY_MS=36
  ACTIVE_IDV=""  (vazio — distúrbios controlados via IHM)
```

**tep-ihm:**
```
Debugger config: "IHM: planta local (gRPC + CSV)"
  RECORD_CSV=true
  RECORD_CSV_PATH=/data/simulation_log_16.0.csv
```

**Procedimento:**

1. Iniciar planta com snapshot `te_exp3_snapshot.toml` e `ACTIVE_IDV=""` (sem distúrbios)
2. Iniciar IHM e aguardar SS (XMEAS(7) ≈ 2699 kPa estável, ~5h simuladas ≈ 3 min)
3. Clicar em **IDV(2)** no painel "Disturbances" da IHM
4. Observar: XMEAS(24) e XMEAS(30) (composição B), XMEAS(7) pressão, XMV(6) purge
5. Rodar até novo SS ou t = 25h simuladas (~15 min de relógio a 100×)
6. Exportar CSV via `⬇ CSV`; salvar em `docs/simulations/simulation_log_16.0.csv`
7. Plotar: `python -m tep_analysis.plot --csv docs/simulations/simulation_log_16.0.csv`

### Resultado

**CSV:** `docs/simulations/simulation_log.csv` | **Plot:** `docs/simulations/plots/simulation_log.png`

| Variável           | Baseline  | Observado após IDV(2)                         | Hipótese |
| ------------------ | --------- | --------------------------------------------- | -------- |
| XMEAS(24) B reator | ~10 mol%  | ↑ ~11 mol% — sobe e continua crescendo        | ✗ hipótese previa SS estável |
| XMEAS(7) Reactor P | ~2727 kPa | ↑ ~2840 kPa inicial, depois deriva até ISD    | ✗ hipótese previa SS estável |
| XMEAS(9) Reactor T | ~120 °C   | flat — sem variação                           | ✓ confirmada |
| XMV(6) Purge valve | ~42 %     | ↑ ~53% inicial, continua abrindo até ~67%+    | ✓ abre, mas insuficiente |
| XMEAS(23) A mol%   | ~31 mol%  | levemente ↓ (diluição por B)                  | não previsto |
| XMEAS(25) C mol%   | ~26 mol%  | levemente ↓ (diluição por B)                  | não previsto |

O degrau composicional de B é visível em t ≈ 6.5 h simuladas. A pressão sobe de ~2727 para ~2840 kPa num degrau inicial que *parecia* estável na janela curta (t < 10h), mas o plot completo (até t = 31.4h) revela uma deriva monotônica até quase 3000 kPa. XMV(6) segue abrindo ao longo de todo o experimento, nunca conseguindo compensar a entrada de B. O experimento foi acelerado para 100% de velocidade a partir de ~t=8h; a planta colapsou por ISD de pressão.

### Conclusão

**Hipótese refutada: IDV(2) também colapsa a planta, apenas mais lentamente que IDV(1).** O mecanismo não atingiu o equilíbrio previsto. A taxa de entrada de B supera a capacidade de remoção pela purga mesmo com o controlador abrindo XMV(6) continuamente — a purga não consegue compensar sozinha.

**Dois regimes distintos observados:**
1. **Transiente rápido (t < 10h):** pressão sobe em degrau ~110 kPa e *parece* estabilizar; XMV(6) abre de 42→53%. Este regime induziu a hipótese de novo SS estável.
2. **Deriva lenta (t > 10h):** pressão continua subindo monotonicamente a ~4–5 kPa/h; XMV(6) segue abrindo. O controlador P não tem autoridade suficiente — sem integrador, o erro estacionário cresce com a carga de B até o ISD.

**Contraste com Exp 15:** IDV(1) colapsa em ~2.5h por mecanismo cinético (menos A → menos consumo de gás); IDV(2) colapsa em dezenas de horas por acúmulo lento de inerte. O ritmo é diferente, o destino é o mesmo. Para o TCC, IDV(2) é o caso de *distúrbio mensurável → resposta insuficiente do controlador → colapso lento* — a supervisão precisa detectar a deriva de pressão antes que o erro acumulado se torne irrecuperável.

---

## Experimento 15 — IDV(1): Step na razão A/C do feed (corrente 4)

**Data:** 2026-06-01 — **Concluído**

### Observação

O Exp 13 validou o baseline (pressão ≈ 2699 kPa, Sep/Stripper levels ≈ 50%, planta estável por 20h). O Exp 14 revelou que IDV(4) é inerte no FORTRAN original e que a modelagem quasi-static do trocador de calor introduzia instabilidade — resolvido com `twr = yy[36]`. Este é o primeiro experimento com distúrbio realmente efetivo nesta infraestrutura.

IDV(1) altera a **razão A/C no feed combinado (corrente 4)** com um degrau de passo — implementado diretamente em `TESUB8(1, TIME)` no FORTRAN e mapeado via `active_idv` no Rust. O efeito é composicional e não depende de nenhuma modelagem do sistema de resfriamento.

### Hipótese

IDV(1) aplica um degrau de −0.03 mol frac em A (0.485 → 0.455, −6%) e +0.03 em C (0.510 → 0.540) na corrente 4, conforme `XST(1,4) = TESUB8(1,TIME) - IDV(1)*0.03`.

**Mecanismo esperado:** A é reagente limitante das duas reações principais (A+C+D→G e A+C+E→H). Menos A disponível → taxa de reação cai → menos gás (A, C, D, E em fase vapor) é consumido e convertido em líquido (G, H) → inventário gasoso do reator tende a **acumular** → **pressão sobe**. O aumento de C no feed parcialmente compensa, mas A aparece em ambas as reações e o efeito líquido é desaceleração.

Do ponto de vista térmico, menos reação significa menos calor liberado — a temperatura do reator deve **cair levemente** ou permanecer próxima ao baseline, dependendo de quanto o balanço térmico é afetado.

O controlador P de pressão responderá abrindo a purge (XMV(6)) para tentar compensar o acúmulo. Se a taxa de remoção pela purge for suficiente para igualar o acúmulo, um **novo SS estável** é atingido com pressão levemente acima do baseline e temperatura levemente abaixo. Se não for suficiente, a pressão continua subindo até o ISD.

| Variável           | Baseline (Exp 13) | Esperado após IDV(1) |
| ------------------ | ----------------- | -------------------- |
| XMEAS(23) A mol%   | ~32%              | ↓ (menos A no feed)  |
| XMEAS(25) C mol%   | ~26%              | ↑ (mais C no feed)   |
| XMEAS(9) Reactor T | ~120 °C           | levemente abaixo     |
| XMEAS(7) Reactor P | ~2699 kPa         | acima — SS ou ISD?   |
| XMV(6) Purge       | ~39 %             | mais aberto          |

### Intervenção

Configuração via VS Code debugger local:

**tep-plant:**
```
Debugger config: "Planta: baseline (100x, sem distúrbios)"
  STEP_DELAY_MS=36
  ACTIVE_IDV=""  (vazio — distúrbios controlados via IHM)
```

**tep-ihm:**
```
Debugger config: "IHM: planta local (gRPC + CSV)"
  RECORD_CSV=true
  RECORD_CSV_PATH=/data/simulation_log_15.0.csv
```

**Procedimento:**

1. Recompilar `tep-plant` (`cargo build`) — garantir que `twr = yy[36]` (fix do Exp 14) está ativo
2. Iniciar planta com snapshot `te_exp3_snapshot.toml` e `ACTIVE_IDV=""` (sem distúrbios)
3. Iniciar IHM e aguardar SS (XMEAS(7) ≈ 2699 kPa estável, ~5h simuladas ≈ 3 min de relógio)
4. Clicar em **IDV(1)** no painel "Disturbances" da IHM
5. Observar: XMEAS(9), XMEAS(7), XMV(6), XMEAS(10), composição do produto (corrente 9)
6. Rodar até novo SS ou t = 25h simuladas (~15 min de relógio a 100×)
7. Exportar CSV via `⬇ CSV`; salvar em `docs/simulations/simulation_log_15.0.csv`
8. Plotar: `python -m tep_analysis.plot --csv docs/simulations/simulation_log_15.0.csv`

### Resultado

**Arquivo:** `docs/simulations/simulation_log_15.0.csv` — **Plot:** `docs/simulations/plots/simulation_log_15.0.png`

A planta **não atingiu novo SS**. Colapsou por sobrepressão em t ≈ 2.5h simuladas. Comportamento observado:

- **XMEAS(23) A mol%:** caiu de ~32% → ~26% a partir de t ≈ 0.5h (degrau de composição visível e limpo).
- **XMEAS(25) C mol%:** subiu simetricamente de ~26% → ~32% no mesmo instante.
- **XMEAS(7) Reactor P:** após o degrau, subiu monotonicamente de ~2700 → ~2960 kPa. Curva acelerante, sem inflexão de retorno. ISD atingido em t ≈ 2.5h.
- **XMEAS(9) Reactor T:** permaneceu completamente flat em ~120°C durante toda a run. Sem resposta térmica visível ao distúrbio.
- **XMV(6) Purge Valve:** abriu de ~39% → ~62%. O controlador respondeu ao aumento de pressão, mas não foi suficiente para conter o acúmulo.
- **XMEAS(10) Purge Flow:** visualmente próximo de zero na escala do gráfico (eixo compartilhado com XMV%), mas em valor real ~0.4 kscmh — insuficiente dado o volume de acúmulo.

**Mecanismo identificado:** IDV(1) reduziu A de 0.485 → 0.455 mol frac (−6%) e aumentou C de 0.510 → 0.540 (+6%) na corrente 4. Menos A disponível → reações A+C+D→G(liq) e A+C+E→H(liq) mais lentas → **menos gás consumido pelas reações** → inventário gasoso acumula → pressão sobe. A temperatura não cai porque a redução de calor gerado é compensada pela redução de calor absorvido na formação dos produtos — o balanço térmico permanece, mas o balanço de massa não fecha.

### Conclusão

**Hipótese refutada.** IDV(1) não desloca a planta para um novo SS estável — causa colapso por sobrepressão em ~2.5h simuladas.

O mecanismo dominante é **balanço de massa, não térmico**: A é reagente limitante das reações que consomem gás (fase vapor → fase líquida). Menos A → reações mais lentas → menos gás convertido em líquido → acúmulo de inventário gasoso → pressão monotonicamente crescente. O controlador P de pressão (purge via XMV(6)) abre corretamente mas a taxa de remoção pela purga não acompanha a taxa de acúmulo — não há equilíbrio possível com os 3 controladores atuais sob IDV(1).

A temperatura flat é uma **armadilha diagnóstica**: sem sinal térmico, o operador não tem aviso precoce — a pressão é o único indicador e já está em trajetória de colapso quando se torna observável.

**Implicação para o supervisor:** IDV(1) exige ação composicional (ajuste de setpoint de feed ou razão A/C), não apenas pressão. Um controlador P de pressão via purge é insuficiente para rejeitar este distúrbio. Isso motiva a lógica supervisória do operator (issue [#44]) — detectar a tendência de pressão crescente e agir preventivamente antes do ISD.

**Próximo passo:** Exp 16 — IDV(1) com supervisor ativo, verificar se a lógica do operator consegue detectar e reagir antes do colapso.

---

## Experimento 14 — IDV(4): Step na temperatura de entrada do CW do reator

**Data:** 2026-05-18 — **Iniciado** (em andamento)

### Observação

IDV(4) eleva +5°C a temperatura de entrada da água de resfriamento do reator. Este distúrbio é importante para validar a resposta dinâmica dos controladores P quando há degradação da remoção de calor. A nova infraestrutura (STEP_DELAY_MS=36, RECORD_CSV) permite capturar a resposta em tempo real com precisão.

### Hipótese

Menor gradiente térmico no reator → remoção de calor reduzida → temperatura do reator sobe (XMEAS(9)) e com ela a pressão (XMEAS(7)). O controlador de pressão abre o purge (XMV(6)) para compensar a pressão. XMEAS(21) (CW outlet temp do reator) sobe de forma proporcional. Esperando novo SS estável com temperatura e pressão do reator ~5°C / ~10–30 kPa acima do baseline, e purge levemente mais aberto. Separator e Stripper Levels devem permanecer controlados pelos seus respectivos P-controllers.

### Intervenção

Configuração via debugger VSCode local com controle via painel IHM em tempo real:

**tep-plant:**
```
Debugger config: "Planta: baseline (100x, sem distúrbios)"
  STEP_DELAY_MS=36
  ACTIVE_IDV=""  (vazio — distúrbios controlados via IHM)
```

**tep-ihm:**
```
Debugger config: "IHM: planta local (gRPC + CSV)"
  RECORD_CSV=true
  RECORD_CSV_PATH=/data/simulation_log_exp_14.csv
  ACTIVE_IDV=""  (vazio)
```

**Procedimento:**

1. Iniciar planta com `ACTIVE_IDV=""` (sem distúrbios)
2. Iniciar IHM e conectar via WebSocket
3. Aguardar atingir steady-state (~5min a 100×)
4. Clicar em botão **IDV(4)** no painel "Disturbances" para ativar
5. Observar resposta dinâmica dos controladores em tempo real nos charts
6. Deixar rodar até novo steady-state (~20h simuladas, ~12 min de relógio)

Duração total: ~25h de tempo simulado (~15 min de relógio a 100×). Snapshot inicial: `te_exp3_snapshot.toml`. IDV(4) ativado via painel IHM em t≈5h.

### Resultado

**Arquivo:** `docs/simulations/simulation_log_14.0.csv` — **Plot:** `docs/simulations/plots/simulation_log_14.0.png`

A planta não atingiu novo steady-state. Entrou em colapso térmico durante o cold-start antes de o IDV(4) produzir efeito observável. Comportamento em t = 0,048 → 0,192 h:

- **XMEAS(9) Reactor T:** caiu continuamente de ~118°C → ~83°C. Nunca se recuperou.
- **XMEAS(7) Reactor P:** subiu monotonicamente de ~2700 → ~2950 kPa, chegando próximo ao ISD (3000 kPa).
- **XMV(6) Purge Valve:** controlador abriu a purga de ~39% → ~65%, mas não conteve a pressão.
- **ISD:** ocorreu em t ≈ 0,185 h por `deriv_norm → 0` com alarme de pressão ativo. O solver colapsou antes de cruzar 3000 kPa.

**Mecanismo:** temperatura baixa → cinética de Arrhenius lenta (rr[0] cai ~33× entre 120°C e 95°C, ~200× a 80°C) → reagentes A/C/D/E acumulam no vapor → pressão sobe. Purga age sobre o sintoma, não sobre a causa. Loop de colapso irreversível.

### Conclusão

**Experimento encerrado — infrutífero. Não reabrir sem resolução prévia da modelagem.**

A investigação revelou que IDV(4) requer uma modelagem correta do trocador de calor do reator para ser observável. No FORTRAN original (Downs & Vogel 1993), `YP(37)` nunca é atribuído — `TWR = YY(37)` é efetivamente um estado congelado em 94,6°C, e `IDV(4)` altera `TCWR` mas esse valor não chega a `QUR`. A implementação quasi-static introduzida no Rust ([model.rs L657](../tep-plant/tennessee-eastman-service/core/src/dynamics/tep/model.rs)) fazia `twr` responder a `tcwr` e `tcr`, o que produzia `QUR < 0` quando `tcr` caía abaixo de ~67°C no cold-start — comportamento fisicamente incorreto e potencialmente causador do colapso observado.

**Ação tomada (2026-06-01):** modelagem quasi-static comentada em `model.rs`; `twr = yy[36]` (fiel ao FORTRAN). A questão de como modelar corretamente o trocador de calor é um problema de modelagem aberto que está fora do escopo dos experimentos atuais.

**Redirecionamento:** os próximos experimentos focarão em IDV(1), IDV(2) e IDV(3), cujos efeitos são diretos (composição e temperatura de feed) e não dependem de modelagem do sistema de resfriamento. A sequência Exp 15–17 é ajustada em conformidade.

---




## Experimento 13 — Baseline revalidação com nova infraestrutura

### Observação

O Exp 11 estabeleceu a arquitetura de controladores desacoplados e validou numericamente o comportamento da planta (CSV idêntico ao Exp 10). Desde então, a infraestrutura de execução foi substancialmente alterada:

- **STEP_DELAY_MS=36** introduzido em `main.rs`: 100× real time (1h simulada = 36s de relógio)
- **ACTIVE_IDV** via variável de ambiente em vez de hardcode em `main.rs`
- **RECORD_CSV** na IHM: gravação de XMEAS + XMV via gRPC stream (não mais CSV interno do serviço Rust)
- **IDV panel** na IHM: visualização em tempo real dos distúrbios ativos
- Configuração via `docker-compose.yml` ou VS Code `launch.json` em vez de edição direta de código

Nenhum desses componentes foi validado em conjunto. É possível que a aceleração de tempo (36ms/step) introduza diferenças numéricas, ou que o streaming gRPC perca amostras sob carga.

### Hipótese

A nova infraestrutura é transparente: o modelo físico da planta não foi alterado. Com `STEP_DELAY_MS=36`, `ACTIVE_IDV=` (vazio), e a IHM gravando CSV via gRPC, o comportamento dinâmico deve ser **numericamente equivalente** ao Exp 11. As trajetórias de pressão (~2680→2700 kPa), nível do reator (~69→73%), Sep/Stripper levels (~50%) e temperatura (~120°C) devem reproduzir o baseline do Exp 10/11 dentro da resolução da gravação.

### Intervenção

Configuração via `docker-compose.yml` em `tep-supervisor/local/`:

```yaml
te-plant:
  environment:
    - STEP_DELAY_MS=36
    # ACTIVE_IDV não definido (vazio = sem distúrbio)

tep-ihm:
  environment:
    - RECORD_CSV=true
    - RECORD_CSV_PATH=/data/recording.csv
    - ACTIVE_IDV=
```

Duração: 20h de tempo simulado (≈ 12 min de relógio a 100×). Snapshot inicial: `te_exp3_snapshot.toml`. Download do CSV ao final via `⬇ CSV` na IHM.

### Resultado

Simulação executada de `t = 5h` a `t = 25h` (20h simuladas ≈ 12 min de relógio real) via VS Code debugger local:
- **tep-plant**: debugger "Planta: baseline (100x, sem distúrbios)" — `STEP_DELAY_MS=36`, `ACTIVE_IDV=""` (vazio)
- **tep-ihm**: debugger "IHM: planta local (gRPC + CSV)" — `RECORD_CSV=true`, conectado via `localhost:50051`

CSV gravado: `C:\Projetos\tep\tep-supervisor\local\data\recording.csv` (1445 linhas, 20h simuladas, sem distúrbios).

**Estatísticas do baseline (t=5h→25h):**

| Variável                   | Média        | Desvio Padrão | Intervalo                |
| -------------------------- | ------------ | ------------- | ------------------------ |
| Reactor Pressure (XMEAS_7) | 2699.557 kPa | 1.364 kPa     | [2696.385, 2702.117] kPa |
| Separator Level (XMEAS_12) | 49.959%      | 1.000%        | [46.896, 53.228]%        |
| Stripper Level (XMEAS_15)  | 50.009%      | 0.998%        | [46.870, 53.553]%        |

**Comparação com Exp 11 (baseline anterior):**
- Reactor Pressure: Exp 11 ≈ 2700.53 kPa, Exp 13 ≈ 2699.56 kPa — **diferença: −0.97 kPa** (esperado, dentro do ruído)
- Separator Level: Exp 11 ≈ 50.54%, Exp 13 ≈ 49.96% — **diferença: −0.58%** (muito próximo)
- Stripper Level: Exp 11 ≈ 50.06%, Exp 13 ≈ 50.01% — **diferença: −0.05%** (praticamente idêntico)

### Conclusão

✅ **Hipótese validada.** A nova infraestrutura (`STEP_DELAY_MS=36`, `RECORD_CSV` via gRPC) é **numericamente equivalente** ao Exp 11 (antes do refactor). As trajetórias das 3 variáveis críticas (pressão do reator, nível do separador, nível do stripper) reproduzem o baseline do Exp 10/11 dentro da resolução esperada (±2% de erro relativo máximo). A planta permanece estável por 20h sem distúrbios, os controladores P mantêm os setpoints, e o streaming gRPC não introduz perda de dados ou desvios significativos. **Exp 13 completo — baseline validado. Pronto para Exp 3+ (distúrbios).**


## Experimento 12 — Validação da stack integrada e conectividade do operator

**Data:** 2026-04-10 → **Concluído em:** 2026-05-18

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

| Variável                  | Valor    | Observação                              |
| ------------------------- | -------- | --------------------------------------- |
| XMEAS(7) Reactor Pressure | 2705 kPa | No setpoint                             |
| XMEAS(8) Reactor Level    | 75.5%    | Acima da faixa do PLCMachine (max: 60%) |
| XMEAS(12) Sep Level       | 49.6%    | Normal                                  |
| XMEAS(15) Stripper Level  | 49.5%    | Normal                                  |

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

Após regeneração dos arquivos `.pb.go` (protobuf) no repositório `tep-operator` para resolver incompatibilidade de versão com a imagem Docker, o operator subiu sem erros e estabeleceu conexão com a planta via `host.docker.internal:50051`.

**Evidência — Status do PLCMachine (IHM em 2026-05-18 17:59):**

| Campo                     | Valor                   |
| ------------------------- | ----------------------- |
| Phase                     | **Stable** (de Pending) |
| Plant Time                | 30119.41 h (rodando)    |
| Last Reconcile            | 14:59:36 (ativo)        |
| reactor_pressure (XMEAS7) | 2705.084 kPa — ok       |
| separator_level (XMEAS12) | 50.139 % — ok           |
| stripper_level (XMEAS15)  | 49.343 % — ok           |

**Logs do operator (amostra de 2026-05-18T17:56:27Z):**

```
INFO observation cycle complete
  plantTime: 28019.84600524964 h
  xmeas_count: 41
  xmv_count: 12
  policy_variables: 3
  deriv_norm: 488.38605936327184
```

O operator está reconciliando continuamente, lendo todas as 41 XMEAS e 12 XMV, avaliando as 3 variáveis de política, e mantendo o PLCMachine em fase `Stable`.

### Conclusão

✅ **Hipótese validada.** O `host.docker.internal:50051` é o endereço correto para que o operator (no cluster Kind) alcance a planta (container Docker no host). A conectividade bidirecional está estabelecida e estável. O operator consegue ler a planta, avaliar as faixas de operação, e manter estado sincronizado. **Exp 1 completo — pronto para Exp 2 (baseline).**

## Experimento 11 — Desacoplamento dos controladores da planta

### Observação

O Exp 10 estabeleceu o baseline canônico: planta estável por 20h, sem distúrbio, com 3 controladores P hardcoded diretamente no `runtime.rs`. A lógica de controle está embutida no loop de simulação:

```rust
// runtime.rs — estado atual (acoplado)
let reactor_p = plant.bus.outputs.xmeas[6];
plant.bus.inputs.mv[5] = (40.06 + 0.10 * (reactor_p - 2705.0)).clamp(0.0, 100.0);

let sep_level = plant.bus.outputs.xmeas[11];
plant.bus.inputs.mv[6] = (38.1 + 1.0 * (sep_level - 50.0)).clamp(0.0, 100.0);

let strip_level = plant.bus.outputs.xmeas[14];
plant.bus.inputs.mv[7] = (46.5 + 1.0 * (strip_level - 50.0)).clamp(0.0, 100.0);
```

Nessa arquitetura, trocar, reconfigurar ou adicionar controladores exige modificar o código do runtime. Não há separação entre o modelo da planta e a camada de controle. Isso inviabiliza a gestão externa de controladores via Kubernetes CRDs, que é o objetivo arquitetural do projeto.

### Hipótese

Extraindo os controladores para uma trait `Controller` com interface `step(xmeas, xmv)` e um `ControllerBank` injetável no loop de simulação, o `runtime.rs` passa a ser agnóstico em relação à lógica de controle. O comportamento dinâmico deve ser **matematicamente idêntico** ao Exp 10: mesmos ganhos, mesmos setpoints, mesmas três malhas — apenas a organização do código muda.

A arquitetura proposta:

```
service/src/
  controllers/
    mod.rs            ← trait Controller + ControllerBank
    p_controller.rs   ← PController (implementação concreta)
  runtime.rs          ← loop de simulação sem lógica de controle inline
  main.rs             ← constrói controladores e injeta no runtime
```

**Trait Controller:**
```rust
pub trait Controller: Send {
    fn step(&mut self, xmeas: &[f64], xmv: &mut [f64]);
}
```

**ControllerBank:**
```rust
pub struct ControllerBank {
    controllers: Vec<Box<dyn Controller>>,
}
impl ControllerBank {
    pub fn step(&mut self, xmeas: &[f64], xmv: &mut [f64]) {
        for ctrl in &mut self.controllers {
            ctrl.step(xmeas, xmv);
        }
    }
}
```

**Loop de simulação refatorado:**
```rust
// runtime.rs — após refatoração
plant.step(config.dt);          // integra com mv atuais
// ramp logic (inalterada)...
bank.step(&plant.bus.outputs.xmeas, &mut plant.bus.inputs.mv); // calcula novos mv
```

**Injeção em main.rs:**
```rust
let mut bank = ControllerBank::default();
bank.add(Box::new(PController { xmeas_idx: 6,  xmv_idx: 5, kp: 0.1, setpoint: 2705.0, bias: 40.06 }));
bank.add(Box::new(PController { xmeas_idx: 11, xmv_idx: 6, kp: 1.0, setpoint: 50.0,   bias: 38.1  }));
bank.add(Box::new(PController { xmeas_idx: 14, xmv_idx: 7, kp: 1.0, setpoint: 50.0,   bias: 46.5  }));
```

As premissas de design que governam esta refatoração — ordem do loop, escrita em XMV e responsabilidade da trait — estão registradas em `docs/01-premissas.md § Premissas para o Desacoplamento dos Controladores da Planta`.

Essa separação permite no futuro: alterar setpoints/ganhos via CRD, ativar/desativar malhas individualmente, conectar controladores de qualquer tipo (PID, MPC, RL) sem tocar no runtime.

### Intervenção

Arquivos a modificar:

- `tennessee-eastman-service/service/src/controllers/mod.rs` — novo: trait `Controller` + `ControllerBank`
- `tennessee-eastman-service/service/src/controllers/p_controller.rs` — novo: `PController`
- `tennessee-eastman-service/service/src/runtime.rs` — remover lógica de controle inline; receber `ControllerBank` como parâmetro
- `tennessee-eastman-service/service/src/main.rs` — construir os 3 `PController`s com os parâmetros do Exp 10 e injetar; `active_idv: vec![]`, snapshot `te_exp11_snapshot.toml`

Condição inicial: `te_exp3_snapshot.toml`. Duração: 20h. IDVs: desativados. Parâmetros dos controladores: **idênticos ao Exp 10** (Kp pressão = 0.1, Kp sep = 1.0, Kp strip = 1.0).

### Resultado

Simulação rodou 20h sem ISD, IDVs desativados, controladores injetados via `ControllerBank`. O CSV gerado (`simulation_log_13.csv`) é **numericamente idêntico** ao baseline Exp 10 (`simulation_log_12.csv`) — valores bit-a-bit iguais em todas as 53 colunas, todos os timesteps.

Variáveis-chave em t=20h (idênticas ao Exp 10):
- Pressão do reator: 2700.53 kPa (SP=2705, offset −4.5 kPa)
- Nível do separador: 50.54% (SP=50%)
- Nível do stripper: 50.06% (SP=50%)
- Temperatura do reator: 120.42°C
- UCVR total: 357.1 kmol (drift lento, mesmo perfil do Exp 10)
- Sem ISD, sem oscilações, sem divergência

### Conclusão

A refatoração é **transparente**: a separação dos controladores em trait `Controller` + `ControllerBank` não alterou o comportamento dinâmico da planta. O CSV é idêntico ao Exp 10, confirmando que a mudança é puramente arquitetural.

A planta agora tem separação clara entre modelo e controle. Controladores são injetáveis, substituíveis e configuráveis sem modificar `runtime.rs`. A arquitetura está pronta para:
- gestão externa via Kubernetes CRDs
- adição de novas malhas (PID, MPC, RL)
- ativação/desativação individual de loops
- alteração de setpoints e ganhos em runtime


## Experimento 10 — Baseline de referência para distúrbios (IDV desativado, 20h)

### Observação

Antes de introduzir qualquer IDV, é necessário um run de referência longo que registre o comportamento da planta **sem distúrbio** a partir do mesmo snapshot inicial (`te_exp3_snapshot.toml`, 3 controladores). Esse run serve como baseline quantitativo: as trajetórias de pressão, nível, inventários e deriv_norm do baseline serão subtraídas dos runs com IDV para isolar o efeito puro do distúrbio do drift natural do sistema.

**Precauções metodológicas:**
1. **Snapshot fixo**: todos os experimentos de distúrbio usarão `te_exp3_snapshot.toml` como condição inicial — garantindo comparabilidade entre runs
2. **Baseline de referência**: este Exp 10 documenta as trajetórias de referência (sem distúrbio) que servirão de comparação para todos os IDVs futuros

**Estado de referência em t=0 (te_exp3_snapshot.toml):**

| Variável           | Valor       |
| ------------------ | ----------- |
| Pressão reator     | ~2680 kPa   |
| Temperatura reator | ~120 °C     |
| Nível reator       | ~69 %       |
| Σ UCVR             | ~350 kmol   |
| Σ UCVV             | ~333 kmol   |
| Recycle Flow       | ~26.8 kscmh |

### Hipótese

Com 3 controladores e sem distúrbio, a planta deve manter comportamento idêntico ao Exp 6, mas por 20h — confirmando que o drift de inventário (~0.15%/h) é um fenômeno lento e previsível que não compromete experimentos de distúrbio de curto prazo.

### Intervenção

Arquivos modificados:
- `tennessee-eastman-service/service/src/runtime.rs` — 4ª malha removida, 3 controladores P base restaurados; setpoint de pressão 2705 kPa
- `tennessee-eastman-service/service/src/main.rs` — `active_idv: vec![]`, `max_sim_time_h: Some(20.0)`, snapshot `te_exp10_snapshot.toml`

### Resultado

Simulação completou 20h sem ISD. Snapshot salvo em `cases/te_exp10_snapshot.toml`.

**Trajetórias de referência (baseline para comparação com IDVs):**

| Variável              | t=0         | t=20h       | Drift/h       |
| --------------------- | ----------- | ----------- | ------------- |
| Pressão reator        | ~2680 kPa   | ~2700 kPa   | +1 kPa/h      |
| Temperatura reator    | ~120 °C     | ~120 °C     | ≈0            |
| Nível reator          | ~69 %       | ~73 %       | +0.2 %/h      |
| Sep / Stripper Levels | ~50 %       | ~50 %       | ≈0            |
| Σ UCVR                | ~350 kmol   | ~357 kmol   | +0.35 kmol/h  |
| Σ UCVV                | ~332.5 kmol | ~334.2 kmol | +0.085 kmol/h |
| Recycle Flow          | ~26.8 kscmh | ~26.8 kscmh | ≈0            |
| Purge valve           | ~39.3 %     | ~39.8 %     | +0.025 %/h    |

Os controladores mantiveram todas as variáveis operacionais dentro das faixas normais. O `deriv_norm` manteve-se estável (~500–2000 unidades/h) após o transiente inicial. As válvulas de feed permaneceram no nominal e o recycle só exibiu o ruído de medição já caracterizado.

**Drift de inventário**: UCVR +0.35 kmol/h e UCVV +0.085 kmol/h — total ~0.44 kmol/h, significativamente **mais lento** do que o observado em runs de 5h (Exp 6: ~0.5 kmol/h). Isso confirma que o drift está desacelerando assintoticamente — provavelmente converge para um SS verdadeiro em horizonte muito longo.

### Conclusão

**Baseline validado.** O sistema permanece estável por 20h com 3 controladores, sem qualquer tendência de instabilidade ou aproximação de limites ISD. O drift de inventário (~0.15%/h total sobre 682 kmol) é lento, previsível, e está desacelerando — irrelevante para experimentos de distúrbio de 20h.

Este run constitui a **trajetória de referência canônica**: qualquer desvio observado nos experimentos com IDV em relação a estas curvas pode ser atribuído diretamente ao efeito do distúrbio, não à dinâmica natural do modelo.


## Experimento 9 — Controlador de nível do reator (4ª malha)

### Observação

Os Exps 6–8 demonstraram que a planta acumula ~1 kmol/h de gás com composição constante, indicando desbalanço de massa global não corrigível pelos 3 controladores P atuais. A única forma de fechar o balanço sem alterar a química é adicionar uma malha que regule o inventário total do reator. Na literatura TEP (Downs & Vogel 1993, Ricker 1996), o nível do reator XMEAS(8) é a variável canônica para isso, manipulada via A feed (XMV(3)).

### Hipótese

Adicionando um controlador P de nível do reator: `mv[2] = nominal_A_feed * (1 + Kc*(reactor_lv − SP_lv))` com SP = 69% (nível atual de operação) e Kc moderado (~0.5–1.0 %/%), o nível do reator deve estabilizar e o acúmulo de UCVR deve cessar. Se UCVR ficar horizontal, o balanço de massa foi fechado.

### Intervenção

Arquivo modificado: `tennessee-eastman-service/service/src/runtime.rs`

```rust
// setpoint de pressão revertido para 2705 kPa (base pré-Exp 7)
plant.bus.inputs.mv[5] = (40.06 + 0.10 * (reactor_p - 2705.0)).clamp(0.0, 100.0);

// 4º controlador: nível do reator → A feed (mv[2])
// Raciocínio: mais A feed → mais reação → mais produto líquido → nível sobe.
// Realimentação negativa: nível alto → reduz A feed.
let reactor_lv = plant.bus.outputs.xmeas[7];
plant.bus.inputs.mv[2] = (nominal_mv[2] - 0.5 * (reactor_lv - 69.0)).clamp(0.0, 100.0);
```

SP = 69.0% (nível atual de operação), Kc = 0.5 %/%.

### Resultado

A 4ª malha não estabilizou o balanço de massa — pelo contrário, o acúmulo acelerou:

- **Σ UCVR**: 350 → 377 kmol em 5h (+27 kmol, ~5.4 kmol/h — 6× pior que Exp 6)
- **Σ UCVV**: 333 → 339 kmol em 5h (+6 kmol — também pior)
- **Reactor Level**: subiu de ~69% → ~78%, sem estabilizar apesar do controlador reduzir A feed
- **Reactor Pressure**: subiu de ~2680 → ~2750 kPa, com tendência crescente
- **XMV(3) (A feed)**: reduzido de ~24.6% → ~20.6% pelo controlador — agindo, mas sem efeito sobre o balanço gasoso

### Conclusão

**Hipótese refutada.** A malha nível → A feed não fecha o balanço de massa gasosa. O mecanismo identificado: a pressão sobe pelo acúmulo de gás → o VLE desloca mais material para a fase líquida → o nível do reator sobe como efeito secundário. O controlador vê o sintoma (nível alto) e reduz A feed, mas isso não atua sobre a causa raiz (remoção de gás insuficiente pela purge).

**Decisão estratégica:** A busca por SS perfeito com os atuais 3 controladores P está rendendo retornos decrescentes. O drift de gás é ~0.15%/h sobre o inventário total — desprezível para runs de 10–20h. O TEP como benchmark foi projetado para avaliação de **rejeição de distúrbios**, não para caracterização de SS. Os experimentos 6–9 caracterizaram o comportamento do baseline adequadamente. **A partir do Exp 10, o foco muda de caracterização da planta para avaliação de resposta a distúrbio.**


## Experimento 8 — Identificação do componente acumulante em UCVR

### Observação

O CSV dos Exps 6 e 7 contém YY[0..7] (componentes A–H do vapor do reator) individualmente. Os painéis atuais mostram apenas a soma Σ UCVR. Não sabemos se o acúmulo é em produtos (G, H — gerados pela reação) ou em reagentes/inertes (A, B, C) — e essa distinção determina a ação de controle correta: acúmulo de produtos → remoção insuficiente; acúmulo de inertes → purge insuficiente.

### Hipótese

O componente crescente é G e/ou H (produtos da reação em fase vapor), porque a taxa de condensação/remoção não acompanha a produção. Se for A ou B, o problema é outro (reagente não consumido / inerte acumulando).

### Intervenção

Modificação em `analysis/tep_analysis/plot.py`: adição de painel com os 8 componentes individuais de UCVR (YY[0]–YY[7] = A, B, C, D, E, F, G, H) para re-análise do CSV do Exp 7, sem nova execução da simulação.

### Resultado

O painel de componentes individuais mostrou que **todas as 8 espécies A–H crescem de forma proporcional às suas concentrações iniciais** — nenhum componente dispara isoladamente. G e H (~145 kmol cada) dominam o inventário (~84% do UCVR total) e crescem no mesmo ritmo relativo que A, B, C, D, E, F. A **composição do vapor do reator é essencialmente constante** ao longo de 5h; apenas o total de moles aumenta.

### Conclusão

**A hipótese "acúmulo seletivo de G/H por remoção insuficiente" foi refutada.** A causa não é química nem de separação — é estrutural.

O padrão "todos os componentes crescem proporcionalmente, composição constante" é a assinatura de um **desbalanço de massa global**: entrada total de gás > saída total, com o loop de reciclo mantendo sua composição enquanto pressuriza lentamente. Os 3 controladores P (pressão do reator via purge, sep level, stripper level) não possuem nenhuma variável de estado que feche explicitamente o balanço de massa gasosa — a pressão do reator é o único sinal indireto disponível, mas seu controlador já opera no limite do que consegue compensar com a purge.

**Conclusão estrutural**: para fechar o balanço de massa é necessário um 4º controlador com ação sobre o inventário total. A opção mais natural no TEP é controlar o **nível do reator** (XMEAS(8), variável de nível líquido, proxy do inventário total do reator) via uma válvula de alimentação — tipicamente o A feed (XMV(3)). Isso é o que a literatura de controle do TEP implementa como malha primária de inventário. Enquanto essa malha não existe, a planta acumula gás lentamente (taxa ~1 kmol/h em ~683 kmol total, ~0.15%/h) — irrelevante para runs curtas (<20h) mas significativo em horizontes de 100h+.


## Experimento 7 — Ajuste do setpoint do controlador de pressão

### Observação

O Exp 6 revelou que o inventário gasoso da planta (UCVR + UCVV) acumula lentamente (~0.4–0.5 kmol/h por vaso). O controlador de pressão atual usa setpoint 2705 kPa: `mv[5] = 40.06 + 0.10*(P − 2705)`. A planta opera em ~2680 kPa — 25 kPa abaixo do setpoint — o que mantém a purge valve 2.5% abaixo do seu ponto nominal (39.3% vs 40.06%), reduzindo a remoção de gás.

### Hipótese

Alterando o setpoint do controlador de pressão de 2705 kPa para 2680 kPa (o valor real de operação), a purge valve se abrirá para ~40.06%, aumentando levemente a remoção de gás e zerando o acúmulo de UCVR/UCVV. Se o acúmulo cessar (UCVR e UCVV ficarem constantes), o balanço de massa foi fechado.

### Intervenção

Arquivo modificado: `tennessee-eastman-service/service/src/runtime.rs`

```rust
// setpoint 2705 → 2680 kPa
plant.bus.inputs.mv[5] = (40.06 + 0.10 * (reactor_p - 2680.0)).clamp(0.0, 100.0);
```

Efeito esperado: com P_op ≈ 2680 kPa e setpoint = 2680 kPa, o controlador opera no seu ponto neutro → purge valve ≈ 40.06% (vs ~37.5% no Exp 6).

### Resultado

**Σ UCVR:** crescimento de ~350.0 → ~354.5 kmol em 5h (**+4.5 kmol, ~0.9 kmol/h**) — acúmulo quase o dobro do Exp 6.

**Σ UCVV:** após transiente inicial, converge e praticamente estabiliza (~332.8 → ~333.2 kmol em ~4.8h, +0.4 kmol total) — acúmulo quase zerado.

O ajuste redistribuiu o desbalanço: UCVV convergiu, mas UCVR piorou. A taxa total de acúmulo (UCVR + UCVV combinados) não caiu.

### Conclusão

**Hipótese refutada.** O setpoint de pressão não era a causa raiz do desbalanço de massa. O ajuste mudou a distribuição do acúmulo entre os dois vasos mas não fechou o balanço global. O fato de UCVV quase estabilizar enquanto UCVR acelera sugere que o gás "extra" que antes ficava no compressor passou a ser retido no reator — possivelmente porque o aumento da purge reduziu a pressão no loop de reciclo, diminuindo o fluxo de gás do reator para o separador e retendo mais vapor no espaço gasoso do reator.

A causa real do acúmulo está em **qual componente específico está crescendo dentro de UCVR**. O CSV do Exp 7 já contém YY[0..7] individualmente — o próximo passo é analisar esses dados sem nova simulação.

---

## Experimento 6 — Identificação do estado ODE oscilante

### Observação

O Exp 5 demonstrou que o `deriv_norm` oscila em sincronia com XMEAS(5) (recycle flow), indicando que pelo menos um dos 50 estados ODE está oscilando. O CSV atual registra apenas XMEAS(1–22) e XMV(1–12) — não há logging dos componentes individuais do vetor de estado YY que permitiria identificar qual estado específico carrega a oscilação.

### Hipótese

A oscilação está nos holdups de vapor do vaso/compressor (UCVV, YY[27–34]) que são as variáveis de estado diretamente ligadas ao fluxo de reciclo. Se UCVV oscilar com a mesma frequência e fase que XMEAS(5), a oscilação é uma dinâmica real do loop de reciclo. Se UCVV for liso e apenas XMEAS(5) oscilar, o ruído vem da camada de medição (TESUB8 no modelo FORTRAN/Rust).

### Intervenção

Arquivo modificado: `tennessee-eastman-service/service/src/runtime.rs`

Adicionados ao header e às linhas do CSV:
- **YY[0..10]** — UCVR (holdups de vapor do reator, componentes A–H) + ETR (energia do reator): permite detectar se a oscilação nasce no reator antes de se propagar para o reciclo
- **YY[27..35]** — UCVV (holdups de vapor do compressor/vaso, componentes A–H) + ETV (energia do vaso): estado interno que alimenta diretamente o cálculo de XMEAS(5)

`dt` revertido para 0.001 h e snapshot renomeado para `te_exp6_snapshot.toml`.

### Resultado

**Σ UCVR (reator, YY[0–7]):** tendência monotônica crescente de ~350.4 → ~352.5 kmol ao longo de 5h (+2.1 kmol, ~0.42 kmol/h). Curva completamente lisa — nenhuma oscilação de alta frequência visível.

**Σ UCVV (compressor, YY[27–34]):** spike de inicialização em t≈0.1h (~+12 kmol, artefato algébrico do RK4 — mesmo observado no deriv_norm do Exp 4), seguido de tendência crescente suave de ~334.2 → ~336.6 kmol (+2.4 kmol em ~4.8h, ~0.5 kmol/h). Também completamente liso após o transiente inicial.

Enquanto isso, XMEAS(5) (recycle flow) continuou exibindo as mesmas oscilações de ±0.5 kscmh de experimentos anteriores.

### Conclusão

**A hipótese "dinâmica real do loop de reciclo" foi refutada.** Os estados ODE UCVR e UCVV são lisos — não exibem as oscilações de alta frequência presentes em XMEAS(5). As oscilações do recycle flow são **ruído de medição injetado pelo modelo** (via TESUB8 no FORTRAN original / camada de medição do Rust), não dinâmica real do sistema.

**Descoberta secundária de maior relevância:** ambos UCVR e UCVV acumulam massa lentamente (+0.4–0.5 kmol/h cada). O inventário gasoso total da planta está crescendo de forma persistente. Isso confirma que os 3 controladores P (pressão, sep level, stripper level) **não fecham o balanço de massa** no ponto de operação atual — há um desbalanço lento entre geração de gás pela reação e remoção pelo purge. A deriva de nível do reator observada nos Exps 2 e 3 é a manifestação volumétrica desse acúmulo.

**Próximo passo natural:** investigar o desbalanço de massa. A hipótese mais direta é que o setpoint do controlador de purge (baseado em pressão: `mv[5] = 40.06 + 0.10*(P − 2705)`) não está removendo gás suficientemente — a pressão de operação estabiliza em ~2680 kPa (abaixo de 2705 kPa), o que fecha levemente a purge valve, reduzindo a remoção de gás e permitindo o acúmulo. Ajustar o setpoint de pressão do controlador para 2680 kPa deve reequilibrar o balanço.


## Experimento 5 — Investigação das oscilações do recycle flow

### Observação

No Exp 4, o recycle flow (XMEAS(5)) exibiu oscilações persistentes de ~±0.5 kscmh ao longo de toda a run de 5h, sem amortecimento visível. Todos os outros sinais monitorados (pressão, temperatura, níveis, purge) são estáveis. Não é possível determinar, apenas observando o plot, se essas oscilações são física real ou artefato numérico do integrador RK4 com dt=0.001 h.

### Hipótese

Se as oscilações forem artefato numérico do passo de integração, reduzir dt de 0.001 h para 0.0001 h deve reduzir ou eliminar as oscilações no recycle flow enquanto mantém todos os demais estados estáveis. Se as oscilações persistirem com dt menor, são dinâmica real da planta.

### Intervenção

Arquivo modificado: `tennessee-eastman-service/service/src/main.rs`

```rust
dt: 0.0001,   // reduzido de 0.001 h → 0.0001 h (10× menor)
```

Todos os demais parâmetros idênticos ao Exp 4 (snapshot Exp 3, ramp=0, 5h, sem IDV).

### Resultado

Com dt reduzido 10×, as oscilações de XMEAS(5) persistiram com amplitude e padrão visual idênticos ao Exp 4: mesma faixa (~26.2–27.8 kscmh), mesma rugosidade, mesma persistência ao longo de 5h. Os demais sinais (pressão, temperatura, níveis, purge) permaneceram estáveis e lisos. Adicionalmente, o `deriv_norm` também exibiu oscilações persistentes ao longo de toda a run (faixa aproximada 500–5000 unidades/h), com o mesmo padrão temporal que XMEAS(5). Esse detalhe é relevante: `deriv_norm = max‖dy/dt‖` é calculado diretamente dos derivativos dos 50 estados ODE, sem qualquer componente de ruído de medição.

### Conclusão

A hipótese "as oscilações são artefato numérico do passo de integração RK4" foi **refutada** (ou pelo menos fortemente enfraquecida): a amplitude não variou com redução de 10× no dt.

O fato de `deriv_norm` oscilar em sincronia com XMEAS(5) é evidência de que **o vetor de estado em si está oscilando**, não apenas a medição. Isso elimina a hipótese de ruído puro de medição como causa dominante e aponta para dinâmica real do loop de reciclo — provavelmente uma oscilação não amortecida emergente da interação entre o controlador P de pressão (purge valve) e a dinâmica do compressor/reciclo nesse ponto de operação.

A próxima separação necessária é: **qual estado ODE específico está oscilando?** A hipótese mais forte é que são os holdups de vapor do compressor (UCVV, estados YY[27–34]) que alimentam o cálculo de XMEAS(5). Se o estado interno for liso e apenas XMEAS(5) oscilar, é ruído de medição do modelo; se UCVV oscilar com a mesma frequência, a oscilação é física.

---

## Experimento 4 — Validação do snapshot como ponto de partida direto

### Observação

O Exp 3 gerou `cases/te_exp3_snapshot.toml` em t = 20.0 h. Esse vetor de estado está próximo do attractor da nossa camada de controle — CW temps no nominal, válvulas de feed nos valores nominais de FORTRAN, controladores P estabilizando pressão e níveis. Nunca foi testado se esse snapshot pode substituir completamente o cold start: se `initial_state_path = te_exp3_snapshot.toml` com `ramp_duration = 0.0` produz operação estável imediata ou se o estado YY exportado introduz inconsistências algébricas que causam ISD.

### Hipótese

Com `initial_state_path = te_exp3_snapshot.toml` e `ramp_duration = 0.0` (feed valves já no valor nominal desde t=0), a planta deve iniciar diretamente no attractor sem transiente de cold start, mantendo todos os estados dentro dos limites ISD desde o primeiro passo. O deriv_norm deve partir do mesmo patamar que terminamos no Exp 3 (~200–300 unidades/h) e continuar decaindo. Se a simulação sobreviver 5h sem alarme, o snapshot é validado como condição inicial reutilizável.

### Intervenção

Arquivo modificado: `tennessee-eastman-service/service/src/main.rs`

```rust
initial_state_path: "cases/te_exp3_snapshot.toml".into(), // boot from Exp 3 snapshot
ramp_duration: 0.0,                                        // no cold start (Exp 4)
active_idv: vec![],                                        // no disturbances
max_sim_time_h: Some(5.0),                                 // stop at t=5h
snapshot_path: Some("cases/te_exp4_snapshot.toml".into()), // save final state
```

### Resultado

A simulação completou 5 h sem disparar ISD. O snapshot foi escrito em `cases/te_exp4_snapshot.toml`.

**Comportamento observado:**

- **Feed Valve Ramp**: todas as 4 válvulas de feed constantes desde t=0 (D≈63%, E≈54%, A≈25%, A&C≈61%) — sem transiente de cold start
- **deriv_norm**: spike para ~20 000 unidades/h exatamente em t=0 (inconsistência algébrica de inicialização do integrador RK4), resolvido em <0.01 h, retornando a ~200–300 unidades/h
- **Reactor Level**: plano em ~69% durante toda a run — sem a deriva lenta observada nos Exps 2 e 3 (já estamos no attractor)
- **Reactor Pressure / Temperature**: absolutamente estáveis em ~2690 kPa e ~120 °C
- **Sep & Stripper Levels**: estáveis em ~48% com ruído de pequena amplitude
- **Purge valve**: ~39% constante; Purge Flow: ~0.4 kscmh constante
- **Recycle Flow**: média ~26.8 kscmh com **oscilações persistentes de alta frequência** (~±0.5 kscmh, amplitude consistente ao longo de 5h)

### Conclusão

Hipótese **confirmada**: o snapshot `te_exp3_snapshot.toml` é uma condição inicial válida e o boot direto com `ramp_duration=0.0` é seguro. A planta inicia diretamente no attractor sem transiente de cold start e sem acionar nenhum alarme ISD.

O spike de `deriv_norm` em t=0 não representa instabilidade — é um artefato de inicialização algébrica do RK4 que se dissipa em menos de 0.01 h simulado. A ausência de deriva no nível do reator confirma que o Exp 3 realmente convergiu para o attractor antes de terminar.

**Observação pendente — oscilações do recycle flow**: As oscilações de ~±0.5 kscmh em recycle são persistentes e não atenuam ao longo de 5h. Duas hipóteses: (a) são dinâmica inerente da planta nesse ponto de operação (oscilações naturais do loop de reciclo); ou (b) são artefato numérico do RK4 com dt=0.001 h. Essa questão deve ser investigada no Exp 5.

**Base estabelecida**: a partir deste experimento, todos os experimentos futuros podem usar `te_exp3_snapshot.toml` com `ramp_duration=0.0` como ponto de partida padrão, eliminando os primeiros 0.5h de overhead de cold start.

---

## Experimento 3 — Busca do SS sem distúrbio + snapshot de estado

### Observação

O Experimento 2 encontrou um attractor operável, mas com IDV(4) ativo e sem controlador de nível do reator. Não há evidência de que esse attractor coincide com o Mode 1 SS do FORTRAN. Adicionalmente, a simulação não tinha limite de tempo configurável nem capacidade de exportar
o estado final — o operador precisava interromper manualmente e não havia forma de reusar o estado para reinicializações.

### Hipótese

Removendo IDV(4) e rodando por 20h de tempo simulado, a planta deve convergir para um attractor mais próximo do Mode 1 SS (sem a perturbação do CW do reator). Capturando o vetor YY ao final como TOML, teremos um estado inicial pré-estabilizado que elimina o cold start transiente em
experimentos futuros.

### Intervenção

Arquivos modificados:
- `tennessee-eastman-service/service/src/config.rs` — novos campos `max_sim_time_h` e `snapshot_path`
- `tennessee-eastman-service/service/src/runtime.rs` — lógica de parada por tempo + escritor de snapshot TOML
- `tennessee-eastman-service/service/src/dashboard.rs` — fix label "s" → "h" no título
- `tennessee-eastman-service/service/src/main.rs` — config do Exp 3: sem IDV, 20h, snapshot habilitado

```rust
active_idv: vec![],                                  // sem distúrbio
max_sim_time_h: Some(20.0),                          // parar em t=20h
snapshot_path: Some("cases/te_exp3_snapshot.toml"),  // salvar estado final
```

### Resultado

A simulação completou 20 h de tempo simulado sem disparar ISD (clean exit). O snapshot foi escrito com sucesso em `cases/te_exp3_snapshot.toml`.

**Estado final em t = 20.0 h:**

| Variável               | Exp 3 (t=20h)  | Exp 2 (t=13h)  | Mode 1 nominal |
| ---------------------- | -------------- | -------------- | -------------- |
| Pressão reator         | ~2680 kPa      | ~2680 kPa      | 2705 kPa       |
| Temperatura reator     | ~120 °C        | ~120 °C        | 122.9 °C       |
| Nível reator           | ~69 % (deriva) | ~69 % (deriva) | —              |
| Purge valve (XMV(6))   | 39.07 %        | ~40 %          | 40.06 %        |
| Sep underflow (XMV(7)) | 36.83 %        | ~38 %          | 38.10 %        |
| CW temp reator         | 94.60 °C       | —              | 94.60 °C       |
| CW temp separador      | 77.30 °C       | —              | 77.30 °C       |

O attractor encontrado em Exp 3 é **virtualmente idêntico ao de Exp 2**: a remoção do IDV(4) não alterou o ponto de operação. As temperaturas de água de resfriamento convergiram exatamente para os valores nominais do FORTRAN TEINIT (ausência de IDV(4) → sem forçamento externo). O nível do reator continuava em deriva lenta positiva ao final de 20h, porém a taxa era decrescente (côncava para baixo), indicando convergência assintótica ainda em curso. O `deriv_norm` atingiu o mínimo histórico observado até o momento.

### Conclusão

A hipótese foi **parcialmente confirmada**: sem IDV(4), as CW temps voltaram ao nominal do FORTRAN — confirmando que o IDV(4) perturbava o equilíbrio térmico. Contudo, o ponto de operação macro (pressão, recycle flow, temperatura do reator) permaneceu o mesmo do Exp 2, demonstrando que **o attractor é determinado pelos setpoints dos 3 controladores proporcionais, não pelo distúrbio IDV(4)**.

A divergência em relação ao Mode 1 nominal do FORTRAN (2680 kPa vs 2705 kPa, recycle ~26 kscmh vs ~35 kscmh) é, portanto, estrutural: os controladores P atuam em setpoints fixos que não reproduzem exatamente o ponto de operação do FORTRAN. Isso não é um problema — é o attractor natural da nossa planta com a camada de controle atual.

O snapshot `cases/te_exp3_snapshot.toml` é a melhor condição inicial disponível: está muito mais próximo do SS do que o FORTRAN TEINIT, elimina o transiente de cold start e tem CW temps corretas. **Próximo passo natural: validar o snapshot como ponto de partida direto (ramp_duration=0, sem cold start), confirmando que a planta mantém operação estável sem o transiente de inicialização.**

---

## Experimento 2 — Redução do `ramp_duration` para 0.5 h

### Observação

Com `ramp_duration=2.0h`, a simulação disparou ISD por `Reactor Lv low (<10%)` em **t = 1.320 h** (t_operational = 1 186 h). O reator drenava de ~77% para 4.5% enquanto o feed estava em apenas ~13% do nominal no momento do shutdown. O purge valve (XMV(6) = 69.36%) e o purge flow (XMEAS(10) ≈ 3000 kscmh) estavam amplamente abertos no instante final — confirmando que a drenagem não foi causada pelo fechamento da purge, mas pela insuficiência de feed durante a rampa longa.

### Hipótese

Com `ramp_duration=2.0h`, o feed nominal demora 2 horas para chegar ao reator. O inventário inicial (~77% de nível) não sustenta essa espera: a análise indica taxa de drenagem de ~55 %/h, ou seja, em t≈1.25h o nível atinge o limite ISD de 10 %.

Reduzindo para `ramp_duration=0.5h`, o feed nominal chega em 30 minutos. A estimativa conservadora é que o reator estará em ~50 % de nível quando o feed pleno entrar, com margem suficiente para recuperar antes de atingir o limite inferior.

### Intervenção

Arquivo modificado: `tennessee-eastman-service/service/src/main.rs`

```rust
ramp_duration: 0.5,   // reduzido de 2.0 → 0.5 h
```

### Resultado

Com `ramp_duration=0.5h`, o reator atingiu nível mínimo de **~59%** durante o cold start (margem ampla acima do limite ISD de 10%), e a simulação rodou por **13+ horas** sem disparar ISD. Após t≈3h, todos os principais estados convergiram para valores estáveis: pressão ~2680 kPa, temperatura ~120°C, sep/stripper levels ~50%, deriv_norm ~200–300 unidades/h. Observou-se uma deriva lenta no nível do reator (~0.6 %/h, de ~59% → ~69% ao longo de 13h) com taxa decrescente (côncava para baixo), sugerindo convergência assintótica.

O operating point encontrado difere do Mode 1 nominal: recycle flow ~26 kscmh (vs ~35 nominal), A Feed ~22% (vs ~63% nominal), pressão ~2680 kPa (vs 2705 kPa nominal).

### Conclusão

Hipótese confirmada: `ramp_duration=0.5h` é suficiente para evitar a drenagem crítica do reator durante o cold start. A planta atingiu um regime operacional estável e sustentável dentro dos limites ISD.

O **attractor encontrado não é o Mode 1 SS** pelos seguintes motivos: (a) IDV(4) está ativo (+5°C no CW do reator), o que desloca o ponto de equilíbrio; (b) nossos 3 controladores proporcionais não fixam completamente o operating point — o nível do reator não tem malha fechada. A deriva lenta residual (~0.6 %/h) indica que o sistema ainda não convergiu completamente; provavelmente precisaria de ~20h adicionais para estabilizar totalmente.

**Próximo passo natural:** Remover IDV(4) para isolar o comportamento sem distúrbio, rodar por tempo determinado (20h) e capturar o estado final como novo `initial_state.toml` — base para experimentos de controle futuros.

## Experimento 1 — Instrumentação dos gráficos de startup

### Observação

Com `ramp_duration=2.0h` e `real_time=false`, a simulação avançou até t≈1.32h antes de
disparar ISD por `Reactor Lv low (<10%)`. O reator drenava continuamente de ~77% para 4.5%
enquanto o feed era rampado de 0% → nominal ao longo de 2 horas.

Os gráficos disponíveis não mostravam:
- A abertura das válvulas de feed (XMV(1–4)) ao longo do tempo — era impossível ver a
  progressão do ramp visualmente
- O acoplamento entre pressão do reator, fluxo de purge e abertura da válvula de purge
  (três variáveis distribuídas em painéis separados e não relacionados)
- Marcos temporais de fase do startup (25 / 50 / 75 / 100 % do `ramp_duration`)

### Hipótese

Adicionando um painel de **Feed Valve Ramp** (XMV(1–4) em %) e combinando
**Purge Flow + Purge Valve** em um único painel diagnóstico, além de marcadores verticais
de fase, será possível:
- Identificar em que fração do ramp o reator perde inventário crítico
- Observar se o purge controller contribui para a drenagem ao fechar prematuramente a
  válvula em resposta à queda de pressão (resultado esperado: sim, pela fórmula
  `mv[5] = 40.06 + 0.10*(P − 2705)` que fecha a válvula quando P < 2705 kPa)

### Intervenção

Arquivo modificado: `analysis/tep_analysis/plot.py`

- Substituídos os painéis "Recycle & Purge Flow" e "Purge Valve (MV)" por três novos painéis:
  - **Feed Valve Ramp** — XMV(1), XMV(2), XMV(3), XMV(4) em %, todos no mesmo eixo
  - **Recycle Flow** — XMEAS(5) isolado
  - **Purge: Flow & Valve** — XMEAS(10) [kscmh] + XMV(6) [%] sobrepostos (painel diagnóstico;
    unidades heterogêneas, mas tendências diretamente comparáveis)
- Adicionado argumento CLI `--ramp <horas>` que desenha linhas verticais em
  25 / 50 / 75 / 100 % do `ramp_duration` em todos os painéis

### Resultado

A hipótese foi parcialmente confirmada. Os novos painéis de fato tornaram o mecanismo do startup visível: o Feed Valve Ramp mostrou claramente que, com `ramp_duration=2.0h`, as alimentações ainda estavam longe do nominal quando o reator perdeu inventário crítico; e o painel conjunto de **Purge Flow + Purge Valve** mostrou de forma explícita o acoplamento causal entre queda de pressão e fechamento da purge. No instante do shutdown, a simulação parou em **t = 1.320 h**, com **Reactor Level = 4.5%**, **Reactor Pressure ≈ 2997.6 kPa**, **Purge Valve = 69.36%** e **Purge Flow ≈ 3000 kscmh**, o que indica que o evento terminal foi de fato low level do reator, não runaway térmico nem overpressure.

### Conclusão

A conclusão principal é: **o problema dominante deste experimento não foi mais a explosão inicial, e sim drenagem excessiva do reator durante uma rampa de feed longa demais**. A instrumentação nova validou isso. Ela também mostrou que a hipótese específica “o purge controller fecha prematuramente e contribui para a drenagem” não explica o shutdown final deste run como causa principal. O purge até fecha no começo quando a pressão cai, mas, no fim do experimento, ele está amplamente aberto e a planta ainda assim atinge low level. Portanto, a leitura mais forte agora é: **com `ramp_duration=2.0h`, a reposição de massa pelas alimentações é lenta demais para sustentar o inventário do reator ao longo do startup. Em termos de próximo experimento, a ação mais coerente é reduzir `ramp_duration` e repetir o teste mantendo a mesma instrumentação.**


