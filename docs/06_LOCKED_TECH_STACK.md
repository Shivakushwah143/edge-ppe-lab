# 06 — Locked Technology Stack

## Required

| Technology | Role in EdgePPE Lab | Runs where | Produces/consumes |
|---|---|---|---|
| Python 3.11+ | training, validation, API tooling | Ubuntu/WSL2 | code, environments, scripts |
| PyTorch | training framework under YOLO | Ubuntu/WSL2 | tensors/checkpoints |
| Ultralytics YOLO | detector training/export | Ubuntu/WSL2 | `best.pt`, metrics, export |
| MLflow Tracking | experiment history | local Linux server | run metadata/artifacts |
| MLflow Model Registry | model identity/version lineage | same MLflow server | registered versions/aliases/tags |
| ONNX | deployment graph format | artifact | model graph + weights |
| ONNX Runtime | CPU inference runtime | inference service | predictions |
| FastAPI | HTTP inference surface | Linux process/container | API responses |
| Uvicorn | ASGI process | Linux process/container | listening server process |
| Docker | packaging/runtime | WSL2/Linux integration | image + container |
| Docker Compose | only where useful for local supporting services | WSL2/Linux | local service orchestration |
| Prometheus client format | online metrics | inference process | `/metrics` |
| Git | source/version history | Linux repo | commits/tags |
| GitHub Actions | small CI pipeline | GitHub runner | validation + image candidate |

## MLflow local design decision

Use a local MLflow tracking server with a **database-backed backend store** (SQLite is acceptable for this single-user lab) and a local artifact directory. This keeps the lab small while supporting Model Registry behavior. For real shared production use, a managed/remote database and object storage would replace these local choices.

Use model **aliases and version tags** as the primary release semantics. Legacy model stages are not the center of this design. The active deployment pointer is `edge-ppe-detector@champion`.

## Optional future technologies

TensorRT, CUDA, NVIDIA GPU, Jetson, FP16, and NVIDIA Container Runtime are learning extensions only. The project must remain fully usable on CPU without NVIDIA hardware.

## Explicitly excluded

Kubernetes, Kafka, Redis, React, microservices, LangChain, agents, RAG, Temporal, service mesh, graph databases, and complex cloud infrastructure.

## Why exclusions matter

The training objective is depth, not architecture size. Every excluded tool would create additional failure domains before the learner has mastered the fundamental lifecycle of one model and one service.
