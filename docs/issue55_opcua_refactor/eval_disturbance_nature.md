# Avaliação — qual é a natureza dos distúrbios (IDV) no TEP?

Motivada pela pergunta: pra ligar `Disturbance` em `Flows`/`Heat`/`Reactor` de forma limpa (um "wrapper", não uma dependência confusa), preciso saber se um distúrbio **substitui o valor de uma variável** ou **precisa alterar um cálculo por dentro**. Investigação feita direto em cima do código real: `tep-plant/src/disturbance/{mod.rs,state.rs}` (implementação atual, 4 dos 12 canais já ligados) e `docs/_deprecated_2.rs` (física original dos Blocks 7-34, os 12 canais completos).

## Os 12 canais, e o que cada um alimenta

`TepDisturbanceState::new()` (`disturbance/state.rs:10-22`) já documenta o mapeamento canal→variável física. Rastreei cada um até o Block que o consome:

| Canal | Variável física | IDV | Quem consome | Natureza |
|---|---|---|---|---|
| 0, 1 | Composição A/B do feed A/C (stream 4/nossa stream 3) | IDV 8 | `Flows` (Block 19, `mole_fractions[0][3]`/`[1][3]`) | substitui um valor de composição |
| 2, 3 | Temperatura feed D / feed A-C | IDV 9, 10 | `Flows` (Block 21, `stream_temperatures[0]`/`[3]`) | substitui um valor de temperatura |
| 4, 5 | Temp. água de resfriamento reator/separador | IDV 11, 12 | `Heat` (Block 32/33) — **já ligado hoje** (`reactor_cooling_water_temp`/`separator_cooling_water_temp`) | substitui um valor de temperatura |
| 6, 7 | Fator cinético de reação 1/2 | IDV 13 | `Reactor` (Block 18, multiplica `rates[0]`/`rates[1]`) — **já ligado hoje** (`reaction_factor_1/2`) | multiplica dentro de um cálculo |
| 8 | Coeficiente de troca do condensador (UAC) | IDV 16 | `Flows` (Block 24, `condenser_ua = ... * (1.0 + eval_disturbance(8,...))`) | multiplica dentro de um cálculo |
| 9 | Distúrbio de resfriamento do reator | IDV 17 | `Heat` (Block 32, `reactor_heat = ... * (1.0 - 0.35 * eval_disturbance(9,...))`) | multiplica dentro de um cálculo |
| 10 | Distúrbio de resfriamento do separador | IDV 18 | `Heat` (Block 33, mesmo padrão) | multiplica dentro de um cálculo |
| 11 | Distúrbio de vazão reator→separador | IDV 20 | `Flows` (Block 24, `flows[7] = ... * (1.0 - 0.25 * eval_disturbance(11,...))`) | multiplica dentro de um cálculo |

Além dos 12 canais cúbicos, existem **flags IDV brutos** (não passam por `eval_disturbance`, são só 0/1) usados direto como porta/multiplicador: `idv[5]` (IDV 6) zera o feed E, `idv[6]` (IDV 7) reduz o feed A/C em 20% — ambos dentro do Block 22-24 de `Flows`.

## Conclusão: os dois casos são o mesmo caso, do ponto de vista de `Disturbance`

Em **todos** os 12 canais — e nos flags brutos — `Disturbance` produz **um número escalar** (via `eval_disturbance(canal, time, state)`, já implementado em `simulation_framework::disturbance::cubic`) que **outro componente lê e usa dentro da própria fórmula**. Não existe nenhum canal que precise "alcançar" o estado interno de outro `DynamicModel` ou escrever em um `Proxy` que não seja o dele mesmo. A diferença entre "substitui um valor" (canais 0-5) e "multiplica um cálculo" (canais 6-11) é só **o que o componente consumidor faz com o número** depois de ler — pra `Disturbance`, publicar um `f64` num `Proxy` é sempre a mesma operação.

Isso confirma que dá pra manter `Disturbance` exatamente tão limpo quanto já está hoje pros 4 canais já ligados (`reaction_factor_1/2`, `*_cooling_water_temp`) — só precisa **oferecer mais slots** (seguindo o mesmo padrão de `subscribe()`), um por canal que `Flows`/`Heat` forem passar a consumir como `need`. Nenhuma mudança de mecanismo, só mais chaves.

## O que falta pra `Flows`/`Heat` usarem isso

Hoje `Disturbance::new()` só oferece 4 slots (`disturbance/mod.rs:38-43`). Pra `Flows` consumir os canais 0-3, 8, 11 (e os flags brutos 5/6) e `Heat` consumir 9/10, `Disturbance` precisaria oferecer mais ~8-10 slots análogos — ex.: `"disturbance.feed_ac_composition_a"`, `"disturbance.feed_d_temperature"`, `"disturbance.condenser_heat_transfer_factor"`, `"disturbance.feed_e_blocked"` (o flag bruto do IDV 6, como `0.0`/`1.0`), etc. — e `Flows`/`Heat` declarariam esses nomes como `need` em `subscribe()`, exatamente como `Reactor` já faz hoje com `"disturbance.reaction_factor_1"`.

## Pendência à parte, não resolvida aqui: `Disturbance::advance(time)` ainda não é chamado

`Disturbance` já documenta (`disturbance/mod.rs:6-10`) que precisa de um `advance(&mut self, time: f64)` chamado **antes** do `evaluate()` da árvore, por quem orquestra a simulação — mas `Simulation::run_model()` (seção 11.3 do `plan_refactor.md`) não tem noção de tempo simulado nenhuma hoje, só um `tick_interval` de pacing (sleep entre iterações, não um `dt`/`time` de verdade sendo avançado). Ligar `Disturbance` de verdade nos 12 canais completos esbarra nisso — os canais cúbicos (0-8) e os de pulso aleatório (9-11) só avançam quando `time` cruza o `t_next` de cada canal; sem um relógio real, `advance()` nunca teria um `time` significativo pra passar. Fica registrado como pré-requisito, não como parte desta avaliação.
