# Plano de refatoração — Composite + Registry semântico (issue #55)

Este documento registra, em artigos numerados, as decisões de arquitetura da modelagem do `tep-plant`/`monjolo`. Segue a estrutura definida em `docs/padrao_documentacao.md` — é uma cópia experimental de `plan_refactor.md` reescrita nesse formato, para avaliar o padrão. `eval_refactor.md` continua sendo a avaliação/histórico que levou até aqui.

**Nota metodológica desta cópia (não é conteúdo normativo):** a numeração de artigo herdada de `plan_refactor.md` foi preservada sempre que possível — remissões antigas (`seção X.Y`) continuam batendo com `Art. X.Y` aqui. Usando `git blame` no arquivo original, separei dois casos que lá apareciam com a mesma aparência (`~~texto~~ **Nota:**`): (a) pares onde o texto riscado e a correção foram escritos no mesmo dia — não é uma alteração real, é só o autor documentando "cogitei X, decidi Y" num único ato de escrita; esses viraram caput direto, sem aparato de hachura/data. (b) pares com data real de intervalo entre o texto riscado e a correção — esses mantêm hachura (Art. 4) ou viraram revogação (Art. 2), com data. Números de artigo ausentes (Art. 6.5, 10.5, 10.7, 11.7, e o antigo capítulo 12) não foram apagados por engano — o conteúdo que ocupava esses endereços era pendência mal alocada como artigo próprio; foi reclassificado como parágrafo do artigo que efetivamente qualifica (índice abaixo aponta onde).

## Índice

```
StateRegistry        → Art. 1.3, 3.6, 6, 6.1–6.4
Snapshot              → Art. 11.9
CurrentState          → Art. 1.3, 3.6, 3.6.2
EvaluationState       → Art. 1.2, 1.3, 8, 8.1–8.4
Proxy                 → Art. 1.1, 7, 7.1, 7.2
ReadProxy             → Art. 3.6.2, 3.6.4
DynamicModel          → Art. 1 (capítulo), 1.1, 2.1, 2.2
CompositeDynamicModel → Art. 2, 2.1, 2.3, 2.3.1
add_dynamic           → Art. 2.3, 2.3.1, 2.6
Sensor                → Art. 3.3, 3.5, 3.5.1, 3.6–3.9
SensorBehavior        → Art. 3.6.1
IoImage               → Art. 10, 10.1–10.4
CommandSink           → Art. 10.4
CommandQueue          → Art. 10.6.2, 11.4
SnapshotBus           → Art. 11.4
Simulation            → Art. 9, 9.1–9.9, 11, 11.1–11.10
AdapterConfig         → Art. 11.10
NumericalMethod/RK4   → Art. 9.9, 11.10
Adaptador OPC-UA      → Art. 10.6, 10.6.1–10.6.4
Flows/Heat/Measurements → Art. 2.6, §1º
Controlador           → Art. 3.5, 3.5.1 §2º, 10.4 §1º
DAG/DAE               → Art. 4, 4.1–4.5
StateSlot             → Art. 3.6.5, 5, 5.1–5.4
tep-plant (binário)   → Art. 10.6.1, 11.6, 11.9
```

## Contrato de Integração (Integrator ↔ DynamicModel)

**Art. 1.1.** A relação entre o `Integrator` (RK4) e um `DynamicModel` tem uma única fase real: `evaluate()`, o loop de integração. Não existe fase de construção via `get_state_template()`/`StateTemplate` — foi substituída pela inscrição de cada `DynamicModel` direto no `StateRegistry` (`subscribe()`, Art. 6.2), que devolve `Proxy`s (Art. 7). Não existe `set_state()` como método do `DynamicModel` — quem persiste é `StateRegistry.set_current_state()` (Art. 1.3).

**Art. 1.1.1.** O RK4 nunca assume nada sobre o modelo além do contrato do Art. 1.1: não sabe quantos estados existem, não sabe como as derivadas são calculadas internamente, não sabe como o novo estado é persistido — responsabilidade exclusiva do `DynamicModel`.

**Art. 1.2.** `evaluate()` não muta o `self` do componente que a executa. Com `EvaluationState` (Art. 8), `evaluate()` tem efeito de mutação sobre um buffer externo — escreve seus outputs (valores e derivadas) via `Proxy`, usando mutabilidade interior (`Cell`). Quem é mutado é o `EvaluationState` compartilhado (Art. 8.2), nunca o `self` do componente.

§1º Este desenho elimina o bug do código anterior a este refactor, em que `dynamics()` mutava campos como `self.mole_fractions`/`self.stream_temperatures` como efeito colateral, mesmo sendo chamado 4 vezes por passo do RK4 (k1..k4) — estados intermediários dessincronizados, silenciosamente.

**Art. 1.3.** `StateRegistry` guarda dois repositórios internos: **`CurrentState`** (os slots oficiais, o estado persistido/confirmado) e **`EvaluationState`** (o buffer de trabalho de uma rodada de avaliação, Art. 8, onde os `evaluate()` dos `DynamicModel`s escrevem via `Proxy`). `set_current_state()` é o procedimento — implementado no `StateRegistry`, nunca por-componente no `DynamicModel` — que carrega `EvaluationState` → `CurrentState`, fechando o loop de evolução; é `Simulation` (Art. 9) quem chama isso depois do `step()` (Art. 9.8).

## Contrato de Composição (DynamicModel ↔ DynamicModel)

**Art. 2.1.** `trait CompositeDynamicModel: DynamicModel` — em Rust não existe herança de classe, só herança de trait (supertrait). Implementar `CompositeDynamicModel` exige implementar `DynamicModel` também.

**Art. 2.2.** Só nós compostos implementam `CompositeDynamicModel`. Componentes-folha (`Valve`, `Agitator`, e futuramente Reactor/Separator/Stripper/Compressor, se virarem folhas de fato) não implementam esse trait — tentar compô-los vira erro de compilação, não erro de runtime.

**Art. 2.3.** `add_dynamic` é um método de `CompositeDynamicModel` que adiciona o `DynamicModel` sendo registrado à sequência de avaliação do composto, na ordem em que foi inserido — não declara slots nem funde template nenhum. Quem declara slots é a inscrição direta de cada `DynamicModel` no `StateRegistry` (Art. 6).

**Art. 2.3.1.** Corpo default de `add_dynamic`: `self.models_mut().push(component)` — só o getter `models_mut()` sobre o `Vec<Box<dyn DynamicModel>>` próprio (campo `models`, Art. 2.5).

**Art. 2.4.** Delegar a avaliação a cada filho — chamando o `evaluate()` de cada um, na ordem em que `add_dynamic` (Art. 2.3) os registrou — é a única parte que cada composto escreve do zero. Isso só funciona porque o TEP é um DAG (Art. 4.1): uma única passada, em ordem fixa de inserção, resolve o composto porque não há ciclo algébrico entre os componentes.

§1º Para um caso DAE (Art. 4.3, acoplamento algébrico forte), uma única passada não fecha — seria necessário um objeto análogo ao `Integrator`, mas para a dimensão algébrica (um "`Interator`"), rodando o subconjunto cíclico via Newton/tearing (Art. 4.4) até convergência. Não existe e não é necessário para o TEP atual — extensão futura registrada, não pendência de implementação imediata.

**Art. 2.5.** Não existe uma implementação genérica `Composite` reutilizável. Cogitado um `struct Composite` genérico (`children`/`sizes`) e rejeitado: no sistema inteiro só existe **um** nó composto de fato — `TennesseeEastmanModel`. `TennesseeEastmanModel` implementa `DynamicModel` + `CompositeDynamicModel` diretamente, dono do próprio `Vec<Box<dyn DynamicModel>>` (campo `models`).

**Art. 2.6.** O construtor do TEP (`TennesseeEastmanModel::new()`) não contém lógica de composição própria — só uma sequência de chamadas `add_dynamic` (Art. 2.3) registrando cada componente, na ordem em que devem ser avaliados. Hoje: `Reactor`, `Separator`, `Stripper`, `Compressor` — todos consumindo condição inicial via `Snapshot` (Art. 11.9).

§1º (pendência aberta, identificada em 2026-07-12) `Flows`, `Heat` e `Measurements` — os três subsistemas que fechariam o cálculo (Blocks 19-36 do `teprob.f`) — existem só como `struct`s vazios com `evaluate() { todo!() }` (`tep-plant/src/subsystems/{flows,heat,measurements}.rs`) e não estão `add_dynamic`'d aqui: não são só "não implementados", são código morto, nunca instanciados nem no binário `tep-plant`. Física original preservada, comentada, em `tep-plant/docs/_deprecated_2.rs`: `TepFlows` (Blocks 19-31), `TepHeat` (Blocks 32-34), `TepMeasurements` (Blocks 35-36).

Inciso I — Consequência: `Flows` é quem calcularia a derivada real (`yp`) do `own_state` de Reactor/Separator/Stripper/Compressor. Sem ela, nenhum dos quatro oferece a chave `.derivative` companheira, e `TennesseeEastmanModel` não sobrescreve `state_keys()` (Art. 9.9, fica no default vazio) — o Integrator (Art. 9) não tem o que integrar para o núcleo químico, e `own_state` fica congelado no valor semeado pelo `Snapshot` (Art. 11.9). `evaluate()` só recalcula grandezas termodinâmicas derivadas (temperatura, pressão, composição) em cima desse estado parado. A máquina de integração em si funciona e está testada (`Valve`/`Agitator` já a usam corretamente).

Inciso II — Portar exige decidir os `needs` de cada um sobre o `StateRegistry` atual (`Flows` precisa dos quatro subsistemas químicos + posições de válvula + flags de distúrbio ao mesmo tempo) e reescrever a lógica em cima de `Proxy`/`ReadProxy` (Art. 7), não `&[f64]` posicional.

Inciso III — Ordem de dependência: `Flows` (depende só dos 4 químicos) → `Heat` (depende de Reactor+Stripper+Flows) → `Measurements` (depende de todos+Flows+Heat). Wirear atuador (Art. 11.2, §1º) só produz efeito real na planta depois que `Flows` existir.

**Art. 2.7.** `get_state_template()`/`StateTemplate` não existem — foram substituídos pela inscrição (Art. 6.2). Um `DynamicModel` se inscreve no `StateRegistry`, recebe `Proxy`s de volta, e opera com eles. `DynamicModel` tem, como métodos reais, `evaluate()` e `subscribe()` (o método especial de inscrição, Art. 6.2.1).

## Relação com o mundo externo (Outside ↔ DynamicModel)

**Art. 3.1.** Nome da relação: `AcquisitionLayer`. Cogitado e rejeitado antes: "Process Image" (conotação de automação/PLC, considerado confuso).

**Art. 3.2.** Papel da `AcquisitionLayer`: consulta, não avaliação. Algo externo (ex.: adapters 4-20mA, Modbus, OPC-UA) consulta o `DynamicModel` pai para obter o estado bruto e o transforma para um protocolo específico — leitura pura, depois que o modelo já resolveu tudo, sem participar do `evaluate()`.

**Art. 3.3.** `Sensor` não é um `DynamicModel` na árvore de composição — fica fora do `add_dynamic` (Art. 2.3) porque não participa da avaliação: só lê o estado depois de resolvido.

**Art. 3.4.** `Disturbance` não é um `DynamicModel` na árvore de composição — não é dono de um componente, atravessa vários ao mesmo tempo (reação no Reactor, UA do condensador e vazão nos Flows, coeficientes de troca no Heat). Tratado como entrada injetada, associada a cada componente que o consome.

**Art. 3.5.** Existem exatamente três objetos que dão à física simulada alguma interação com o mundo externo: **Sensor** (expõe um valor observado), **Atuador** (permite ação sobre a planta) e **Controlador** (permite fechar uma malha de controle sobre a planta). Fora desses três, não há outra porta de entrada/saída entre a dinâmica simulada e o mundo de fora.

**Art. 3.5.1.** O design detalhado de Atuador e Controlador (Art. 3.5) foi tratado depois do de Sensor. Os Art. 3.6 a 3.9 especificam só o `Sensor`.

§1º Atuador ganhou design concreto: `CommandSink` (Art. 10.4), canal (Art. 11.4) — não é mais pendência.

§2º (pendência aberta) Controlador ainda não modelado. Design já previsto: lê via `IoImage.read()` (Art. 10.3), escreve via `IoImage.write()` (Art. 10.4) — sem exigir mudança de forma em `IoImage`. Não implementado porque não há Controlador ainda pra testar contra.

**Art. 3.6.** `Sensor` não tem relação com `evaluate()`/`EvaluationState` (Art. 8) — quem escreve ali são os `DynamicModel`s resolvendo sua própria física, a cada sub-passo do RK4. `Sensor` lê de `StateRegistry.CurrentState` (Art. 1.3): o repositório já commitado, depois que `set_current_state()` fechou o passo. `Sensor` nunca é um participante da avaliação, só observa o que já está definitivo.

**Art. 3.6.1.** `Sensor` pode ter estado interno próprio — sem ser `DynamicModel`. Problemas como histerese/banda morta ou ruído não exigem dinâmica integrada: uma função `(valor_bruto, estado_do_sensor) -> saída`, atualizada como efeito colateral de cada leitura, sem entrar no vetor que o `Integrator`/RK4 avança. Implementado como `trait SensorBehavior` (`monjolo/src/sensor/model.rs`), com `Ideal`, `Noisy` e `Hysteresis` como comportamentos plugáveis no `Sensor`.

**Art. 3.6.2.** `current_state` é `Rc<RefCell<Vec<Cell<f64>>>>` — mesma forma de `evaluation_state` (Art. 8), mutado célula-a-célula por `commit()`, nunca substituído por inteiro. `StateRegistry::read_proxy(key) -> Option<ReadProxy>` resolve a chave uma única vez contra esse buffer — é o que `Sensor` (Art. 3.6.3) usa. `StateRegistry::read(key) -> Option<f64>` continua existindo, mas como leitura pontual de debug/inspeção avulsa, não o caminho usado por `Sensor`.

**Art. 3.6.3.** `Sensor` é, na prática, um pipe: observa uma chave, aplica um `SensorBehavior` (Art. 3.6.1) e expõe o resultado — nunca escreve de volta no `StateRegistry`. `Sensor` guarda um `ReadProxy` (Art. 3.6.2), resolvido uma única vez em `Sensor::new()` — `read()` é só `self.proxy.get()`, sem lookup por string. `RegistryView` (fachada somente-leitura sobre `Rc<RefCell<StateRegistry>>`, sem `subscribe()`/`resolve()`/`commit()`) é a fábrica que produz esse `ReadProxy` (`RegistryView::read_proxy(key)`), usada uma única vez na construção do Sensor.

**Art. 3.6.4.** `ReadProxy` é um tipo à parte de `Proxy` (Art. 7) — não pode ser confundido com valor hipotético. `Proxy` endereça `EvaluationState`, que pode conter valor hipotético de um solver iterativo em andamento (Art. 7.2). `ReadProxy` só existe sobre `CurrentState` — sempre o último valor confirmado. Dois `struct`s distintos (mesma forma: buffer + índice) de propósito: com tipos separados, entregar por engano ao `Sensor` um `Proxy` resolvido contra `EvaluationState` não compila. `ReadProxy` nasce já resolvido — só é criado depois que `resolve()` geral já rodou (Art. 3.8) — e não tem `set()`.

**Art. 3.6.5.** `StateSlot` (Art. 5) não guarda mais o estado corrente — é reconstruído sob demanda por `StateRegistry::snapshot() -> Vec<StateSlot>`, zipando `index` (a fonte de verdade operacional pra `key -> posição`) com o buffer atual. Serve só pra metadado/catálogo: inspeção, debug, listagem de sinais, exportação nomeada — nunca o caminho por onde `Proxy`/`ReadProxy` leem ou escrevem.

**Art. 3.7.** Um `Sensor` acompanha exatamente uma variável — não existe "sensor composto" nessa camada. Se o usuário quer acompanhar A, B e C, declara três sensores.

**Art. 3.7.1.** `Sensor` é agnóstico ao tipo físico do sinal. Não existe `FI`/`PI`/`LI`/`TI`/`AI` como tipos distintos — tentativa existente no código anterior (um struct por grandeza física, todos com o mesmo corpo) e abandonada. O que varia entre sensores é o comportamento de leitura (Art. 3.6.1), não a grandeza física medida.

**Art. 3.8.** A declaração de `Sensor` é explícita, feita por quem monta a planta/simulação — nunca automática ou implícita na dinâmica em si. Só pode ser construído depois que todo `DynamicModel` já chamou `subscribe()` e `StateRegistry::resolve()` geral já rodou (Art. 9.2) — nunca junto dos `add_dynamic` (Art. 2.3) na composição do modelo. Motivo: `Sensor::new()` resolve a chave contra `CurrentState` uma única vez, na hora (Art. 3.6.2/3.6.4), sem segunda fase de resolução como `Proxy::unresolved` tem para `needs` (Art. 6.2) — se a chave ainda não existir em `index` nesse momento, é erro (`Result<Self, String>`). Isso combina com a instanciação de `Simulation` (Art. 9), não com o construtor do modelo composto.

**Art. 3.9.** (revogado, ver Art. 10.1 e Art. 11.1, 2026-07-09/2026-07-10)

## Viabilidade da arquitetura (DAG vs. DAE)

**Art. 4.1.** O TEP hoje é um DAG (grafo acíclico dirigido). As dependências entre Reactor → Separator → Stripper/Compressor → Flows → Heat/Measurements → derivadas formam um grafo acíclico. Uma ordem fixa (`EvaluationPlan`) é suficiente — não há equação implícita circular no código atual.

**Art. 4.2.** Reciclo físico não implica ciclo algébrico. O TEP tem reciclo físico (saída do compressor volta ao reator), mas vazões e composições são calculadas usando estados já conhecidos, em ordem causal explícita. O problema algébrico só apareceria se a variável `A(t)` de um bloco precisasse simultaneamente de `B(t)` de outro *e* `B(t)` precisasse de `A(t)`.

**Art. 4.3.** Um DAG simples quebra em plantas mais gerais com equilíbrio de rede hidráulica, flash acoplado, reciclo forte ou relação pressão-vazão implícita (ex.: `F = Cv·√(PA-PB)`, com `PA`/`PB` dependendo de `F` no mesmo instante). Isso forma um ciclo algébrico — vira uma DAE (`0 = g(y, z, t)`), não resolvível por uma sequência linear.

**Art. 4.4.** Um solver iterativo resolve o ciclo chutando um valor para a variável que fecha o ciclo, avaliando o resto do grafo como DAG a partir desse palpite, medindo o resíduo, ajustando e repetindo até convergir — transforma o ciclo em um problema de ponto fixo.

**Art. 4.4.1.** Newton usa o Jacobiano do resíduo para escolher a direção de correção, convergindo em muito menos iterações que substituição sucessiva.

**Art. 4.4.2.** Tearing isola deliberadamente a(s) variável(is) que fecham o ciclo e itera só sobre elas, reavaliando o resto como DAG a cada tentativa — reduz drasticamente o tamanho do sistema iterado.

**Art. 4.5.** Válido para o escopo atual do TEP (DAG simples, Art. 4.1). Não é a arquitetura universal para simulação de plantas em geral — plantas com acoplamento algébrico forte exigiriam um solver iterativo embutido dentro da fase de avaliação (Art. 4.4), mantendo o RK4 só para o avanço no tempo.

## Sobre `StateSlot` e a malha de nomes semânticos

**Art. 5.1.** Estrutura final de `StateSlot`: `key: String` + `value: f64`, sem campo `index`. A posição de um slot dentro do `Vec` que o contém é o seu índice — não é redeclarada dentro do slot.

**Art. 5.1.1.** `index` foi removido de `StateSlot` porque guardá-lo dentro do próprio slot cria uma invariante que ninguém garante (`slots[3].index == 4`) e que pode divergir silenciosamente se alguém filtrar, reordenar ou fundir slots. Resolver posição em tempo real é sempre trabalho do `index: HashMap<String, usize>` (Art. 6), nunca de vasculhar um `Vec<StateSlot>`.

**Art. 5.2.** Invariante: append-only. Uma vez que um slot é registrado, sua posição nunca muda nem é reaproveitada.

**Art. 5.3.** Um componente que depende de um valor semântico de outro (ex.: Separator precisando de `reactor.temperature`) resolve essa string contra a lista de slots uma única vez, no momento da construção/composição — não a cada `evaluate()`. Guarda o `usize` resultante como campo próprio.

**Art. 5.4.** `EvaluationResult` (`{ derivatives: Vec<f64>, values: Vec<StateSlot> }`, devolvido por `evaluate()`) foi superado pelo `EvaluationState`/`Proxy` (Art. 8) — `evaluate()` deixou de retornar qualquer coisa.

## Sobre o `StateRegistry` como singleton de inscrição

**Art. 6.1.** `StateRegistry` é um serviço singleton de inscrição/resolução, usado na construção — não durante o loop de simulação. Todo `DynamicModel` se reporta a um e somente um `StateRegistry`, mesmo que não faça parte de uma composição.

**Art. 6.2.** Um `DynamicModel`, na sua construção, se inscreve no `StateRegistry` (`subscribe()`): reserva espaço para os próprios slots (outputs), declarando a semântica deles, e declara quais inputs (chaves de outros componentes) precisa.

§1º (pendência aberta, identificada em 2026-07-07) A inscrição não deveria depender de alguém lembrar de chamar `subscribe()`/`add_dynamic()` explicitamente dentro de `TennesseeEastmanModel::new()` (Art. 2.6). Em Python isso seria resolvido com efeito colateral de import; em Rust, compilado, a ideia é usar a própria compilação para pré-registrar isso, sem depender de uma sequência imperativa de chamadas. Mecanismo concreto ainda em aberto — candidatos: registro via linker section (estilo `inventory`/`linkme`), ou `ctor` para rodar código antes de `main()`.

**Art. 6.2.1.** `subscribe` é um método especial, separado de `add_dynamic` (Art. 2.3) — que serve só para fins estruturais de composição. Na inicialização, primeiro os `DynamicModel`s se inscrevem, e só depois são avaliados — sem a inscrição resolvida, não têm os índices necessários para rodar `evaluate()`.

**Art. 6.3.** Resolução em duas fases: não é necessário respeitar ordem na inscrição — todo mundo se inscreve primeiro. Só depois disso tem um passo explícito (`resolve()`), rodado uma única vez, que resolve o índice de cada slot e de cada input declarado.

**Art. 6.4.** Validação: se um input declarado não tiver provedor correspondente durante a resolução, é erro (exceção sobe). Se um slot (output) oferecido nunca for consumido por ninguém, sem problema — a única coisa avaliada é se os inputs solicitados foram todos mapeados.

## Sobre `Proxy`

**Art. 7.1.** `Proxy` é um handle compartilhado entre um `DynamicModel` e o `StateRegistry`, do tipo "resolvido uma vez, usado para sempre" (na prática, algo como `Rc<Cell<usize>>`). Nasce sem resolução; o `StateRegistry`, durante `resolve()` (Art. 6.3), escreve o índice real nele. Dali em diante, todo clone desse `Proxy` enxerga o índice resolvido, sem precisar achar de novo.

**Art. 7.2.** `Proxy` é agnóstico a valor "hipotético" ou "real" — só endereça uma posição; o que existe *dentro* dessa posição (um chute intermediário de um solver iterativo/Newton, Art. 4.4, ou um valor já convergido) é problema de outra camada.

## Sobre `EvaluationState`

**Art. 8.1.** `EvaluationState` é uma cópia inicializada a partir do `StateRegistry` já resolvido — mesmo tamanho, mesmos índices. É o buffer de trabalho de uma rodada de avaliação, carregando os valores reais durante a simulação.

**Art. 8.2.** Como `evaluate()` continua `&self` (Art. 1.2), mas precisa escrever nos próprios outputs, `EvaluationState` precisa de mutabilidade interior (`Vec<Cell<f64>>`). Quem muta é o buffer externo, não o `self` do componente — a regra do Art. 1.2 continua de pé.

**Art. 8.3.** Derivadas também são slots endereçados por `Proxy` (Art. 7). Cada slot de estado ganha, além do seu valor, uma chave própria para sua derivada (ex.: `"Separator.temperature.derivative"`), resolvida junto no `subscribe()` (Art. 6.2). Isso unifica derivadas e valores algébricos sob o mesmo mecanismo de endereçamento.

**Art. 8.4.** `EvaluationResult` foi eliminado (Art. 5.4). `evaluate()` não retorna mais nada — só escreve dentro do `EvaluationState`, usando os `Proxy`s de output que já tem guardados desde a inscrição.

## Sobre `Simulation` (objeto de orquestração)

**Art. 9.1.** `Simulation` é o objeto de alto nível que instancia o TEP (`TennesseeEastmanModel`) e o `Integrator` (RK4). É quem sabe o que precisa passar para o integrador — nem o TEP nem o `Integrator` sabem disso sozinhos.

**Art. 9.2.** Depois que o TEP (e todos os `DynamicModel`s que ele registrou via `add_dynamic`, Art. 2.3) já rodaram seu `subscribe()` (Art. 6.2) no `StateRegistry`, `Simulation` chama `registry.resolve()` (Art. 6.3) uma única vez.

**Art. 9.3.** `Simulation` passa uma lista de nomes de derivada para o `StateRegistry`, que devolve o vetor de `Proxy`s correspondente — resolvido uma única vez, guardado, na mesma ordem do vetor de estado que o `Integrator` usa.

**Art. 9.4.** O `Integrator` continua recebendo um `state: Vec<f64>` cru — só soma vetores, sem saber nada sobre `Proxy`, `EvaluationState` ou `StateRegistry`.

**Art. 9.5.** `Integrator::step()` recebe uma closure/callback, fornecida por `Simulation`, chamada internamente a cada sub-etapa (k1..k4) — não recebe mais `model: &mut dyn DynamicModel`.

**Art. 9.6.** A closure do Art. 9.5 escreve o estado perturbado (`s2`, `s3`, `s4` do RK4) no `EvaluationState`, via os `Proxy`s dos próprios slots de estado, e dispara o `evaluate()` de toda a árvore de `DynamicModel`s.

**Art. 9.7.** A closure do Art. 9.5 atua diretamente sobre o subconjunto das derivadas (Art. 9.3) — não extrai e devolve uma cópia isolada.

**Art. 9.8.** Depois do `step()`, `Simulation` grava o `EvaluationState` inteiro nos slots reais — não só o subconjunto de derivadas, também os valores algébricos calculados como efeito colateral (ex.: `reactor.temperature`), disponíveis para quem precisar deles depois (ex.: a `AcquisitionLayer`, Art. 3.2) sem custo extra.

**Art. 9.9.** Implementado em `monjolo/src/method/{integrator.rs,rk4.rs}` + `Simulation::run()`. Decisões que os Art. 9.1-9.8 não fixavam:

Inciso I — a lista de nomes de derivada (Art. 9.3) vem de `DynamicModel::state_keys(&self) -> Vec<String>` (default vazio, mesmo padrão de `sensors()`, Art. 11.8); a chave da derivada é sempre `<key>.derivative` por convenção. `Simulation::set_model()` captura `state_keys()` no mesmo momento em que captura `sensors()`. Dentro de `run()` (Art. 11.10), cada par `(key, key.derivative)` vira dois `need`s em `subscribe(&[], ...)`.

Inciso II — `tick_interval` (ritmo de parede) ≠ `dt_hours` (passo físico simulado): `Simulation` tem os dois campos, independentes (`set_dt_hours`/`set_tick_interval`).

Inciso III — depois de `Integrator::step()` devolver o estado combinado (`y_new`), `EvaluationState` ainda reflete o último sub-passo `k4` (ponto hipotético) — `run()` faz uma escrita + `evaluate()` extra com o estado final antes de commitar, para que valores algébricos (ex.: `reactor.temperature`) fiquem consistentes com o estado de fato commitado.

§1º Estado real da integração do núcleo químico do TEP hoje: ver Art. 2.6, §1º.

§2º (2026-07-10) RK4 deixou de ser hardcoded: `Simulation::set_numerical_method(NumericalMethod)` (inciso I) passou a ser consumido de verdade dentro de `spawn_plant_thread` via `NumericalMethod::integrator() -> Box<dyn Integrator>` — antes o campo existia mas `run()` ignorava e usava RK4 fixo.

## Sobre a I/O Image — fronteira externa mínima

**Art. 10.1.** `IoImage` (`monjolo/src/io_image.rs`) é um catálogo central de sinais nomeados — o lugar único onde `Sensor`s (leitura) e comandos de Atuador (escrita) ficam disponíveis por nome. Convenção de nome (não imposta pelo tipo): `sensors/<algo>` pra leitura, `actuators/<algo>` pra escrita.

**Art. 10.2.** `io_image.rs` não importa `state_registry` — só conhece `Sensor` (Art. 3) como tipo de leitura, e um trait `CommandSink` próprio como tipo de escrita. `IoImage` nunca precisa saber que `StateRegistry`/`Proxy`/`ReadProxy`/`EvaluationState` existem.

**Art. 10.3.** `IoImage` guarda um `HashMap<String, Sensor>` — publicar é só inserir um `Sensor` já construído sob um nome (`register_sensor(name, sensor)`). `read(name)` chama `Sensor::read()` por trás (Art. 3.6.1), devolvendo `None` se o nome não existir.

§1º (pendência aberta) Não está fechado se `IoImage.read()` deveria virar push/observer em vez de pull dentro do processo, nem se `commit()` deveria notificar assinantes — o adaptador (Art. 10.6) contorna isso com um `interval` de 500ms que só lê tudo de novo a cada tick, não um mecanismo de notificação de verdade.

**Art. 10.4.**
```rust
pub trait CommandSink {
    fn write(&mut self, value: f64);
}
```
Qualquer `FnMut(f64)` implementa `CommandSink` de graça — `Valve::set_command`/`Agitator::set_command` viram sinal de escrita só por fechamento: `io.register_actuator("actuators/cooling_water.command", move |v| valve.set_command(v))`. `IoImage` nunca precisa conhecer `Valve` como tipo — só o `CommandSink` por trás.

§1º Ver Art. 3.5.1, §2º, para o design (ainda pendente) do Controlador sobre este mesmo mecanismo.

**Art. 10.6.** O primeiro adaptador de rede é `monjolo/src/adapter/opcua.rs` (`pub async fn serve(...)`), atrás da feature `opcua` (puxa `async-opcua` + `tokio`). Sobe um servidor OPC-UA real: um node read-only por `io.sensor_names()` (Art. 10.6.4), atualizado por push (`node_manager.set_values()`) a cada tick, depois de cada `Simulation::run()` (Art. 9.9) — nunca por `add_read_callback`, porque o valor já está pronto.

**Art. 10.6.1.** `opcua_adapter::serve()` não conhece TEP — só itera `simulation.io().sensor_names()`/`actuator_names()`, nomes já declarados por fora. Quem declara é o binário real da aplicação, `tep-plant/src/bin/tep_plant.rs` (`[[bin]] name = "tep-plant"`, ~~antes um `examples/opcua_server.rs`, quando `tep-plant` ainda era workspace com subcrate~~ → 2026-07-10) — `cargo run --bin tep-plant`, não uma demonstração. O nome OPC-UA (`"TEP/Reactor/Temperature"`) e a chave do `StateRegistry` (`"reactor.temperature"`) são decisão exclusiva de quem monta a `Simulation` — o adaptador só vê o primeiro.

**Art. 10.6.2.** Atuadores têm um caminho de escrita completo: `SimpleNodeManager::add_write_callback` exige `Fn(...) + Send + Sync + 'static`, e `Simulation`/`IoImage`/`StateRegistry` são deliberadamente `Rc<RefCell<_>>` (Art. 11.1) — não-`Send`. O callback registrado não toca em `Simulation` direto: só empurra `(nome, valor)` num canal, ~~`tokio::sync::mpsc::UnboundedSender`~~ → `CommandQueue` (Art. 11.4), 2026-07-10 — o mecanismo de canal sobreviveu, o tipo concreto e o lado receptor mudaram com a divisão em threads.

**Art. 10.6.3.** (revogado, ver Art. 11, 2026-07-10)

**Art. 10.6.4.** `IoImage` ganhou `sensor_names()`/`actuator_names()` — necessário pro adaptador genérico distinguir, sem conhecer TEP, quais nomes viram node read-only e quais viram node writable.

## Sobre `Simulation` como builder — "Thread da planta" separada da "Thread do OPC-UA"

**Art. 11.1.** `Simulation` deixou de construir tudo na hora (`new(build) -> Result<Self, String>`) e virou um builder que só guarda definições até `run()` — a chamada terminal que de fato cria `StateRegistry`/modelo/`IoImage` e sobe a(s) thread(s). Motivo: `Simulation` (uma vez montada) sempre guarda algo enraizado em `Rc<RefCell<StateRegistry>>` — impossível de mover pra dentro de uma thread nova depois de já existir. A construção de verdade precisa acontecer *dentro* da thread que vai rodar o tick loop; por isso `set_model`/`add_sensor`/`add_actuator` só empacotam o que precisam num `Box<dyn FnOnce(...) + Send>` — o que a closure *produz* (o modelo, os `Sensor`) nunca precisa ser `Send`, porque nunca sai da thread que os criou.

**Art. 11.2.**
```rust
let mut simulation = Simulation::new();
simulation.set_model(TennesseeEastmanModel::new);
simulation.add_sensor("TEP/Reactor/Temperature", "reactor.temperature", Ideal);
simulation.set_adapter(AdapterConfig::OpcUa { endpoint: "opc.tcp://0.0.0.0:4840/tep/server/".into() });
simulation.run().expect("run encerrou com erro");
```
Quem chama nunca vê `StateRegistry`, `thread::spawn`, canal ou runtime tokio — tudo isso é interno a `run()`. `add_sensor` não devolve `Result` (a checagem "essa chave existe?" só pode acontecer depois que `run()` já criou o `StateRegistry`); se uma chave não existir, a "Thread da planta" entra em pânico na construção do `Sensor`, e isso vira `Err` em `run()` via o supervisor (Art. 11.10).

§1º (pendência aberta) `add_actuator(name, sink: impl CommandSink + Send + 'static)` funciona pra sinks que só capturam dados `Send` externos (ex.: um canal, um `Arc<AtomicXxx>`). Não funciona pra algo como `move |v| valve.set_command(v)`, porque `Valve` só existe *depois* que a `model_factory` roda dentro da "Thread da planta" — na hora que `add_actuator()` é chamado (antes de `run()`), a `Valve` em questão ainda nem foi construída. Hoje isso não trava nada porque nenhum atuador real (`Valve`/`Agitator`) está wireado em `TennesseeEastmanModel` ainda (Art. 2.6, §1º) — mas quando existir, vai precisar de um mecanismo "chave resolvida depois", simétrico ao que `add_sensor` já tem via `key: &str`, em vez de aceitar uma closure pronta.

**Art. 11.3.** `run(self) -> Result<(), String>` consome a `Simulation` por valor. Dentro de `std::thread::spawn`: cria `StateRegistry::shared()`, chama a `model_factory` guardada, `resolve()` (Art. 6.3), constrói cada `Sensor`/registra cada `CommandSink` na `IoImage` — só agora esses objetos existem de verdade. Loop: drena comandos pendentes → `model.evaluate()` + `registry.commit()` → publica cada sensor no `SnapshotBus` (Art. 11.4) → dorme `tick_interval`. Se `set_adapter()` foi chamado, uma segunda thread sobe (Art. 11.5).

**Art. 11.4.** `SnapshotBus` e `CommandQueue` são as duas únicas pontes thread-safe, sem dependência de tokio (só `std::sync`):
- **`SnapshotBus`** (`Arc<RwLock<HashMap<String, f64>>>`): a "Thread da planta" publica o valor de cada sensor a cada tick; qualquer leitor de fora só lê.
- **`CommandQueue`** (`Arc<Mutex<std::sync::mpsc::Sender<(String, f64)>>>`): sentido oposto — quem está fora empurra `(nome, valor)`; a planta drena no início de cada tick. O `Mutex` existe porque um write callback do OPC-UA exige `Fn(...) + Send + Sync` e `Sender` sozinho não é `Sync`.

Nenhum dos dois sabe o que é OPC-UA, TEP ou `StateRegistry`.

**Art. 11.5.** `opcua_adapter::serve(sensor_names, actuator_names, snapshot: SnapshotBus, commands: CommandQueue, endpoint)` não importa `Simulation`/`IoImage`/`StateRegistry` — só os nomes e as duas pontes do Art. 11.4. O loop de push lê `snapshot.read(name)` a cada tick; o `add_write_callback` de cada atuador só chama `commands.write(name, value)`. Como nada aqui é `!Send`, o loop de push roda em `tokio::spawn` comum. `run()` cria o runtime tokio só dentro da "Thread do OPC-UA" — o resto do processo nunca vê tokio.

**Art. 11.6.** `tep-plant/src/bin/tep_plant.rs`: `main()` é síncrono — sem `#[tokio::main]`, sem `async fn main()`, sem `.await`. `Simulation::run()` é a única coisa que cria um runtime, internamente. `Cargo.toml` do `tep-plant` não depende de `tokio` diretamente.

**Art. 11.8.** `DynamicModel` ganhou `sensors(&self) -> Vec<(String, String)>` (nome de exposição, chave do `StateRegistry`) — o próprio modelo declara o que expõe, não quem monta a `Simulation`. Método com corpo default vazio — só quem orquestra (`TennesseeEastmanModel`) sobrescreve. `Simulation::set_model()` chama `model.sensors()` enquanto o tipo ainda é concreto, antes de virar `Box<dyn DynamicModel>`. Dentro da "Thread da planta", esses sensores "do modelo" são fundidos com os que vieram de `add_sensor()` externo. Handshake (`std::sync::mpsc::channel::<Vec<String>>()`) garante que a "Thread do OPC-UA" só monta o address space depois que a "Thread da planta" terminou de registrar tudo na `IoImage`. Resultado em `tep_plant.rs`: o binário não menciona mais `"reactor.temperature"` nem `"TEP/Reactor/Temperature"` em lugar nenhum.

**Art. 11.9.** `tep-plant/src/initial_state.rs` (struct rígido, um campo Rust por chave do TOML, batendo posição a posição com `YY(1..50)` do `teprob.f`) foi apagado — substituído por `monjolo::snapshot::Snapshot`, genérico: carrega um TOML qualquer e achata as tabelas aninhadas em chaves com ponto (`[state.reactor_vapor] A = 1.0` vira `"state.reactor_vapor.A" -> 1.0`) num `HashMap<String, f64>`. `Snapshot::get(key) -> Option<f64>`; `Snapshot::from_pairs(&[(&str, f64)])` para teste. `Reactor::new(registry, initial: &Snapshot)` busca só as chaves que interessam pra ele, chave ausente vira `0.0`. `TennesseeEastmanModel::new(registry, initial: &Snapshot)` repassa o mesmo `&Snapshot` para os quatro subsistemas — ~~só `Reactor` usa por enquanto; `Separator`/`Stripper`/`Compressor` ainda nascem sem condição inicial~~ → os quatro consomem `Snapshot` hoje, 2026-07-12. `tep_plant.rs` carrega o `Snapshot` (`Snapshot::from_file("src/cases/te_exp3_snapshot.toml")`) e passa por uma closure a `set_model`, já que `TennesseeEastmanModel::new` deixou de caber como ponteiro de função direto (dois parâmetros).

**Art. 11.10.** `Simulation` é o lifecycle manager/supervisor: `run()` orquestra 0/1/2 serviços dependendo do que foi configurado — sobe a "Thread da planta" só se `set_model()` foi chamado, sobe a "Thread do adapter" só se `set_adapter()` foi chamado (`AdapterConfig`, `monjolo/src/adapter/mod.rs` — enum fechado, hoje só `OpcUa { endpoint: String }`), e devolve `Err` sem subir nada se nenhum dos dois foi configurado. Supervisor (`ServiceEvent`/`ServiceKind`, privados em `simulation.rs`): cada thread interna roda dentro de `std::panic::catch_unwind` e manda exatamente um `ServiceEvent` (`Stopped`/`Failed`/`Panicked`) por um canal de lifecycle antes de retornar. `run()` bloqueia em `events_rx.recv()`: o primeiro evento de qualquer serviço configurado já é motivo pra retornar — testado (`run_returns_err_instead_of_hanging_when_plant_panics`).

§1º (pendência aberta, deixada explícita de propósito) Não existe cancelamento cooperativo — nem a plant thread nem a thread do adapter checam um sinal de parada; quando uma morre, a outra (se houver) não é avisada, e `run()` só para de esperar por ela. Cabe a quem chamou `run()` decidir encerrar o processo. Shutdown gracioso de verdade fica como próximo passo.
