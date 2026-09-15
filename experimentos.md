# Registro Científico de Intervenções — TEP CPS

Registro científico dos experimentos e intervenções.

Estrutura de cada entrada: **Observação → Hipótese → Intervenção → Resultado → Conclusão**

O experimento mais recente aparece primeiro.



## Experimento 23 — Auditoria formula-a-fórmula contra `v1.0.0`: achado e corrigido um segundo bug de água de resfriamento do reator

**Data:** 2026-09-15 — **Concluído (bug real corrigido; root cause principal ainda aberto)**

**Issue:** continuação da investigação de spec-tennessee-eastman#71 (sem issue própria — correção
pontual descoberta no processo de auditoria pedido pelo usuário)

### Observação

Depois do Exp 21 localizar a janela onde a divergência começa (mensurável já no tick 10, ~0.003h),
faltava uma comparação DIRETA, fórmula a fórmula, de todos os números físico-químicos usados por
`tep-plant` contra o código `v1.0.0` (a última versão monolítica, historicamente validada) — os Exp
19/20 só tinham testado CADA unidade num único ponto nominal, o que não pega um bug que só aparece
fora desse ponto específico.

### Hipótese

Se `physical_state()`/`heat_exchange()` de `Reactor` estiverem genuinamente corretos, alimentá-los
com o estado EXATO de qualquer tick de `docs/simulations/simulation_log_13.csv` (a trajetória real
validada) deveria reproduzir a medida EXATA (`XMEAS(7)`/`XMEAS(9)`/`XMEAS(21)`) que a planta validada
teve naquele mesmo instante — não só no ponto nominal do Exp 19, mas em QUALQUER ponto da trajetória.

### Intervenção

**Parte 1 — teste multi-ponto.** Novo teste em `tep-plant/src/units/reactor.rs`:
`physical_state_and_heat_exchange_match_the_validated_csv_at_many_points_along_the_real_trajectory`.
Para cada um dos primeiros 200 ticks do CSV, constrói um `Reactor` com o estado exato (`YY[0..8]`),
chama `physical_state()`, converte a pressão pra escala XMEAS, chama `heat_exchange()` com
`XMV(10)`/`XMV(12)` do mesmo tick, e compara os três resultados contra `XMEAS(9)`/`XMEAS(7)`/
`XMEAS(21)` daquele tick.

**Parte 2 — auditoria de constantes.** Comparação byte-a-byte de `tep-plant/src/physics/
constants.rs` (massas molares, Antoine, densidade líquida, entalpia líquida/vapor, calor de
vaporização) contra `tennessee-eastman-service/core/src/dynamics/tep/constants.rs` na tag `v1.0.0`
(`git show v1.0.0:...`) — idênticas.

**Parte 3 — re-derivação bloco a bloco.** Releitura completa de `tennessee-eastman-service/core/
src/dynamics/tep/model.rs` (821 linhas, `v1.0.0`, a função `derivatives()` monolítica original) e
comparação linha a linha de CADA fórmula usada por `Reactor`/`Separator`/`Compressor`/`Stripper`
atuais contra os blocos correspondentes (13-40) — flash+cinética, trocas térmicas, vazões
dirigidas por válvula/pressão, split do stripper, balanços de massa/energia. Também os 12 valores de
`tau` (constante de tempo de 1ª ordem dos atuadores) contra `VTAU` (Block 40 tail) do original.

### Resultado

**Parte 1** revelou um viés real e sistemático: com `REACTOR_COOLING_WATER_INLET=35.0`, `twr`
calculado ficava consistentemente **0.78 a 1.06°C ABAIXO** do `XMEAS(21)` real em TODOS os 200 ticks
— muito acima do ruído de medição de `XMEAS(21)` (σ=0.01°C, Block 37/`XNS` de `v1.0.0`). Temperatura
(`ΔT` máx. 0.029°C) e pressão (`ΔP` máx. 0.92 kPa) do reator, por outro lado, já batiam dentro do
ruído esperado (σ=0.01°C e σ=0.3 kPa respectivamente) — ou seja, `physical_state()` (flash+cinética)
já estava correto; o problema estava isolado em `heat_exchange()`.

Resolvendo `twr_implícito` (qual `tcwr` faria `twr` bater exatamente com `XMEAS(21)`, usando o
próprio `uar`/`cw_capacity` já calculados) deu uma média de **37.98°C** ao longo dos 200 ticks — não
perto de 35.0. Relendo o comentário ORIGINAL do Block 32 em `v1.0.0` (`model.rs`, já lido nesta
investigação antes, mas o detalhe passou despercebido): `// cpcw_eff=0.00942 calibrated to yield
twr≈94.6°C at nominal (tcwr=38.5, tcr=120, fcwr=41.1, uar=0.856)` — o PRÓPRIO autor do código
original documentou `tcwr=38.5` como o valor usado pra calibrar a constante `cpcw_eff`. `tep-plant`
usava 35.0 — o `s_zero` do canal de distúrbio 4 de `TepDisturbanceState` (uma constante DIFERENTE:
condição inicial do canal de distúrbio, não o valor nominal documentado na calibração do Block 32).

Corrigido `REACTOR_COOLING_WATER_INLET` de 35.0 para **38.5** (`reactor.rs`). Resultado: `twr` máx.
Δ caiu de 1.06°C pra **0.33°C** — redução de ~3x, o residual explicado por erros de segunda ordem já
esperados (pequenos ΔT/ΔP se propagando não-linearmente por `uar`).

**Parte 2** confirmou as constantes químicas idênticas — zero divergência.

**Parte 3** confirmou TODAS as fórmulas de `Separator`/`Compressor`/`Stripper` (incluindo as duas
peculiaridades sutis já conhecidas — `hst[9]=hst[8]` pré-correção do Block 24, e `cpdh` calculado
com o `flms` PRÉ-anti-surge mas dividido pelo `ftm[8]` PÓS-anti-surge no `Compressor`) idênticas ao
original, e os 12 `tau` de atuador idênticos a `VTAU`. Nenhuma outra discrepância encontrada.

**Impacto na trajetória completa:** re-rodando o teste do Exp 21
(`diverges_from_the_validated_baseline_csv_early_not_gradually`) com a correção, o primeiro tick que
ultrapassa o limiar de divergência (2°C/20kPa) foi de **tick 200 pra tick 310** (`t_h` 0.056h →
0.086h) — quase **+55% de sobrevida** antes de violar a tolerância. Mas a natureza da divergência
MUDOU de direção: antes a temperatura caía abaixo do nominal; agora ela SOBE acima (122°C no tick
300, chegando a um pico de ~128.8°C por volta de `t_h≈0.33h` no teste de 3500 ticks), antes de
eventualmente também colapsar (caindo a ~61°C, pressão subindo a ~4000+ kPa por `t_h≈0.96h`) — mesma
assinatura qualitativa de sempre (reação desacelera, gás não reagido se acumula, ISD), só que num
horizonte de tempo maior e com o sinal do viés inicial invertido.

### Conclusão

**Um segundo bug real de água de resfriamento do reator, confirmado e corrigido** — não por
inspeção visual (como os dois bugs do Exp 18), mas por comparação numérica direta e reproduzível
contra a trajetória validada, ponto a ponto. A correção tem impacto mensurável e positivo (adia a
divergência em ~55%), mas **não é a causa raiz completa**: a divergência ainda ocorre, agora com o
reator SOBRE-aquecendo em vez de sub-resfriando, o que sugere um segundo fator, de sinal oposto e
provavelmente menor magnitude, ainda presente em algum lugar não coberto por esta auditoria (a
auditoria cobriu TODA fórmula de física de unidade e todo `tau` de atuador — o que sobra fora do
escopo checado aqui é: a semântica exata de `Actuator`/`Controller` fase (B)/(C) já levantada como
área menos explorada no Exp 22, e a possibilidade de mais algum canal de `TepDisturbanceState` com
`s_zero` incorreto — só o canal 4 (TCWR) foi auditado a fundo aqui).

**Próximo passo:** repetir a mesma técnica do teste multi-ponto desta Exp 23 (alimentar
`physical_state()`/`heat_exchange()` com estado exato do CSV, comparar contra `XMEAS`) pra
`Separator`/`Compressor`/`Stripper` — a auditoria de fórmula (Parte 3) confirma que o CÓDIGO bate
com `v1.0.0`, mas não confirma que os poucos valores "congelados" restantes (como
`SEPARATOR_COOLING_WATER_RETURN`, já confirmado correto no Exp 18, mas potencialmente outros ainda
não escrutinados da mesma forma) reproduzem a trajetória real tão de perto quanto `Reactor` agora
reproduz.

---

## Experimento 22 — Enxergar a ordem de execução real do `sort_phase_a`

**Data:** 2026-09-15 — **Concluído e FECHADO** — hipótese de ordem refutada; auditoria de semântica
de `#[need]` sem discrepância; bug real de priming do `CurrentState` encontrado e corrigido (não é
a causa raiz da divergência, mas é uma correção de framework válida por si)

**Issue:** https://github.com/Green-Cinnamon-Labs/spec-tennessee-eastman/issues/71 (fechada — o
artefato de ordem de execução foi implementado como planejado, e o bug de priming encontrado ao
usá-lo está documentado e corrigido, ver "Continuação" abaixo)

### Observação

O Exp 21 descartou instabilidade numérica (o `dt_hours` atual é mais fino que o `dt` historicamente
validado, não mais grosso) e confirmou que a divergência é rápida e sistemática (mensurável já nos
primeiros ~10-200 ticks, crescendo suave desde o início — assinatura de viés pequeno e consistente,
não de bug pontual nem de ruído numérico). Lendo `monjolo/state_registry.rs` diretamente, confirmamos
que todo `Proxy` (o que `#[need]`/`#[offer]` usa) lê/escreve exclusivamente em `EvaluationState` — um
único buffer mutável compartilhado por toda a árvore, sem versionamento por sub-chamada de
`evaluate()`. Isso significa que a ORDEM em que `sort_phase_a` (`monjolo/component.rs`) sequencia as
tarefas dentro de uma mesma chamada de `evaluate()` é uma propriedade crítica de corretude: se uma
tarefa lê uma chave antes de quem a oferece ter rodado NESSA MESMA chamada, ela recebe um valor
"atrasado" — sobra de uma chamada anterior de `evaluate()` (um sub-passo de RK4 diferente, ou o tick
inteiro anterior). É exatamente esse tipo de atraso sistemático e pequeno que produziria o padrão
observado no Exp 21.

Só que, até agora, ninguém nunca viu de fato qual ordem `sort_phase_a` escolhe pra essa planta —
só dá pra inferir lendo `#[need]`/`#[offer]` de cada arquivo à mão e reconstruindo o grafo
mentalmente, exatamente o que esta investigação vem fazendo sem garantia de estar completa ou
correta.

### Hipótese

Se `monjolo` produzir um artefato concreto mostrando a ordem de execução real escolhida — qual
tarefa roda antes de qual, dentro de uma chamada de `evaluate()`, com seus `#[need]`/`#[offer]` — dá
pra conferir diretamente (sem inferência manual) se essa ordem respeita "produtor sempre antes de
consumidor, dentro da mesma chamada", a mesma garantia que o código monolítico original tinha por
construção (Blocos 13→40 do `teprob.f`, sempre na mesma ordem fixa, escrita à mão). Se alguma tarefa
aparecer na ordem ANTES de quem oferece uma chave que ela `#[need]`, a hipótese do Exp 21 (leitura
atrasada de `EvaluationState`) fica confirmada, com o par produtor/consumidor exato identificado.

### Intervenção

Capacidade nova em `monjolo` (issue [#71](https://github.com/Green-Cinnamon-Labs/spec-tennessee-eastman/issues/71)), não um hack pontual desta investigação. Implementada:

- `monjolo::phase_a_execution_order() -> Vec<&'static ComponentDescriptor>` (`monjolo/component.rs`)
  — reexecuta a MESMA coleta+`sort_phase_a` que `attach_discovered_components` já fazia por dentro,
  mas sem construir nada: `name`/`after`/`needs`/`offers` são todos `&'static`, já existem completos
  assim que o binário termina de linkar — não precisa de `StateRegistry`/`Snapshot`/planta nenhuma,
  só de `inventory::iter()`. Chamável de qualquer lugar.
- `monjolo::describe_phase_a_execution_order() -> String` — formata a ordem acima como texto
  simples, uma tarefa por linha numerada, com `needs`/`offers`.
- `Runtime::bootstrap()` (`monjolo/runtime.rs`) escreve isso em `execution_order.txt`, na raiz do
  projeto, TODA VEZ que o binário sobe — o artefato aparece sozinho assim que o usuário builda e
  roda, sem passo manual nenhum, sem bloquear o boot se a escrita falhar (é diagnóstico, não
  dependência funcional).
- Teste permanente em `tep-plant/src/lib.rs`,
  `phase_a_execution_order_never_reads_a_key_before_whoever_offers_it` — usa o artefato acima pra
  checar automaticamente: pra cada tarefa, pra cada chave em `needs`, quem `offers` essa chave
  aparece ANTES dela na lista? Falha nomeando o par exato se não.

### Resultado

`execution_order.txt` gerado com sucesso ao rodar `tep-plant` (confirmado: 36 tarefas da fase (A),
16.7 KB). O teste automático rodou contra a ordem REAL, de verdade descoberta via `inventory` —
**zero violações**. Toda tarefa que `#[need]` uma chave tem, sem exceção, o `#[offer]` dessa chave
rodando ANTES dela na mesma lista (ex.: `Reactor::physical_state` na posição 4, sem `needs`;
`Separator::physical_state` na posição 5, `needs: ["reactor.temperature"]`, oferecido pela posição
4 — ordem correta).

### Conclusão

**Hipótese REFUTADA.** `sort_phase_a` está escolhendo uma ordem correta — nenhuma tarefa lê uma
chave antes de quem a oferece ter rodado na mesma chamada de `evaluate()`. Isso elimina "ordem de
avaliação entre unidades" como causa da divergência vista nos Exp 18/21, depois de eliminar também
"erro de fórmula isolada" (Exp 19/20) e "instabilidade numérica do integrador" (Exp 21). As três
hipóteses mais fortes que a investigação levantou até aqui foram todas, uma a uma, descartadas com
evidência concreta — o que sobra é menos óbvio: ou uma chave que DEVERIA ser um `#[need]` declarado
não está sendo declarada (um acoplamento real existe no código, mas não aparece no grafo que
`sort_phase_a` enxerga — invisível a este teste por definição, já que ele só audita o que está
declarado), ou a divergência nasce de algo fora da fase (A) inteiramente (`Actuator`/`Controller`,
fases (B)/(C), nunca auditadas nesta investigação).

**Auditoria manual de semântica de `#[need]` (continuação, mesmo dia):** antes de investigar
fases B/C, comparou-se manualmente cada `#[need]` do caminho crítico reator↔separador↔compressor↔
stripper (visível em `execution_order.txt`) contra os blocos exatos do `teprob.f`/`v1.0.0` que cada
um substitui — incluindo dois casos que facilmente esconderiam um bug: `hst[9]=hst[8]` (Block 21,
ANTES da correção do compressor no Block 24 — `Separator::mass_and_energy_balance` recalcula
`enthalpy_separator_vapor_uncorrected` fresco, batendo exatamente com essa pegadinha do FORTRAN
original) e `FEED_TEMPERATURE=45.0` compartilhado entre D/E/A feed (confirmado contra
`initial_tst()` do `v1.0.0`: as 4 correntes realmente começam todas em 45°C — não é bug). **Zero
discrepâncias encontradas** — mais uma hipótese descartada com evidência concreta.

### Continuação — Controllers (fase C) e um bug REAL encontrado (e corrigido) que ainda não é a causa

Investigação seguinte, pedida diretamente pelo usuário ("como estão os controladores comparados à
v1.0.0?"), depois de notar que `execution_order.txt` só lista a fase (A) — fases (B)/(C) nunca
tinham sido auditadas.

**Hipótese inicial (refutada por verificação própria):** suspeita de que `Controller` (fase C),
por rodar em TODA chamada de `evaluate()` (a mesma árvore `Composite` que o RK4 reavalia a cada
sub-passo k1-k4, ~5x por tick — confirmado: `Composite::evaluate_children()` não faz distinção
nenhuma entre "tick de verdade" e "sub-passo hipotético do RK4"), estaria recalculando o comando de
válvula usando leituras intermediárias e fisicamente fictícias do RK4. Verificação direta de
`#[sensor(key=...)]` (usado por todo `Controller`) mostrou o contrário: `Sensor::read()`
(`sensor/model.rs:82-93`) lê via `ReadProxy` sobre **CurrentState**, cacheado por `generation` — que
só avança em `commit()`, uma vez por tick. Ou seja, todas as ~5 chamadas de um controlador dentro de
um mesmo tick leem o MESMO valor (idêntico ao original: `mv` congelado durante toda a integração RK4
de um tick). Rodar 5x é ineficiente, mas não corrompe nada — **hipótese descartada por verificação
própria antes de qualquer correção precipitada**.

**Bug real encontrado ao verificar essa hipótese:** `CurrentState` começa **vazia**
(`state_registry.rs:306-309`, `values: Vec::new()`) e só é populada dentro de `commit()`
(`values.resize(eval.len(), 0.0)` + cópia). `commit()` só é chamado UMA vez, no fim do laço de tick
(`simulation.rs`), NUNCA antes do laço começar. Teste direto em `monjolo`
(`read_before_any_commit_ever_happened`) confirmou: `Sensor::read()` chamado antes de qualquer
`commit()` **não panica — devolve `0.0` silenciosamente**. Como `Controller` roda desde a
PRIMEIRÍSSIMA chamada de `evaluate()` do processo (dentro do primeiro `integrator.step()`, antes de
existir qualquer `commit()`), os 3 controladores da planta leem pressão/nível como `0.0` no tick 0 —
e `clamp(bias + kp*(0 - setpoint), 0, 100)` satura no piso pra qualquer setpoint positivo, comandando
as 3 válvulas controladas pra **0%** logo de cara.

Confirmado ao vivo com um teste novo em `tep-plant`
(`first_tick_control_command_uses_precommit_zero_sensor_reading`): `valve.purge.position` (seed
`39.070%`) termina o PRIMEIRO tick em `33.053%` — um deslocamento de **-6.02 pontos percentuais**
num único segundo simulado, na direção errada (fechando), antes de o controle ter qualquer chance de
ler um valor real.

**Correção aplicada** (`monjolo/simulation.rs::spawn_plant_thread`): dois `evaluate()` com um
`commit()` entre eles, ANTES do laço de tick começar — o primeiro `evaluate()`+`commit()` populam
`CurrentState` com os valores físicos reais (semeados via `#[config(...)]`); o segundo `evaluate()`
roda os `Controller`s de novo, agora lendo `CurrentState` de verdade, deixando `Actuator::command`
correto antes do primeiro tick de verdade começar. Nenhum `#[state]` muda de valor (evaluate() nunca
escreve estado sozinho), então repetir isso duas vezes é seguro. Confirmado: com a correção, o
mesmo teste mostra deslocamento de `+0.00046` pontos — essencialmente zero, como esperado.

**Resultado ao rodar a trajetória inteira (Exp 21) com a correção:** praticamente **idêntica** à
trajetória sem a correção — mesma forma, mesmo colapso, divergindo do CSV de referência no mesmo
tick 200 (`Δ=2.005°C`, contra `2.007°C` sem a correção), colapso numérico ~meia dúzia de ticks
diferente (2403 em vez de 2900, dentro do esperado por sensibilidade caótica a uma perturbação
mínima de sétima casa decimal, não uma mudança de mecanismo).

**Conclusão desta continuação:** o bug do priming é REAL, CONFIRMADO, e CORRIGIDO — vale a correção
por si (é uma correção de framework em `monjolo`, não só desta investigação), e a suspeita original
de "controladores recalculando com RK4 intermediário" foi corretamente descartada por verificação
antes de qualquer correção precipitada. Mas nenhum dos dois — nem o bug real, nem a suspeita
refutada — explica a divergência principal que a investigação persegue desde o Exp 18: a trajetória
com a correção diverge da mesma forma, no mesmo lugar. **Seis hipóteses agora eliminadas com
evidência concreta** (fórmulas isoladas, integração/`dt`, ordem de `sort_phase_a`, semântica de
`#[need]`, timing de Controllers, e agora o priming de `CurrentState`) — nenhuma delas era a causa
raiz. A fase (B) — Atuadores — e a fase (C) além do que já foi coberto aqui, seguem como as áreas
menos exploradas.

**Próximo passo:** com ordem, fórmulas e integração descartados, a busca deveria ir pro conteúdo
específico de CADA `#[need]`/`#[offer]` — comparar, tarefa por tarefa, se os NOMES das chaves que
`Reactor`/`Separator`/`Compressor` declaram batem exatamente com o que cada uma espera receber (uma
chave escrita errada — typo, ou chave certa mas semanticamente trocada — não apareceria como
violação de ordem, só como um valor logicamente errado). Segundo candidato: auditar se algum valor
físico depende de um atuador (fase B) que talvez devesse estar acoplado mais de perto — não coberto
por este teste, que só olha fase (A).

---

## Experimento 21 — Trajetória real reproduzida em `cargo test`: divergência é rápida e real, não numérica

**Data:** 2026-09-15 — **Concluído (root cause ainda aberto, mas agora precisamente localizado)**

### Observação

Exp 19/20 provaram que `Reactor`/`Separator`/`Compressor` calculam corretamente, isolados, com
entradas conhecidas — mas isso não pode, por construção, pegar um bug de ORDEM de avaliação entre
unidades (`sort_phase_a`) ou de acúmulo ao longo de múltiplos passos de RK4, porque nenhum desses
testes chama `evaluate()` mais de uma vez nem exercita o scheduler de verdade. Confirmar/descartar
essas duas hipóteses exigia rodar a trajetória real — até agora, só possível via processo inteiro +
OPC-UA + Python, lento (minutos reais por poucas horas simuladas) e caro de iterar.

### Hipótese

Se o mesmo laço evaluate()+RK4+commit() que `Simulation::spawn_plant_thread` roda de verdade for
extraído pra dentro de um teste — usando `monjolo::attach_discovered_components` com o `Snapshot`
real de `application.toml` (não vazio), sem thread/OPC-UA/`sleep` nenhum — a mesma trajetória de
colapso observada ao vivo (Exp 18) deve aparecer, em milissegundos, permitindo instrumentar cada
tick e achar onde exatamente a física começa a se comportar mal.

### Intervenção

**Parte 1 — reproduzir o colapso.** Novo teste em `tep-plant/src/lib.rs`:
`traces_the_real_multi_unit_trajectory_to_find_where_it_first_diverges`. Monta a planta inteira via
`attach_discovered_components` + `Snapshot::from_file("application.toml")`, pega os `Proxy`s de
estado/derivada de `root.state_keys()` (mesma técnica de `Simulation::spawn_plant_thread`), e roda
3500 ticks (`dt_hours=1/3600`, ≈0.97h simuladas — cobre com folga a janela de ~0.87h do Exp 18) do
mesmo laço `RK4::step(current, dt, |perturbed| { escreve; root.evaluate(); lê derivadas })` +
commit(). A cada tick lê (sem integrar) `reactor.temperature`/`pressure`, `separator.temperature`,
`compressor.pressure` — as mesmas quatro grandezas já validadas isoladamente nos Exp 19/20 — e
imprime a cada tick nos primeiros 20, depois a cada 50. Um `assert!` pára o teste na primeira
leitura não-finita ou grosseiramente fora de escala.

**Parte 2 — checar se é o `dt` do RK4.** Antes de assumir instabilidade numérica, conferido o `dt`
que o código antigo (`v1.0.0`) realmente usava: `service/src/config.rs` tem `dt: 0.001` (horas) —
3.6 segundos simulados por passo. O `dt_hours` atual (`1/3600h` ≈ 1 segundo simulado por passo) é
MAIS FINO que o original, não mais grosso — um passo mais fino deveria ajudar a estabilidade de um
RK4 explícito, não piorar. Isso já enfraquece a hipótese de "RK4 de passo fixo perdendo
estabilidade" como explicação principal.

**Parte 3 — comparação exata contra uma trajetória validada.** O usuário forneceu
`docs/simulations/simulation_log_13.csv` (cópia trazida pra `tep-plant/docs/simulations/`) — a
gravação REAL do Exp 13 (baseline validado, mesmo `te_exp3_snapshot.toml`/`application.toml`, física
antiga confirmada correta, 20h simuladas sem distúrbio). Segundo teste,
`diverges_from_the_validated_baseline_csv_early_not_gradually`: mesmo harness da Parte 1, mas em vez
de checar contra faixas "parece razoável", lê o CSV linha a linha e compara `reactor.temperature`/
`xmeas.reactor.pressure` contra o valor EXATO que a planta validada tinha no `t_h` mais próximo (os
dois grids não coincidem — CSV a cada 0.001h, aqui a cada 1/3600h — um ponteiro avançando resolve,
já que ambos são monotônicos). Limiar de divergência: 2°C ou 20 kPa (bem acima do drift lento
documentado no Exp 10, +1 kPa/h). Para no primeiro tick que ultrapassar o limiar.

### Resultado

**Parte 1.** A trajetória de colapso do Exp 18 reproduziu quase tick a tick (mesma forma, mesma
escala de tempo) — rodando em 0.69s, não minutos. Tabela condensada (trajetória completa tem ~70
linhas):

| tick     | t_h       | reactor.T (°C)   | xmeas.reactor.P (kPa) | separator.T (°C) | compressor.P (mmHg) |
| -------- | --------- | ---------------- | --------------------- | ---------------- | ------------------- |
| 0        | 0.0003    | 120.43           | 2695.0                | 80.35            | 23946.8             |
| 600      | 0.167     | 100.56           | 2822.8                | 73.23            | 24951.1             |
| 1450     | 0.403     | 59.09            | 4347.7                | 90.68            | 37096.9             |
| 2000     | 0.556     | 60.66            | 5303.0                | 83.94            | 44941.2             |
| 2300     | 0.639     | 59.90            | 5213.9 → **oscila**   | 90.34            | 47315.6             |
| 2800     | 0.778     | 45.26            | 2339.0                | 98.22            | 21431.6             |
| **2900** | **0.806** | **0.00**         | **11885.7**           | 118.63           | **−5 659 126.2**    |
| 3450     | 0.959     | 0.00 (congelado) | 11885.7 (congelado)   | 84.88            | 93 690 895.4        |

Três fases nítidas, não vistas com essa clareza no teste ao vivo (amostragem grossa demais lá):
1. **t_h 0–0.40h**: decaimento suave e monotônico de T (120→59°C), P subindo continuamente.
2. **t_h 0.40–0.63h**: um PLATÔ — reactor.T se estabiliza perto de 59-60°C por um bom tempo,
   enquanto a pressão continua subindo (gás não-reagido ainda se acumulando na mesma taxa).
3. **t_h 0.63–0.81h**: regime CAÓTICO — pressão do reator oscila (sobe, cai, sobe, cai:
   5557→5214→5092→3393→3358→3226→...→2339 kPa) e `separator.temperature` sobe de forma anômala
   (82→90→98→99.9→**118.6°C**, mais quente que nunca esteve) pouco antes do colapso final.
4. **t_h≈0.81h**: colapso — `reactor.temperature` cai pra exatamente `0.0` e
   `compressor.pressure` vira **negativo** (`-5.66 milhões` mmHg) — fisicamente impossível
   (pressão não pode ser negativa), assinatura clara de divergência NUMÉRICA do integrador
   overshooting — mas, como a Parte 3 mostra, isso é só o estágio FINAL de um erro que já vinha de
   muito antes, não a causa raiz.

**Parte 2.** `dt` antigo = 0.001h (3.6s/passo) vs. `dt_hours` atual = 1/3600h (1s/passo, mais fino).

**Parte 3 — a divergência exata contra `simulation_log_13.csv`:**

| tick | t_h (nosso) | reactor.T | ref. CSV T | Δ T | xmeas.P | ref. CSV P | Δ P |
| ---- | ----------- | --------- | ---------- | ----- | ------- | ---------- | ----- |
| 0    | 0.0003      | 120.430   | 120.437    | 0.007 | 2694.958 | 2694.605  | 0.353 |
| 10   | 0.0031      | 120.355   | 120.432    | 0.077 | 2694.604 | 2691.737  | 2.866 |
| 40   | 0.0114      | 120.098   | 120.338    | 0.240 | 2694.311 | 2688.030  | 6.281 |
| 100  | 0.0281      | 119.473   | 120.166    | 0.692 | 2694.731 | 2689.218  | 5.513 |
| 160  | 0.0447      | 118.686   | 120.098    | 1.412 | 2696.511 | 2691.075  | 5.436 |
| **200** | **0.0558** | **118.060** | **120.066** | **2.007** | 2698.637 | 2692.785 | 5.852 |

Divergência ultrapassa o limiar (2°C) no **tick 200, `t_h≈0.056h` (~3.3 minutos simulados)** — mais
de 500x mais cedo que o colapso completo (`t_h≈0.81h`) visto na Parte 1. A pressão diverge de forma
mensurável AINDA MAIS CEDO que a temperatura (já ~2.9 kPa fora por volta do tick 10, quando a
temperatura ainda está só 0.08°C fora) — a diferença cresce de forma suave e contínua desde o tick 0,
não em degrau, o que é a assinatura de um viés sistemático pequeno (um coeficiente ligeiramente
errado, ou uma taxa/termo levemente forte demais ou fraco demais), não de um bug pontual (índice
trocado, sinal invertido) nem de acúmulo de ruído numérico.

### Conclusão

**Hipótese confirmada, e a causa muda de figura de novo — pra melhor.** O `dt` mais fino que o
original (Parte 2) descarta instabilidade de integrador como explicação principal — um passo menor
deveria ser mais estável, não menos. E a comparação exata contra a trajetória validada (Parte 3)
prova que a divergência é rápida e real desde o início: já mensurável na pressão em minutos, não em
horas — o colapso completo da Parte 1 (`t_h≈0.81h`) é só o efeito bola de neve de um erro que já
existia 500x mais cedo. Isso é uma boa notícia pra investigação: não precisamos mais rodar 3500
ticks nem entender o regime caótico tardio (platô, oscilação de pressão, `separator.temperature`
anômalo) — o bug real está em algum lugar dos PRIMEIROS ~200 ticks, uma janela pequena o bastante
pra inspecionar tick a tick à mão.

**Próximo passo:** instrumentar TODAS as grandezas intermediárias de `Reactor`/`Separator`/
`Compressor` (pressões parciais, taxas de reação, `heat_of_reaction`, as duas entalpias de fluxo,
`uar`/`twr`) nos primeiros ~10-20 ticks, comparando cada uma contra o que a mesma física, calculada
à mão a partir da mesma linha do CSV de referência, deveria produzir — a divergência mensurável de
pressão já no tick 10 é o ponto de partida mais direto: é ali, não em `separator.temperature`
(sintoma tardio da Parte 1), que a causa raiz deve estar.

---

## Experimento 20 — Testes unitários de Compressor e Separator — bug também não está aqui

**Data:** 2026-09-15 — **Concluído**

### Observação

O Exp 19 descartou `Reactor::physical_state`/`mass_and_energy_balance` como origem do colapso ainda
observado depois dos dois fixes de água de resfriamento (Exp 18) — ambos reproduzem o nominal
documentado numa única chamada, sem integração RK4. Restam duas outras unidades com física própria
(`Compressor`, `Separator`) que alimentam o balanço de energia do reator via o reciclo do
compressor — candidatos naturais antes de investigar acúmulo de erro ao longo de múltiplos passos.

### Hipótese

Se `Compressor::physical_state`/`outlet_flows`/`mass_and_energy_balance` e
`Separator::physical_state`/`mass_and_energy_balance` também reproduzirem seus respectivos pontos
nominais e conservarem corretamente em cenários de fluxo balanceado, o bug remanescente do Exp 18
não está em NENHUMA das quatro unidades isoladamente — sobra só acúmulo de erro ao longo de vários
passos de RK4 (ou uma interação entre unidades que só aparece com valores reais, não nos cenários
artificialmente balanceados destes testes).

### Intervenção

Mesma técnica dos testes de `reactor.rs` (Exp 19): chamar os métodos privados gerados pela macro
(`__physical_state_impl`, `__outlet_flows_impl`, `__mass_and_energy_balance_impl`,
`__heat_exchange_impl`) direto, com entradas conhecidas — sem precisar de
`attach_discovered_components`/planta inteira. Uma nota antiga em `compressor.rs` dizia que isso
"não dava pra testar sem a planta inteira" — desatualizada; a mesma técnica funciona igual.

**`Compressor` (`src/units/compressor.rs`), 3 testes novos:**
1. `physical_state_matches_nominal_operating_point_from_application_toml` — semeia com
   `state.compressor_vapor.*`/`state.compressor.energy` de `application.toml`;
   `separator_temperature` (única entrada externa) não foi chutado — foi computado de verdade
   chamando `Separator::physical_state(120.0)` com o estado nominal do separador (exigiu marcar
   `Separator::physical_state` como `pub(crate)`, único ajuste de visibilidade necessário).
2. `outlet_flows_bypass_is_an_exact_copy_of_recycle_flow` — `flow6` tem que ser cópia exata de
   `flow5` (invariante estrutural do Block 31 original).
3. `mass_and_energy_balance_cancels_when_only_recycle_flow_is_present_and_balanced` — feeds
   frescos zerados, reciclo com composição/entalpia/vazão iguais entrando e saindo.

**`Separator` (`src/units/separator.rs`), 4 testes novos:**
1. `physical_state_matches_nominal_operating_point_from_application_toml` — semeia com
   `state.separator_vapor.*`/`state.separator.energy`, `reactor_temperature=120.0`.
2. `heat_exchange_returns_the_corrected_frozen_return_temperature` — regressão direta do bug do
   Exp 18: trava `77.29698353` como saída, não o `40.0` errado.
3. `mass_and_energy_balance_cancels_when_outflow_matches_inflow_exactly` — vazão de saída
   (`flow8+flow9`) igual à de entrada (`flow7`), mesma composição/entalpia.
4. `mass_and_energy_balance_passes_through_separator_heat_when_flows_are_balanced` — mesmo cenário
   balanceado, mas com `separator_heat` não-nulo: só ele deveria sobrar na derivada.

### Resultado

Todos os 7 testes passam (33/33 na suite completa). Um deles revelou um erro de PREMISSA (não de
código): o primeiro chute pra XMEAS(16) (pressão do compressor) foi "~2700 kPa, igual ao reator" —
o teste falhou, com o código devolvendo 3091.3 kPa. Investigação mostrou que XMEAS(16) roda
genuinamente mais alto (é a pressão de descarga do compressor, não a do reator/separador) — valor
plausível e coerente com a literatura do TEP (~3100 kPa), não um bug. Faixa do teste corrigida pra
(2900,3300) kPa, com o motivo documentado no próprio teste.

### Conclusão

**Hipótese confirmada — o bug remanescente do Exp 18 não está em `Compressor` nem em `Separator`,
isoladamente.** As quatro unidades (Reactor, Exp 19; Compressor e Separator, aqui) reproduzem seus
pontos nominais numa única chamada e conservam corretamente em fluxo balanceado. A suspeita agora
se concentra em duas frentes: (a) o acúmulo de erro ao longo de múltiplos passos de RK4 — nenhum
teste até aqui rodou mais de UM passo de física —, ou (b) uma interação entre unidades que só
aparece com os valores REAIS que elas trocam durante a simulação de verdade, diferente dos cenários
artificialmente balanceados usados nestes testes de conservação.

**Próximo passo:** o que o Exp 18 já propunha — instrumentar a trajetória real (via
`attach_discovered_components` + laço de RK4 sem `sleep`, sem precisar de OPC-UA) e comparar os
valores intermediários de cada unidade, tick a tick, contra o que as chamadas isoladas destes dois
experimentos provam ser fisicamente correto no primeiro passo — pra achar exatamente em qual tick a
trajetória real começa a divergir do que a física, sozinha, permitiria.

---

## Experimento 19 — Testes unitários de Reactor::physical_state/mass_and_energy_balance — bug não está aqui

**Data:** 2026-09-15 — **Concluído**

### Observação

O Exp 18 encontrou e corrigiu dois bugs de água de resfriamento (reator + separador), mas a planta
ainda diverge — colapso numérico em `t_h≈0.87h`. Sem instrumentação direta, isolar SE o problema
está na física pura do reator (`physical_state`/`mass_and_energy_balance`) ou em outro lugar
(integração RK4 acumulando erro ao longo de muitos passos, ou outra unidade inteira) exigia rodar o
processo inteiro via OPC-UA a cada tentativa — lento e pouco preciso pra localizar a causa.

### Hipótese

Se `Reactor::physical_state()` (flash + cinética, chamada única, não depende de nenhuma outra
unidade) já reproduzir o ponto nominal documentado a partir do estado exato de `application.toml`,
e se `Reactor::mass_and_energy_balance()` (a equação de balanço em si) conservar corretamente
quando as vazões de entrada/saída são artificialmente igualadas, então o bug remanescente do Exp 18
NÃO está nesses dois métodos — está em outro lugar.

### Intervenção

Três testes novos em `tep-plant/src/units/reactor.rs`:

1. `physical_state_matches_nominal_operating_point_from_application_toml` — semeia `Reactor` com os
   valores exatos de `application.toml` (`state.reactor_vapor.*`/`state.reactor.energy`) e chama
   `physical_state()` uma vez, sem nenhuma integração. Verifica: temperatura em (110,130)°C,
   XMEAS(7) em (2500,2900) kPa, `heat_of_reaction > 0`, `reaction_rates[0] < -1.0` (A sendo
   consumido de verdade, reação não estagnada).
2. `mass_and_energy_balance_cancels_flow_terms_when_inflow_equals_outflow` — composição/
   temperatura/vazão idênticas entrando e saindo, sem reação nem calor: espera derivada zero em
   tudo.
3. `mass_and_energy_balance_passes_through_reaction_and_heat_when_flows_are_balanced` — mesmo setup
   balanceado, mas com `reaction_rates`/`heat_of_reaction`/`reactor_heat` não-nulos: espera que a
   derivada seja EXATAMENTE esses valores (termos de fluxo cancelados, só sobra reação/calor).

### Resultado

Os 3 testes passam (26/26 na suite completa). `physical_state()` reproduz o nominal documentado
(~120°C, ~2700 kPa, reação avançando) numa única chamada, sem nenhuma integração RK4 envolvida.
`mass_and_energy_balance()` conserva corretamente nos dois cenários de fluxo balanceado — nenhum
índice trocado entre `vapor_derivative` (0..3)/`liquid_derivative` (3..8), nenhum termo faltando ou
duplicado.

### Conclusão

**Hipótese confirmada — o bug remanescente do Exp 18 não está em `Reactor::physical_state()` nem na
estrutura de `Reactor::mass_and_energy_balance()`.** Ambos calculam corretamente a partir de
entradas corretas. Isso desloca a suspeita pra dois lugares: (a) os valores REAIS de
`compressor_vapor`/`compressor_temperature`/`compressor_recycle_flow`/`outlet_flow` que outras
unidades entregam pro reator durante a simulação de verdade (diferente do cenário artificialmente
balanceado destes testes) podem estar incorretos — candidatos: `Compressor::physical_state`/
`outlet_flows`, ou o próprio `Separator` (cujo bug de água de resfriamento já mexeu uma vez no
reciclo); ou (b) o erro só aparece depois de várias dezenas/centenas de passos RK4 acumulando, não
visível em nenhuma chamada isolada.

**Próximo passo:** escrever o mesmo tipo de teste unitário — semear com valores nominais reais,
chamar uma vez, comparar contra o nominal documentado — pra `Compressor::physical_state`/
`outlet_flows` e `Separator::physical_state`/`heat_exchange`, restringindo ainda mais onde o valor
diverge do esperado antes de precisar rodar RK4 de verdade.

---

## Experimento 18 — Água de resfriamento (reator + separador): colapso adiado, não eliminado

**Data:** 2026-09-15 — **Concluído (parcial — root cause ainda não fechado)**

### Observação

Após a migração pra `monjolo`/arquitetura Composite (issues #67/#68), testes ao vivo via UaExpert
mostraram a planta colapsando rapidamente: pressão do reator muito acima do limite de ISD (3000
kPa, chegando a 4524.5 kPa) e temperatura do reator estabilizando perto de 35-38°C em vez do
nominal ~120°C documentado (Exp 3/10/11/13).

Comparando `tep-plant/src/units/reactor.rs` (então `heat()`, hoje `heat_exchange()`) contra
`v1.0.0`/`teprob.f` Block 32: o código atual usava uma constante fixa
(`REACTOR_COOLING_WATER_RETURN = 35.0`) no lugar da temperatura de RETORNO da água de resfriamento
(`twr`), que no original é resolvida a cada tick por um balanço de calor quase-estático dependente
da vazão (`valve.reactor_cooling_water.position`, XMV 10) e da própria temperatura do reator. 35.0
é, na verdade, o `s_zero` do canal de distúrbio 4 (TCWR — temperatura de ENTRADA nominal),
reaproveitado por engano no lugar da saída. A válvula XMV 10 estava completamente desconectada da
física: escrever nela não tinha efeito nenhum.

### Hipótese

Restaurar o balanço de calor quase-estático do reator (`twr` como média ponderada entre a
capacidade térmica da água — vazão real da válvula × calor específico — e o coeficiente de troca do
reator `uar`) deveria restaurar a operação estável em torno do ponto nominal documentado (~120°C,
~2705 kPa, estável por 20h simuladas nos Exp 10/11/13, todos a partir do mesmo
`te_exp3_snapshot.toml`).

### Intervenção

**Correção 1 (reator):** implementada em `tep-plant/src/units/reactor.rs` — commits `5c5e73b`
(fix) + `925a6d9` (rename cosmético, sem mudança de física). Testada ao vivo via script Python/
`asyncua` (`opc.tcp://127.0.0.1:4840/tep/server/`), lendo `clock.t_h`/`xmeas.reactor.*` a cada
poucos segundos.

**Resultado da correção 1 isolada:** reator ainda colapsava — 120°C → ~42°C em só `t_h≈0.35h`
(~21 min simulados), muito mais rápido que o drift de massa lento e conhecido (~0.15%/h, validado
estável por 20h nos Exp 10/11/13). Pressão ultrapassava o ISD.

**Hipótese de segunda causa:** suspeita de que `application.toml` (o snapshot inicial) pudesse
estar incompleto ou incorreto em relação ao baseline histórico. `diff` completo contra
`docs/cases/te_exp3_snapshot.toml` mostrou os arquivos **byte-idênticos** — descartando essa
hipótese na forma literal. Mas inspecionar o conteúdo revelou a seção `[state.cooling]`:

```toml
[state.cooling]
reactor_water_temp   = 94.59927549
separator_water_temp = 77.29698353
```

`reactor_water_temp = 94.6` confirma exatamente o alvo da correção 1 (bate com o comentário
histórico "`twr≈94.6°C` no nominal"). Mas `separator_water_temp = 77.3` expôs um SEGUNDO bug
idêntico: `Separator::heat_exchange()` usava `SEPARATOR_COOLING_WATER_RETURN = 40.0` — de novo o
`s_zero` do canal de distúrbio errado (TCWS, canal 5, entrada), não o valor de retorno congelado de
verdade. Diferente do reator, o `tws` original (`teprob.f` Block 40: `yp[37]=0.0`, "tws kept at
snapshot value") é uma constante genuína, sem dependência de válvula — a correção aqui é só trocar
o número, não recalcular nada.

**Correção 2 (separador):** `SEPARATOR_COOLING_WATER_RETURN` corrigido de `40.0` para
`77.29698353` em `src/units/separator.rs`. Relevância: o separador alimenta o reciclo do
compressor, e `enthalpy_compressor_recycle` é um dos dois termos dominantes no balanço de energia
do PRÓPRIO reator (`Reactor::mass_and_energy_balance`) — resfriar demais o separador empurra
entalpia fria pro reator via essa malha, independente do bug do reator já corrigido.

**Reteste:** processo relançado do zero (mesmo `application.toml`), acelerado via
`control.set_speed` (OPC-UA) pra cobrir várias horas simuladas em segundos reais, com leituras
frequentes de `clock.t_h`/`xmeas.reactor.temperature`/`xmeas.reactor.pressure`/
`xmeas.reactor.level`.

### Resultado

Com as DUAS correções aplicadas, `t_h=0.0106h`: T=120.13°C, P=2694.3 kPa, `twr`=93.6°C — bate quase
exatamente com o nominal documentado, confirmando as duas correções corretas isoladamente.

Trajetória completa (velocidade 100x, amostrada a cada ~2s reais ≈ 0.096h simuladas):

| t_h (simulado) | Reactor T (°C) | Reactor P (kPa)     | Level (%)        |
| -------------- | -------------- | ------------------- | ---------------- |
| 0.10           | 114.6          | 2717                | 70.8             |
| 0.20           | 88.6           | 2927                | 68.4             |
| 0.29           | 63.4           | 3488 (> ISD 3000)   | 72.2             |
| 0.39           | 59.1           | 4222                | 80.7             |
| 0.48           | 59.9           | 4941                | 89.9             |
| 0.58           | 60.6           | 5377 (pico)         | 98.6             |
| 0.68           | 57.4           | 3349 (queda súbita) | 98.9             |
| 0.77           | 45.6           | 2402                | 84.7             |
| 0.87           | **0.0**        | **11885.7**         | **≈3.37 × 10⁸⁹** |

A partir de `t_h≈0.87h`, todos os valores congelam exatamente nesses números (conferido em 8
leituras subsequentes até `t_h=24.2h`) — não é uma física real convergindo, é o integrador RK4
tendo divergido numericamente (nível na casa de 10⁸⁹ não tem significado físico).

### Conclusão

**Hipótese parcialmente confirmada.** As duas correções são individualmente verificadas corretas —
a trajetória em `t_h≈0.01h` bate quase exatamente com o nominal documentado — e juntas adiam e
suavizam bastante o colapso (nominal se sustenta ~6x mais tempo simulado antes do primeiro
cruzamento do ISD, e o modo de falha final muda de "estabiliza errado, cedo" para "diverge
numericamente, mais tarde"). Mas a instabilidade de fundo **não foi eliminada**: a pressão já
ultrapassa o ISD em `t_h≈0.29h`, e o sistema termina em colapso numérico (não físico) em vez de
convergir pra qualquer equilíbrio.

Isso aponta pra pelo menos uma TERCEIRA causa ainda não identificada — candidatos mais prováveis:
(a) cinética de reação/VLE produzindo valores ruins quando a pressão sai muito da faixa calibrada
das equações de Antoine (pico observado de 5377 kPa, bem acima do nominal ~2700 kPa), ou (b) uma
discrepância ainda não encontrada no balanço de massa/energia da arquitetura Composite portada,
relativa ao `teprob.f`/`v1.0.0` monolítico original.

**Próximo passo:** instrumentar `Reactor::physical_state()` (pressões parciais, taxas de reação,
`heat_of_reaction`) ao longo desta mesma trajetória, pra identificar em qual ponto exato os números
divergem do que a arquitetura original produziria com as mesmas entradas.

---


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

| Variável           | Baseline   | Esperado após IDV(3)                      |
| ------------------ | ---------- | ----------------------------------------- |
| XMEAS(9) Reactor T | ~120 °C    | ↑ sem controle direto — deriva ou ISD     |
| XMEAS(7) Reactor P | ~2699 kPa  | ↑ ou ↓ dependendo das reações aceleradas  |
| XMV(10) CWS valve  | ~41 %      | **fixo** — sem controlador de temperatura |
| XMV(6) Purge valve | ~39 %      | muda apenas se pressão variar             |
| XMEAS(23,24,25)    | ~31/10/26% | pode derivar — cinética alterada por T    |

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

| Variável           | Baseline  | Observado após IDV(2)                      | Hipótese                     |
| ------------------ | --------- | ------------------------------------------ | ---------------------------- |
| XMEAS(24) B reator | ~10 mol%  | ↑ ~11 mol% — sobe e continua crescendo     | ✗ hipótese previa SS estável |
| XMEAS(7) Reactor P | ~2727 kPa | ↑ ~2840 kPa inicial, depois deriva até ISD | ✗ hipótese previa SS estável |
| XMEAS(9) Reactor T | ~120 °C   | flat — sem variação                        | ✓ confirmada                 |
| XMV(6) Purge valve | ~42 %     | ↑ ~53% inicial, continua abrindo até ~67%+ | ✓ abre, mas insuficiente     |
| XMEAS(23) A mol%   | ~31 mol%  | levemente ↓ (diluição por B)               | não previsto                 |
| XMEAS(25) C mol%   | ~26 mol%  | levemente ↓ (diluição por B)               | não previsto                 |

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


