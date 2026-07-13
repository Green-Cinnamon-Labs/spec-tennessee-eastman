# Padrão de registro — estrutura tipo legislativa

Objetivo: qualquer leitor (humano ou IA) que já conhece o domínio deve conseguir ir direto ao ponto que precisa, sem ler o documento inteiro, e sem depender de um resumo de status mantido à parte (que desincroniza do corpo).

## 1. Unidades da estrutura

- **Artigo** — unidade endereçável. Numeração decimal fixa (`Art. 2.3`), nunca reaproveitada, nunca renumerada. É o equivalente ao que hoje são as seções `###`, mas sem título hierárquico por cima — o número já é o endereço.
- **Caput** — o corpo do artigo, a decisão vigente. Direto, sem histórico embutido, sem "antes era assim, agora é assado" dentro dele.
- **Parágrafo (§)** — desdobra o caput: exceção, condição, ou **pendência**. Pendência é sempre parágrafo, nunca vira artigo próprio, porque só existe em função do artigo que qualifica.
- **Inciso** — item de enumeração paralela dentro do caput ou de um parágrafo (mesma natureza, mesmo nível — não é hierarquia, é lista).
- **Alínea / item** — subdivide inciso, quando precisar (raro em documento técnico).

Não se usa `##`/`###` como estrutura de conteúdo. Título de seção grande só separa capítulos temáticos (ex.: "Contrato de Integração", "Contrato de Composição"), sem carregar status.

## 2. Como uma decisão muda

Uma decisão nunca é reescrita por cima da antiga. Dois casos:

- **Alteração** — cria-se um novo artigo com o caput correto. O artigo antigo recebe, ao final, uma linha fixa e formulaica: `(alterado pelo Art. X)` — sem prosa explicando o que mudou ali, porque a explicação mora no artigo novo. Nenhuma prosa livre no artigo velho além dessa linha.
- **Revogação** — o artigo é mantido só como marcador: `Art. 2.3-A: (revogado, ver Art. 6.2)`. Corpo esvaziado, número preservado. Nunca se apaga um artigo do documento.

Regra geral: **remissão por número, nunca por reexplicação**. Se você precisa contar de novo o que o outro artigo diz pra dar contexto, é sinal de que devia ser remissão (`nos termos do Art. X`) e não duplicação.

## 3. Índice no topo

O índice não registra status (isso é papel do corpo, via `(alterado)`/`(revogado)`). Ele é só uma tabela de **tópico → artigo**, um índice reverso por conceito/tipo/nome, não por assunto vago:

```
StateRegistry     → Art. 1.3, 3.6, 6
Snapshot          → Art. 11.9, 11.11
EvaluationState   → Art. 1.2, 1.3, 8
Flows             → Art. 12, 12.1–12.4
```

Isso não desincroniza porque não descreve conteúdo nem estado — é só endereço. Adicionar uma linha nova quando um conceito novo aparece é a única manutenção que ele exige.

## 4. Uso de hachura (~~texto riscado~~)

Hachura marca **texto que existiu e foi substituído no lugar**, quando não compensa abrir artigo novo — é uma ferramenta de granularidade fina, não o mecanismo principal de versionamento (esse é alteração/revogação de artigo, seção 2).

Regras:
- Hachura sempre acompanhada de nota curta logo em seguida indicando o destino: `~~trecho antigo~~ → ver Art. X`. Nunca hachura "solta" sem apontar pra onde foi.
- Hachura não se acumula: se um trecho já hachurado precisa mudar de novo, isso é sinal de que deveria ter virado artigo novo (seção 2), não uma segunda camada de rasura por cima.
- Hachura é para frases/trechos dentro de um caput já estável. Se a mudança afeta o caput inteiro, o caso é alteração de artigo — não hachura.

## 5. Data e horário

Todo registro de alteração, revogação ou pendência resolvida leva data no formato `AAAA-MM-DD` (hora só se houver mais de um evento no mesmo dia relevante à ordem):

- Na linha de remissão: `(alterado pelo Art. 8, 2026-07-12)`.
- Na resolução de pendência: `(§1º revogado, ver Art. 12, 2026-07-12)`.
- Data não entra no caput nem na decisão em si — só nas linhas de transição (alteração/revogação/remissão). O caput descreve o que é verdade agora, atemporal; a data mora exclusivamente no rastro de como se chegou até aqui.

Isso dá ordem cronológica auditável sem precisar de changelog separado: basta ler as datas nas linhas de remissão espalhadas pelo texto, na ordem em que aparecem.

## 6. Fluxo de leitura

1. Consulta o índice de tópicos (seção 3) → pega o número do artigo.
2. Vai direto ao artigo pelo número.
3. Lê o caput. Se houver `(alterado pelo Art. X)` ou `(revogado, ver Art. X)`, salta para lá — não há necessidade de ler mais nada daquele artigo.
4. Se houver §, verifica se é pendência ainda aberta ou já resolvida (marcador de revogação do parágrafo, seção 2).

Nunca é necessário ler o documento inteiro nem manter uma tabela de status paralela — o próprio texto, através de alteração/revogação/hachura/remissão, sempre indica se está vigente e para onde ir se não estiver.
