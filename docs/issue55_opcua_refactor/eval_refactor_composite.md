# Avaliação da refatoração: padrão Composite no te-core

## Status quo das modificações

O ponto de partida era uma arquitetura V1 centrada no trio `Plant<M: DynamicModel, I: Integrator>` + `Bus` + `Params`. Essa camada existia para resolver um problema de coordenação: o modelo não sabia seu próprio tamanho, não sabia como passar inputs nem como expor outputs — alguém de fora precisava declarar `n_states`, `n_mv`, `n_outputs` em `Params`, e o `Bus` servia de contêiner compartilhado para transportar `mv`, `dv` e `xmeas` entre chamadas de `step`. A abstração era genérica mas antiquada: ela resolvia um problema de indireção que o padrão Composite elimina por design.

Paralelamente ao V1, já existia uma stack V2 incompleta espalhada pelo crate: `trait DynamicModelV2` e `CompositeDynamicModel` em `dynamics/model_v2.rs`, `TepPlantCore` em `dynamics/tep/plant_v2.rs` implementando o trait, e implementações de `FirstOrderValve`, `Agitator`, `FirstOrderSensor` e `SampledSensor` nos módulos de atuador e sensor. O `RK4V2` já operava diretamente sobre um `Vec<f64>` sem precisar de `State` ou `Integrator`. A stack V2 estava funcional mas convivendo com o V1 sem substituí-lo de fato.

A limpeza executada removeu dez arquivos do V1 (`state.rs`, `snapshot.rs`, `plant.rs`, `params.rs`, `bus.rs`, `dynamics/model.rs`, `dynamics/tep/model.rs`, `method/integrator.rs`, `method/euler.rs`, `method/rk4.rs`) e atualizou os quatro `mod.rs` correspondentes. O `TepPlantCore::new()` foi reescrito diretamente a partir de `InitialState`, absorvendo as três funções de inicialização de correntes (`initial_xst`, `initial_tst`, `initial_sfr`) que antes viviam no modelo legado. O `core` compila limpo com apenas a stack V2.

## A ideia: DynamicModelV2 como interface universal

`DynamicModelV2` é a interface que toda unidade dinâmica do sistema deve implementar, independentemente de ser planta, atuador, sensor ou distúrbio. O contrato é mínimo e preciso: `state_size() -> usize` informa quantos estados a unidade possui, e `derivatives(&[f64]) -> Vec<f64>` recebe o slice correspondente do vetor global e retorna as derivadas. Não há referência a `Bus`, `Params` ou qualquer outra estrutura de coordenação externa — a unidade é autocontida. Isso significa que `FirstOrderValve`, `TepPlantCore` e um futuro `DisturbanceDynamics` são todos o mesmo tipo do ponto de vista do integrador: objetos que consomem um slice de estado e produzem derivadas.

## A ideia: CompositeDynamicModel como montador

`CompositeDynamicModel` é o padrão Composite aplicado ao vetor de estado: ele mantém uma lista de filhos (`Vec<Box<dyn DynamicModelV2>>`), calcula os offsets via `state_offsets()` somando os `state_size()` de cada filho em sequência, e quando `derivatives()` é chamado, fatia o vetor global e delega para cada filho o seu pedaço. O resultado concatenado forma o vetor de derivadas global que o `RK4V2` integra em um único passo. A consequência direta é que adicionar uma válvula de primeira ordem ao sistema é apenas um `.add(Box::new(FirstOrderValve::new(tau)))` — o integrador não precisa saber nada sobre quantos estados existem agora.

## A ideia: TennesseeEastmanModel como montagem concreta

`TennesseeEastmanModel` será a instância de topo: um `CompositeDynamicModel` que assemble `TepPlantCore` (50 estados da planta química) com 12 `FirstOrderValve` (uma por XMV, 1 estado cada) e eventualmente sensores dinâmicos e modelos de distúrbio. O vetor de estado integrado terá dimensão 62 ou mais, mas isso é transparente para quem chama — a camada de serviço gRPC recebe o composite, chama `step()` via `RK4V2`, lê `raw_xmeas()` do core e envia para o cliente. Não há `Bus`, `Params` nem `Snapshot` no caminho crítico. `TennesseeEastmanModel` é ao mesmo tempo a fronteira pública do crate e o ponto de composição de toda a física modelada.
