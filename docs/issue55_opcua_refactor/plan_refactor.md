# Plano de refatoração — Composite + Registry semântico (issue #55)

Este documento registra, em definições numeradas, todas as decisões de arquitetura fechadas na modelagem do novo `core` do `tep-plant`. É o plano a ser implementado — `eval_refactor.md` é a avaliação/histórico que levou até aqui.

## 1. Sobre o Contrato de Integração (Integrator ↔ DynamicModel)

### 1.1. Três fases

~~A relação entre o `Integrator` (RK4) e um `DynamicModel` acontece em três fases, cada uma um par chamada/resposta: construção (`get_state_template()` → `StateTemplate`), loop de integração (`evaluate()` → resultado da avaliação) e loop de evolução (`set_state()` → `StateRegistry`).~~

**Atualizado (seções 1.3, 2.7):** a fase de "construção" não existe mais como `get_state_template()`/`StateTemplate` — foi substituída pela inscrição (`subscribe`, seção 6.2) de cada `DynamicModel` direto no `StateRegistry`, que devolve `Proxy`s. A fase de "loop de evolução" não é mais `set_state()` do `DynamicModel` — é `StateRegistry.set_current_state()` (seção 1.3). Sobra só uma fase que continua sendo, de fato, um método do próprio `DynamicModel`: `evaluate()`, o loop de integração.

### 1.1.1. O RK4 nunca assume nada sobre o modelo além desse contrato

Não sabe quantos estados existem, não sabe como as derivadas são calculadas internamente, não sabe como o novo estado é persistido. Isso é responsabilidade do `DynamicModel`.

### 1.2. `evaluate()` não muta o `self` do componente

`evaluate()` é uma consulta pura — não muta o componente que a executa. ~~Mudar o estado interno só pode acontecer via `set_state(&mut self, ...)`.~~ **(desatualizado, ver correção abaixo)** Isso elimina de vez o problema do código antigo, em que `dynamics()` mutava campos como `self.mole_fractions`/`self.stream_temperatures` como efeito colateral, mesmo sendo chamado 4 vezes por passo do RK4 (k1..k4) — um bug silencioso de estados intermediários dessincronizados.

**Correção (pós seção 8):** com `EvaluationState`, `evaluate()` passou a ter, sim, efeito de mutação — escreve seus outputs (valores e derivadas) no buffer externo via `Proxy`, usando mutabilidade interior (`Cell`). A regra que vale é mais estreita do que "evaluate não muta nada": é "evaluate não muta o `self` do componente" — quem é mutado é o `EvaluationState` compartilhado, não o objeto que está calculando. Isso precisa ser revisto junto com a seção 1.3 (ver nota lá).

### 1.3. `StateRegistry` guarda dois repositórios: `CurrentState` e `EvaluationState`

~~`set_state()` tem corpo default no trait `DynamicModel`~~ — **resolvido, não é mais assim.** `set_state()` não é (e nunca foi de fato) um método por-componente que persiste um slice recebido. Ele é o nome do procedimento que carrega `EvaluationState` → `CurrentState`, e vive no `StateRegistry`, não no `DynamicModel`.

`StateRegistry` guarda dois repositórios internos:
- **`CurrentState`** — os Slots oficiais, o estado persistido/confirmado (o que antes chamávamos vagamente de "os Slots reais").
- **`EvaluationState`** — o buffer de trabalho de uma rodada de avaliação (seção 8), onde os `evaluate()` dos `DynamicModel`s escrevem via `Proxy`.

`set_current_state()` é o procedimento que carrega `EvaluationState` → `CurrentState` — o commit que fecha o "loop de evolução". É quem `Simulation` chama depois do `step()` (seção 9.8), não algo que cada `DynamicModel` implementa individualmente. Isso fecha a pendência que estava aberta aqui: não existe mais `set_state(&mut self, ...)` como método do `DynamicModel` — as seções 2.4/2.5 (que citavam `set_state` sendo delegado pelo composto) estão desatualizadas e precisam ser revisadas.

## 2. Sobre o Contrato de Composição (DynamicModel ↔ DynamicModel)

### 2.1. `CompositeDynamicModel` é supertrait de `DynamicModel`

`trait CompositeDynamicModel: DynamicModel` — em Rust não existe herança de classe, só herança de trait (supertrait). Implementar `CompositeDynamicModel` exige implementar `DynamicModel` também. Isso é o "extends" equivalente ao que se teria em uma linguagem orientada a objetos.

### 2.2. Só nós compostos implementam `CompositeDynamicModel`

Componentes-folha (`Valve`, `Agitator`, e futuramente Reactor/Separator/Stripper/Compressor, se virarem folhas de fato) não implementam esse trait — tentar compô-los vira erro de compilação, não erro de runtime.

### 2.3. `add_dynamic` (antes `add_component`) — ~~fundir StateTemplate~~ apenas ordena a avaliação

~~O nome mudou de `add_component` para `add_dynamic`. Seu trabalho real: pegar o `get_state_template()` do componente que está entrando e fundir os slots dele no `StateTemplate` acumulado do composto, no momento do registro — resolver a posição uma única vez, em vez de recomputar o layout inteiro toda vez que `get_state_template()` do composto for chamado depois.~~

**Correção:** essa ideia inteira (fundir `StateTemplate`/slots dentro do `add_dynamic`) está ultrapassada — quem declara slots agora é a inscrição direta de cada `DynamicModel` no `StateRegistry` (seção 6), não o composto. `add_dynamic` fica com um papel bem mais estreito: é só um método do `Composite` que adiciona o `evaluate()` do `DynamicModel` sendo registrado à sequência de avaliação do composto, na ordem em que foi inserido. Nada de nomes semânticos, nada de posição em vetor de estado — só ordem de chamada.

### 2.3.1. `add_dynamic` tem corpo default: só um `push`

Corpo do default: `self.models_mut().push(component)`. Não precisa mais de `template_mut()`/`StateTemplate` nenhum — só o getter `models_mut()` pro próprio `Vec<Box<dyn DynamicModel>>` (campo chamado `models`, não `children` — nome mais direto, já que são `DynamicModel`s, não uma árvore genérica).

### 2.4. `evaluate()` continua sendo a única coisa que cada composto escreve do zero

Delegar a avaliação a cada filho — chamando o `evaluate()` de cada um, na ordem em que `add_dynamic` os registrou — é a única parte que cada composto escreve do zero. `add_dynamic` (seção 2.3.1) é mecânico.

**Isso só funciona porque o TEP é um DAG (seção 4.1).** Uma única passada, em ordem fixa de inserção, resolve o composto exatamente porque não há ciclo algébrico entre os componentes — cada `evaluate()` já tem, quando é chamado, tudo que precisa dos que vieram antes. Para um caso DAE (seção 4.3, acoplamento algébrico com reciclo forte, rede hidráulica etc.), uma única passada não fecha: seria preciso um objeto novo, análogo ao `Integrator` mas para a dimensão algébrica em vez da temporal — um **`Interator`** — responsável por rodar o subconjunto cíclico de componentes repetidas vezes (Newton/tearing, seção 4.4) até o resíduo convergir, antes de considerar aquela rodada de avaliação como definitiva. Isso ainda não existe e não é necessário para o TEP atual — fica registrado como extensão futura, não como pendência de implementação imediata.

### 2.5. Não existe uma implementação genérica `Composite` reutilizável

Cogitou-se extrair um `struct Composite` genérico (contendo `children`/`sizes`) para qualquer nó composto reaproveitar. Rejeitado: no sistema inteiro só existe **um** nó composto de fato — `TennesseeEastmanModel`. Extrair uma abstração genérica para algo usado uma única vez é complicação desnecessária. `TennesseeEastmanModel` vai implementar `DynamicModel` + `CompositeDynamicModel` diretamente, dono do próprio `Vec<Box<dyn DynamicModel>>`.

### 2.6. `TennesseeEastmanModel::new()` é uma sequência de `self.add_dynamic(...)`

O construtor do TEP não deve conter lógica de composição própria — só uma lista de chamadas registrando cada componente (Reactor, Separator, Stripper, Compressor, Agitator, Valves), na ordem em que devem ser avaliados.

### 2.7. Resolvido: `get_state_template()`/`StateTemplate` não existem mais

Foram substituídos pela inscrição. Um `DynamicModel` se inscreve no `StateRegistry`, recebe `Proxy`s de volta, e opera com eles — não há mais um método que devolve um "layout" separado, nem um tipo `StateTemplate`. `DynamicModel` fica só com `evaluate()` (e o `subscribe`, que é o método especial de inscrição da seção 6.2.1) como métodos reais.

## 3. Sobre a relação com o mundo externo (Outside ↔ DynamicModel)

### 3.1. Nome da relação: `AcquisitionLayer`

Cogitado e rejeitado antes: "Process Image" (nome carregado de conotação de automação/PLC, considerado confuso) e "Process Image ↔ DynamicModel" como nome da relação. Fechado em `AcquisitionLayer ↔ DynamicModel`.

### 3.2. Papel: consulta, não avaliação

Algo externo (ex.: adapters 4-20mA, Modbus, OPC-UA) consulta o `DynamicModel` pai para obter o estado bruto e o transforma para um protocolo específico. É leitura pura, depois que o modelo já resolveu tudo — não participa do `evaluate()`.

### 3.3. Sensor não é um `DynamicModel` na árvore de composição

Sensor fica fora do `add_dynamic` porque não participa da avaliação — ele só lê o estado depois de resolvido, papel que cabe à relação `AcquisitionLayer`.

### 3.4. Disturbance não é um `DynamicModel` na árvore de composição

Disturbance fica fora por um motivo diferente: não é dono de um componente, atravessa vários ao mesmo tempo (reação no Reactor, UA do condensador e vazão nos Flows, coeficientes de troca no Heat). Não tem um único lugar na árvore onde caiba como filho — será tratado como entrada injetada, associada a cada componente que o consome.

### 3.5. Três objetos, único ponto de entrada/saída para o mundo externo

Quem escreve a dinâmica de uma planta em cima do `simulation-framework` (implementando `DynamicModel`/`evaluate()`) não se preocupa em expor dado nenhum — via de regra, a única preocupação dele é escrever a física corretamente. Existem exatamente três objetos que dão a essa lógica algum tipo de interação com o mundo externo, e só eles: **Sensor** (expõe um valor observado), **Atuador** (permite ação sobre a planta) e **Controlador** (permite fechar uma malha de controle sobre a planta). Fora desses três, não há outra porta de entrada/saída entre a dinâmica simulada e o mundo de fora — se o usuário do framework quer expor ou influenciar algo, é através de um desses objetos que ele faz isso, nunca mexendo direto na dinâmica.

### 3.5.1. Escopo fechado em Sensor, por ora

Atuador e Controlador ficam registrados aqui como parte do mesmo trio — já são papéis reconhecidos e nomeados — mas o design detalhado de cada um fica para depois. As seções 3.6 a 3.10 especificam só o `Sensor`.

### 3.6. Sensor não participa do `evaluate()` — opera sobre `CurrentState`

Sensor não tem nenhuma relação com `evaluate()`/`EvaluationState` (seção 8) — quem escreve ali são os `DynamicModel`s resolvendo sua própria física, a cada sub-passo do RK4. Sensor lê de `StateRegistry.CurrentState` (seção 1.3): o repositório já commitado, depois que `set_current_state()` fechou o passo. Isso é a versão concreta do que 3.2 já dizia ("leitura pura, depois que o modelo já resolveu tudo") — Sensor nunca é um participante da avaliação, só observa o que já está definitivo.

### 3.6.1. Sensor pode ter estado interno próprio — sem ser `DynamicModel`

Problemas como histerese/banda morta ou ruído não exigem dinâmica integrada: Sensor pode guardar estado mutável próprio (última leitura, gerador de ruído) atualizado como efeito colateral de cada leitura — uma função `(valor_bruto, estado_do_sensor) -> saída`. A diferença para um `DynamicModel` é que esse estado nunca entra no vetor que o `Integrator`/RK4 avança; não há `state_size()`/derivada, só memória local consultada a cada `read()`. Implementado como `trait SensorBehavior` (`simulation-framework/src/sensor/model.rs`), com `Ideal`, `Noisy` e `Hysteresis` como comportamentos plugáveis no `Sensor`.

### 3.6.2. Leitura concreta: `StateRegistry::read(key)` e `ReadProxy`

~~Implementado: `StateRegistry::read(&self, key: &str) -> Option<f64>` devolve o valor já commitado em `current_state`... Por ora é lookup por hash a cada leitura, aceitável porque Sensor não é lido a cada sub-passo do RK4... não implementado agora por ser otimização prematura sobre um ponto de acesso que ainda nem tem consumidor real.~~ **Superado:** o consumidor real chegou (o próprio `Sensor`) e o lookup por hash a cada leitura foi trocado por um handle resolvido-uma-vez. `current_state` deixou de ser `Vec<StateSlot>` e virou `Rc<RefCell<Vec<Cell<f64>>>>` — mesma forma de `evaluation_state`, mutado célula-a-célula por `commit()`, nunca substituído por inteiro (isso também eliminou uma alocação de `Vec` + clone de `String` por variável a cada passo, que o `commit()` antigo pagava). `StateRegistry::read_proxy(key) -> Option<ReadProxy>` resolve a chave uma vez contra esse buffer; `StateRegistry::read(key) -> Option<f64>` continua existindo, mas rebaixado a leitura pontual de debug/inspeção avulsa — não é mais o que `Sensor` usa.

### 3.6.3. `Sensor` só lê — garantido pelo tipo, não por disciplina

Sensor é, na prática, um pipe: observa uma chave, aplica um `SensorBehavior` (seção 3.6.1) e expõe o resultado — nunca escreve de volta no `StateRegistry`. ~~`Sensor` guarda um `RegistryView`... `RegistryView` só expõe `read()`~~ **Atualizado:** `Sensor` guarda um `ReadProxy` (seção 3.6.2), resolvido uma única vez em `Sensor::new()` — não guarda mais `RegistryView` depois de construído, e `read()` não faz mais lookup por string nenhum, só `self.proxy.get()`. `RegistryView` não desapareceu: continua a fachada somente-leitura sobre `Rc<RefCell<StateRegistry>>` (sem `subscribe()`/`resolve()`/`commit()`), mas seu papel principal virou ser a **fábrica** que produz o `ReadProxy` — `RegistryView::read_proxy(key)` — usada uma única vez, na construção do Sensor, não a cada leitura. `Sensor::new()` continua recebendo o `Rc<RefCell<StateRegistry>>` normal por fora; a conversão pra `RegistryView`/`ReadProxy` é interna.

### 3.6.4. `ReadProxy` é um tipo à parte de `Proxy` — não pode ser confundido com valor hipotético

`Proxy` endereça `EvaluationState`, que pode conter valor hipotético de um solver iterativo em andamento (seção 7.2). `ReadProxy` só existe sobre `CurrentState` — sempre o último valor confirmado. São dois `struct`s distintos (mesma forma: buffer + índice), de propósito: se fosse o mesmo tipo pros dois buffers, nada impediria alguém entregar por engano ao `Sensor` um `Proxy` resolvido contra `EvaluationState`, e o `Sensor` passaria a ler valor intermediário sem ninguém perceber — mesmo tipo, mesmo `get()`, compila igual. Com tipos separados isso não compila. Diferente de `Proxy`, `ReadProxy` nasce já resolvido (não tem fase `unresolved`/`usize::MAX`): só é criado depois que `resolve()` geral já rodou (seção 3.8) e a chave, portanto, já existe — e não tem `set()`, porque quem lê `CurrentState` nunca deveria escrever nele por fora do `commit()` do `StateRegistry`.

### 3.6.5. `StateSlot` deixou de ser o armazenamento principal

Com `current_state` virando `Rc<RefCell<Vec<Cell<f64>>>>`, `StateSlot{key, value}` não guarda mais o estado corrente — é reconstruído sob demanda por `StateRegistry::snapshot() -> Vec<StateSlot>`, zipando `index` (a fonte de verdade operacional pra `key -> posição`) com o buffer atual. Serve só pra metadado/catálogo: inspeção, debug, listagem de sinais, exportação nomeada — nunca o caminho por onde `Proxy`/`ReadProxy` leem ou escrevem. Resolver uma chave em tempo real é sempre trabalho do `index: HashMap<String, usize>`, nunca de vasculhar um `Vec<StateSlot>`.

### 3.7. Sensor acompanha exatamente uma variável

Um `Sensor` não agrega várias variáveis de uma vez — não existe "sensor composto" nessa camada. Se o usuário quer acompanhar os valores de A, B e C, ele declara três sensores, um por variável. Cada `Sensor` aponta para uma única chave do `StateRegistry`.

### 3.7.1. Sensor é agnóstico ao tipo físico do sinal

Não existe `FI`/`PI`/`LI`/`TI`/`AI` como tipos distintos — essa tentativa existiu no código de `simulation-framework` (um struct por grandeza física, todos com o mesmo corpo) e foi abandonada. Sensor não sabe se está lendo vazão, pressão, temperatura ou nível — isso é metadado de quem declara o sensor (tag/unidade/faixa, ver `eval_naming_standard.md`), não parte do tipo do objeto. O que varia entre sensores é o **comportamento** de leitura (seção 3.6.1: ideal, com ruído, com histerese), plugável via `SensorBehavior`, não a grandeza física medida.

### 3.8. Onde o Sensor é declarado

A declaração é explícita e feita por quem monta a planta/simulação — nunca automática ou implícita na dinâmica em si. ~~Ainda em aberto exatamente em qual altura... Pendência de design — as duas opções fecham igualmente bem com o resto do modelo.~~ **Resolvido:** `Sensor` só pode ser construído depois que todo `DynamicModel` já chamou `subscribe()` e `StateRegistry::resolve()` geral já rodou (seção 9.2) — nunca junto dos `add_dynamic` na implementação principal. Motivo prático, não só estético: `Sensor::new()` resolve a chave contra `CurrentState` uma única vez, na hora (seção 3.6.2/3.6.4), sem segunda fase de resolução como `Proxy::unresolved` tem para `needs` — se a chave ainda não existir em `index` nesse momento, é erro (`Result<Self, String>`), não um estado que se resolve depois. Isso empurra a declaração de Sensores pra depois do `resolve()`, o que combina melhor com a instanciação de `Simulation` (seção 9) do que com o construtor do modelo composto.

### 3.9. Exposição para fora do processo ainda em aberto

~~Declarar um `Sensor` sobre uma chave equivale a registrar um observer/subscriber que acompanha as mudanças daquele `Proxy` dentro de `CurrentState`...~~ **Corrigido (seção 3.6.2/3.6.4):** o mecanismo real é `ReadProxy`, resolvido uma vez contra `current_state` (agora `Rc<RefCell<Vec<Cell<f64>>>>`), tipo distinto de `Proxy`. O que ainda não está fechado é como o valor lido por um `Sensor` sai de fato do processo: que forma toma — porta, registrador, canal, arquivo, socket — é decisão de design em aberto, não uma pendência de implementação já especificada.

**Esclarecido:** o servidor OPC-UA não vai rodar dentro do processo da simulação — vai consumir a simulação de outra máquina/container por alguma interface de rede ainda a desenhar (gRPC, HTTP, WebSocket, stream, snapshot API...). Por isso a base `Rc<RefCell<_>>`/`Cell` de `StateRegistry`/`Proxy`/`ReadProxy` — que é estritamente single-thread, nem `Send` nem `Sync` — não é um problema para o OPC-UA em si; é só uma decisão interna de como o processo da simulação organiza sua própria memória. O ponto de atenção fica deslocado: não é mais "o Sensor precisa ser thread-safe", é "o que quer que sirva a interface de rede (a próxima camada a desenhar) precisa rodar dentro do mesmo processo/thread que já fala `Rc<RefCell<StateRegistry>>`, e serializar/expor os valores lidos pelos Sensores pra fora dali" — a fronteira thread-safe, se houver, é entre esse serviço local e a rede, não dentro do `simulation-framework`. Fica registrado aqui como o próximo ponto a resolver antes de qualquer gateway poder ser construído em cima disso.

## 4. Sobre a viabilidade da arquitetura (DAG vs. DAE)

### 4.1. TEP hoje é um DAG (grafo acíclico dirigido)

As dependências entre Reactor → Separator → Stripper/Compressor → Flows → Heat/Measurements → derivadas formam um grafo acíclico. Uma ordem fixa (`EvaluationPlan`) é suficiente — não há equação implícita circular no código atual.

### 4.2. Reciclo físico não implica ciclo algébrico

O TEP tem reciclo físico (saída do compressor volta ao reator), mas vazões e composições são calculadas usando estados já conhecidos, em ordem causal explícita. O problema algébrico só apareceria se a variável `A(t)` de um bloco precisasse simultaneamente de `B(t)` de outro *e* `B(t)` precisasse de `A(t)`.

### 4.3. Quando um DAG simples quebra

Plantas mais gerais com equilíbrio de rede hidráulica, flash acoplado, reciclo forte ou relação pressão-vazão implícita (ex.: `F = Cv·√(PA-PB)`, com `PA`/`PB` dependendo de `F` no mesmo instante) formam um ciclo algébrico. Vira uma DAE (`0 = g(y, z, t)`), não resolvível por uma sequência linear.

### 4.4. Como um solver iterativo resolve o ciclo

Chuta um valor para a variável que fecha o ciclo, avalia o resto do grafo como DAG a partir desse palpite, mede o resíduo, ajusta e repete até convergir — transforma o ciclo em um problema de ponto fixo.

### 4.4.1. Newton

Usa o Jacobiano do resíduo para escolher a direção de correção, convergindo em muito menos iterações que substituição sucessiva.

### 4.4.2. Tearing

Isola deliberadamente a(s) variável(is) que fecham o ciclo e itera só sobre elas, reavaliando o resto como DAG a cada tentativa — reduz drasticamente o tamanho do sistema iterado, em vez de resolver tudo de uma vez.

### 4.5. Conclusão de viabilidade

Válido para o escopo atual do TEP (DAG simples). Não é a arquitetura universal para simulação de plantas em geral — plantas com acoplamento algébrico forte exigiriam um solver iterativo embutido dentro da fase de avaliação, mantendo o RK4 só para o avanço no tempo.

## 5. Sobre `StateSlot` e a malha de nomes semânticos

### 5.1. Estrutura final: `key: String` + `value: f64`

Sem campo `index`. A posição de um slot dentro do `Vec` que o contém É o seu índice — não é redeclarada dentro do slot.

### 5.1.1. Por que `index` foi removido

Guardar `index` dentro do próprio slot cria uma invariante que ninguém garante (`slots[3].index == 4`) e que pode divergir silenciosamente se alguém filtrar, reordenar ou fundir slots durante a composição. Redundante e perigoso — mesma crítica válida tanto para `StateRegistry` (onde a posição já é, por definição, o índice usado em todo o resto do sistema, hoje resolvido via `Proxy`, seção 7) quanto para valores algébricos avulsos (onde a posição nem tem significado próprio).

### 5.2. Invariante: append-only

Essas listas só crescem. Uma vez que um slot é registrado, sua posição nunca muda nem é reaproveitada. Essa é a invariante central que torna seguro resolver um nome uma única vez e confiar na posição para sempre.

### 5.3. Resolver uma vez, cachear, acessar por posição depois

Um componente que depende de um valor semântico de outro (ex.: Separator precisando de `reactor.temperature`) resolve essa string contra a lista de slots **uma única vez**, no momento da construção/composição — não a cada `evaluate()`. Guarda o `usize` resultante como campo próprio. Daí em diante, acesso é O(1) por posição, sem comparação de string.

### 5.4. `EvaluationResult` (tipo intermediário, depois obsoleto — ver seção 8.4)

Chegou a existir como `{ derivatives: Vec<f64>, values: Vec<StateSlot> }`, devolvido por `evaluate()`. Superado pelo `EvaluationState`/`Proxy` (seção 8) — `evaluate()` deixou de retornar qualquer coisa.

## 6. Sobre o `StateRegistry` como singleton de inscrição

### 6.1. Papel: registro central, não snapshot por chamada

`StateRegistry` deixou de ser só "o que `set_state()` devolve" (papel que tinha na seção 1) e passou a ser também um serviço singleton de inscrição/resolução, usado na construção — não durante o loop de simulação. Todo `DynamicModel` se reporta a um e somente um `StateRegistry`, mesmo que não faça parte de uma composição.

### 6.2. Inscrição (subscribe)

Um `DynamicModel`, na sua construção, se inscreve no `StateRegistry`: reserva espaço para os próprios slots (outputs), declarando a semântica deles, e declara quais inputs (chaves de outros componentes) precisa.

### 6.2.1. `subscribe` é um método especial, separado de `add_dynamic`

`add_dynamic` (seção 2.3) serve só para fins estruturais do `Integrator`/composição — fatiar o vetor de estado entre filhos. A inscrição no `StateRegistry` é um passo separado. Na inicialização, primeiro os `DynamicModel`s precisam ser inscritos, e só depois avaliados — sem a inscrição resolvida, eles não têm os índices necessários para rodar seus próprios `evaluate()`.

### 6.3. Resolução em duas fases

Não é necessário respeitar ordem na inscrição — todo mundo se inscreve primeiro. Só depois disso tem um passo explícito (`resolve()`), rodado uma única vez, que resolve o índice de cada slot e de cada input declarado.

### 6.4. Validação

Se um input declarado não tiver provedor correspondente durante a resolução → erro, uma exceção sobe. Se um slot (output) oferecido nunca for consumido por ninguém → sem problema, nada a validar nessa direção. A única coisa avaliada é se os inputs solicitados foram todos mapeados.

### 6.5. Mecanismo de auto-inscrição independente da construção do TEP

Pendência de design, ainda não implementada: a inscrição não deveria depender de alguém lembrar de chamar `subscribe()`/`add_dynamic()` explicitamente dentro de `TennesseeEastmanModel::new()`. Em Python, isso era resolvido com efeito colateral de inicialização de arquivo (código de módulo rodando no import). Em Rust, por ser compilado, a ideia é usar a própria etapa de compilação para pré-gerar/registrar isso, de forma que no início da execução já esteja correto — sem depender de uma sequência imperativa de chamadas para "lembrar" de inscrever cada tipo. (Mecanismo concreto ainda em aberto — candidatos naturais em Rust: registro distribuído via linker section, no estilo dos crates `inventory`/`linkme`, ou `ctor` para rodar código antes de `main()`.)

## 7. Sobre `Proxy`

### 7.1. O que é

Um handle compartilhado entre um `DynamicModel` e o `StateRegistry`, do tipo "resolvido uma vez, usado para sempre" (na prática, algo como `Rc<Cell<usize>>`). Nasce sem resolução; o `StateRegistry`, durante `resolve()`, escreve o índice real nele. Dali em diante, todo clone desse `Proxy` — inclusive o que o componente guardou desde a inscrição — enxerga o índice resolvido, sem precisar achar de novo.

### 7.2. Agnóstico a valor "hipotético" ou "real"

O `Proxy` só endereça uma posição — o que existe *dentro* dessa posição (um chute intermediário de um solver iterativo/Newton, ou um valor já convergido) é problema de outra camada. Isso é relevante para o cenário da seção 4 (DAG vs. DAE): o mecanismo de endereçamento não muda entre avaliação direta e avaliação iterativa.

## 8. Sobre `EvaluationState`

### 8.1. Cópia inicializada a partir do `StateRegistry` resolvido

Mesmo tamanho, mesmos índices do `StateRegistry` já resolvido. É o buffer de trabalho de uma rodada de avaliação — carrega os valores reais durante a simulação.

### 8.2. Mutabilidade interior

Como `evaluate()` continua `&self` (seção 1.2), mas precisa escrever nos próprios outputs, `EvaluationState` precisa de mutabilidade interior (ex.: `Vec<Cell<f64>>`). Quem muta é o buffer externo, não o `self` do componente — a regra "evaluate não muta o próprio componente" continua de pé.

### 8.3. Derivadas também são slots endereçados por `Proxy`

Não existe mais um `Vec<f64>` cru e separado só para derivadas. Cada slot de estado ganha, além do seu valor, uma chave própria para sua derivada (ex.: `"Separator.temperature.derivative"`), resolvida junto no `subscribe()`. Isso unifica derivadas e valores algébricos sob o mesmo mecanismo de endereçamento — a preocupação original de performance (evitar busca por string a cada passo) continua garantida, porque a resolução também acontece uma única vez, não porque as derivadas são estruturalmente diferentes de tudo o mais.

### 8.4. `EvaluationResult` foi eliminado

`evaluate()` não retorna mais nada. Ele só escreve dentro do `EvaluationState`, usando os `Proxy`s de output que já tem guardados desde a inscrição. Ler inputs funciona da mesma forma, via `Proxy`s de input.

## 9. Sobre `Simulation` (novo objeto de orquestração)

### 9.1. Responsabilidade

Objeto de alto nível que instancia o TEP (`TennesseeEastmanModel`) e o `Integrator` (RK4). É quem sabe o que precisa passar para o integrador — nem o TEP nem o `Integrator` sabem disso sozinhos.

### 9.2. Fecha a fase de inscrição

Depois que o TEP (e todos os `DynamicModel`s que ele registrou via `add_dynamic`) já rodaram seu `subscribe()` no `StateRegistry`, `Simulation` chama `registry.resolve()` uma única vez.

### 9.3. Resolve a lista de `Proxy`s das derivadas, por nome

`Simulation` passa uma lista de nomes (ex.: `["Reactor.A.derivative", "Separator.temperature.derivative", ...]`) para o `StateRegistry`, que devolve o vetor de `Proxy`s correspondente — resolvido uma única vez, guardado, na mesma ordem do vetor de estado que o `Integrator` usa.

### 9.4. O `Integrator` continua recebendo um `state: Vec<f64>` cru

O RK4 não muda sua relação com o vetor de estado — continua um algoritmo numérico que só soma vetores, sem saber nada sobre `Proxy`, `EvaluationState` ou `StateRegistry`.

### 9.5. `Integrator::step()` muda de assinatura

Deixa de receber `model: &mut dyn DynamicModel` e passa a receber uma closure/callback, fornecida por `Simulation`, que o `Integrator` chama internamente a cada sub-etapa (k1..k4) no lugar de `model.dynamics(estado_perturbado)`.

### 9.6. O que a closure faz

Escreve o estado perturbado (`s2`, `s3`, `s4` do RK4) no `EvaluationState`, via os `Proxy`s dos próprios slots de estado, e dispara o `evaluate()` de toda a árvore de `DynamicModel`s — que lê inputs e escreve outputs/derivadas no `EvaluationState`, tudo via `Proxy`.

### 9.7. A closure atua só no subconjunto das derivadas

Não é que ela extrai e devolve uma cópia isolada do subconjunto — ela opera diretamente sobre esse subconjunto (os `Proxy`s resolvidos na seção 9.3) para alimentar a matemática do RK4.

### 9.8. Depois do `step()`, `Simulation` grava o `EvaluationState` inteiro nos slots reais

Não só o subconjunto de derivadas que o `Integrator` operou — o `EvaluationState` inteiro, incluindo todos os valores algébricos que os `DynamicModel`s calcularam como efeito colateral durante a última avaliação daquele passo. Por tabela, informações que nem o `Integrator` nem o `Simulation` precisaram olhar (ex.: `reactor.temperature`) ficam corretas e disponíveis para quem quer que precise delas depois (ex.: a `AcquisitionLayer` da seção 3) — sem custo extra de computação, porque já foram calculadas durante o `evaluate()`.

## 10. Sobre a I/O Image — fronteira externa mínima

### 10.1. O que é: um catálogo central de sinais nomeados

Implementado em `simulation-framework/src/io_image.rs`, struct `IoImage`. É o lugar único onde `Sensor`s (leitura) e comandos de `Atuador` (escrita) ficam disponíveis por nome — análogo a uma imagem de I/O/tabela de tags/registradores numa planta real. Convenção de nome (não imposta pelo tipo): `sensors/<algo>` pra leitura, `actuators/<algo>` pra escrita — ex.: `sensors/reactor.temperature`, `actuators/cooling_water.command`.

### 10.2. Separado de `DynamicModel`, RK4, `StateRegistry` e avaliação hipotética

`io_image.rs` não importa `state_registry` — só conhece `Sensor` (seção 3) como tipo de leitura, e um trait `CommandSink` próprio como tipo de escrita. Quem já resolveu a chave contra o `StateRegistry` (construindo o `Sensor`, seção 3.8) entrega o `Sensor` pronto pra `IoImage.publish_sensor()`; `IoImage` nunca soube nem precisa saber que `StateRegistry`/`Proxy`/`ReadProxy`/`EvaluationState` existem.

### 10.3. Leitura: `IoImage.publish_sensor(name, sensor)` / `IoImage.read(name)`

`IoImage` guarda um `HashMap<String, Sensor>` — publicar é só inserir um `Sensor` já construído sob um nome. `read(name)` chama `Sensor::read()` por trás (mesmo comportamento plugável — ideal/ruído/histerese — da seção 3.6.1), devolvendo `None` se o nome não existir.

### 10.4. Escrita: `CommandSink`, um trait de propósito, não acoplado a `Valve`/`Agitator`

```rust
pub trait CommandSink {
    fn write(&mut self, value: f64);
}
```

Qualquer `FnMut(f64)` implementa `CommandSink` de graça (impl genérica sobre closures) — então `Valve::set_command`/`Agitator::set_command` (que são métodos inerentes concretos, não um trait; seção 2.2 já não os torna `DynamicModel` do tipo composto) viram sinal de escrita só por fechamento: `io.register_actuator("actuators/cooling_water.command", move |v| valve.set_command(v))`. `IoImage` nunca precisa conhecer `Valve` como tipo — só o `CommandSink` por trás.

### 10.5. Controlador ainda não modelado — mesma interface, sem mudança de forma

Controlador (seção 3.5) não tem implementação ainda. Quando existir, o desenho já previsto é: ele lê sinais via `IoImage.read()` (os mesmos `sensors/...` que qualquer outro consumidor leria) e escreve via `IoImage.write()` (nos mesmos `actuators/...`) — sem exigir nenhuma mudança na forma de `IoImage`. Se um Controlador quiser publicar sua própria saída como sinal observável (`controllers/reactor_temp.output`), o caminho natural é ele também virar, do lado de escrita, o mesmo `CommandSink` por closure — não foi implementado porque não há Controlador ainda pra testar contra.

### 10.6. ~~Único adaptador hoje: em memória, dentro do processo~~

~~`IoImage` é, ela mesma, o "adaptador tosco" pedido... Adaptadores futuros (OPC-UA, Modbus/register-map, HTTP/gRPC, WebSocket/stream) consumiriam essa mesma interface por fora... nenhum desses existe ainda.~~ **Superado — o primeiro adaptador de rede existe:** `simulation-framework/src/opcua_adapter.rs` (`pub async fn serve(simulation: Simulation, endpoint: &str)`), atrás da feature `opcua` (puxa `async-opcua` + `tokio` — pesados demais pra serem dependência default do framework). Sobe um servidor OPC-UA de verdade: um node read-only por `io.sensor_names()`, atualizado por push (`node_manager.set_values()`) a cada tick, depois de cada `Simulation::run()` — nunca por `add_read_callback`, porque o valor já está pronto, não precisa ser computado sob demanda pela árvore de conexão do servidor.

### 10.6.1. A fronteira real ficou como o usuário desenhou: framework expõe, TEP declara

`opcua_adapter::serve()` não conhece TEP — só itera `simulation.io().sensor_names()`/`actuator_names()`, nomes que já foram declarados por fora. Quem declara é `tep-plant/tennesseeEastman-process/examples/opcua_server.rs`: chama `simulation.add_sensor("TEP/Reactor/Temperature", "reactor.temperature", Box::new(Ideal))` (etc.) e só então `opcua_adapter::serve(simulation, "opc.tcp://0.0.0.0:4840/tep/server/")`. O nome OPC-UA (`"TEP/Reactor/Temperature"`) e a chave do `StateRegistry` (`"reactor.temperature"`) são decisão exclusiva de quem monta a `Simulation` — o adaptador só vê o primeiro.

### 10.6.2. Atuadores: node writable de verdade, com escrita chegando na simulação — via canal, não callback direto

Diferente do que a seção 10.4 previa como hipótese ("não foi implementado porque não há Controlador ainda pra testar contra"), atuadores já têm um caminho de escrita completo: `SimpleNodeManager::add_write_callback` exige `Fn(...) + Send + Sync + 'static`, e `Simulation`/`IoImage`/`StateRegistry` são deliberadamente `Rc<RefCell<_>>` (seção 3.9) — não-Send. O callback registrado não toca em `Simulation` direto: só empurra `(nome, valor)` num `tokio::sync::mpsc::UnboundedSender` (esse sim `Send + Sync`, mesmo sem nada do outro lado ser thread-safe). O `Receiver` fica dentro do mesmo loop de tick que já chama `simulation.run()`, e drena os comandos pendentes (`simulation.io().write(name, value)`) antes de cada passo. Resolve exatamente a pendência que a seção 3.9 tinha deixado em aberto pra escrita — sem precisar tornar `StateRegistry`/`Sensor` thread-safe.

### 10.6.3. Threading: `current_thread` + `LocalSet`/`spawn_local`, não `tokio::spawn`

Como `Simulation` não é `Send`, o loop de tick que chama `simulation.run()`/`simulation.io()` roda via `tokio::task::spawn_local` dentro de um `LocalSet`, nunca `tokio::spawn` (que exige `Send`). O runtime é `#[tokio::main(flavor = "current_thread")]`. Isso não limita o servidor OPC-UA em si — ele é internamente `Arc`/`RwLock` (`Send + Sync`) e funciona igual num runtime `current_thread`; a restrição é só sobre onde o *nosso* código (não-Send) pode rodar. Confirma a leitura da seção 3.9: o servidor OPC-UA agora roda dentro do mesmo processo/thread que fala `Rc<RefCell<StateRegistry>>`, exatamente como esclarecido lá.

### 10.6.4. `IoImage` ganhou `sensor_names()`/`actuator_names()`

Necessário pro adaptador genérico distinguir, sem conhecer TEP, quais nomes viram node read-only e quais viram node writable — `signals()` (seção 10.3) só devolve a lista combinada, insuficiente pra decidir o `access_level` de cada node.

### 10.7. Não fecha a discussão fina de `Sensor::read()`/notificação

Esta seção resolve a fronteira de catálogo/nome e agora também um transporte de rede real — quem publica o quê, sob qual nome, lido/escrito como, e como isso chega a um cliente OPC-UA externo. Não decide (segue em aberto) se `IoImage.read()` deveria virar push/observer em vez de pull dentro do processo, nem se `commit()` deveria notificar assinantes — o adaptador contorna isso com um `interval` de 500ms que simplesmente lê tudo de novo a cada tick, não com um mecanismo de notificação de verdade.
