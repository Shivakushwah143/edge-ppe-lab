# Implementation Report

## Release summary

EdgePPE Lab is implemented as a compact, Linux-first CPU MLOps repository. The implementation follows the source-of-truth documents and the execution-mode override: the official Ultralytics Construction-PPE source is deterministically reduced to the canonical classes `Person`, `Hardhat`, and `NO-Hardhat`; training produces a real YOLO checkpoint; MLflow records the run and registers immutable model versions; ONNX export is gated by PT↔ONNX parity; FastAPI performs real ONNX Runtime inference; Linux, systemd, Docker, Prometheus, CI, model-v2, failure, and rollback paths are represented explicitly.

This report distinguishes **implemented code** from **runtime verification**. Runtime claims are recorded only in `VERIFICATION_REPORT.md` and evidence files.

## Implemented repository surfaces

### Data lifecycle

`scripts/prepare_dataset.py` downloads the official Ultralytics Construction-PPE archive when it is not already present. It preserves the upstream archive under `data/raw/`, maps upstream class IDs `6=Person`, `0=helmet`, `7=no_helmet` to canonical `0=Person`, `1=Hardhat`, `2=NO-Hardhat`, discards unrelated classes, and writes a reproducible compact subset by default. `--full` preserves the same transformation while processing the complete official split.

The generated `manifest.json` records source identity, source and canonical class maps, split image counts, annotation counts, class counts, preprocessing version/Git commit, generation time, and a dataset fingerprint. `scripts/verify_dataset.py` rejects class-map drift, missing splits, malformed labels, invalid normalized boxes, and canonical classes with zero annotations.

### Training and experiment tracking

`configs/train-v1.yaml` and `configs/train-v2.yaml` deliberately keep CPU training small. V2 is a real second run with changed seed, learning rate, and epoch count; it is not a renamed copy of v1.

`scripts/train.py` verifies the dataset before training, runs Ultralytics YOLO, requires a real `best.pt`, logs training parameters/metrics and dataset identity to MLflow, copies the selected checkpoint into the release directory, and writes release metadata. No synthetic metric, checkpoint, or detection path is present.

### Model Registry

`scripts/register_model.py` logs a real MLflow pyfunc model whose checkpoint lineage points to the selected YOLO artifact, registers it under `edge-ppe-detector`, records the immutable numeric registry version, and tags model lineage/status. `scripts/set_champion.py` refuses promotion unless parity passed; there is no parity-bypass flag. The mutable `champion` alias is the deployment pointer; the service resolves it to a concrete immutable version at startup.

### ONNX qualification

`scripts/export_onnx.py` exports a static CPU ONNX artifact, loads it with `onnx` and ONNX Runtime, records input/output/opset/provider contracts and SHA-256, logs the deployment artifact to the source MLflow run, and tags the registry version with exact ONNX identity.

`scripts/validate_parity.py` runs the same validation images through the PyTorch/Ultralytics checkpoint and the direct ONNX Runtime path. It compares classes, confidence deltas, boxes/IoU, unmatched detections, produces `parity_report.json`, logs parity metrics, and marks the registry version `passed` or `failed`. A failed parity gate exits non-zero and blocks normal promotion.

### Inference service

`app/main.py` implements:

- `GET /health` — process liveness.
- `GET /ready` — model readiness; returns 503 when no qualified model is loaded.
- `GET /model-info` — concrete registry version, alias, format, SHA-256, provider, load time, source run, and input contract.
- `POST /predict` — decodes a real uploaded image and performs direct ONNX Runtime inference.
- `GET /metrics` — Prometheus-format application/model metrics.

`app/model_runtime.py` supports the normal registry path (`champion` → concrete version → parity-tagged ONNX artifact) and an explicit concrete-artifact path for controlled deployment/failure drills. The normal registry path verifies downloaded artifact SHA-256 before creating the ONNX Runtime session.

### Linux operations

`START_HERE.md`, the Linux source-of-truth documentation, and `scripts/inspect_linux.sh` expose the lifecycle rather than hiding it behind orchestration. The learner manually starts MLflow, trains, registers, exports, promotes, runs Uvicorn, inspects processes/ports/env/resources/logs, runs systemd when available, and runs Docker when available.

### systemd

`deploy/systemd/edge-ppe.service` runs the API as a non-login `edgeppe` account from `/opt/edge-ppe-lab`, uses an external `/etc/edge-ppe/edge-ppe.env`, restarts on failure, and applies basic service hardening. `deploy/systemd/install.sh` installs the tree/venv/unit and correctly makes the environment file readable by group `edgeppe` while not making it world-readable.

### Docker

`docker/Dockerfile` uses Python 3.11 slim, a runtime-only dependency set, a non-root user, OCI Git revision metadata, and a readiness healthcheck. The documented container exercise mounts the already parity-qualified ONNX artifact read-only and sets the exact concrete registry version. This avoids falsely depending on WSL loopback networking to MLflow while still proving the production inference container against the exact qualified artifact.

### Observability

The API exports `inference_requests_total`, `inference_failures_total`, `inference_latency_seconds`, `detections_total`, and `model_info`. Training metrics such as precision/recall/mAP remain ML/model-quality metrics rather than being conflated with service health metrics.

### CI/CD candidate pipeline

`.github/workflows/ci.yml` installs the locked environment on Python 3.11, compiles Python, runs tests, validates a committed ONNX contract if one is intentionally present, and builds a Docker candidate tagged by Git SHA. It intentionally stops before inventing a cloud deployment target.

## Deliberately excluded

The implementation does not add Kubernetes, Kafka, Redis, a frontend, RAG, agents, microservices, or complex cloud infrastructure. TensorRT/CUDA/NVIDIA/Jetson remain a documented future extension and are not required for the CPU lab.

## Build-state conclusion

The repository is implementation-complete for the requested lab surface. Full runtime qualification of the model lifecycle could not be performed in the execution sandbox because the sandbox could not download the official dataset or missing Python packages and did not provide Docker/systemd runtime capabilities. Those are recorded as environmental blockers rather than converted into fake success.
