# REPO_MAP.md

## Objetivo

Este arquivo orienta o Claude Code a escolher o repositório correto antes de ler arquivos ou propor alterações.

## Regra principal

Antes de abrir arquivos, classifique a tarefa em um dos alvos:

| Tipo de tarefa                                     | Repo-alvo                | Ler primeiro                              |
| -------------------------------------------------- | ------------------------ | ----------------------------------------- |
| Issue, decisão, roadmap, experimento, texto de TCC | `spec-tennessee-eastman` | Issue indicada ou `docs/`                 |
| Modelo TEP, RK4, XMEAS, XMV, IDV, snapshot, CSV    | `tep-plant`              | `tennessee-eastman-service/`              |
| Dashboard, WebSocket, gráficos, FastAPI            | `tep-ihm`                | `src/`, `proto/`, arquivos de frontend    |
| CRD, controller, reconciliation, Kubebuilder       | `tep-operator`           | `api/`, `internal/controller/`, `config/` |
| Docker, Kind, deploy local, scripts                | `tep-supervisor`         | `local/`, `docker-compose.yml`, scripts   |

## Protocolo de leitura

1. Identifique o repo-alvo.
2. Explique em uma frase por que esse repo é o alvo.
3. Liste no máximo 5 arquivos/diretórios que pretende abrir.
4. Só leia outro repo se houver dependência explícita.
5. Se faltar contexto, peça o arquivo exato em vez de explorar o workspace inteiro.

## Casos comuns

### Revisar modelagem ou ideia

Repo-alvo: `spec-tennessee-eastman`.

Ação esperada:
- Ler a issue ou markdown indicado.
- Produzir crítica curta.
- Registrar decisão em `/docs`, se solicitado.

### Ler issue e comentar

Repo-alvo: `spec-tennessee-eastman`.

Ação esperada:
- Ler a issue.
- Identificar repo técnico envolvido.
- Propor comentário objetivo.
- Não editar código sem pedido explícito.

### Diagnosticar bug

Repo-alvo: depende do bug.

Ação esperada:
- Perguntar/identificar sintoma.
- Localizar repo provável.
- Ler logs/arquivos mínimos.
- Explicar causa provável antes de alterar código.

### Implementar alteração

Repo-alvo: repo técnico correspondente.

Ação esperada:
- Plano curto.
- Arquivos a tocar.
- Alteração pequena.
- Teste/comando de validação.