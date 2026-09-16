# Requirements Traceability

This matrix maps the execution-mode requirements to concrete implementation locations and current verification state.

| Requirement | Implementation | Verification state |
|---|---|---|
| Official Construction-PPE source | `scripts/prepare_dataset.py` official Ultralytics asset URL | Source/config verified; runtime download BLOCKED |
| Canonical 3-class mapping | `UPSTREAM_TO_CANONICAL={6:0,0:1,7:2}`, `data/ppe.yaml` | VERIFIED by unit/config checks |
| Reproducible preprocessing | `prepare_dataset.py`, deterministic name hash selection, `manifest.json` | IMPLEMENTED; real-data run BLOCKED |
| Dataset manifest/fingerprint | `prepare_dataset.py::dataset_fingerprint` and manifest fields | IMPLEMENTED; generation BLOCKED |
| Real lightweight YOLO training | `scripts/train.py`, `configs/train-v1.yaml` | BLOCKED by dependencies/data |
| Real distinct model v2 | `configs/train-v2.yaml` changes epochs/seed/lr0; same training pipeline | IMPLEMENTED; runtime BLOCKED |
| MLflow Tracking | `scripts/start_mlflow.sh`, `scripts/train.py` | BLOCKED by missing MLflow install |
| Model Registry numeric versions | `scripts/register_model.py` | IMPLEMENTED; runtime BLOCKED |
| `champion` alias | `scripts/set_champion.py`, `RuntimeModel.from_settings` | Current MLflow alias API used; runtime BLOCKED |
| Resolve alias to concrete version | `app/model_runtime.py` | IMPLEMENTED; runtime BLOCKED |
| ONNX export | `scripts/export_onnx.py` | IMPLEMENTED; runtime BLOCKED |
| Record input/output/opset/SHA/lineage | `onnx_contract.json`, release JSON, MLflow tags | IMPLEMENTED; runtime BLOCKED |
| Real PT↔ONNX parity | `scripts/validate_parity.py` | IMPLEMENTED; runtime BLOCKED |
| Machine-readable parity report | `var/releases/<release>/parity_report.json` | IMPLEMENTED; runtime BLOCKED |
| Block promotion on failed parity | `scripts/set_champion.py` + `docs/evidence/14_release_gate.txt` | VERIFIED negative gate; real registry promotion BLOCKED |
| `GET /health` | `app/main.py` | VERIFIED in degraded runtime |
| `GET /ready` | `app/main.py` | VERIFIED returns 503 without model |
| `GET /model-info` | `app/main.py` | IMPLEMENTED; successful-model response BLOCKED |
| `POST /predict` real ONNX inference | `OnnxDetector.predict_*`, API endpoint | IMPLEMENTED; real artifact runtime BLOCKED |
| `GET /metrics` | `app/metrics.py`, API endpoint | VERIFIED in degraded runtime |
| Linux process/port/env/resource inspection | `START_HERE.md`, `inspect_linux.sh` | Partially VERIFIED with evidence |
| systemd unit | `deploy/systemd/edge-ppe.service`, installer/env | IMPLEMENTED — NOT RUNTIME VERIFIED |
| Docker production-oriented image | `docker/Dockerfile`, `requirements-runtime.txt` | IMPLEMENTED — NOT RUNTIME VERIFIED |
| Non-root Docker runtime | Dockerfile `edgeppe` user | IMPLEMENTED — NOT RUNTIME VERIFIED |
| Immutable image identity | Git-SHA image tag + OCI revision build arg in `START_HERE.md` | IMPLEMENTED — NOT RUNTIME VERIFIED |
| Model/system Prometheus metrics | `app/metrics.py` | Endpoint VERIFIED; inference counters need real prediction |
| Compact GitHub Actions pipeline | `.github/workflows/ci.yml` | YAML VERIFIED; hosted execution NOT RUNTIME VERIFIED |
| Safe failure labs | code + `START_HERE.md` + evidence | 7 diagnostic exercises verified/partially verified; Docker and full rollback blocked |
| Rollback v2→v1 | `set_champion.py` + manual restart procedure | IMPLEMENTED; end-to-end runtime BLOCKED |
| WSL2 manual journey | `START_HERE.md` | IMPLEMENTED |
| Preserve source-of-truth docs | `docs/01...23`, diagrams, references | VERIFIED present |
| No Kubernetes/Kafka/Redis/frontend/RAG/agents | repository audit | VERIFIED absent from implementation |
| Future TensorRT/Jetson path only | source-of-truth docs | VERIFIED not required by runtime |
| Build-phase reports | `IMPLEMENTATION_REPORT.md`, `VERIFICATION_REPORT.md`, `KNOWN_LIMITATIONS.md`, this file, `FAILURE_VERIFICATION.md` | VERIFIED present |
