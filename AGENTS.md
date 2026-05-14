# AGENTS.md

This file provides guidance to OpenAI Codex when working with code in this repository.

## Role of this repository

`spec-tennessee-eastman` does not contain executable source code. It is the lab's entry point: specifications, experiment log, open assignments, and architectural decisions. Any code changes should be made in the sibling technical repositories.

## Context Files

Read these before opening any other file:

| File                          | When to use                                                      |
| ----------------------------- | ---------------------------------------------------------------- |
| `tasks.md`                    | Current operational status — open issues and experiment sequence |
| `experiments.md`              | Scientific history — observations, hypotheses, results           |
| `docs/ai/REPO_MAP.md`         | Routing by task type — which technical repo to touch             |
| `docs/ai/ARCHITECTURE.md`     | Lab architecture and structural rules                            |
| `docs/ai/COMMANDS.md`         | Commands per repo (build, run, test, diagnostic)                 |
| `docs/ai/ISSUE_PROTOCOL.md`   | Flow for reading and commenting on issues                        |
| `docs/forDummies/commands.md` | Complete lab operation sequence (Windows)                        |

## Work Rules
1. Identify the target repo (`spec`, `plant`, `ihm`, `operator`, or `supervisor`) before opening files.
2. Do not read multiple repos without explicit need.
3. When receiving an issue, read it first and then list which files you need to open.
4. Before editing any file, present a short plan and a list of files to be addressed.
5. Respond in a maximum of 2 paragraphs, unless otherwise requested.
6. Prefer `docs/ai/` over extensive exploration of the workspace.

## Lab Architecture

```
Browser ──WebSocket──► tep-ihm (FastAPI :8080)
                            │
                          gRPC StreamMetrics
                            │
                       tep-plant (Rust :50051)  ◄── gRPC UpdateController ── plc-operator (Go / Kind)
                            │
                         RK4 loop (dt = 0,001 h/step)
                            │
                       te-core + ControllerBank (3 P-controllers)
```

- The plant exposes: `StreamMetrics`, `GetPlantStatus`, `ListControllers`, `UpdateController`.
- The operator evaluates the CRD `PLCMachine` and calls `UpdateController` when XMEAS go out of range.
- **Connectivity:** HMI → plant via `te-plant:50051` (Docker Compose); operator → plant via `host.docker.internal:50051` (Kind).
- **Canonical protocol:** in `tep-plant`. Manual copies in `tep-operator/proto/` and `tep-ihm/proto/`.
- **`make generate manifests`** only works on Linux — use GitHub Codespace on Windows.


## Issue Workflow

Upon receiving an issue, respond with:

```text
Type: bug | feature | architecture | docs
Target Repo: <name>
Objective: <one line>
Likely files: <short list>
Next step: <action>
```

Before editing, present:

```
Plan: <numbered steps>
Files to address: <list>
Commands to suggest: <list>
```

Do not run Docker, Kind, kubectl, deploy, destructive, or environment-changing commands unless explicitly authorized. Prefer suggesting the command and explaining its purpose in one line.