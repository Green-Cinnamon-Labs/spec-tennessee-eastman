---
purpose: Working notes for Claude during the OPC-UA refactor (issue #55)
scope: spec-tennessee-eastman — but decisions affect tep-plant, tep-ihm, tep-operator
issue: https://github.com/Green-Cinnamon-Labs/spec-tennessee-eastman/issues/55
---

## What this folder is

This is the base directory for the OPC-UA implementation initiative (issue #55).
All documents here feed into sub-issues, architecture decisions, and eventually code changes across the sibling repos.

## Current architecture (before OPC-UA)

```
Browser ──WebSocket──► tep-ihm (FastAPI :8080)
                            │
                          gRPC StreamMetrics
                            │
                       tep-plant (Rust :50051)  ◄── gRPC UpdateController ── tep-operator (Go / Kind)
```

- **tep-plant**: Rust — source of truth for plant state, exposes gRPC
- **tep-ihm**: Python/FastAPI — HMI, consumes gRPC StreamMetrics, serves browser via WebSocket
- **tep-operator**: Go — evaluates PLCMachine CRD, calls UpdateController gRPC

## Why OPC-UA (IEC 62264)

- IEC 62264 defines the interface between enterprise and control systems (ISA-95 levels)
- OPC-UA is the recommended interoperability protocol at those boundaries
- gRPC is internal-only and not interoperable with external SCADA/MES tools
- OPC-UA provides: address space, subscriptions, alarms, historical access — all relevant here

## Key decisions to make (TBD)

- Which layer hosts the OPC-UA server? (tep-plant natively, or a gateway sidecar?)
- Do we replace gRPC entirely or run both protocols in parallel?
- What nodes go in the OPC-UA address space? (map XMEAS/XMAC to nodes)
- Which OPC-UA security profile? (None / Sign / SignAndEncrypt — lab context)
- Client strategy for tep-ihm and tep-operator (replace gRPC stubs or add UA client)

## Vocabulary / abbreviations used in this project

| Term           | Meaning                                                 |
| -------------- | ------------------------------------------------------- |
| XMEAS          | Plant measurements (41 variables, TEP outputs)          |
| XMAC           | Manipulated variables (12 inputs, controller setpoints) |
| TEP            | Tennessee Eastman Process                               |
| PLCMachine     | Kubernetes CRD managed by tep-operator                  |
| te-core        | Rust crate implementing the TEP simulation              |
| ControllerBank | P-controller set inside tep-plant                       |

## Sub-issues to open (draft)

- [ ] Architecture decision: OPC-UA server placement
- [ ] OPC-UA address space design (node mapping)
- [ ] tep-plant: add OPC-UA server (open62541 or opcua crate)
- [ ] tep-ihm: migrate from gRPC to OPC-UA subscription
- [ ] tep-operator: migrate from gRPC to OPC-UA monitored items
- [ ] Security profile definition
- [ ] Validation experiment spec

## Session log

| Date       | Note                                                                          |
| ---------- | ----------------------------------------------------------------------------- |
| 2026-06-29 | Folder created; kickoff doc drafted; issue #55 opened and added to project #6 |
