# Failure Verification

## Evidence convention

A failure lab is considered verified only when the failure was actually induced and command/output evidence was captured. Source inspection alone is not verification.

| Failure exercise | Status | Symptom / evidence | Root cause / fix path |
|---|---|---|---|
| Wrong model path | VERIFIED | Strict Uvicorn startup exits with `FileNotFoundError`; `06_failure_wrong_model_path.txt` | Incorrect `EDGE_PPE_MODEL_PATH`; verify with `pwd/ls/find`, correct path, restart |
| Missing required environment value | VERIFIED | Explicit model path without version exits with clear runtime config error; `07_failure_missing_env.txt` | `EDGE_PPE_MODEL_VERSION` missing; inspect `env`, set paired value, restart |
| Permission denied reading model | VERIFIED | `nobody` cannot read root-owned `0600` model; `08_failure_permission_denied.txt` | OS file ownership/mode; inspect `ls -l`, apply least-privilege `chown/chmod` |
| Port occupied | VERIFIED | `ss` shows owner; second bind fails `Errno 98`; `09_failure_port_occupied.txt` | Existing process owns port; inspect PID, stop/reconfigure appropriate process/port |
| Inference/service process crashes | VERIFIED at process level | Killed process disappears from `ps`; `10_process_crash_observation.txt` | Process exit; supervised deployment should restart according to systemd/container policy |
| Docker container exits | BLOCKED | Docker command unavailable | On WSL2: `docker ps -a`, `docker logs`, `docker inspect`, fix env/mount/path, recreate |
| High CPU/RAM inspection | VERIFIED | `top` and `free` captured; `11_resource_inspection.txt` | Diagnostic exercise completed; no artificial resource exhaustion was needed |
| Disk-space inspection | VERIFIED | `df` and `du` captured; `11_resource_inspection.txt` | Diagnostic exercise completed; destructive disk filling intentionally avoided |
| MLflow unavailable | VERIFIED | Model resolution reports missing MLflow dependency; degraded API stays live but `/ready`=503; `05_degraded_api_runtime.txt` | Tracking/registry dependency unavailable; restore MLflow/package/network then restart |
| Healthy v2 → bad deployment config → rollback v1 | BLOCKED | Requires real v1/v2 model versions that could not be produced | On WSL2: prove healthy v2, inject bad explicit artifact path/config, diagnose, repoint `champion` to v1, restart and prove v1 via `/model-info` + `/predict` |

## Safe v2 rollback drill to run on WSL2

Do not corrupt the validated v2 ONNX file and do not falsify parity. First prove `champion` resolves to the concrete v2 version, `/ready` is healthy, and `/predict` returns a real result. Then start a separate strict API instance against an intentionally wrong v2 artifact path. Capture its logs and port/process state. Repoint `champion` to the concrete v1 version, restart the normal service, and prove `/model-info` reports v1, `/ready` is healthy, and `/predict` works again.

This preserves the important distinction: the **model** was valid; the **deployment configuration** failed; rollback recovered the serving system.
