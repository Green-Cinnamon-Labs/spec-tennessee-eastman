# ISSUE_PROTOCOL.md

## Objetivo

Definir um fluxo curto para o Claude Code trabalhar com issues do `spec-tennessee-eastman` sem explorar o workspace inteiro.

---

## Regra principal

Antes de abrir arquivos ou editar código, o Claude deve:

1. Ler a issue indicada.
2. Identificar o tipo da tarefa.
3. Identificar o repo-alvo.
4. Propor um plano curto.
5. Listar os arquivos que pretende consultar ou alterar.

---

## Tipos de tarefa

| Tipo           | Quando usar                             |
| -------------- | --------------------------------------- |
| `bug`          | erro, falha, comportamento inesperado   |
| `feature`      | nova funcionalidade                     |
| `architecture` | decisão estrutural, modelagem, contrato |
| `docs`         | documentação, registro, monografia      |

---

## Mapa rápido de repo

| Assunto                                      | Repo provável            |
| -------------------------------------------- | ------------------------ |
| documentação, decisões, issues, experimentos | `spec-tennessee-eastman` |
| planta, Rust, RK4, XMEAS, XMV, IDV, gRPC     | `tep-plant`              |
| dashboard, FastAPI, WebSocket, Chart.js      | `tep-ihm`                |
| CRD, PLCMachine, Kubebuilder, reconcile      | `tep-operator`           |
| Docker Compose, Kind, scripts, ambiente      | `tep-supervisor`         |

---

## Resposta inicial obrigatória

Ao receber uma issue, responder primeiro:

## Leitura da issue

- Tipo:
- Repo-alvo:
- Objetivo:
- Arquivos prováveis:
- Próximo passo:

---

## Antes de editar

Antes de alterar qualquer arquivo, responder:

## Plano

1.
2.
3.

## Arquivos a tocar

- `repo/caminho/arquivo`

## Comandos a rodar

- `comando`

---

## Regras de economia

- Não varrer o workspace inteiro.
- Não abrir múltiplos repos sem necessidade explícita.
- Não ler `target/`, `dist/`, `.next/`, `node_modules/`, `gen/`, logs, CSVs grandes ou artefatos de build.
- Preferir `REPO_MAP.md`, `ARCHITECTURE.md` e `COMMANDS.md` antes de explorar código.
- Se faltar contexto, pedir o menor conjunto possível de arquivos.
- Responder em no máximo 2 parágrafos, salvo pedido contrário.

---

## Comentário em issue

Quando for comentar uma issue, usar:

## Atualização

**Resumo:**  
...

**Decisão / encaminhamento:**  
...

**Arquivos relacionados:**  
- ...

**Comandos executados:**  
- ...

**Pendências:**  
- ...

---

## Fechamento

Ao finalizar uma tarefa, responder:

## Fechamento

- Feito:
- Arquivos alterados:
- Comandos executados:
- Resultado:
- Pendências: