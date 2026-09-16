# EdgePPE Lab — Production Model Lifecycle on Linux

EdgePPE Lab is a deliberately small, Linux-first MLOps lab for a three-class PPE detector:

- `0 = Person`
- `1 = Hardhat`
- `2 = NO-Hardhat`

The learning lifecycle is:

`official Construction-PPE dataset → deterministic canonical preprocessing → YOLO training → MLflow Tracking → MLflow Model Registry → registered v1/v2 → ONNX export → PT↔ONNX parity gate → FastAPI + ONNX Runtime → Linux operations → Docker/systemd → monitoring → failure drill → rollback`

Start with [`START_HERE.md`](START_HERE.md). The original source-of-truth documents are preserved under `docs/`.

## Build and verification status

The implementation is complete, but this build sandbox could not download the official dataset or missing MLflow/Ultralytics/ONNX dependencies and does not provide Docker or a running systemd instance. No model-lifecycle success is fabricated. See `docs/VERIFICATION_REPORT.md`, `docs/KNOWN_LIMITATIONS.md`, and `docs/evidence/` for exact VERIFIED / BLOCKED evidence. On your WSL2 Ubuntu machine, follow `START_HERE.md` to generate and qualify v1/v2 end to end.

## Design guardrails

CPU operation is mandatory. NVIDIA/CUDA/TensorRT/Jetson are future extensions only. There is no Kubernetes, Kafka, Redis, frontend, RAG, agent framework, or microservice sprawl.

## Dataset provenance

The preparation script downloads the official Ultralytics Construction-PPE archive and maps only upstream `Person`, `helmet`, and `no_helmet` into the canonical class IDs. Unrelated upstream labels are discarded; annotations are never fabricated.
