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

`deploy/systemd/edge-ppe.service` runs the API as an in-place deployment of the repository: `WorkingDirectory` and `ExecStart` are the absolute paths of the real tree (`/home/shiva_kushwah/projects/edge-ppe-lab` and its `.venv/bin/uvicorn`), with no reliance on an activated virtualenv, on `~` expansion, or on the caller's environment. It reads `/etc/edge-ppe/edge-ppe.env`, uses `Restart=on-failure` with `RestartSec=3`, and applies `NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=full` and `ReadWritePaths=<tree>/var`. `ProtectHome=false` and `User=shiva_kushwah` are deliberate: the deployment root is inside the operator's home directory (`0750`), so a dedicated service account would have required loosening the home directory; relocating the tree to `/opt` with an `edgeppe` account is the hardening upgrade path.

`deploy/systemd/install.sh` installs that unit verbatim and refuses to proceed unless the unit's `WorkingDirectory` matches the tree it was pointed at and the interpreter is executable, so the installed unit cannot silently serve a different copy of the code. It seeds `/etc/edge-ppe/edge-ppe.env` from `edge-ppe.env.example` with the same absolute model-cache path and leaves it `0640`.

### Docker

`docker/Dockerfile` uses Python 3.11 slim, a runtime-only dependency set, a non-root user, OCI Git revision metadata, and a readiness healthcheck. The runtime set installs `mlflow-skinny` rather than full `mlflow`, because the runtime only needs `mlflow.set_tracking_uri` + `MlflowClient`; that removes pandas, matplotlib, scipy, scikit-learn, docker and flask from the image. The pip step sets `PIP_DEFAULT_TIMEOUT=180` and `PIP_RETRIES=10`, retries the whole resolve up to three times, and mounts a BuildKit pip cache so a slow or aborted build resumes rather than re-downloading. The resulting image is CPU-only: it contains no torch, ultralytics or CUDA packages, and `onnxruntime` exposes only `AzureExecutionProvider` + `CPUExecutionProvider`.

The documented container exercise mounts the already parity-qualified ONNX artifact read-only and sets the exact concrete registry version. This avoids falsely depending on WSL loopback networking to MLflow while still proving the production inference container against the exact qualified artifact.

### Observability

The API exports `inference_requests_total`, `inference_failures_total`, `inference_latency_seconds`, `detections_total`, and `model_info`. Training metrics such as precision/recall/mAP remain ML/model-quality metrics rather than being conflated with service health metrics.

### CI/CD candidate pipeline

`.github/workflows/ci.yml` installs the locked environment on Python 3.11, compiles Python, runs tests, validates a committed ONNX contract if one is intentionally present, and builds a Docker candidate tagged by Git SHA. It intentionally stops before inventing a cloud deployment target.

## Deliberately excluded

The implementation does not add Kubernetes, Kafka, Redis, a frontend, RAG, agents, microservices, or complex cloud infrastructure. TensorRT/CUDA/NVIDIA/Jetson remain a documented future extension and are not required for the CPU lab.

## Build-state conclusion

The repository is implementation-complete for the requested lab surface, and the CPU model lifecycle has since been **executed end to end on the user's WSL2 environment**: real dataset preparation, real v1 and v2 training runs, MLflow tracking and immutable registry versions (v1 and v2), ONNX export with `onnx.checker` validation, real PT↔ONNX parity for both releases, alias-driven promotion, real CPU inference from both the host service and the Docker container, a controlled deployment failure with full diagnosis, and a real rollback to v1. See `VERIFICATION_REPORT.md` and `docs/evidence/RUNTIME_LIFECYCLE_VERIFICATION.md`.

An earlier build session ran in a restricted sandbox that could not download the dataset or PyPI packages and had no Docker; those entries remain only as historical evidence files and are no longer the current state.

The systemd unit has since been **installed and runtime-verified**: the `edge-ppe` service is enabled
and `active (running)` on `:8000`, generated journal evidence, survived a real `kill -9` through
`Restart=on-failure`, and served a real `/predict` as champion version 1
(`docs/evidence/systemd_runtime_verification.txt`). The promotion path was also tightened so the
`release_status` tags can no longer contradict the `champion` alias
(`docs/evidence/registry_tag_hygiene.txt`). The only surfaces still not runtime-verified are the
GitHub Actions workflow (no hosted runner) and any GPU/TensorRT/Jetson path (no NVIDIA hardware).
