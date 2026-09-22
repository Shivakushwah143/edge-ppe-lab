# Runtime Lifecycle Verification — v2 promotion → controlled failure → rollback → final state

Executed: **2026-09-22 (UTC)** in the user's real WSL2 environment (not a sandbox).

Status vocabulary used in this document and in the sibling reports:

- **VERIFIED** — actually executed in this environment; raw output captured in an evidence file.
- **IMPLEMENTED — NOT RUNTIME VERIFIED** — code/config exists and was inspected, but was not executed here.
- **BLOCKED** — a prerequisite was unavailable, so the exercise could not be run.
- **FAILED** — executed and did not meet its acceptance criteria.

## Constraints honoured

- v1 was **not** retrained; v2 was **not** retrained; the dataset was **not** rebuilt.
- Working v1 artifacts were **not** replaced or modified (v1 ONNX SHA-256 is byte-identical before and after the whole lifecycle).
- No registry, parity, or deployment evidence was fabricated: every number below is copied from real API responses, real command output, or real log files.
- The v2 ONNX artifact was never corrupted, not even during the deliberate failure drill.

## Environment

| Fact | Value |
|---|---|
| OS | Ubuntu 24.04.3 LTS on WSL2 |
| Kernel | 6.18.33.2-microsoft-standard-WSL2 |
| CPU / RAM | Intel Core i3-1005G1 @ 1.20GHz, 4 logical cores / 7 GiB |
| GPU | none — `nvidia-smi` absent, `torch.cuda.is_available() == False` |
| Python | 3.12.3 in `/home/shiva_kushwah/.edge-ppe-venv` |
| torch / ultralytics | 2.14.0+cpu / 8.4.153 |
| onnx / onnxruntime | 1.22.0 / 1.30.0 (providers: `AzureExecutionProvider`, `CPUExecutionProvider`) |
| MLflow | 3.16.0 server, SQLite backend store, local artifact store |
| Docker | 29.2.1 (Docker Desktop) |

## Stage 1 — stale process audit

`ps -eo pid,ppid,etime,rss,cmd` showed **no training processes at all**. Every Python process is live
infrastructure: the MLflow server (`mlflow server … --port 5000`), its four MLflow-internal
`--workers 4` uvicorn children, the MLflow jobs runner and huey consumers, and the EdgePPE API
uvicorn on `:8000`. The four `multiprocessing.spawn` children (PIDs 3551-3554) are **MLflow server
workers, not orphaned Ultralytics dataloaders** — killing them would have broken the registry.

**Conclusion: nothing was terminated.** `free -h` before `3.9Gi used / 3.7Gi available`, after
`3.8Gi used / 3.7Gi available`. Evidence: `final_state_verification.txt`.

## Stage 2 — real v2 MLflow run + registry version 2

The v2 training run already existed and was **reused, not recreated**: `edge-ppe-v2`,
run id `133cc86b38ad4ec7971e60d8e1155c1f`, status `FINISHED`, experiment `edge-ppe-lab` (id 1).
It carried params (seed 43, lr0 0.008, epochs 12, imgsz 320, batch 8, device cpu, dataset ppe-v1,
git commit `4aac66e…`) and the real training metrics. The one thing genuinely missing was
**environment information**, which was then logged into the same run (python/torch/ultralytics/
onnxruntime/platform/CPU/GPU-absent + an `environment/environment.json` artifact and `edge_ppe.environment.*` tags).

Registration used the existing mechanism `scripts/register_model.py --release v2` (no parallel path):
`edge-ppe-detector` gained the next immutable numeric version **2**, linked to run
`133cc86b38ad4ec7971e60d8e1155c1f`, with lineage tags and `parity_status=not-run`.

Evidence: `v2_mlflow_run_registry_onnx_metadata.txt`.

## Stage 3 — real v2 ONNX export and verification

Exported with the existing mechanism `scripts/export_onnx.py --release v2` from
`var/releases/v2/best.pt` (5,427,674 bytes, the real v2 checkpoint).

| Property | Value |
|---|---|
| Path | `var/releases/v2/model.onnx` (the project's canonical name; `best.onnx` is the raw export next to it) |
| Size | 10,440,792 bytes |
| SHA-256 | `43e14f6484290bfd44349e68dc14781c2e17268999ce0100b8a13e809f276fd4` |
| Opset / IR | `ai.onnx` 17 / IR 8 |
| Producer | pytorch 2.14.0 |
| `onnx.checker` | PASS |
| Input | `images` `[1,3,320,320]` `tensor(float)` |
| Output | `output0` `[1,7,2100]` `tensor(float)` |
| Execution providers | `["CPUExecutionProvider"]` |
| Real inference | image1057 → Hardhat 0.9084, Person 0.7980 |

Registry version 2 was tagged `onnx_artifact_path=deployment/v2/model.onnx` and
`onnx_sha256=43e14f64…`; `var/releases/v2/release.json` was updated with the real ONNX path/hash.

## Stage 4 — PT↔ONNX parity (release gate)

`scripts/validate_parity.py --release v2` executed **both** runtimes on the same five validation
images (`data/processed/ppe-v1/images/val/image1057,1083,1096,1107,115`):

| Check | Tolerance | Observed | Result |
|---|---|---|---|
| Minimum matched IoU | ≥ 0.95 | **0.999982796774978** | pass |
| Max confidence delta | ≤ 0.03 | **9.26136016876633e-07** | pass |
| Unmatched detection fraction | ≤ 0.10 | **0.0** | pass |
| Execution providers | CPU only | `["CPUExecutionProvider"]` | pass |

`parity_status=passed` was written to registry version 2 and to `release.json`; parity metrics were
logged to the run; `docs/evidence/v2-onnx-parity.json` is a byte-identical copy of
`var/releases/v2/parity_report.json`.

## Stage 5 — promotion to champion (v2) and redeploy

`scripts/set_champion.py --release v2` (the only promotion path; it refuses to run unless
`parity_status=passed` and the qualified ONNX identity is present) moved the mutable `champion`
alias from version 1 to version **2** and rewrote `var/deployment/champion.json`.

Two deployment surfaces were then redeployed against the real v2 artifact:

1. **Host service, registry mode** (`MLFLOW_TRACKING_URI=http://127.0.0.1:5000`,
   `EDGE_PPE_MODEL_ALIAS=champion`, `EDGE_PPE_STARTUP_STRICT=true`): restarting it resolved the
   alias to version 2 and **downloaded the qualified artifact through MLflow** into
   `var/model-cache/v2/model.onnx` with a matching SHA-256 `43e14f64…`. This is the registry-driven
   deployment path, not a mounted file.
2. **Docker container** (`edge-ppe-lab:local`, CPU-only): recreated with the v2 ONNX mounted
   read-only and `EDGE_PPE_MODEL_VERSION=2`.

Note: the host service does **not** hot-reload — before the restart it still served v1 while the
alias already pointed at v2. Redeploy is an explicit restart, which is the documented semantic.

## Stage 6 — real v2 runtime verification

Host service (registry mode) and Docker container both reported concrete version **2**:

| Probe | Host service :8000 | Docker :18000 |
|---|---|---|
| `GET /health` | 200 `{"status":"alive"}` | 200 |
| `GET /ready` | 200 model_version 2 | 200 model_version 2 |
| `GET /model-info` | version 2, alias `champion`, CPUExecutionProvider | version 2, sha `43e14f64…`, CPUExecutionProvider |
| `POST /predict` ×3 | real detections, 200 | real detections, 200 |

Metric deltas proved the counters changed correctly (Docker, fresh process):

```
before: inference_requests_total 0.0  inference_failures_total 0.0  inference_latency_seconds_count 0.0
after : inference_requests_total 3.0  inference_failures_total 0.0  inference_latency_seconds_count 3.0
        inference_latency_seconds_sum 0.1725043149999692
        detections_total{class_name="Hardhat"} 3.0   detections_total{class_name="Person"} 3.0
        model_info{...version="2", provider="CPUExecutionProvider", sha256="43e14f64…"} 1.0
```

Evidence: `v2_runtime_verification.txt`.

## Stage 7 — controlled deployment failure

- **SYMPTOM (expected and observed):** the service refuses to start; the container exits non-zero;
  the port is dead; `/health` is unreachable.
- **HYPOTHESIS:** with `EDGE_PPE_MODEL_PATH` set, `RuntimeModel.from_settings` takes the explicit
  local-artifact branch; pointing it at a non-existent file must fail fast under
  `EDGE_PPE_STARTUP_STRICT=true`. The model itself is irrelevant to the failure.
- **COMMANDS:** `docker run … -e EDGE_PPE_MODEL_PATH=/nonexistent/model-v2.onnx -e EDGE_PPE_MODEL_VERSION=2`,
  then `docker ps -a`, `docker inspect`, `docker logs`, `curl /health`, `ss -lntn`, MLflow alias API,
  `sha256sum`, `onnx.checker`.
- **EVIDENCE:** container `status=exited exit_code=3`; log ends with
  `FileNotFoundError: ONNX model not found: /nonexistent/model-v2.onnx` →
  `ERROR: Application startup failed. Exiting.`; `curl /health` → `http_code=000` (connection
  refused); nothing listening on `:18000`; registry untouched (`champion=v2`, `parity_status=passed`).
- **ROOT CAUSE:** the introduced **deployment configuration** was invalid. The qualified v2 model
  was valid throughout — same file, unchanged SHA-256 `43e14f64…`, `onnx.checker` PASS, and it had
  just served real 200 predictions in Stage 6. Raw capture: `v2_controlled_deployment_failure.txt`.

## Stage 8 — real rollback to v1

`scripts/set_champion.py --release v1` was executed for real (lineage check against the registry
passed). The MLflow alias API then reported `champion → version 1`
(run `c283e4ec5f504ba9864354342a802d68`).

Both surfaces were restored to valid v1 configuration and re-verified:

| Probe | After rollback |
|---|---|
| Host service `:8000` | 200, `/ready` model_version **1**, `/model-info` version 1, alias `champion`, sha `e22e6aeb…` |
| Host service `/predict` | 200 — Hardhat 0.8832, Person 0.8645 |
| Docker container | `running / healthy`, `/model-info` version **1**, sha `e22e6aeb…` |
| Docker `/predict` | 200 — Hardhat 0.8832, Person 0.8645 |

The v1 predictions reproduce the v1 parity reference values exactly, which is independent
confirmation that the rollback restored the qualified v1 artifact and not merely a path.
Evidence: `v2_rollback_to_v1.txt`.

## Stage 9 — final state gate

| Required final state | Observed | Status |
|---|---|---|
| `champion = v1` | MLflow alias API: version 1, alias `champion` | VERIFIED |
| service healthy | `:8000` `/health` 200, `/ready` 200 (v1) | VERIFIED |
| `/model-info` = v1 | version 1, provider `CPUExecutionProvider` | VERIFIED |
| `/predict` working | 200 with real detections on a real validation image | VERIFIED |
| Docker container healthy | `running / healthy`, `/model-info` v1, `/predict` 200 | VERIFIED |

Evidence: `final_state_verification.txt`.

## Stage 10 — final release cleanup (executed after the lifecycle)

No model was retrained and no destructive lifecycle step was repeated. Two release-hygiene defects
that Stage 9 exposed were fixed and verified:

1. **Metadata contradicted the alias.** Both v1 and v2 carried `release_status=champion` while the
   alias pointed at v1. `scripts/set_champion.py` now demotes every other version still claiming
   `release_status=champion` to `release_status=qualified` and only then tags the promoted version
   `champion`. Aliases + version tags only — no deprecated MLflow stage is read or written.
   Re-running the documented promotion for v1 produced `demoted_versions=["2"]`;
   the registry now reports alias → **1**, v1 = `champion`, v2 = `qualified`.
   Evidence: `registry_tag_hygiene.txt`.
2. **The API was not actually supervised.** The `edge-ppe` systemd unit existed in the repository but
   had never been installed; the API was a hand-started Uvicorn. The unit's paths were corrected to
   the real tree (`/home/shiva_kushwah/projects/edge-ppe-lab` and its `.venv/bin/uvicorn`), installed
   by `deploy/systemd/install.sh`, and the service was verified end to end — including a `kill -9` of
   the main PID to prove `Restart=on-failure`. Evidence: `systemd_runtime_verification.txt`.

The hand-started Uvicorn was stopped so the unit could own `:8000`; the Docker container was not
touched and stayed `running/healthy` on `:18000`, still serving v1. Final state after cleanup:

| Required final state | Observed | Status |
|---|---|---|
| `champion = v1` | alias API → version 1; v1 `release_status=champion`, v2 `release_status=qualified` | VERIFIED |
| systemd service = active | `is-enabled=enabled`, `is-active=active (running)`, supervised restart survived | VERIFIED |
| `/ready` = true | 200 `{"ready":true,"model_version":"1"}` after restart and after the crash drill | VERIFIED |
| `/model-info` = v1 | version 1, alias `champion`, `CPUExecutionProvider`, sha `e22e6aeb…` | VERIFIED |
| `/predict` = real inference | 200, Person 0.919593 + Hardhat 0.592677 on `image1003.jpg` | VERIFIED |
| Docker container = healthy | `running/healthy`, `/ready` v1, real `/predict` 200 | VERIFIED |

## Docker image (runtime dependency fix)

The image is CPU-only and contains **no** torch, ultralytics, pandas, matplotlib, scipy or sklearn.
`onnxruntime` exposes only `AzureExecutionProvider` + `CPUExecutionProvider`.

The earlier build failure was **not** CUDA/NVIDIA related: `grep -icE "nvidia|cuda|torch|triton"`
over the failing build log returned `0`. The build died with a PyPI `ReadTimeoutError` while
downloading the 62 MB `opencv-python-headless` wheel (~300 KB/s link). Fixes applied:

- runtime requirements switched from `mlflow` to `mlflow-skinny` (the runtime only needs
  `set_tracking_uri` + `MlflowClient`), removing MLflow's pandas/matplotlib/scipy/scikit-learn tree;
- `PIP_DEFAULT_TIMEOUT=180`, `PIP_RETRIES=10`, a 3-attempt retry loop and a BuildKit pip cache mount
  so a slow or aborted build resumes instead of re-downloading ~120 MB;
- the image was rebuilt to `EXIT=0` (`edge-ppe-lab:local`, 569 MB) and then used for every runtime
  verification above.

## Evidence index

| File | Contents |
|---|---|
| `v2_mlflow_run_registry_onnx_metadata.txt` | v2 run params/metrics/tags/artifacts, both registry versions, ONNX metadata |
| `v2-onnx-parity.json` | full PT↔ONNX comparison for v2 (5 images) |
| `v2_runtime_verification.txt` | Docker + registry-mode service runtime probes and metric deltas on v2 |
| `v2_controlled_deployment_failure.txt` | controlled failure capture with config, logs, exit code, artifact integrity |
| `v2_rollback_to_v1.txt` | champion rollback, service/Docker rollback verification |
| `final_state_verification.txt` | process audit, `free -h`, final registry/service/container state |
| `registry_tag_hygiene.txt` | `release_status` fix: before/after tags, promotion output, alias/v1/v2 acceptance checks |
| `systemd_runtime_verification.txt` | unit inspection, in-place install, daemon-reload/enable/start, status, journal, restart, `/health`+`/ready`+`/model-info`+`/predict`, metrics, Docker re-check, supervised `kill -9` restart |
| `var/docker/build.log`, `var/docker/build.exit` | successful CPU-only image build (`EXIT=0`) |
| `var/docker/build.failed-pypi-timeout.log` | preserved pre-fix failure (PyPI read timeout, no CUDA) |

## Explicit non-claims

- **GitHub Actions CI**: workflow is not executed on a hosted runner here —
  **IMPLEMENTED — NOT RUNTIME VERIFIED**.
- **GPU/TensorRT**: untestable on this hardware; remains a documented future path.
- **systemd is now runtime-verified in this distro** (`systemctl is-system-running` → `running`).
  The unit is installed at `/etc/systemd/system/edge-ppe.service`, enabled, `active (running)`, and
  was proven to restart itself after an injected process kill. Two honest qualifications remain:
  the unit runs as the tree owner because the deployment root is inside `/home` (so `ProtectHome`
  cannot be enabled), and WSL boot-time activation of units is a WSL lifecycle property rather than
  something this exercise claims to guarantee.
- The `release_status` **tag** no longer contradicts the alias. It was a real wart in the earlier
  state (v1 and v2 both claimed `champion`) and is fixed in `scripts/set_champion.py`; exactly one
  version now carries `release_status=champion` and the alias resolves to that same version.
