# Plano — Planta como função para otimização (issue #91)

## Contexto

O objetivo é viabilizar otimização sobre o código da planta: expor o modelo como uma interface que qualquer um pode chamar para otimizar do jeito que quiser. Reproduzir Ricker (1995) é o primeiro marco, porque prova que a interface basta para um problema real e conhecido.

O trabalho é um ramo paralelo ao TCC, que está fechado. Ele acontece nas branches `feat/steady-state-optimization` de `monjolo` e `tep-plant`, e no repositório `tep-optimizer`. Nada vai para o `main`.

Dois problemas da planta de hoje precisam ser resolvidos:

- **Não há como chamar o modelo de fora.** O OPC-UA só mostra as 41 medições e as 12 válvulas da planta rodando; estados e derivadas não aparecem.
- **O resfriamento está congelado (#90).** Sem as duas equações da água de resfriamento, a temperatura do reator não é uma escolha. No ótimo de Ricker para o Modo 1 a água do reator sai a 102,4 °C, contra 94,6 °C no caso base.

## Decisões

- **A interface é o StateRegistry.** Estado, derivada, medição, posição de válvula e liga/desliga de distúrbio já são chaves dele. A função é: escrever chaves, avaliar o modelo, ler chaves.
- **A função precisa ser pura, e isso é testado, não suposto.** O resultado de um ponto não pode depender dos pontos avaliados antes. O teste de memória das etapas 2, 3 e 4 é condição para seguir adiante.
- **Os controladores ficam de fora da função, por enquanto.** Quem chama escreve as 12 posições de válvula direto, como no artigo. Setpoints como entrada ficam anotados na #91 para depois.
- **Primeiro validar, depois expor.** A função é testada dentro do Rust, no caso base, antes de existir qualquer serviço.
- **O serviço é HTTP e mínimo.** Sem Docker e sem tep-lab nesta fase.
- **O custo vem da equação 3 do artigo**, escrita no otimizador.
- **Issues antigas não entram no plano.** Onde este trabalho ajuda, deixo um comentário na issue e você avalia depois.

## O que o artigo define

Conferido no PDF (`tep-monografia/referencial/articles/art15_...Ricker.pdf`):

- **Variáveis:** os 50 estados. As válvulas não são variáveis à parte porque, em regime, a posição é igual ao comando.
- **Igualdades (42):** as 38 primeiras derivadas iguais a zero; nível do separador e do stripper em 50 %; produção de G e de H nos valores do modo.
- **Desigualdades (2):** pressão do reator ≤ 2800 kPa; nível do reator ≥ 65 %.
- **Graus de liberdade:** 50 − 42 = 8.
- **Agitador fixo em 100 %.** É uma escolha do autor, não um resultado econômico: em regime a velocidade do agitador é arbitrária enquanto a água do reator não estiver no limite (seção 3.7).
- **Limites:** válvulas entre 0 e 100 %. O autor apertou para 1 ou 99 % só nas variáveis em que o solver teve problema numérico (reciclo, vapor e água do condensador).
- **Escala:** os 38 primeiros estados valem 1 no ponto de partida; as válvulas são divididas por 100.
- **Solver:** MINOS 5.1, com gradientes numéricos, partindo do caso base.
- **Resultado do Modo 1:** 114,31 $/h, contra 170,61 $/h no caso base. As Tabelas 2, 3 e 4 trazem medições, válvulas e custos dos seis modos.
- **Mínimos locais existem.** A seção 3.3 mostra duas estratégias de operação bem diferentes com custo quase igual (118,49 e 118,15 $/h), e o solver pode cair em qualquer uma conforme o ponto de partida.
- **Modos 4 a 6** (produção máxima) são resolvidos em dois passos, e o autor relata convergência difícil.

## Visão geral

| Etapa | Repositório | Entrega | Depende de |
|---|---|---|---|
| 0 | spec | Documento salvo, #91 atualizada, comentários nas issues | — |
| 1 | tep-plant | Resfriamento como no original (#90) | 0 |
| 2 | monjolo | Avaliar o modelo num ponto, sem rede | 0 |
| 3 | tep-plant | Função validada no caso base, sem rede | 1, 2 |
| 4 | monjolo, tep-plant | StateRegistry exposto por HTTP | 3 |
| 5 | tep-optimizer | Projeto Python, cliente e modelo de teste | 0 |
| 6 | tep-optimizer | **Marco 1:** Modo 1 de Ricker | 4, 5 |
| 7 | tep-optimizer, tep-lab, spec | **Marco 2:** seis modos e registro | 6 |

As etapas 1, 2 e 5 não dependem umas das outras.

## Etapas

### 0. Especificação

- Salvar este documento em `spec-tennessee-eastman/docs/issue91_steady_state_optimization/atividades.md`.
- Atualizar a #91: o objetivo passa a ser a interface, com Ricker como marco; os controladores ficam de fora por enquanto.
- Criar as sub-issues da #91, uma por etapa, com o prefixo `[repositório]`.
- Deixar um comentário curto nas issues em que este trabalho ajuda, sem mudar o estado delas:

| Issue | O que este trabalho traz |
|---|---|
| #2 | O ponto de equilíbrio sai da etapa 6, calculado pelo otimizador |
| #3 | O Jacobiano por diferenças finitas sai da etapa 5 |
| #4 | Com o Jacobiano no equilíbrio, a estabilidade é o cálculo dos autovalores |
| #5 | Varrer um parâmetro vira repetir a chamada da função |
| #19 | A etapa 3 compara a planta com o caso base publicado |
| #89 | A etapa 6 diz se existe ponto de regime perto do caso base |

### 1. tep-plant — resfriamento como no original (#90)

- Trocar `docs/fortran-original/teprob.f` pelo arquivo intacto. A cópia atual fica com outro nome e um aviso de que está truncada.
- `src/units/reactor.rs`: a temperatura da água vira estado, com valor inicial em `state.cooling.reactor_water_temp` (a chave já existe no `application.toml`). A derivada é `(FWR*500.53*(TCWR-TWR) - QUR*1e6/1.8)/HWR`, com `FWR = posição da XMV 10 × 1000/100`, `HWR = 7060` e `TCWR = 35`.
- `src/units/separator.rs`: o mesmo para a água do condensador, com `FWS = posição da XMV 11 × 1200/100`, `HWS = 11138` e `TCWS = 40`.
- Corrigir `docs/12-reator.md` e `docs/13-separador.md`, que dizem "fiel ao FORTRAN".

Fica de fora: implementar os distúrbios que dependem do resfriamento.

Dois avisos:
- Nesta branch a planta rodando em tempo real pode ficar instável, porque não há controlador de temperatura. Isso não afeta a otimização, que não roda a planta no tempo.
- Os testes de trajetória em `src/lib.rs` comparam com a planta de resfriamento congelado. Se falharem, ficam marcados como ignorados nesta branch, com uma nota.

Como verificar: testes de unidade no padrão de `tests/units/`, conferindo as duas derivadas novas contra a conta feita à mão no caso base.

### 2. monjolo — avaliar o modelo num ponto

Novo módulo `monjolo/model_function.rs`, com um tipo que monta o modelo e o avalia fora do laço de simulação.

- **Montagem:** reaproveita `attach_discovered_components` (`component.rs:135`), com uma opção para não anexar os controladores nem os sensores. As medições são lidas direto das chaves `xmeas.*`, que não têm ruído; o ruído só existe dentro dos sensores.
- **Lista de chaves:** o `StateRegistry` ganha um método que devolve todas as chaves. O tipo novo pede um `Proxy` para cada uma e marca quais são estados integráveis, com o mesmo pareamento estado/derivada de `simulation.rs:378-392`.
- **Avaliação:** escreve os valores pedidos, chama `evaluate()` e lê as chaves pedidas. Uma chamada deve bastar, porque a ordem das tarefas já garante que nenhuma lê um valor antes de quem o calcula. Se o teste de memória mostrar o contrário, a avaliação é corrigida até passar.

Como verificar (`cargo test` no monjolo, com modelos de brinquedo):
- A derivada devolvida bate com a expressão analítica.
- **Teste de memória:** avaliar o ponto A, depois o B, depois o A de novo devolve exatamente o mesmo resultado para A. Um dos modelos de brinquedo é feito para falhar nesse teste, para provar que o teste pega o problema.

### 3. tep-plant — função validada no caso base

Teste de integração em `tep-plant/tests/`, usando o tipo da etapa 2 com o estado base de Downs & Vogel (`docs/cases/te_mode1_initial_state.toml`).

- As 38 derivadas físicas ficam próximas de zero. Os valores ficam registrados.
- As medições batem com a coluna "Base case" da Tabela 2 de Ricker (pressão 2705 kPa, temperatura 120,4 °C, água a 94,6 e 77,3 °C).
- O custo pela equação 3 fica perto de 170,6 $/h.
- **Teste de memória na planta inteira**, em duas formas:
  - A, B, A, com B bem distante de A (outra pressão, outras temperaturas, outras válvulas).
  - Uma sequência de pontos variados avaliada numa instância reaproveitada dá o mesmo resultado que cada ponto avaliado numa instância recém-criada.

Onde a memória pode se esconder na planta, e o teste precisa cobrir: os cálculos iterativos de temperatura, que partem de um valor anterior como chute; o comando guardado dentro de cada atuador; e qualquer chave lida antes de ser recalculada.

Este é o ponto de parada do plano. Duas coisas se investigam aqui, antes de construir o resto:
- Se as derivadas não forem próximas de zero, a física do Rust difere do FORTRAN no caso base.
- Se o teste de memória falhar, a função não é pura, e o otimizador receberia respostas diferentes para a mesma pergunta.

### 4. monjolo e tep-plant — StateRegistry por HTTP

- **monjolo:** nova feature `function` no `Cargo.toml`, opcional como a `opcua`, com `tiny_http` e `serde_json`. O servidor é síncrono: recebe, avalia e responde na mesma thread, sem tokio.
- **monjolo:** novo adaptador `monjolo/adapter/function.rs`:

| Rota | Faz |
|---|---|
| `GET /healthz` | Diz se o serviço está no ar |
| `GET /keys` | Lista todas as chaves, com o valor atual e a marca de quais são estados |
| `POST /evaluate` | Recebe uma lista de pontos (chaves a escrever) e as chaves a ler; devolve os valores |

- `/evaluate` aceita vários pontos por chamada, porque um gradiente pede dezenas de avaliações.
- **Escolha do modo:** `[monjolo] mode = "function"` no `application.toml`, lido em `BootstrapSettings` (`runtime.rs:53-99`), com uma variável de ambiente que tem precedência. `Runtime::bootstrap()` (`runtime.rs:254`) decide o que subir, e o `main.rs` da planta não muda. Nesse modo não sobem a thread da planta nem o OPC-UA.
- **tep-plant:** feature `function = ["monjolo/function"]` no `Cargo.toml` e um documento novo, `docs/21-modo-funcao.md`.

Como verificar:
- Teste no monjolo que sobe o serviço numa porta livre com um modelo de brinquedo.
- Manual no tep-plant: subir no modo função, `curl /keys` e um `curl /evaluate` no caso base, que devolve os mesmos números da etapa 3.
- O teste de memória repetido pelo HTTP: A, B, A numa mesma chamada e em chamadas separadas.

### 5. tep-optimizer — fundação

- Projeto no molde do `tep-historian`: Poetry, layout `src/tep_optimizer`, ruff com linha de 100, pytest.
- `client.py`: cliente do serviço (`/keys`, `/evaluate`).
- `model.py`: interface do modelo e um modelo falso, pequeno e com solução conhecida, para os testes não dependerem da planta.
- `scaling.py`: a escala do artigo.
- `jacobian.py`: diferenças finitas, com todos os pontos perturbados numa única chamada.

Como verificar: `pytest` e `ruff check`, sem a planta no ar. O Jacobiano do modelo falso bate com o analítico.

### 6. Marco 1 — Modo 1 de Ricker

- `ricker.py`: o problema do artigo, escrito com as chaves do StateRegistry.
  - Variáveis: os 50 estados (38 físicos e 12 posições de válvula).
  - Custo: equação 3.
  - Restrições: equações 5 e 10 a 15, com P_max = 2800 kPa e L_min = 65 %.
  - Agitador fixo em 100 %, como no artigo.
  - Limites entre 0 e 100 %, apertados para 1 ou 99 % só onde o solver tiver problema.
  - Escala como no artigo.
- `equilibrium.py`: primeiro passo, com as válvulas fixas no caso base, resolver derivadas = 0.
- `optimize.py`: resolver o problema completo, partindo do caso base e de outros pontos.
- `report.py`: gravar estados, válvulas, medições, custo por parcela e restrições ativas, para cada ponto de partida.

Critérios de sucesso do marco:
- O solver converge: as 38 derivadas e as 4 igualdades ficam dentro da tolerância, na escala do artigo.
- O ponto respeita todas as restrições e todos os limites.
- O custo é menor que o do caso base desta mesma planta.

Comparação com a coluna "Mode 1" das Tabelas 2, 3 e 4, que é referência e não critério:
- Custo: 114,31 $/h no artigo. A diferença é relatada, com a divisão entre purga, produto, compressor e vapor.
- Limites atingidos no artigo: pressão em 2800 kPa, nível do reator em 65 %, válvulas de vapor e de reciclo em 1 %.
- Onde o resultado diferir do artigo, o relatório diz em que variável e quanto.

Sobre os pontos de partida: eles servem para mapear os mínimos locais, não para exigir um único ótimo. O relatório lista cada mínimo encontrado e o seu custo, e o resultado do marco é o melhor deles.

Verificação opcional, boa para entender o problema: repetir alguns pontos da Tabela 5 do artigo, que mostra o custo caindo com a pressão do reator e com o nível mais baixo.

Os números não vão bater exatamente, porque esta planta não é numericamente idêntica ao FORTRAN.

O equilíbrio do primeiro passo também responde uma pergunta do Experimento 27: se a planta tem ponto de regime perto do caso base.

### 7. Marco 2 — seis modos e registro

- **tep-optimizer:** especificações dos seis modos (Tabela 1 do artigo) num arquivo TOML. Os modos 2 e 3 partem do ótimo do Modo 1. Os modos 4 a 6 seguem os dois passos do artigo: aumentar a produção até um reagente (D ou E) chegar ao limite, e então minimizar o custo com esse reagente em 100 %.
- **tep-lab:** resultados em `data/experiment_91/` e a tabela de comparação em `analysis/tep_analysis/`.
- **spec:** entrada no `experimentos.md`, com a avaliação do caso base como rodada de controle.

Como verificar: tabela dos seis modos lado a lado com a Tabela 4 do artigo, com os mesmos critérios de sucesso do marco 1. Os custos do artigo são referência.

## Fica para depois

Anotado na #91, fora deste plano:

- Controladores dentro da função, com os setpoints como entrada.
- Rodar a planta em tempo real no ponto ótimo para ver se ela se sustenta.
- Container e subida pelo tep-lab.

## Tecnologias do tep-optimizer

| Item | Escolha | Para quê |
|---|---|---|
| Linguagem | Python 3.11 ou mais novo | Mesma do `tep-historian` |
| Empacotamento | Poetry, layout `src/` | Mesmo molde do `tep-historian` |
| Qualidade | ruff e pytest | Mesmo molde |
| Chamadas HTTP | `httpx` | Cliente do serviço; nos testes, respostas simuladas sem rede |
| Vetores e matrizes | `numpy` | Estados, resíduos, Jacobiano |
| Equilíbrio | `scipy.optimize.least_squares` | Derivadas = 0, com limites nas variáveis |
| Otimização | `scipy.optimize.minimize`, método SLSQP | 50 variáveis, 42 igualdades e 2 desigualdades |
| Otimização, alternativa | método `trust-constr` do SciPy | Se o SLSQP não convergir |
| Otimização, reserva | IPOPT, pelo pacote `cyipopt`, como dependência opcional | Modos de produção máxima, onde o artigo relata dificuldade |
| Configuração | `tomllib`, da biblioteca padrão | Especificações dos modos |
| Linha de comando | `argparse`, da biblioteca padrão | `keys`, `equilibrium`, `optimize` |
| Resultados | JSON e CSV, da biblioteca padrão | Entrada para o `tep-lab/analysis` |

São três dependências de execução: `httpx`, `numpy` e `scipy`.

O que não entra, e por quê:

- **CasADi, Pyomo e JAX:** precisam das equações do modelo escritas na linguagem deles. Aqui o modelo é uma caixa-preta atrás de HTTP, e as derivadas vêm de diferenças finitas.
- **pandas e matplotlib:** tabelas e figuras ficam em `tep-lab/analysis`, que já tem os dois.
- **OPC-UA:** o otimizador não fala com a planta rodando.

A instalação do `cyipopt` no Windows precisa ser conferida se ele for necessário.

## Verificação de ponta a ponta

1. `cargo test` em `monjolo` e em `tep-plant`, nas branches mãe, incluindo o teste do caso base e o teste de memória da etapa 3.
2. Subir a planta no modo função e conferir `GET /keys` e `POST /evaluate` com `curl`, incluindo o teste de memória pelo HTTP.
3. `pytest` no `tep-optimizer`, sem a planta.
4. Com a planta no ar: equilíbrio do caso base, e depois a otimização do Modo 1.
5. Comparar com as Tabelas 2, 3 e 4 do artigo e registrar no `experimentos.md`.
