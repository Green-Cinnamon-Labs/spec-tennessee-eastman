# Experimento #82 — J sob distúrbio, observado pelo Kubernetes

**Issue:** https://github.com/Green-Cinnamon-Labs/spec-tennessee-eastman/issues/82
**Epic:** #77
**Data:** 2026-10-08 (rodado — Experimento 25 em `experimentos.md`)

---

A epic #77 montou a cadeia planta → historian → `plant-supervisor` → `Plant.status` e mostrou que ela funciona em operação nominal: J ≈ 166 $/h, `Compliant`. Também mostrou o veredito virando, mas só *mudando a regra* (baixando o `maxCost` para 150 com `kubectl patch`). O que ainda não foi mostrado é o caso que importa para a tese: a **própria planta** se degradando enquanto as regras ficam fixas, e o Kubernetes percebendo. O experimento #82 é esse teste — é a evidência de que a camada supervisória realmente observa o estado econômico da planta, e não apenas os números que alguém digitou numa política.

O procedimento é simples de enunciar. Com a planta rodando no caso base do Modo 1 e a política do Modo 1 ativa, primeiro registra-se um trecho de operação nominal (J, metas e limites todos ok). Depois liga-se um distúrbio do TEP escrevendo no seu node OPC-UA — por exemplo `disturbance.idv6 = 1`, perda da alimentação de A, o mesmo comando já testado em 2026-10-02 — sem mexer na política. A partir daí, acompanha-se o `Plant.status` ao longo do tempo: J deve se afastar do valor nominal, alguma meta ou limite deve eventualmente falhar e, depois de `persistenceEvaluations` (3) avaliações ruins seguidas, `PolicyCompliant` deve virar `False` e a fase, `NonCompliant`.

O que se mede é a *observação*, não o distúrbio em si (caracterizar cada IDV é a #47). As perguntas são: como J evolui depois do distúrbio e quais dos seus 12 termos se mexem; qual condição falha primeiro — custo (`CostWithinBudget`), produto (`TargetsMet`) ou envelope de operação (`ConstraintsSatisfied`); quanto tempo passa entre ligar o distúrbio e o veredito virar, separando o tempo de resposta da própria planta do atraso que o supervisor acrescenta (janela de média de 60 s, intervalo de avaliação de 30 s, persistência de 3); e se o veredito volta a `Compliant` quando o distúrbio é desligado. Um segundo distúrbio com assinatura diferente (por exemplo IDV1, um degrau na razão A/C da alimentação) mostraria se o veredito distingue um problema econômico de um problema de limite.

O principal obstáculo é o tempo. O IDV6 é um distúrbio lento e severo: no TEP original ele leva horas de tempo *simulado* para levar a planta aos seus limites, e a planta simulada roda hoje a cerca de 2× o tempo real, então uma rodada completa pode levar horas de relógio — e a janela de 60 s do supervisor também é em tempo de relógio, cobrindo só uns 2 minutos simulados. Antes de rodar, é preciso decidir alguns pontos, listados abaixo. O resultado deve entrar em `experimentos.md` como um novo experimento e na monografia como a principal evidência da camada supervisória.

## Resultado (2026-10-08) — Experimento 25

Rodada com IDV6, regras fixas (política calibrada), velocidade 5. Linha do tempo: `tep-lab/data/experiment_82/idv6_2026-10-08.png`; registro completo como **Experimento 25** em `experimentos.md`.

- **IDV6 ligado em `clock.t_h` 2.31, desligado em 3.84.**
- **Nível econômico:** `TargetsMet` caiu primeiro (3.29, vazão de produto 21.48 < 21.80), depois `CostWithinBudget` (3.46, J 171.6 > 170.6) e, na 3ª avaliação ruim seguida, **`NonCompliant` em 3.46** — 1.15 h de processo depois do distúrbio. O veredito ficou `NonCompliant` até o fim (J chegou a 218 $/h).
- **A planta não se recuperou** depois de desligar o IDV6: sem malha de nível do reator e com a pressão só proporcional, pressão e nível continuaram subindo.
- **Nível das malhas:** `ControlLoopsHealthy` ficou True o tempo todo. Sob o distúrbio o erro vira deriva lenta, previsível, e o PI sobe (pressão ≈ 1.0 com offset de −131 kPa). O índice de Bradu mede previsibilidade, não seguimento de setpoint — o segundo nível precisa de um critério de offset/saturação (#87).

## Decisões tomadas (2026-10-07)

O experimento vai mostrar **dois níveis de observação**: a função de custo J (#77) e a qualidade das malhas de controle (#85). Para isso:

- **Saúde das malhas é um veredito separado** — uma condition própria, `ControlLoopsHealthy`, que não entra no `PolicyCompliant`. Assim os dois níveis aparecem lado a lado.
- **Excitação da planta: só ruído nos sensores** (#66), com os desvios-padrão reais de `tep-plant/docs/06-ruidos.md`. Distúrbios aleatórios (IDV8–12) ficam fora deste experimento.
- **Índice: só o Predictability Index de Bradu**; o de Harris fica para depois.
- **Velocidade da simulação** não exige trabalho novo: a planta já aceita mudar a velocidade em tempo de execução (os botões 1×/10×/Max da IHM).

O trabalho é feito em blocos, um de cada vez, acompanhado na #85.

## Calibração (bloco 6, 2026-10-08)

Rodada de operação nominal, com ruído nos sensores e sem distúrbio, na velocidade 5 (≈ 10× o tempo real), gravada com `record_run.py`: `clock.t_h` de 1.75 a 5.06 h (~3.3 h de processo, 20 min de relógio), 41 avaliações do supervisor, todas `Compliant` e com as malhas saudáveis. Arquivo: `tep-lab/data/experiment_82/calibracao_2026-10-08.csv`.

| Grandeza | Resultado nominal |
|---|---|
| J | 166.83 ± 0.18 $/h (166.47 a 167.19) |
| PI — nível do separador | 0.15 a 0.40 (mediana 0.27); σ da válvula 0.29–0.34 % |
| PI — nível do stripper | 0.15 a 0.35 (mediana 0.25); σ da válvula 0.28–0.33 % |
| PI — pressão do reator | 0.17 a 0.38 (mediana 0.31); σ da válvula 0.012–0.015 %, offset 8.7 kPa — fica abaixo do portão, não é julgada |

Parâmetros escolhidos a partir disso e aplicados em `policy-mode1.yaml` (tep-lab#31):

- **`maxCost` 179 → 170.6 $/h** — o custo do caso base de Downs & Vogel; J precisa subir ~2.3 % acima do nominal para estourar.
- **`minPredictability` 0.1 → 0.12** — abaixo do menor PI nominal (0.147), com margem.
- **`minOutputStd` 0.05 %** (mantido) — níveis julgados, pressão não (#86).
- Velocidade 5 e janelas 60 / 300 / 30 s mantidas para o experimento.

O PI baixo dos níveis em operação nominal reflete o ruído do sensor dominando o erro (categoria "Noise" de Bradu), não sintonia ruim (#87). O experimento vai mostrar se, sob distúrbio, o PI sai dessa faixa.

## Decisões antes de rodar

- **Velocidade da simulação** — **resolvido:** velocidade 5 (≈ 10× o tempo real) pelo método OPC-UA `control.set_speed`; a base de tempo única em tempo simulado fica para a #88.
- **Janela e intervalo** — manter 60 s / 30 s, ou alongar a janela para que J seja julgada sobre um trecho relevante de tempo simulado (ou passar a janela para tempo simulado, usando o sinal `clock.t_h` da planta).
- **Orçamento** — ~~com `maxCost: 179` e J ≈ 166, J precisa subir cerca de 8 %~~ **resolvido na calibração:** `maxCost` 170.6 $/h, J precisa subir ~2.3 %.
- **Registro** — o `Plant.status` guarda só o veredito mais recente, então a rodada precisa de uma série temporal: um script consultando `kubectl get plant tep -o json` (junto com o `clock.t_h` da planta), o log do próprio supervisor (uma linha por avaliação), ou as sessões SQLite da IHM.
- **Quais distúrbios** — só o IDV6, ou o IDV6 mais um mais rápido (IDV1) para contraste; e se a planta deve chegar aos limites de shutdown (o shutdown da planta hoje é só diagnóstico, #70).

## Qualidade do controle — a segunda coisa que o experimento pode mostrar

Além da função de custo, o mesmo experimento pode mostrar a **qualidade das malhas de controle**, o outro tema do Cap 2 (Harris; Bradu et al.). A planta tem hoje três controladores proporcionais (P), os clássicos de Downs & Vogel, em `tep-plant/src/controllers/`: a **pressão do reator** é controlada pela válvula de purga ([reactor_pressure_control.rs](../../../tep-plant/src/controllers/reactor_pressure_control.rs), Kp = 0.1, setpoint 2705 kPa), o **nível do separador** pela válvula de underflow do separador ([separator_level_control.rs](../../../tep-plant/src/controllers/separator_level_control.rs), Kp = 1.0, setpoint 50 %) e o **nível do stripper** pela válvula de produto do stripper ([stripper_level_control.rs](../../../tep-plant/src/controllers/stripper_level_control.rs), Kp = 1.0, setpoint 50 %). Eles existem porque, sem eles, a pressão e os inventários de líquido derivam sem limite (Exp 8/9): a purga é a única saída de gás da planta, e os dois níveis acumulam líquido se ninguém tirar. A variável medida (PV) e a saída do controlador (OP, a posição da válvula) de cada malha já são publicadas via OPC-UA e chegam ao historian; o setpoint (SP) hoje é uma constante dentro do código Rust, então teria de ser declarado no manifesto.

Dos 20 distúrbios do TEP, cinco estão implementados hoje: IDV1, IDV2, IDV3, IDV6 e IDV7; os outros têm TODO (epic #71). O efeito esperado sobre as malhas — a confirmar no experimento, a caracterização completa é a #47 — é o seguinte. O **IDV1** (degrau na razão A/C da alimentação 4) aumenta a geração de gás no reator e carrega a malha de pressão (a purga precisa abrir mais; no Exp 11 levou a planta ao shutdown em ~2 h). O **IDV2** (degrau na composição de B na alimentação 4) traz mais inerte, que só sai pela purga, e também pesa sobre a malha de pressão. O **IDV6** (perda da alimentação de A) desequilibra o balanço de gás e a produção, afetando a malha de pressão e os dois níveis. O **IDV7** (perda de pressão no header de C, reduzindo a alimentação 4) tem efeito parecido, mais brando. O **IDV3** (degrau na temperatura da alimentação de D) deve ter pouco efeito sobre essas três malhas, porque nenhuma delas controla temperatura.

Para medir a qualidade de uma malha, **ruído e distúrbio aleatório são indispensáveis**. Os índices do Cap 2 são estatísticos: o de Harris compara a variância observada da variável controlada com a variância mínima alcançável, e o Predictability Index de Bradu (PI = σ²ᵣ / mse) ajusta um modelo autorregressivo ao erro `e = SP − PV` e mede quão previsível ele é. Hoje os sensores são ideais, sem ruído (`Ideal`, ver [sensors/mod.rs](../../../tep-plant/src/sensors/mod.rs)), e os cinco distúrbios implementados são todos degraus determinísticos. Depois que a planta se acomoda a um degrau, o erro fica praticamente constante (um controlador P sempre deixa um offset), a variância vai a quase zero, e os dois índices degeneram — divisões por números minúsculos, sem significado. Para os índices dizerem algo, a planta precisa de excitação estocástica: ruído nos sensores (#66, os desvios-padrão reais já estão documentados) ou os distúrbios aleatórios IDV8–IDV12, que ainda são TODO.

Quanto a **como o historian consulta a planta**: ele não espera ser chamado. Assim que sobe, o coletor abre uma conexão OPC-UA com a planta e faz *polling* contínuo — a cada 500 ms (`SAMPLE_INTERVAL_MS`) lê todos os sinais de uma vez ([collector.py:83](../../../tep-historian/src/tep_historian/collector.py#L83)) e guarda cada amostra num buffer em memória que mantém a última hora (`RETENTION_S` = 3600 s, [buffer.py](../../../tep-historian/src/tep_historian/buffer.py)). Quando o `plant-supervisor` chama `POST /aggregate`, o historian **não fala com a planta**: calcula média, desvio padrão, mín. e máx. a partir do que já está na memória e responde na hora. É exatamente por isso que o índice de Bradu (ou o de Harris) caberia no historian: ele precisa da série temporal completa do erro de cada malha, que só o historian tem. A ideia seria um novo endpoint, por exemplo `POST /loop-performance`, que recebe PV, SP, OP e os parâmetros do método (janela, horizonte de predição `b`, ordem `m = 2b`), calcula o erro, ajusta o modelo autorregressivo com numpy e devolve o índice e o σ da saída do controlador; o supervisor só compararia esse número com um limiar (`PI_L`), aplicaria a mesma regra de persistência e escreveria uma condition como `LoopsHealthy` no `Plant.status`. O cálculo pesado fica no historian, o julgamento no supervisor — a mesma divisão de papéis da função de custo.
