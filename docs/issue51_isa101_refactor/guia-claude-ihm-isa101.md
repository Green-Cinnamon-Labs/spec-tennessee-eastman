# Guia operacional para geração e revisão de telas IHM/SCADA segundo ISA-101

> Documento para uso por IA, especialmente Claude, ao criar, revisar ou refatorar telas de IHM industrial.  
> Aplicável ao projeto Tennessee Eastman CPS Lab e a interfaces industriais similares.  
> Prioridade: clareza operacional, consciência situacional, consistência e redução de erro do operador.  
> Não é um guia estético. Não é uma tentativa de deixar a tela “bonita”. É uma especificação de comportamento visual e semântico.

---

## 1. Regra principal

Uma tela IHM industrial deve ajudar o operador a:

1. **Detectar**: perceber rapidamente que algo mudou ou saiu do normal.
2. **Diagnosticar**: entender onde, por que e em que direção o processo está evoluindo.
3. **Responder**: tomar uma ação correta, segura e validada.
4. **Valorar**: avaliar criticidade, prioridade e consequência operacional.

Se um elemento visual não ajuda em pelo menos uma dessas quatro funções, ele deve ser removido, simplificado ou rebaixado visualmente.

---

## 2. Fontes normativas e conceituais usadas

Este guia consolida os conceitos do material `ISA-101-III-Simpósio-ISA-São-Paulo-Sabesp-Nov2016.pdf`, complementado por referências públicas oficiais:

- ISA-101: série de normas e relatórios técnicos para projeto, implementação, operação e manutenção de IHMs em automação de processos.
- ANSI/ISA-101.01-2015: norma para interfaces homem-máquina em sistemas de automação de processos.
- ISA-TR101.02-2019: relatório técnico sobre usabilidade e desempenho de IHM.
- ISO 9241-11: usabilidade como resultado de uso, envolvendo efetividade, eficiência e satisfação em um contexto de uso.
- EEMUA-201: citado no material como referência complementar para interação, comandos, botões, representação numérica, faceplates e análise de tarefa.

Interpretação adotada neste projeto:

- A ISA-101 define a filosofia, o ciclo de vida e os princípios de organização da IHM.
- O material da ISA Distrito 4 traduz esses princípios em exemplos de cognição, cor, forma, acessibilidade, movimento, posição e hierarquia.
- Este documento transforma esses princípios em regras práticas para uma IA editar telas sem improvisação visual.

---

## 3. Definições obrigatórias

### 3.1 IHM / HMI

Interface Homem-Máquina. É o sistema visual e interativo pelo qual o operador observa o processo, interpreta o estado da planta e executa comandos.

A IHM não é apenas uma representação do campo. Ela é uma camada operacional de decisão e resposta. Deve ser tratada como parte do sistema de operação.

### 3.2 Tela

Uma tela é uma unidade funcional de operação. Toda tela deve ter:

- um objetivo operacional explícito;
- um nível hierárquico definido;
- um conjunto limitado de variáveis exibidas;
- regras claras de destaque;
- navegação previsível;
- ausência de decoração sem função operacional.

### 3.3 Operador

Usuário que precisa decidir sob restrição de tempo, ruído, fadiga, distração, estresse e informação incompleta. A tela deve reduzir carga cognitiva, não aumentá-la.

### 3.4 Consciência situacional

Capacidade do operador de alinhar a situação percebida com a situação real do processo.

Deve ser suportada em três níveis:

| Nível       | Pergunta operacional      | Tela deve responder                                                    |
| ----------- | ------------------------- | ---------------------------------------------------------------------- |
| Percepção   | O que está acontecendo?   | Estados, desvios, alarmes, tendências imediatas                        |
| Compreensão | O que isso significa?     | Relações causais, unidades afetadas, comparação com limites            |
| Projeção    | Para onde isso está indo? | Tendência, taxa de variação, aproximação de limites, risco de shutdown |

### 3.5 Sinal

Qualquer variável observável ou comandável na IHM.

No projeto Tennessee Eastman:

- `XMEAS`: medições do processo;
- `XMV`: variáveis manipuladas / atuadores;
- `IDV`: distúrbios;
- `state`: estados internos do modelo;
- `alarm`: condição anormal derivada de limites, intertravamentos ou lógica de segurança.

### 3.6 Estado visual

Estado visual é a forma normalizada de representar uma condição operacional.

Estados mínimos:

| Estado                 | Significado                                        |
| ---------------------- | -------------------------------------------------- |
| `normal`               | Variável dentro da faixa esperada                  |
| `warning`              | Atenção; aproximação de limite operacional         |
| `alarm`                | Condição anormal ativa                             |
| `unacknowledged_alarm` | Alarme ativo ainda não reconhecido                 |
| `acknowledged_alarm`   | Alarme ativo reconhecido                           |
| `invalid`              | Dado inválido, ausente, congelado ou inconsistente |
| `disabled`             | Elemento indisponível ou fora de serviço           |
| `manual`               | Atuador/controlador em modo manual                 |
| `auto`                 | Atuador/controlador em modo automático             |
| `inhibited`            | Alarme, intertravamento ou ação inibida            |
| `selected`             | Elemento atualmente selecionado pelo operador      |

Nunca criar estados visuais ad hoc sem registrá-los neste vocabulário.

---

## 4. Princípios cognitivos

### 4.1 A tela deve explorar percepção pré-atentiva

O operador deve perceber anormalidades antes de precisar ler todos os números.

Use percepção pré-atentiva por:

- contraste;
- forma;
- posição;
- tamanho;
- agrupamento;
- orientação;
- barras de tendência;
- símbolos simples.

Evite exigir que o operador compare manualmente dezenas de valores numéricos.

### 4.2 Reduzir unidades de informação

Muitas unidades visuais aumentam memória e processamento mental. Poucas unidades bem agrupadas reduzem esforço cognitivo.

Regra para Claude:

- agrupar variáveis por função operacional, não por conveniência técnica;
- evitar listas longas sem hierarquia;
- evitar mostrar tudo porque “está disponível”;
- preferir visão resumida + drill-down para detalhe.

### 4.3 O dado importante deve se destacar; o normal deve ser silencioso

Em condição normal, a tela deve parecer calma. Cores fortes, movimento e alto contraste devem ser reservados para exceções.

O operador deve olhar para a tela e perceber rapidamente:

- o que está normal;
- o que está anormal;
- onde está anormal;
- quão grave é;
- se está piorando ou melhorando.

---

## 5. Hierarquia de telas

Toda tela deve pertencer exatamente a um nível hierárquico.

### 5.1 Nível 1 — Visão geral / Overview

Objetivo: percepção rápida do estado global da planta.

Deve mostrar:

- principais unidades do processo;
- estado geral de cada unidade;
- alarmes ativos por área;
- variáveis críticas agregadas;
- tendências essenciais;
- links para telas Nível 2.

Não deve mostrar:

- todos os instrumentos;
- todos os controladores;
- comandos detalhados;
- ajustes finos;
- tabelas densas.

Exemplo Tennessee Eastman:

- Reactor;
- Condenser;
- Separator;
- Compressor;
- Stripper;
- Feed/Purge/Product overview.

### 5.2 Nível 2 — Área / Unidade de processo

Objetivo: diagnosticar uma área específica.

Deve mostrar:

- fluxos principais da unidade;
- PVs críticas;
- MVs relacionadas;
- limites operacionais;
- alarmes da unidade;
- pequenos trends das variáveis-chave;
- acesso a faceplates e detalhes.

Exemplo:

- tela do reator;
- tela do separador;
- tela do stripper;
- tela de alimentação e reciclo.

### 5.3 Nível 3 — Equipamento / Malha / Faceplate

Objetivo: executar ação operacional controlada.

Deve mostrar:

- tag do instrumento ou controlador;
- PV, SP e MV;
- modo manual/automático;
- limites;
- alarmes associados;
- tendência curta;
- botões de comando;
- validação de entrada.

### 5.4 Nível 4 — Diagnóstico avançado / Engenharia / Configuração

Objetivo: análise detalhada, manutenção, calibração, tuning ou investigação.

Pode mostrar:

- estados internos;
- parâmetros do controlador;
- logs;
- séries históricas longas;
- diagnósticos de comunicação;
- dados brutos;
- configurações.

Não deve ser usado como tela operacional primária.

---

## 6. Navegação

### 6.1 Regras gerais

Toda tela deve ter:

- título claro;
- nível da tela;
- breadcrumb ou indicação de localização;
- status global resumido;
- link para voltar ao nível superior;
- links para telas relacionadas.

Padrão:

```text
[Plant Overview] > [Reactor Area] > [Pressure Control Loop]
```

### 6.2 Drill-down

O detalhe aumenta conforme a navegação avança.

Regra:

- Nível 1 detecta;
- Nível 2 diagnostica;
- Nível 3 responde;
- Nível 4 investiga/configura.

Não colocar informação de Nível 4 em Nível 1.

### 6.3 Navegação lateral ou superior

Use navegação constante. Não mudar posição de menus entre telas.

Claude deve preservar:

- mesmos nomes;
- mesma ordem;
- mesma posição;
- mesmo padrão de ícones;
- mesmo comportamento de clique.

---

## 7. Cores

### 7.1 Filosofia de cor

Cores normais devem ser neutras. Cores fortes são reservadas para ênfase operacional.

A cor não deve decorar. A cor deve codificar significado.

### 7.2 Separar cores normais de cores de ênfase

| Categoria       | Uso permitido                                                                     |
| --------------- | --------------------------------------------------------------------------------- |
| Cores normais   | equipamentos, tubulações, textos, painéis, status normal                          |
| Cores de ênfase | alarmes, falhas, bloqueios, inibições, setpoints, intertravamentos, seleção ativa |

### 7.3 Paleta semântica recomendada

Os valores abaixo são uma decisão de engenharia deste guia. Eles não são valores normativos da ISA.

| Token            |       Cor | Uso                                            |
| ---------------- | --------: | ---------------------------------------------- |
| `--hmi-bg`       | `#D9DEE2` | Fundo geral cinza claro                        |
| `--hmi-panel`    | `#EEF1F3` | Cartões e grupos                               |
| `--hmi-line`     | `#6F767D` | Linhas de processo, bordas, tubulações normais |
| `--hmi-text`     | `#1F252A` | Texto principal                                |
| `--hmi-muted`    | `#6B7278` | Texto secundário                               |
| `--hmi-data`     | `#263238` | Valores de processo normais                    |
| `--hmi-good`     | `#4B6F44` | Estado saudável, usar pouco                    |
| `--hmi-warning`  | `#B7791F` | Atenção / pré-alarme                           |
| `--hmi-alarm`    | `#B00020` | Alarme crítico                                 |
| `--hmi-invalid`  | `#7A3E9D` | Dado inválido ou inconsistente                 |
| `--hmi-manual`   | `#1F5F8B` | Modo manual                                    |
| `--hmi-selected` | `#005A9C` | Seleção/foco do operador                       |
| `--hmi-disabled` | `#9AA1A6` | Indisponível                                   |

### 7.4 Regras obrigatórias de cor

Claude deve obedecer:

- Não usar gradiente decorativo em fundo, tanque, tubulação ou equipamento.
- Não usar sombra 3D decorativa.
- Não usar vermelho/verde como única diferença entre estados.
- Não usar cor forte para elemento normal.
- Não usar paleta arco-íris para dados operacionais.
- Não codificar quantidade apenas por cor.
- Não codificar severidade apenas por cor.
- Toda cor de alarme deve ter forma, texto ou ícone redundante.

### 7.5 Data pixels vs non-data pixels

Priorizar pixels que carregam informação de processo.

Remover ou reduzir:

- gradientes;
- reflexos;
- texturas metálicas;
- ícones realistas;
- sombras;
- excesso de linhas;
- preenchimentos decorativos.

Manter ou destacar:

- valores;
- limites;
- tendências;
- alarmes;
- estados;
- direções de fluxo relevantes;
- relações entre variáveis.

---

## 8. Forma, tamanho e agrupamento

### 8.1 Quantidade

Representar quantidade por comprimento, posição ou escala, não apenas por número solto.

Exemplos:

- nível de tanque: barra vertical com limites;
- pressão: indicador horizontal com faixa normal e limite alto;
- abertura de válvula: barra percentual;
- vazão: valor + mini trend.

### 8.2 Hierarquia

Representar hierarquia por:

- tamanho de texto;
- posição;
- contorno;
- densidade visual;
- agrupamento;
- nível da tela.

Não usar tudo com o mesmo peso visual.

### 8.3 Agrupamento

Variáveis relacionadas devem estar próximas e contidas em um grupo visual.

Agrupar por:

- unidade de processo;
- função operacional;
- cadeia causal;
- malha de controle;
- família de alarmes.

Não agrupar apenas por índice técnico, salvo em telas Nível 4.

Exemplo ruim:

```text
XMEAS 1, XMEAS 2, XMEAS 3, XMEAS 4, ...
```

Exemplo bom:

```text
Feeds
- A Feed
- D Feed
- E Feed
- A/C Feed

Reactor
- Pressure
- Level
- Temperature
- Cooling Water
```

---

## 9. Acessibilidade

### 9.1 Cor nunca é suficiente

Toda diferença de status deve ser reconhecível em tons de cinza.

Use redundância por:

- forma;
- ícone;
- texto;
- padrão de linha;
- contorno;
- posição;
- espessura.

### 9.2 Daltonismo

Assumir que haverá usuários com dificuldade de diferenciar vermelho/verde.

Proibido:

- “verde = ligado, vermelho = desligado” como única codificação;
- severidade baseada apenas em matiz;
- gráfico com séries diferenciadas apenas por cor.

### 9.3 Contraste luminoso

Contraste de luminosidade é mais robusto do que contraste de matiz.

Regra prática:

- desligado: mais claro que o fundo ou visualmente rebaixado;
- inválido: mesmo peso do fundo + marcação explícita `INVALID`;
- ligado: mais escuro que o fundo ou com contorno forte;
- alarme: alto contraste + forma + texto.

---

## 10. Movimento e animação

Movimento atrai a atenção de forma forte. Por isso deve ser raro.

Permitido:

- piscar apenas para alarme ativo não reconhecido;
- animação discreta de carregamento de dados;
- transição curta para mudança de estado, sem loop contínuo.

Proibido:

- tubulação com fluido animado continuamente;
- equipamento girando sem necessidade operacional;
- gráficos decorativos animados;
- pisca-pisca para status normal;
- animação em fundo.

Regra de alarme:

- `unacknowledged_alarm`: pode piscar.
- `acknowledged_alarm`: não deve piscar; deve continuar destacado de forma estática enquanto ativo.
- `normal`: nunca pisca.

---

## 11. Posição e 3D

### 11.1 Preferir posicionamento plano

A tela deve ser plana, legível e previsível.

Usar:

- layout 2D;
- alinhamento em grade;
- leitura esquerda → direita, cima → baixo;
- fluxos compatíveis com a lógica do processo;
- labels próximos ao objeto associado.

Evitar:

- perspectiva 3D;
- objetos inclinados;
- gráficos em perspectiva;
- texto rotacionado;
- profundidade falsa.

### 11.2 Uso de 3D

3D é proibido em telas com status operacional ou controle.

Pode ser aceito apenas em:

- telas demonstrativas;
- telas institucionais;
- telas de navegação geral sem status nem comando;
- visão conceitual sem decisão operacional.

Mesmo nesses casos, não deve esconder estados, alarmes ou dados.

---

## 12. Tipografia

### 12.1 Fontes

Usar fonte sans-serif legível.

Recomendação:

```css
font-family: Inter, Roboto, Segoe UI, Arial, sans-serif;
```

### 12.2 Escala tipográfica

| Uso               | Tamanho sugerido | Peso |
| ----------------- | ---------------: | ---: |
| Título da tela    |         22–28 px |  600 |
| Título de grupo   |         16–18 px |  600 |
| Label de variável |         12–14 px |  500 |
| Valor principal   |         18–28 px |  600 |
| Unidade           |         11–13 px |  400 |
| Texto auxiliar    |         11–13 px |  400 |

### 12.3 Regras

- Unidade sempre visível.
- Tag técnica pode aparecer, mas não deve substituir nome operacional.
- Valores numéricos devem estar alinhados por ponto decimal quando em tabela.
- Não usar caixa alta em textos longos.
- Não usar fonte condensada para valores críticos.

---

## 13. Representação numérica

### 13.1 Estrutura obrigatória de variável

Toda variável exibida deve ter:

```text
[NOME OPERACIONAL]
[valor] [unidade]
[estado visual]
[opcional: tag técnica]
[opcional: limite / SP / tendência]
```

Exemplo:

```text
Reactor Pressure
2705 kPa
NORMAL
XMEAS(7)
SP 2705 | HH 3000
```

### 13.2 Precisão

Não exibir mais casas decimais do que o operador consegue usar.

Regra prática:

| Tipo                  | Casas sugeridas |
| --------------------- | --------------: |
| Pressão kPa           |             0–1 |
| Temperatura °C        |               1 |
| Nível %               |               1 |
| Vazão kg/h            |             0–1 |
| Abertura de válvula % |               1 |
| Fração/composição %   |               2 |

### 13.3 Dados inválidos

Nunca esconder dado inválido.

Representar como:

```text
INVALID
last good: 2705 kPa at 12:03:05
```

Não substituir dado inválido por zero.

---

## 14. Alarmes

### 14.1 Princípio

Alarme é chamada para ação. Não é decoração, log nem simples mudança de cor.

Toda condição de alarme deve responder:

- o que está errado;
- onde está errado;
- quão grave é;
- há quanto tempo está ativo;
- se foi reconhecido;
- qual ação operacional é esperada.

### 14.2 Severidade visual

| Severidade | Estado             | Codificação visual                                     |
| ---------- | ------------------ | ------------------------------------------------------ |
| 1          | Atenção            | contorno âmbar, texto `WARN`                           |
| 2          | Alarme             | vermelho escuro, ícone, texto `ALARM`                  |
| 3          | Crítico            | vermelho escuro forte, borda espessa, texto `CRITICAL` |
| 4          | Shutdown/interlock | vermelho + preto, símbolo de bloqueio/interlock        |

Sempre redundar cor com forma/texto.

### 14.3 Reconhecimento

| Estado                              | Movimento                       | Visual                                      |
| ----------------------------------- | ------------------------------- | ------------------------------------------- |
| Ativo não reconhecido               | pode piscar                     | alto destaque                               |
| Ativo reconhecido                   | não pisca                       | destaque fixo                               |
| Retornado ao normal não reconhecido | sem piscar ou destaque moderado | exige limpeza/ack conforme regra do sistema |
| Normal                              | sem movimento                   | visual neutro                               |

---

## 15. Tendências e histórico

### 15.1 Quando usar trend

Usar trend quando a decisão depende de direção, velocidade ou estabilidade.

Exemplos:

- pressão do reator subindo em direção ao limite;
- nível caindo lentamente;
- válvula saturada;
- temperatura oscilando;
- vazão instável.

### 15.2 Mini trend

Em Nível 1 e 2, usar mini trends sem excesso de detalhe.

Deve mostrar:

- janela temporal curta;
- linha simples;
- faixa normal;
- limite operacional quando relevante;
- indicação de subida/descida.

### 15.3 Trend detalhado

Em Nível 3 e 4, trend pode permitir:

- múltiplas variáveis correlacionadas;
- seleção de janela temporal;
- comparação com baseline;
- cursor de leitura;
- exportação.

---

## 16. Comandos e interação

### 16.1 Botões

Botões devem ter verbo + objeto.

Bom:

```text
Set Reactor Pressure SP
Open Purge Valve
Enable IDV(1)
Acknowledge Alarm
```

Ruim:

```text
OK
Apply
Do it
Start
```

### 16.2 Comandos críticos

Comandos críticos exigem confirmação contextual.

Confirmação deve dizer consequência, não apenas pedir “tem certeza?”.

Exemplo:

```text
Confirmar alteração de Reactor Pressure SP de 2705 para 2645 kPa?
Esta ação altera a pressão-alvo do reator e pode afetar purge/recycle.
```

### 16.3 Entrada de setpoint

Toda entrada deve validar:

- tipo numérico;
- unidade;
- faixa permitida;
- limite operacional;
- taxa máxima de alteração, se existir;
- confirmação para alteração grande.

### 16.4 Feedback de escrita

Depois de um comando, a tela deve mostrar:

- comando enviado;
- aguardando controlador;
- aceito ou rejeitado;
- valor observado após atualização;
- tempo de resposta.

---

## 17. Faceplates

Faceplate é o painel padronizado de uma malha, válvula, controlador ou instrumento.

### 17.1 Estrutura obrigatória

```text
[TAG] [Nome operacional]
[Modo: AUTO/MANUAL/CASCADE/OFF]
[PV] valor unidade estado
[SP] valor unidade editável se permitido
[MV] valor % ou unidade
[Status] normal/alarm/invalid/inhibited
[Mini trend]
[Ações permitidas]
[Links: trend detalhado | alarmes | histórico | configuração]
```

### 17.2 Regras

- Todos os faceplates devem ter a mesma estrutura.
- Não inventar layout específico por malha sem justificativa.
- Campo editável deve ser visualmente diferente de campo somente leitura.
- Modo manual deve ter destaque claro.
- Saturação de MV deve ser visível.

---

## 18. Padrões de tela para o Tennessee Eastman CPS Lab

### 18.1 Tela Level 1 — Plant Overview

Deve conter:

- estado global da simulação;
- tempo simulado;
- `dt`;
- status de shutdown/interlock;
- blocos principais: Reactor, Condenser, Separator, Compressor, Stripper;
- alarmes ativos por bloco;
- variáveis críticas:
  - Reactor Pressure `XMEAS(7)`;
  - Reactor Level `XMEAS(8)`;
  - Reactor Temperature `XMEAS(9)`;
  - Separator Level `XMEAS(12)`;
  - Stripper Level `XMEAS(15)`;
  - Product Flow `XMEAS(17)`;
  - Purge Flow `XMEAS(10)`;
  - Recycle Flow `XMEAS(5)`.

Não deve conter:

- todos os `XMEAS`;
- todos os `XMV`;
- estados internos `YY`;
- parâmetros de PID;
- logs longos.

### 18.2 Tela Level 2 — Reactor Area

Deve conter:

- Reactor Pressure, Level, Temperature;
- Reactor Feed Rate;
- Cooling Water Flow / Outlet Temperature;
- Purge Valve e Purge Flow se causalmente relacionados;
- mini trends de pressão, temperatura e nível;
- limites operacionais e shutdown;
- links para faceplates de pressão, cooling water e purge.

### 18.3 Tela Level 2 — Separator Area

Deve conter:

- Separator Temperature;
- Separator Level;
- Separator Pressure;
- Underflow;
- Purge composition/analysis se disponível;
- relação com condenser cooling.

### 18.4 Tela Level 2 — Stripper Area

Deve conter:

- Stripper Level;
- Stripper Pressure;
- Product Flow;
- Stripper Temperature;
- Steam Flow;
- Product composition/analyzer se disponível.

### 18.5 Tela Level 3 — Controller Faceplate

Para cada controlador:

- `controller_id`;
- variável controlada `xmeasIndex`;
- variável manipulada `xmvIndex`;
- tipo `P/PI/PID`;
- PV, SP, MV;
- modo;
- saturação;
- erro;
- saída calculada;
- parâmetros;
- trend PV/SP/MV.

### 18.6 Tela Level 4 — Simulation Diagnostics

Pode conter:

- deriv norm;
- solver status;
- step count;
- estado interno;
- `YY`;
- snapshots;
- filas de comandos;
- latência de WebSocket/gRPC;
- logs.

Não usar como tela normal de operação.

---

## 19. Padrões semânticos para HTML/SVG/CSS

### 19.1 Atributos obrigatórios

Todo componente dinâmico deve ter identificação semântica.

```html
<div
  class="hmi-value hmi-state-normal"
  data-signal-id="XMEAS_7"
  data-signal-kind="measurement"
  data-unit="kPa"
  data-state="normal"
>
  2705 kPa
</div>
```

### 19.2 Convenção de IDs

| Tipo             | Padrão                          |
| ---------------- | ------------------------------- |
| Medição          | `xmeas-7`                       |
| Manipulada       | `xmv-6`                         |
| Distúrbio        | `idv-1`                         |
| Valor textual    | `val-xmeas-7`                   |
| Mini trend       | `trend-xmeas-7`                 |
| Faceplate        | `faceplate-controller-pressure` |
| Grupo de unidade | `unit-reactor`                  |

### 19.3 Classes semânticas

```css
.hmi-screen {}
.hmi-header {}
.hmi-nav {}
.hmi-panel {}
.hmi-unit-card {}
.hmi-faceplate {}
.hmi-value {}
.hmi-label {}
.hmi-unit {}
.hmi-trend {}
.hmi-alarm-summary {}
.hmi-command-panel {}

.hmi-state-normal {}
.hmi-state-warning {}
.hmi-state-alarm {}
.hmi-state-unacknowledged-alarm {}
.hmi-state-invalid {}
.hmi-state-disabled {}
.hmi-state-manual {}
.hmi-state-auto {}
.hmi-state-inhibited {}
.hmi-state-selected {}
```

### 19.4 SVG

SVG deve representar topologia e relações físicas. Não deve virar um desenho decorativo.

Regras:

- cada unidade de processo deve ter `id` estável;
- cada sensor/atuador deve ter âncora geométrica explícita;
- texto dinâmico deve estar em elemento próprio, com `id` estável;
- não posicionar texto “no olho” sem anchor declarada;
- cada medição deve declarar lado preferido de label: `left`, `right`, `top`, `bottom`;
- não usar gradientes, sombra ou textura;
- não animar fluxo continuamente;
- tubulações devem ser linhas simples, neutras e legíveis.

Exemplo de metadado para posicionamento:

```js
const SIGNAL_LAYOUT = {
  "xmeas-7": {
    name: "Reactor Pressure",
    unit: "kPa",
    anchorId: "anchor-reactor-pressure",
    preferredSide: "right",
    screenLevel: 2,
    criticality: "high"
  },
  "xmeas-8": {
    name: "Reactor Level",
    unit: "%",
    anchorId: "anchor-reactor-level",
    preferredSide: "left",
    screenLevel: 2,
    criticality: "high"
  }
}
```

### 19.5 Padrão para texto em analisadores/sensores

Não deixar a IA escolher posição aleatória.

Função esperada:

```js
function placeSignalLabel(signalId, value, options) {
  // options.anchorId: id do ponto físico/semântico no SVG
  // options.preferredSide: left | right | top | bottom
  // options.offsetPx: distância do anchor
  // options.state: normal | warning | alarm | invalid
}
```

Regra:

- a posição do label vem de metadado, não de cálculo genérico aleatório;
- se não existir anchor, não renderizar silenciosamente: registrar erro de layout;
- se o label colidir, aplicar regra de prioridade, não deslocamento arbitrário.

---

## 20. Performance da IHM

A ISA-101 trata desempenho como parte da qualidade da IHM. Este guia adota os seguintes conceitos:

| Métrica                | Definição                                                              |
| ---------------------- | ---------------------------------------------------------------------- |
| `call_up_time`         | tempo para carregar todos os objetos e informações de uma tela         |
| `display_refresh_rate` | intervalo entre atualizações dos dados exibidos                        |
| `write_time`           | tempo entre alteração na tela e recebimento pelo controlador/simulador |
| `write_refresh_time`   | tempo entre ação do operador e feedback visual da resposta             |

Valores-alvo de engenharia para este projeto:

| Métrica                           |           Alvo inicial |
| --------------------------------- | ---------------------: |
| Carregar tela operacional         |                  ≤ 2 s |
| Atualização de medições críticas  |           250 ms – 1 s |
| Atualização de trends             |              1 s – 5 s |
| Feedback visual após comando      |               ≤ 500 ms |
| Confirmação de escrita no backend | ≤ 1 s, quando possível |

Se o backend não garantir esse tempo, a tela deve mostrar estado `pending` ou `stale`, nunca parecer atualizada falsamente.

---

## 21. Proibições explícitas

Claude não deve fazer:

- tela estilo videogame;
- excesso de cor;
- 3D em tela operacional;
- gradiente decorativo;
- animação contínua de fluxo;
- sombras e texturas metálicas;
- alarmes só por cor;
- status normal com vermelho, amarelo ou cor saturada;
- esconder unidade;
- mostrar número sem contexto;
- misturar controle com diagnóstico avançado na mesma tela;
- colocar tudo em uma única dashboard;
- criar botões com rótulos vagos;
- mudar convenções entre telas;
- usar índices técnicos como principal forma de navegação;
- renderizar dados inválidos como zero;
- posicionar labels dinamicamente sem metadado semântico.

---

## 22. Checklist obrigatório para Claude antes de entregar uma tela

Antes de propor código ou alteração visual, responder internamente às perguntas:

1. Qual é o nível da tela? 1, 2, 3 ou 4?
2. Qual decisão operacional essa tela suporta?
3. Quais sinais são estados observados?
4. Quais sinais são comandos/entradas?
5. Quais sinais são alarmes ou condições anormais?
6. O normal está visualmente calmo?
7. O anormal se destaca sem depender só de cor?
8. Existe excesso de decoração?
9. Existem unidades em todos os valores?
10. Há tendência onde direção importa?
11. Botões têm verbo + objeto?
12. Comandos críticos têm confirmação contextual?
13. Há feedback de escrita?
14. O layout funciona em tons de cinza?
15. A navegação respeita drill-down?
16. A tela usa componentes e estados já definidos?
17. A posição de labels em SVG vem de metadado?
18. A tela evita 3D, gradiente e animação sem função?

Se a resposta a qualquer item crítico for “não”, corrigir antes de entregar.

---

## 23. Formato de resposta esperado da IA ao modificar uma tela

Quando Claude for solicitado a alterar uma tela, deve responder neste formato:

```md
## Enquadramento
- Tela afetada:
- Nível hierárquico:
- Objetivo operacional:
- Sinais envolvidos:
- Entradas/comandos envolvidos:

## Diagnóstico
- Problema atual:
- Risco operacional/cognitivo:
- Regra deste guia aplicável:

## Alteração proposta
- O que muda:
- O que permanece:
- Como a alteração melhora detectar/diagnosticar/responder/valorar:

## Implementação
[código ou instruções]

## Validação
- Teste visual normal:
- Teste visual em alarme:
- Teste em tons de cinza:
- Teste de dado inválido:
- Teste de navegação:
```

---

## 24. Exemplo de componente visual recomendado

```html
<section class="hmi-unit-card" id="unit-reactor" data-unit="reactor" data-state="normal">
  <header class="hmi-unit-card__header">
    <h2>Reactor</h2>
    <span class="hmi-state-pill hmi-state-normal">NORMAL</span>
  </header>

  <div class="hmi-metric-grid">
    <div class="hmi-value" data-signal-id="xmeas-7" data-state="normal">
      <span class="hmi-label">Pressure</span>
      <span class="hmi-number">2705</span>
      <span class="hmi-unit">kPa</span>
      <span class="hmi-limit">HH 3000</span>
    </div>

    <div class="hmi-value" data-signal-id="xmeas-8" data-state="normal">
      <span class="hmi-label">Level</span>
      <span class="hmi-number">75.0</span>
      <span class="hmi-unit">%</span>
      <span class="hmi-limit">LL 10%</span>
    </div>

    <div class="hmi-value" data-signal-id="xmeas-9" data-state="normal">
      <span class="hmi-label">Temperature</span>
      <span class="hmi-number">120.4</span>
      <span class="hmi-unit">°C</span>
      <span class="hmi-limit">HH 175°C</span>
    </div>
  </div>
</section>
```

---

## 25. CSS-base recomendado

```css
:root {
  --hmi-bg: #D9DEE2;
  --hmi-panel: #EEF1F3;
  --hmi-line: #6F767D;
  --hmi-text: #1F252A;
  --hmi-muted: #6B7278;
  --hmi-data: #263238;
  --hmi-good: #4B6F44;
  --hmi-warning: #B7791F;
  --hmi-alarm: #B00020;
  --hmi-invalid: #7A3E9D;
  --hmi-manual: #1F5F8B;
  --hmi-selected: #005A9C;
  --hmi-disabled: #9AA1A6;
}

.hmi-screen {
  background: var(--hmi-bg);
  color: var(--hmi-text);
  font-family: Inter, Roboto, Segoe UI, Arial, sans-serif;
}

.hmi-panel,
.hmi-unit-card,
.hmi-faceplate {
  background: var(--hmi-panel);
  border: 1px solid var(--hmi-line);
  border-radius: 6px;
}

.hmi-value {
  color: var(--hmi-data);
}

.hmi-state-normal {
  color: var(--hmi-data);
  border-color: var(--hmi-line);
}

.hmi-state-warning {
  color: var(--hmi-warning);
  border-color: var(--hmi-warning);
}

.hmi-state-alarm,
.hmi-state-unacknowledged-alarm {
  color: var(--hmi-alarm);
  border-color: var(--hmi-alarm);
  font-weight: 700;
}

.hmi-state-unacknowledged-alarm {
  animation: hmi-alarm-pulse 1s step-end infinite;
}

.hmi-state-invalid {
  color: var(--hmi-invalid);
  border-style: dashed;
}

.hmi-state-disabled {
  color: var(--hmi-disabled);
  opacity: 0.65;
}

@keyframes hmi-alarm-pulse {
  50% { opacity: 0.35; }
}
```

Observação: a animação acima só pode ser aplicada a alarme não reconhecido. Não usar para status normal.

---

## 26. Critério final de aceitação

Uma tela é aceita se um operador conseguir, sem treinamento adicional específico da tela:

1. reconhecer o estado geral em poucos segundos;
2. identificar anormalidades sem varrer todos os números;
3. entender quais unidades são afetadas;
4. navegar para o detalhe correto;
5. executar comandos sem ambiguidade;
6. perceber se o comando foi aceito;
7. distinguir dado normal, inválido, alarme e modo manual;
8. usar a tela em tons de cinza sem perder significado crítico.

Se a tela impressiona visualmente mas dificulta qualquer um desses itens, ela falhou.

---

## 27. Prompt curto para colar no Claude

```md
Você está editando uma IHM industrial. Siga rigorosamente o guia ISA-101 deste projeto.

Priorize consciência situacional, detecção de anormalidades, diagnóstico e ação operacional.
Não use estética decorativa: sem 3D operacional, sem gradientes decorativos, sem animação contínua, sem cor forte para estado normal.
Use cores apenas com significado semântico. Nunca codifique status apenas por cor.
Classifique a tela em Nível 1, 2, 3 ou 4 antes de alterar.
Preserve drill-down: overview detecta, unidade diagnostica, faceplate permite resposta, diagnóstico avançado investiga.
Todo valor deve ter nome, unidade, estado e origem semântica.
Todo comando deve ter verbo + objeto, validação e feedback.
Em SVG, labels dinâmicos devem ser posicionados por metadado de anchor e preferredSide, nunca por deslocamento aleatório.
Antes de entregar, valide: normal calmo, anormal destacado, tons de cinza, dado inválido, alarme não reconhecido, navegação e consistência.
```
