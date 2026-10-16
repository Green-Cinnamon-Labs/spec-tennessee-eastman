# Archive

Material from earlier phases of the project, kept for the record. It is **not** a description of the current system: most of it predates the move to OPC UA and describes a plant that served gRPC, a `ControllerBank` inside the simulation loop and a Kubernetes operator built around a `PLCMachine` resource. None of that exists anymore.

| Folder | What it was |
|---|---|
| [`ai/`](ai/) | Instructions written for a coding assistant (repository map, commands, issue protocol, architecture overview), from the gRPC phase. |
| [`notes/`](notes/) | Learning notes from the same phase: how experiments were run, the old disturbance system, protobuf regeneration, WSL2 builds, FastAPI and asyncio (the concepts still hold, the examples use the old gRPC stream). |

For the current system, start at the [repository README](../../README.md).
