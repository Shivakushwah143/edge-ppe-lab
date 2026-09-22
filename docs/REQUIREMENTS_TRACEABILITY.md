# Requirements Traceability

This matrix maps the execution-mode requirements to concrete implementation locations and the
verification state observed on the user's WSL2 environment on **2026-09-22 UTC**.
States: **VERIFIED** / **IMPLEMENTED — NOT RUNTIME VERIFIED** / **BLOCKED** / **FAILED**.

| Requirement | Implementation | Verification state |
|---|---|---|
| Official Construction-PPE source | `scripts/prepare_dataset.py` official Ultralytics asset URL | VERIFIED — dataset prepared and verified |
| Canonical 3-class mapping | `UPSTREAM_TO_CANONICAL={6:0,0:1,7:2}`, `data/ppe.yaml` | VERIFIED — class counts recorded in both release files |
| Reproducible preprocessing | `prepare_dataset.py`, deterministic name hash selection, `manifest.json` | VERIFIED — `data/processed/ppe-v1/manifest.json` |
| Dataset manifest/fingerprint | `prepare_dataset.py::dataset_fingerprint` | VERIFIED — logged to MLflow as a run artifact |
| Real lightweight YOLO training | `scripts/train.py`, `configs/train-v1.yaml` | VERIFIED — v1 run `c283e4ec…`, real `best.pt` |
| Real distinct model v2 | `configs/train-v2.yaml` (epochs 12, seed 43, lr0 0.008) | VERIFIED — run `133cc86b…`, metrics precision 0.5571446570824707, recall 0.6117216117216118, mAP50 0.592819785851068, mAP50-95 0.26245204921499393 |
| MLflow Tracking | `scripts/start_mlflow.sh`, `scripts/train.py` | VERIFIED — server on `:5000`, runs + artifacts + environment metadata |
| Model Registry numeric versions | `scripts/register_model.py` | VERIFIED — v1 and v2 registered, v2 = immutable version **2** |
| `champion` alias | `scripts/set_champion.py`, `RuntimeModel.from_settings` | VERIFIED — alias moved v1→v2→v1 via the alias API; `release_status` tags now agree with it (v1 `champion`, v2 `qualified`) |
| Resolve alias to concrete version | `app/model_runtime.py` | VERIFIED — registry-mode service resolved `champion` and downloaded the qualified artifact with SHA match |
| ONNX export | `scripts/export_onnx.py` | VERIFIED — v1 SHA `e22e6aeb…`, v2 SHA `43e14f64…`, opset 17 |
| Record input/output/opset/SHA/lineage | `onnx_contract.json`, release JSON, MLflow tags | VERIFIED — `onnx.checker` PASS, contract + hashes recorded |
| Real PT↔ONNX parity | `scripts/validate_parity.py` | VERIFIED — v1 min IoU 0.9999836536246481; v2 min IoU 0.999982796774978, max conf delta 9.26136016876633e-07, unmatched 0.0 |
| Machine-readable parity report | `var/releases/<release>/parity_report.json` | VERIFIED — v1 and v2, copied to `docs/evidence/` |
| Block promotion on failed parity | `scripts/set_champion.py` + `14_release_gate.txt` | VERIFIED — negative gate rejected; positive path required `parity_status=passed` |
| `GET /health` | `app/main.py` | VERIFIED — 200 on service and container |
| `GET /ready` | `app/main.py` | VERIFIED — 200 with model version; 503 without model |
| `GET /model-info` | `app/main.py` | VERIFIED — concrete version 1 and 2 with provider `CPUExecutionProvider` |
| `POST /predict` real ONNX inference | `OnnxDetector.predict_*`, API endpoint | VERIFIED — real detections on real validation images (service + container) |
| `GET /metrics` | `app/metrics.py`, API endpoint | VERIFIED — counters/histogram deltas measured under real load |
| Linux process/port/env/resource inspection | `START_HERE.md`, `inspect_linux.sh` | VERIFIED — `ps`, `ss`, `env`, `free`, plus the stale-process audit recorded in `final_state_verification.txt` |
| systemd unit | `deploy/systemd/edge-ppe.service`, `deploy/systemd/install.sh`, `deploy/systemd/edge-ppe.env.example` | VERIFIED — unit installed with the real tree paths (`/home/shiva_kushwah/projects/edge-ppe-lab` + its `.venv`), `enabled` + `active (running)`, `journalctl -u edge-ppe` captured, restart verified; `Restart=on-failure` proven with an injected `kill -9` (`systemd_runtime_verification.txt`) |
| systemd supervised restart on crash | unit `Restart=on-failure` / `RestartSec=3` | VERIFIED — main PID killed, service returned to `active (running)` with `NRestarts=1` and `/ready` 200 again |
| Promotion metadata cannot contradict the alias | `scripts/set_champion.py` | VERIFIED — superseded versions are demoted to `release_status=qualified`; alias → v1, v1 `champion`, v2 `qualified`; no deprecated stage used (`registry_tag_hygiene.txt`) |
| Docker production-oriented image | `docker/Dockerfile`, `requirements-runtime.txt` | VERIFIED — `edge-ppe-lab:local` built `EXIT=0`, 569 MB, CPU-only |
| Non-root Docker runtime | Dockerfile `edgeppe` user (uid 10001) | VERIFIED — image runs as `edgeppe` |
| Immutable image identity | Git-SHA tag + OCI revision build arg in `START_HERE.md` | IMPLEMENTED — NOT RUNTIME VERIFIED — locally the image is tagged `edge-ppe-lab:local` |
| Model/system Prometheus metrics | `app/metrics.py` | VERIFIED — `inference_requests_total`, `inference_failures_total`, `inference_latency_seconds`, `detections_total`, `model_info` all advanced correctly |
| Compact GitHub Actions pipeline | `.github/workflows/ci.yml` | IMPLEMENTED — NOT RUNTIME VERIFIED — no hosted runner executed it |
| Safe failure labs | code + `START_HERE.md` + evidence | VERIFIED — including the new Docker container exit and invalid-artifact-path failure with full diagnosis |
| Rollback v2→v1 | `set_champion.py` + redeploy procedure | VERIFIED — end-to-end: alias repointed, both surfaces restarted, v1 serving real predictions |
| WSL2 manual journey | `START_HERE.md` | VERIFIED — the journey was executed on WSL2, including Docker |
| Preserve source-of-truth docs | `docs/01...23`, diagrams, references | VERIFIED — present and unchanged |
| No Kubernetes/Kafka/Redis/frontend/RAG/agents | repository audit | VERIFIED — absent from implementation |
| Future TensorRT/Jetson path only | source-of-truth docs | VERIFIED — not required by the CPU runtime; GPU path untestable on this hardware |
| Build-phase reports | `IMPLEMENTATION_REPORT.md`, `VERIFICATION_REPORT.md`, `KNOWN_LIMITATIONS.md`, this file, `FAILURE_VERIFICATION.md`, `evidence/RUNTIME_LIFECYCLE_VERIFICATION.md` | VERIFIED — present and updated with executed results |
