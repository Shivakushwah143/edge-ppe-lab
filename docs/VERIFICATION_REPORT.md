# Verification Report

Verification timestamp: **2026-09-16 UTC**

Status vocabulary is intentionally strict:

- **VERIFIED** — executed in the current environment and evidence captured.
- **IMPLEMENTED — NOT RUNTIME VERIFIED** — implementation exists, but this environment cannot execute the required runtime.
- **BLOCKED** — a prerequisite needed to perform the exercise is unavailable in this environment.

## Verification matrix

| Capability | Status | Evidence / reason |
|---|---|---|
| Repository Python compilation | VERIFIED | `docs/evidence/15_post_audit_validation.txt`; exit 0 |
| Unit tests | VERIFIED | 7/7 passed in `15_post_audit_validation.txt` |
| Shell syntax | VERIFIED | `bash -n` passed for scripts and systemd installer |
| CI YAML parse | VERIFIED | Workflow parsed as YAML |
| Official dataset source/class mapping | VERIFIED at source/config level | Preprocessing source map matches official Construction-PPE YAML; actual archive fetch blocked by sandbox DNS |
| Dataset download/preparation | BLOCKED | `03_dataset_attempt.txt`: official GitHub asset could not resolve from sandbox |
| Dataset manifest generation on real data | BLOCKED | Depends on dataset download |
| YOLO v1 training / real `best.pt` | BLOCKED | Missing `ultralytics` and MLflow; dependency install blocked by DNS |
| MLflow server startup | BLOCKED | `mlflow` package absent and cannot be installed here |
| MLflow run logging | BLOCKED | Same prerequisite |
| Registry model v1 | BLOCKED | Requires successful run + MLflow server |
| Registry `champion → v1` | BLOCKED | Requires registry v1 + parity pass |
| Promotion parity gate | VERIFIED | `14_release_gate.txt`: a failed-parity release is rejected with non-zero exit; no bypass flag exists |
| ONNX v1 export | BLOCKED | `ultralytics`, `onnx`, and `onnxruntime` unavailable |
| PT↔ONNX parity v1 | BLOCKED | Requires real checkpoint and ONNX artifact |
| FastAPI `/health` degraded-mode behavior | VERIFIED | `05_degraded_api_runtime.txt`: HTTP 200 |
| FastAPI `/ready` fails without model | VERIFIED | Same evidence: HTTP 503 with concrete startup error |
| Prometheus endpoint in degraded mode | VERIFIED | Same evidence contains inference and model metrics |
| Uvicorn process inspection | VERIFIED | Same evidence: `ps` shows Uvicorn PID |
| Port inspection | VERIFIED | Same evidence: `ss` shows bound port 8091 |
| Real `/predict` | BLOCKED | No qualified ONNX artifact could be produced |
| `/model-info` with concrete v1 | BLOCKED | No qualified ONNX/registry version |
| systemd files | IMPLEMENTED — NOT RUNTIME VERIFIED | `systemctl is-system-running` reports `offline` |
| Dockerfile/runtime path | IMPLEMENTED — NOT RUNTIME VERIFIED | `docker` command is unavailable in sandbox |
| Docker real `/predict` | BLOCKED | Docker unavailable and no qualified model artifact |
| CI workflow | IMPLEMENTED — NOT RUNTIME VERIFIED | Workflow syntax validated locally; GitHub Actions runner not available here |
| Real v2 training/registration | BLOCKED | Same training/MLflow prerequisites as v1 |
| Healthy v2 deployment | BLOCKED | Requires v2 lifecycle completion |
| Runtime v2 failure → registry rollback → v1 | BLOCKED | Requires concrete registry versions v1/v2 |

## Verified failure/operations exercises

The current Linux sandbox was sufficient to execute several real operations and failure exercises:

- Wrong explicit model path causes strict startup failure with `FileNotFoundError` (`06_failure_wrong_model_path.txt`).
- Missing `EDGE_PPE_MODEL_VERSION` with an explicit path fails startup with a clear configuration error (`07_failure_missing_env.txt`).
- A non-owner account receives real `Permission denied` when reading a restricted model file (`08_failure_permission_denied.txt`).
- `ss -lntp` identifies a deliberately occupied port and a second server fails with `Address already in use` (`09_failure_port_occupied.txt`).
- Process termination is visible through `ps` (`10_process_crash_observation.txt`).
- CPU, RAM, disk and working-tree size were inspected with `top`, `free`, `df`, and `du` (`11_resource_inspection.txt`).
- MLflow-unavailable behavior is explicit: strict startup fails; degraded mode can stay alive while `/ready` remains 503 (`05_degraded_api_runtime.txt`).

Docker-container-exit diagnosis cannot be truthfully marked verified because Docker is unavailable in the current sandbox.

## Environment facts

The final probe (`15_post_audit_validation.txt`) shows Linux x86_64, Python 3.13.5 in the sandbox, CPU PyTorch available, FastAPI/Uvicorn/OpenCV available, but `ultralytics`, `mlflow`, `onnx`, and `onnxruntime` absent. The project itself targets Python 3.11+ as requested; Python 3.11 is used in the Docker image and CI configuration.

## What remains for full qualification on the user's WSL2 Ubuntu environment

Run `START_HERE.md` from top to bottom with network access. The first complete qualification must produce the real dataset manifest, v1 `best.pt`, MLflow run and registry v1, ONNX v1 and parity report, real API prediction, Docker prediction, then a genuinely distinct v2 followed by the safe failure and `champion` rollback to v1. The resulting `/model-info`, `/ready`, prediction, MLflow UI/API, Docker/systemd logs, and release JSON files are the evidence that upgrades these rows from BLOCKED to VERIFIED.
