# Failure Verification

## Evidence convention

A failure lab is considered verified only when the failure was actually induced and command/output
evidence was captured. Source inspection alone is not verification.

| Failure exercise | Status | Symptom / evidence | Root cause / fix path |
|---|---|---|---|
| Wrong model path | VERIFIED | Strict Uvicorn startup exits with `FileNotFoundError`; `06_failure_wrong_model_path.txt` | Incorrect `EDGE_PPE_MODEL_PATH`; verify with `pwd/ls/find`, correct path, restart |
| Missing required environment value | VERIFIED | Explicit model path without version exits with clear runtime config error; `07_failure_missing_env.txt` | `EDGE_PPE_MODEL_VERSION` missing; inspect `env`, set paired value, restart |
| Permission denied reading model | VERIFIED | `nobody` cannot read root-owned `0600` model; `08_failure_permission_denied.txt` | OS file ownership/mode; inspect `ls -l`, apply least-privilege `chown/chmod` |
| Port occupied | VERIFIED | `ss` shows owner; second bind fails `Errno 98`; `09_failure_port_occupied.txt` | Existing process owns port; inspect PID, stop/reconfigure appropriate process/port |
| Inference/service process crashes | VERIFIED | Killed process disappears from `ps` (`10_process_crash_observation.txt`); under systemd the unit was restarted by `Restart=on-failure` and served traffic again | Process exit; the systemd unit now restarts it automatically |
| **Supervised restart after a crash (systemd)** | **VERIFIED** | `kill -9` of the unit's main PID → journal: `Main process exited, code=killed, status=9/KILL` → `Scheduled restart job, restart counter is at 1` → `active (running)`, `NRestarts=1`, `/ready` 200 again in ~10 s; `docs/evidence/systemd_runtime_verification.txt` §14 | Supervisor policy configured as intended; a *permanent* fault would exit again until the start limit (the invalid-artifact-path drill above is that permanent-fault case) |
| **Docker container exits (invalid artifact path)** | **VERIFIED** | Container `status=exited exit_code=3`; `docker logs` ends with `FileNotFoundError: ONNX model not found: /nonexistent/model-v2.onnx` → `ERROR: Application startup failed. Exiting.`; `curl /health` → `http_code=000`; nothing listening on `:18000`; `docker inspect` shows `exit_code=3`; `v2_controlled_deployment_failure.txt` | Invalid deployment configuration (`EDGE_PPE_MODEL_PATH` pointed at a non-existent file with `EDGE_PPE_STARTUP_STRICT=true`). Fix: correct the path or use registry mode, then recreate the container |
| High CPU/RAM inspection | VERIFIED | `top` and `free` captured; `11_resource_inspection.txt`, plus before/after `free -h` in `final_state_verification.txt` | Diagnostic exercise completed; no artificial resource exhaustion was needed |
| Disk-space inspection | VERIFIED | `df` and `du` captured; `11_resource_inspection.txt` | Diagnostic exercise completed; destructive disk filling intentionally avoided |
| MLflow unavailable | VERIFIED | Model resolution reports missing MLflow dependency; degraded API stays live but `/ready`=503; `05_degraded_api_runtime.txt` | Tracking/registry dependency unavailable; restore MLflow/package/network then restart |
| **Healthy v2 → bad deployment config → rollback to v1** | **VERIFIED** | Sequence executed for real: champion v2 healthy and serving → invalid path injected → diagnosed → `champion` repointed to v1 → service and container restarted → `/model-info` v1 and `/predict` 200; `v2_rollback_to_v1.txt`, `RUNTIME_LIFECYCLE_VERIFICATION.md` | Mutable `champion` alias + explicit redeploy is the recovery mechanism; the qualified artifacts were never modified |
| Registry alias changed but service keeps serving the old version | VERIFIED (observed) | After promoting v2, the running service still reported v1 until it was restarted | Model is resolved once at startup; redeploy/restart is required. Intended immutable-load semantics, not a bug |

## Controlled v2 deployment failure — full record

**SYMPTOM.** After recreating the API container with a deliberately invalid model artifact path, the
container is not serving: `docker ps -a` shows `Exited (3)`, `curl /health` returns no HTTP code
(`000`, connection refused), and `ss -lntn` shows nothing bound on `:18000`.

**HYPOTHESIS.** With `EDGE_PPE_MODEL_PATH` set, `RuntimeModel.from_settings()` takes the explicit
local-artifact branch and calls `OnnxDetector(path)`, which raises `FileNotFoundError` for a missing
file. Because `EDGE_PPE_STARTUP_STRICT` defaults to `true`, the lifespan hook re-raises and Uvicorn
aborts startup. Therefore the failure should be attributable purely to configuration, with the model
artifact uninvolved.

**COMMANDS.**

```bash
docker rm -f edgeppe-api
docker run -d --name edgeppe-api -p 18000:8000 \
  -e EDGE_PPE_MODEL_PATH=/nonexistent/model-v2.onnx \
  -e EDGE_PPE_MODEL_VERSION=2 \
  edge-ppe-lab:local
docker ps -a --format '{{.Names}} image={{.Image}} status={{.Status}}'
docker inspect --format 'status={{.State.Status}} exit_code={{.State.ExitCode}}' edgeppe-api
docker logs edgeppe-api
curl -s -o /dev/null -w 'http_code=%{http_code}\n' http://127.0.0.1:18000/health
ss -ltn | grep ':18000'
curl -s "http://127.0.0.1:5000/api/2.0/mlflow/registered-models/alias?name=edge-ppe-detector&alias=champion"
sha256sum var/releases/v2/model.onnx
python -c "import onnx; onnx.checker.check_model('var/releases/v2/model.onnx')"
```

**EVIDENCE.**

```
status=exited exit_code=3 error= started=…10:00:23Z finished=…10:00:31Z
/app/app/model_runtime.py:47  raise FileNotFoundError(f"ONNX model not found: {self.path}")
FileNotFoundError: ONNX model not found: /nonexistent/model-v2.onnx
ERROR:    Application startup failed. Exiting.
curl /health -> http_code=000 (connection refused)
ss -ltn :18000 -> (nothing listening on 18000)
MLflow: champion still version 2 | parity_status passed
v2 artifact: sha256=43e14f6484290bfd44349e68dc14781c2e17268999ce0100b8a13e809f276fd4 size=10440792
onnx.checker on v2 artifact: PASS (artifact intact)
```

**ROOT CAUSE.** The introduced deployment configuration was invalid — `EDGE_PPE_MODEL_PATH` pointed
at a file that does not exist, and strict startup correctly refused to serve without a model. The
qualified v2 model itself was valid and unaffected: identical SHA-256 before and after, `onnx.checker`
still passes, the registry entry still reports `parity_status=passed`, and the same artifact had just
served real HTTP 200 predictions. This preserves the required distinction — **the model was valid;
the deployment configuration failed**.

## Safe v2 rollback drill (executed)

`champion` was repointed from the concrete v2 version to the concrete v1 version with the ordinary
promotion path (`scripts/set_champion.py --release v1`, which verifies registry/local lineage), then
both surfaces were restarted. Post-rollback proof: MLflow alias API → version 1; registry-mode
service `/model-info` → version 1 (alias `champion`, SHA `e22e6aeb…`); Docker container
`running/healthy`, `/model-info` → version 1; `/predict` → HTTP 200 with Hardhat 0.8832 and Person
0.8645, i.e. the exact v1 parity reference values. The validated v2 ONNX file was never corrupted and
no parity evidence was altered.

## systemd supervision drill (executed, failure-injection)

**SYMPTOM (expected).** The unit's main process dies from a signal; the port goes dead until systemd
acts.

**HYPOTHESIS.** With `Restart=on-failure` and `RestartSec=3`, systemd must observe the killed main
process, schedule a restart, and bring the API back to `/ready` without operator intervention — i.e.
supervision is real, not merely a directive in the unit file.

**COMMANDS.**

```bash
systemctl show -p MainPID --value edge-ppe
kill -9 "$(systemctl show -p MainPID --value edge-ppe)"
systemctl is-active edge-ppe                 # activating
systemctl show -p NRestarts -p MainPID -p ActiveState -p SubState edge-ppe
journalctl -u edge-ppe --no-pager -n 20 | tail -14
curl -s http://127.0.0.1:8000/ready
curl -s -F image=@data/processed/ppe-v1/images/test/image1003.jpg http://127.0.0.1:8000/predict
```

**EVIDENCE.**

```
edge-ppe.service: Main process exited, code=killed, status=9/KILL
edge-ppe.service: Failed with result 'signal'.
edge-ppe.service: Scheduled restart job, restart counter is at 1.
Started edge-ppe.service - EdgePPE Lab ONNX Inference API.
model_loaded name=edge-ppe-detector version=1 alias=champion sha256=e22e6aeb… provider=CPUExecutionProvider
NRestarts=1  ActiveState=active  SubState=running
curl /ready      -> {"ready":true,"model_version":"1"} [HTTP 200]
curl /predict    -> 200, Person 0.919593 + Hardhat 0.592677 on image1003.jpg
```

**ROOT CAUSE / OUTCOME.** Expected process death; systemd performed the documented recovery. No model,
registry, or artifact state changed — the restarted process re-resolved `champion` → version 1 through
MLflow and reproduced the same SHA-256 `e22e6aeb…`.
