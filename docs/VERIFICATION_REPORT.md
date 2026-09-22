# Verification Report

Verification timestamp: **2026-09-22 UTC** (executed on the user's WSL2 Ubuntu environment)

Status vocabulary is intentionally strict:

- **VERIFIED** — executed in this environment and evidence captured.
- **IMPLEMENTED — NOT RUNTIME VERIFIED** — implementation exists, but this environment did not execute it.
- **BLOCKED** — a prerequisite needed to perform the exercise is unavailable in this environment.
- **FAILED** — executed and did not meet its acceptance criteria.

Environment: Ubuntu 24.04.3 LTS on WSL2 (kernel 6.18.33.2-microsoft-standard-WSL2), Intel i3-1005G1
(4 cores, 7 GiB RAM), **no NVIDIA GPU**, Python 3.12.3 in `~/.edge-ppe-venv` (training/MLflow) and
in the project's own `/home/shiva_kushwah/projects/edge-ppe-lab/.venv` (the systemd service
interpreter), torch 2.14.0+cpu, ultralytics 8.4.153, onnx 1.22.0, onnxruntime 1.30.0 (CPU only),
MLflow 3.16.0, systemd PID 1 (`systemctl is-system-running` → `running`), Docker 29.2.1.

## Verification matrix

| Capability | Status | Evidence / reason |
|---|---|---|
| Repository Python compilation | VERIFIED | `docs/evidence/15_post_audit_validation.txt`; exit 0 |
| Unit tests | VERIFIED | 7/7 passed in `15_post_audit_validation.txt` |
| Shell syntax | VERIFIED | `bash -n` passed for scripts and systemd installer |
| CI YAML parse | VERIFIED | Workflow parsed as YAML |
| Official dataset source/class mapping | VERIFIED | `var/releases/v1/release.json` and `v2` dataset verification blocks: official archive prepared, canonical classes Person/Hardhat/NO-Hardhat |
| Dataset download/preparation | VERIFIED | `data/processed/ppe-v1/manifest.json`; splits train 180 / val 60 / test 60 images, 0 missing label files |
| Dataset manifest generation on real data | VERIFIED | Same manifest + dataset verification recorded in both release files and logged to MLflow |
| YOLO v1 training / real `best.pt` | VERIFIED | run `c283e4ec…`, checkpoint 5,427,418 bytes in `var/releases/v1/` |
| MLflow server startup | VERIFIED | `mlflow server … --port 5000` running with SQLite backend + artifact store |
| MLflow run logging | VERIFIED | `docs/evidence/v2_mlflow_run_registry_onnx_metadata.txt` (params, metrics, tags, artifacts) |
| Registry model v1 | VERIFIED | version 1, run `c283e4ecf…`, source `models:/m-82c41e07fc08423397e93dbc788409ef` |
| Registry `champion → v1` | VERIFIED | alias API returns version 1 after the rollback (`v2_rollback_to_v1.txt`) |
| Registry tag hygiene on promotion | VERIFIED | `set_champion.py` demotes any other `release_status=champion` version to `qualified`; after re-promotion v1=`champion`, v2=`qualified`, alias→1 (`registry_tag_hygiene.txt`) |
| Real distinct model v2 | VERIFIED | run `133cc86b…`, version 2, different seed/lr0/epochs; ONNX SHA differs from v1 (`43e14f64…` vs `e22e6aeb…`) |
| Promotion parity gate | VERIFIED | Negative case `14_release_gate.txt`; positive case: only a `parity_status=passed` release could be promoted to version 2 |
| ONNX v1 export | VERIFIED | `var/releases/v1/model.onnx`, 10,440,792 bytes, SHA `e22e6aeb…` |
| PT↔ONNX parity v1 | VERIFIED | `docs/evidence/v1-onnx-parity.json`, min IoU 0.9999836536246481 |
| ONNX v2 export | VERIFIED | `var/releases/v2/model.onnx`, 10,440,792 bytes, SHA `43e14f64…`, opset 17, `onnx.checker` PASS |
| PT↔ONNX parity v2 | VERIFIED | `docs/evidence/v2-onnx-parity.json`, min IoU 0.999982796774978, max conf delta 9.26e-07, 0 unmatched |
| Registry version 2 with ONNX identity | VERIFIED | version 2 tags: `onnx_artifact_path=deployment/v2/model.onnx`, `onnx_sha256=43e14f64…`, `parity_status=passed` |
| FastAPI `/health` | VERIFIED | 200 on both the registry-mode service and the Docker container (`final_state_verification.txt`) |
| FastAPI `/ready` | VERIFIED | 200 with concrete model version; 503 without a model (`05_degraded_api_runtime.txt`) |
| `/model-info` with concrete version | VERIFIED | reported version 1 and version 2 across the lifecycle, with provider `CPUExecutionProvider` |
| Real `/predict` (host service) | VERIFIED | 200, real Hardhat/Person detections; v1 rollback reproduces the v1 parity numbers exactly |
| Real `/predict` (Docker container) | VERIFIED | 200, real detections for v1 and v2 (`v2_runtime_verification.txt`) |
| Prometheus endpoint in degraded mode | VERIFIED | `05_degraded_api_runtime.txt` |
| Prometheus metric deltas under real load | VERIFIED | requests 0→3, failures 0, latency count/sum, `detections_total` per class, `model_info` with version/sha (`v2_runtime_verification.txt`) |
| Registry-alias-driven deployment | VERIFIED | restarting the service resolved `champion` → v2 and **downloaded** the qualified artifact into `var/model-cache/v2/model.onnx` (SHA match) |
| Champion rollback v2 → v1 (runtime) | VERIFIED | alias repointed, both surfaces restarted and re-verified as v1 (`v2_rollback_to_v1.txt`) |
| Controlled deployment failure (invalid artifact path) | VERIFIED | container `exit_code=3`, `FileNotFoundError`, port dead, artifact and registry untouched (`v2_controlled_deployment_failure.txt`) |
| Dockerfile/runtime path | VERIFIED | image `edge-ppe-lab:local` built `EXIT=0`, 569 MB, CPU-only (no torch/pandas/matplotlib/scipy/sklearn) |
| Docker real `/predict` | VERIFIED | container healthy, real predictions for v1 and v2 |
| Uvicorn process inspection | VERIFIED | `ps` / `ss` evidence across the lifecycle |
| Port inspection | VERIFIED | `ss` shows `:5000`, `:8000`, `:18000`; occupied-port failure `09_failure_port_occupied.txt` |
| systemd unit installed | VERIFIED | `deploy/systemd/install.sh` installed `/etc/systemd/system/edge-ppe.service` and `/etc/edge-ppe/edge-ppe.env` with the real tree paths (`systemd_runtime_verification.txt`) |
| systemd service enabled + active | VERIFIED | `is-enabled=enabled`, `is-active=active`, `systemctl status` shows the unit; the hand-started Uvicorn was stopped so systemd owns `:8000` |
| systemd journal logging | VERIFIED | `journalctl -u edge-ppe -n 100 --no-pager` shows startup, model load with the v1 SHA-256, and HTTP access lines |
| systemd supervised restart | VERIFIED | `Restart=on-failure`: `kill -9` of the main PID produced `NRestarts=1`, the unit returned to `active (running)` and `/ready` was 200 again |
| systemd service serves the champion | VERIFIED | after `systemctl restart`, `/ready` model_version 1, `/model-info` version 1 / alias `champion` / CPU, `/predict` real Hardhat+Person |
| CI workflow | IMPLEMENTED — NOT RUNTIME VERIFIED | Workflow validated locally; no hosted runner executed it |
| GPU / TensorRT / Jetson path | BLOCKED | No NVIDIA GPU (`nvidia-smi` absent, `torch.cuda.is_available()==False`) |

## Executed failure/operations exercises

- Wrong explicit model path causes strict startup failure with `FileNotFoundError` (`06_failure_wrong_model_path.txt`).
- Missing `EDGE_PPE_MODEL_VERSION` with an explicit path fails startup with a clear configuration error (`07_failure_missing_env.txt`).
- A non-owner account receives real `Permission denied` when reading a restricted model file (`08_failure_permission_denied.txt`).
- `ss -lntp` identifies a deliberately occupied port and a second server fails with `Address already in use` (`09_failure_port_occupied.txt`).
- Process termination is visible through `ps` (`10_process_crash_observation.txt`).
- CPU, RAM, disk and working-tree size were inspected with `top`, `free`, `df`, and `du` (`11_resource_inspection.txt`).
- MLflow-unavailable behavior is explicit: strict startup fails; degraded mode can stay alive while `/ready` remains 503 (`05_degraded_api_runtime.txt`).
- **NEW — Docker container exit diagnosis**: a container deliberately deployed with an invalid model path exits with code 3, `docker logs` shows the exact `FileNotFoundError`, the port is not bound, and the qualified artifact is provably untouched (`v2_controlled_deployment_failure.txt`).
- **NEW — full v2 lifecycle and rollback**: promotion → healthy v2 → injected config failure → real rollback to v1 → healthy v1 (`docs/evidence/RUNTIME_LIFECYCLE_VERIFICATION.md`).

## Environment facts

Python 3.12.3 in `~/.edge-ppe-venv`; torch 2.14.0+cpu with `cuda_available=False`; FastAPI, Uvicorn,
OpenCV, ultralytics, mlflow, onnx and onnxruntime all importable. Docker 29.2.1 available. The
project targets Python 3.11+; the Docker image and CI use Python 3.11.

## What remains unverified

Two things on this machine are not runtime-verified: the **GitHub Actions workflow** (no hosted
runner) and any **GPU/TensorRT/Jetson** path (no NVIDIA hardware). Everything else on the CPU model
lifecycle — data → training → registry → ONNX → parity → promotion → CPU inference → failure →
rollback → systemd supervision — has been executed and evidenced.

## Step 4 addendum — systemd and registry metadata (2026-09-22)

Executed after the lifecycle above, without retraining and without repeating the failure/rollback
steps:

- `scripts/set_champion.py` no longer leaves `release_status=champion` on the superseded version.
  Promotion demotes every other version that still claims it to `release_status=qualified` and then
  tags the promoted version `champion`. Aliases + version tags only — **no deprecated MLflow stage**
  is read or written. Verified: alias → version 1, v1 `champion`, v2 `qualified`.
- The API now runs as the enabled systemd unit `edge-ppe` on `:8000` (the earlier hand-started
  Uvicorn was stopped, since only one process can bind the port). `sudo systemctl daemon-reload`,
  `enable`, `start`, `status`, `journalctl -u edge-ppe`, `restart` and a real `/predict` were all
  executed; a `kill -9` of the main PID proved `Restart=on-failure`.
- The Docker container was not touched and remained `running/healthy` on `:18000` serving v1.

Evidence: `docs/evidence/systemd_runtime_verification.txt`, `docs/evidence/registry_tag_hygiene.txt`.
