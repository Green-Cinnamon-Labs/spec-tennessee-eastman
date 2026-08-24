# Avaliação — Sensor/Actuator/Controller como fronteira explícita da planta

Contexto: retoma o que a Etapa 1 da Issue #56 ("Sensor e Actuator como entidades injetáveis") já
pedia, mas por um caminho bem diferente do previsto em `eval_kickoff.md` (injeção via construtor,
`NoisySensor`/`FirstOrderActuator`) — hoje isso existe via `#[sensor(...)]`/`#[actuator(...)]`/
`#[controller(...)]` (`monjolo-macros`) e catálogos dedicados em `StateRegistry`
(`offer_sensor`/`offer_actuator`/`offer_controller`, resolvidos pelo mesmo ciclo declare → register
→ resolve → inject de qualquer `need`). Este documento avalia, contra o código real hoje (branch
`feat/proc-macro-components`, `monjolo` + `tep-plant`), o quanto da leitura proposta — Sensor/
Actuator como pontos autorizados de observação/comando, Controller como componente executável que
depende obrigatoriamente deles — já é fato e o que falta pra fechar.

Para Sensor, a leitura já é literalmente verdade, não só por analogia. `sensor::model::Sensor::read()`
aplica um `SensorBehavior` (`Ideal`, identidade, hoje; `Noisy`, ruído gaussiano, já existe no
framework) sobre o valor bruto lido via `ReadProxy`, com cache por geração de `CurrentState` — a
cadeia "raw state → comportamento → valor observado" é código real, não um placeholder. O
`#[sensor(key = "...")]` que anota `CompressorPressure` (`tep-plant/src/sensors/compressor_pressure.rs`)
é só a porta declarativa: `new()` embrulha `sensor::model::Sensor::new(registry, key,
Box::new(Ideal))` e já cataloga sob a própria chave. Nada aqui precisa ser construído — o gap, se
houver, é de composição (nenhum sensor hoje usa `Noisy`, `docs/06-ruidos.md` fica em aberto), não de
arquitetura.

Actuator também bate com a leitura — comando → dinâmica física → estado é real: `command: Cell<f64>`,
`state`/`derivative: Proxy` publicados via `offer_actuator`, `evaluate()` chama a lei física uma vez
por tick e escreve a derivada, `state_keys()` garante que o RK4 avança esse estado. Mas a simetria
com Sensor quebra num ponto que vale registrar: `SensorBehavior` é um trait injetável — qualquer
sensor troca `Ideal` por `Noisy` sem tocar sua declaração. Actuator não tem equivalente hoje. Desde
a migração pra `#[actuator(...)]`, cada struct anotada (`FeedD`, etc.) escreve sua própria
`fn dynamics(&self) -> f64` à mão, inline — a lei física é parte do tipo, não um objeto trocável de
fora. Não é necessariamente um defeito (pode ser a escolha certa: a física de uma válvula não é
"comportamento de leitura" plugável, é a própria identidade do atuador), mas é uma assimetria real
na "fronteira" e vale uma decisão explícita registrada, não só implícita no código.

Achado concreto de documentação desatualizada: o comentário de topo de `monjolo/actuator/mod.rs`
ainda afirma "não há mais um tipo Rust por atuador físico... cada válvula é só uma instância de
`actuator::model::Actuator` com sua própria chave/lei" — descrição do desenho anterior à migração
pra macro (um único tipo genérico, N instâncias por closure). Hoje isso é falso: com
`#[actuator(...)]`, cada válvula volta a ser um tipo Rust próprio (`FeedD`, `FeedE`, ...), cada um
com seu `dynamics()` hand-written. `actuator::model::Actuator` (o tipo genérico por closure) parece
continuar existindo no crate, mas nenhum atuador concreto de `tep-plant` o usa mais — precisa
decisão: é caminho alternativo intencional pra quem não quiser a macro, ou código morto que devia
sair.

Controller bate exatamente com a metade "dependência obrigatória" da leitura, e falha exatamente
onde o usuário já havia apontado — mas vale nomear o motivo com precisão. `Controller::new()`/
`#[controller(name, sensors=[...], actuators=[...])]` força declarar nomes de Sensor/Actuator no
próprio construtor, resolvidos pelo mesmo ciclo de duas fases, catalogado via `offer_controller()`;
`sensor()`/`actuator()` devolvem os handles vivos. "Lê Sensors, escreve Actuators, nunca toca
`current_state` direto" já é garantido por construção, não por convenção. O que falta não é "ninguém
escreveu um PID ainda" — é que não existe hoje NENHUM ponto de extensão pra lei de controle.
`impl DynamicModel for Controller { fn evaluate(&self) {} }` é um único `impl` manual, deliberadamente
vazio, compartilhado por todo Controller (macro ou não) — ao contrário de Sensor
(`Box<dyn SensorBehavior>` injetado em `new()`) ou Actuator (`dynamics()` escrito à mão pelo usuário,
nunca tocado pela macro), `#[controller(...)]` não deixa nenhum método do usuário sobreviver à
expansão: a struct anotada é sempre `Fields::Unit`, sem corpo pra guardar lógica nenhuma.

Fechar esse gap exige desenhar um ponto de injeção por instância, no mesmo espírito dos dois outros
— duas formas candidatas, não mutuamente exclusivas: (a) espelhar Actuator — permitir
`#[controller(...)]` sobre uma struct com campos/métodos do usuário, e gerar um `fn step(&self)` (ou
nome equivalente) que a macro chama de dentro do `evaluate()` que hoje é vazio, lendo via
`self.sensor("nome").read()` e escrevendo via `self.actuator("nome").write(valor)`; (b) espelhar
Sensor — um `ControllerBehavior`/`ControlLaw` trait injetado em `Controller::new()`, com um método
tipo `fn compute(&self, sensors: &..., actuators: &...)`. A opção (a) é mais consistente com o
padrão que Actuator já estabeleceu (lei específica de instância, sem indireção extra); a opção (b)
mantém Controller mais perto de Sensor (comportamento como objeto trocável). De qualquer forma, isso
não decide sozinho a frequência/cadência de execução — hoje Controller ocupa a fase (C), avaliado
uma vez por tick igual a tudo mais, e `controller/mod.rs` já registra isso como item propositalmente
em aberto (sem `step()`/scheduler); um controle real pode ou não precisar de cadência diferente da
integração física, e essa pergunta continua sem resposta.

Um ponto lateral, mas que a leitura do usuário toca de raspão ao dizer "Controller... escrevendo
Actuators": pra isso funcionar de verdade, o `Actuator` que um `Controller` resolve via
`need_actuator()` precisa ser a MESMA instância `Rc` que está anexada à árvore de avaliação
(`Composite`) — não uma cópia. Pela leitura do código, `#[actuator(...)]`'s `new()` já garante isso
(`registry.offer_actuator(key, __instance.clone())` e o `ComponentDescriptor.construct` devolvem o
mesmo `Rc` pro `Composite`), então a propriedade parece já valer — mas não existe hoje nenhum teste
que prove isso ponta a ponta (construir via inventory, resolver por um Controller, chamar
`.write()`, e checar que o `command` da MESMA instância mudou). Vale escrever esse teste antes de
assumir a propriedade como garantida.

Punch list, em ordem prática: (1) escrever o teste de round-trip Controller→Actuator descrito acima,
pra confirmar (não presumir) que a mesma instância é compartilhada; (2) decidir e implementar o
ponto de extensão da lei de controle em Controller — esse é o item que efetivamente bloqueia
qualquer controlador real hoje, os outros dois já compilam e resolvem corretamente; (3) registrar
uma decisão explícita sobre a assimetria Sensor/Actuator (comportamento injetável vs. lei inline) —
mesmo que a decisão seja "está certo do jeito que está"; (4) corrigir o comentário desatualizado de
`actuator/mod.rs` e decidir o destino de `actuator::model::Actuator` (closure genérica) — mantém como
caminho alternativo documentado, ou remove; (5) só depois de (2) existir de verdade, decidir
cadência/scheduling de Controller — pergunta que não faz sentido responder em abstrato, sem um
controlador real pra testar contra. A maior parte do que a leitura do usuário descreve — a fronteira
Sensor/Actuator como pontos autorizados, catalogados e resolvidos pelo mesmo mecanismo,
indistinguíveis pra um consumidor interno ou um futuro adaptador externo — já é código real e
testado hoje; o que falta está concentrado quase inteiramente em Controller, não espalhado pelos
três.
