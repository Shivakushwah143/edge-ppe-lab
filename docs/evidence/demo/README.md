# EdgePPE Lab — demo evidence pack

Screenshots of what is **actually verified** on this machine, plus explicit
placeholders for the delivery stages that cannot be captured yet.

This pack exists so that no claim in the demo runbook has to be taken on trust:
every image below is backed by a real source, and each one carries an annotation
band inside the image stating what it proves.

Repository: `/home/shiva_kushwah/projects/edge-ppe-lab` (WSL2 Ubuntu)
Commit at capture: `0fb3e11` — *fix(cd): gate CD on a green CI run for the exact commit SHA*
Captured: 2026-09-23

> **How to read this pack honestly.** Everything numbered 01–12 is captured and
> verified. Everything numbered 13–19 is **PENDING — requires self-hosted runner**.
> No image is illustrative, mocked or reconstructed: a screenshot was written only
> after the page had been asserted to contain the expected content.

---

## Status

| # | Evidence | Status |
|---|---|---|
| 01 | MLflow runs | **VERIFIED** |
| 02 | MLflow v2 metrics | **VERIFIED** |
| 03 | Model registry v1 + v2 | **VERIFIED** |
| 04 | `champion` alias on v1 | **VERIFIED** |
| 05 | ONNX parity v1 + v2 | **VERIFIED** |
| 06 | systemd `edge-ppe` active | **VERIFIED** |
| 07 | Real `/predict` | **VERIFIED** |
| 08 | Prometheus target UP | **VERIFIED** |
| 09 | Prometheus metrics ingested | **VERIFIED** |
| 10 | GitHub CI green | **VERIFIED** |
| 11 | Release contract 61 checks | **VERIFIED** |
| 12 | Docker build + boot smoke test in CI | **VERIFIED** |
| 13–19 | CD: runner, GHCR, deploy, health gate, failure, rollback | **PENDING — requires self-hosted runner** |

---

## How these were captured (and how to re-verify)

| | |
|---|---|
| Browser | Playwright 1.62.1 (headless Chromium), 1600×1100 viewport |
| Harness | `capture.mjs` — navigates, **asserts expected content is present in the rendered page**, dumps the page's visible text, appends the annotation band, then screenshots |
| Failure behaviour | If the assertion fails, **no PNG is written**. A screenshot cannot exist without its content having been verified. |
| Audit trail | `raw/<name>.page_text.txt` — the exact rendered text behind each image; `raw/00_capture_report.json` — per-shot URL, byte size, page size and annotation position |

Reproduce: start MLflow and the API (see `docs/DEMO_END_TO_END.md` §1), then run
the capture harness and compare `raw/00_capture_report.json`.

Every image ends with a dark-green band headed
**"WHAT THIS SCREENSHOT PROVES — ADDED ANNOTATION (not part of the captured page)"**.
That band is added by the harness; nothing above it is modified, and it is placed
below the page content so it never covers the evidence.

---

## Verified evidence

### 01 — `01_mlflow_runs.png`
**Source:** live MLflow 3.16.0 UI, `http://127.0.0.1:5000/#/experiments/1/runs`
**Proves:** the tracking server holds real training runs in experiment `edge-ppe-lab`
— `edge-ppe-v2` and `edge-ppe-v1`, FINISHED, each producing a registered model
version (`edge-ppe-detector` v2 and v1). This is the system of record the registry
and the deployment read from.
**Asserted content:** `edge-ppe-v1`, `edge-ppe-v2`.

### 02 — `02_mlflow_v2_metrics.png`
**Source:** live MLflow run page, run `133cc86b38ad4ec7971e60d8e1155c1f`
**Proves:** v2 is a genuinely trained model with logged metrics — `metrics/mAP50(B)`
0.5928, `metrics/mAP50-95(B)` 0.2625, `metrics/precision(B)` 0.557 — **and** logged
parity metrics (`parity_min_iou` 0.99998, `parity_unmatched_fraction` 0.0). The
numbers were produced by training and export, not written by hand.
**Asserted content:** `mAP50`.

### 03 — `03_model_registry_v1_v2.png`
**Source:** live MLflow Model Registry, `#/models/edge-ppe-detector`
**Proves:** the registered model `edge-ppe-detector` holds **two distinct versions**
(1 and 2), both READY. Two distinct versions is exactly what the release contract
gate cross-checks against `var/releases/v1` and `var/releases/v2`.
**Asserted content:** `edge-ppe-detector`.

### 04 — `04_champion_alias_v1.png`
**Source:** live MLflow UI, `#/models/edge-ppe-detector/versions/1`
**Proves:** the **promotion mechanism**. The page shows `Aliases: @ champion` and
the version's own tags: `release=v1`, `release_status=champion`,
`parity_status=passed`, `onnx_sha256=e22e6aeb…`. This is the single pointer that
decides what production serves, and it matches what `/model-info` reports (01/07).
Note version 2 exists but is **not** champion — it was demoted after the controlled
failure.
**Asserted content:** `champion`.

### 05 — `05_onnx_parity_v1_v2.png`
**Source:** `var/releases/v1/parity_report.json` and `var/releases/v2/parity_report.json`
(read directly; raw copies in `raw/05_parity_v1.txt`, `raw/05_parity_v2.txt`)
**Proves:** the exported ONNX graph reproduces the PyTorch detections for **both**
releases. Measured vs tolerance:

| release | min matched IoU | max confidence delta | unmatched fraction | providers |
|---|---|---|---|---|
| v1 | 0.999984 | 1.04e-06 | 0.0 | CPUExecutionProvider |
| v2 | 0.999983 | 9.26e-07 | 0.0 | CPUExecutionProvider |

…against tolerances of 0.95 / 0.03 / 0.1. Every compared image has identical
PyTorch and ONNX detection counts with **zero unmatched detections on either side**.
This is the gate that makes an export safe to ship.
**Asserted content:** `minimum_matched_iou`, `unmatched_fraction`, `parity_status`.

### 06 — `06_systemd_active.png`
**Source:** live `systemctl status/show edge-ppe` + live HTTP probes
**Proves:** the API runs as a supervised service — `Active: active (running)`,
`User=shiva_kushwah`, `Restart=on-failure`, `RestartSec=3`, `WorkingDirectory` in
the deployment tree, `ExecStart` using that tree's `.venv`. With live
`/health → 200`, `/ready → 200`, `/model-info → 200`.
**Asserted content:** `edge-ppe`, `active`.

### 07 — `07_real_predict.png`
**Source:** real `POST /predict` with a real Construction-PPE test-split image
**Proves:** the service actually **infers**. `image1003.jpg` → HTTP 200,
`model_version=1`, 640×640, 2 detections: `Person 0.9196`, `Hardhat 0.5927`. It also
shows `/model-info` (`concrete_model_version: 1`, `registry_alias_used: champion`,
`CPUExecutionProvider`). This is the difference between "the process is up" and
"the service works".
**Asserted content:** `detections`, `Person`. Raw JSON: `raw/07_real_predict.json`.

### 08 — `08_prometheus_target_up.png`
**Source:** live Prometheus UI, `http://127.0.0.1:9090/targets`
**Proves:** the scrape target is healthy — `edgeppe-api (1/1 up)`, endpoint
`http://host.docker.internal:18000/metrics`, **State UP**, with labels
`job="edgeppe-api"`, `runtime="docker"`, `environment="local"`, and an empty error
column with a ~4 ms scrape duration.
**Asserted content:** `edgeppe-api`.

### 09 — `09_prometheus_metrics.png`
**Source:** live PromQL query `model_info`, `http://127.0.0.1:9090/graph?g0.expr=model_info&g0.tab=1`
**Proves:** Prometheus did not merely reach the endpoint — it **ingested** the
application metrics. The returned series carries `registered_model="edge-ppe-detector"`,
`version="1"`, `format="onnx"`, `sha256="e22e6aeb…"`, `provider="CPUExecutionProvider"`
straight from the running service.
**Asserted content:** `model_info`.

### 10 — `10_github_ci_green.png`
**Source:** live GitHub Actions run page
<https://github.com/Shivakushwah143/edge-ppe-lab/actions/runs/35827278330>
**Proves:** GitHub-hosted CI is **GREEN** on the pushed commit. `edge-ppe-ci` run #4,
title *fix(cd): gate CD on a green CI run for the exact commit SHA*, triggered via
`push`, ref `main`, commit `0fb3e11`, **Status: Success**, total duration 56s.
**Asserted content:** `edge-ppe-ci`, `Success`.

### 11 — `11_release_contract_61_checks.png`
**Source:** `python scripts/verify_release_contract.py`, run locally — the exact
command CI runs in its *Release contract gate* step
**Proves:** `CONTRACT GATE PASSED: 61 checks`. Covers both releases: registry
metadata integrity, the pinned ONNX I/O contract (input `[1,3,320,320]`, output
`output0` shape `1×7×2100`, opset 17, float32), parity evidence for every compared
image, the CPU-only runtime contract (no torch/CUDA/NVIDIA anywhere in the shipping
runtime), the dataset class contract (`Person / Hardhat / NO-Hardhat`) and the API
surface.
**Asserted content:** `CONTRACT GATE PASSED: 61 checks`.

### 12 — `12_docker_build_ci_green.png`
**Source:** live GitHub Actions **job** page
<https://github.com/Shivakushwah143/edge-ppe-lab/actions/runs/35827278330/job/107071676156>
**Proves:** the immutable image genuinely builds in CI and boots correctly:
`succeeded in 53s`, with every step green including **Build immutable Docker
candidate** and **Image boot smoke test**. The smoke test boots the image with
`EDGE_PPE_STARTUP_STRICT=false` and asserts `/health → 200` **and** `/ready → 503` —
the readiness contract, verified for real. The image contains no model by design;
the qualified artifact is mounted read-only at deploy time.
**Asserted content:** `Build immutable Docker candidate`.

---

## PENDING — requires self-hosted runner

Nothing below has been captured, because the CD path has not executed. These are
placeholders, not evidence: **do not present them as achieved.** They stay marked
PENDING until a run actually happens and the source can be asserted.

| # | Evidence | Will be captured from | Blocked by |
|---|---|---|---|
| 13 | `13_self_hosted_runner_online.png` | GitHub → Settings → Actions → Runners, showing the runner **Idle** with labels `self-hosted, linux, x64, edgeppe-deploy` | **PENDING — requires self-hosted runner** |
| 14 | `14_ghcr_immutable_image.png` | the GHCR package page / `docker manifest inspect ghcr.io/shivakushwah143/edge-ppe-lab:0fb3e11c…` proving the immutable SHA tag exists for a green commit | **PENDING — requires self-hosted runner** |
| 15 | `15_cd_success.png` | the `edge-ppe-cd` run for the green SHA: `build-and-push` green and the `deploy` job claimed by the runner | **PENDING — requires self-hosted runner** |
| 16 | `16_cd_runtime_health_gate.png` | `scripts/cd_deploy.sh` log lines showing `/health` 200, `/ready` 200, `/model-info` version match and a real `/predict` 200, plus `var/deployment/cd_state.json` | **PENDING — requires self-hosted runner** |
| 17 | `17_controlled_failure.png` | `workflow_dispatch` with `fault_injection=bad_model_path`: the candidate dies against an invalid in-container model path and fails the gate | **PENDING — requires self-hosted runner** |
| 18 | `18_automatic_rollback.png` | the same run's rollback section: previous immutable image restored and the gate **re-passed** post-rollback, with the run still marked **failed** | **PENDING — requires self-hosted runner** |
| 19 | `19_final_healthy_state.png` | final state: `/ready` true, a working real `/predict`, and `var/deployment/cd_state.json` recording outcome/rollback | **PENDING — requires self-hosted runner** |

When the runner is genuinely online, capture these the same way (assert the
content, then screenshot) and **replace** the PENDING entries — do not renumber.

---

## Honest limitations

- **CD is NOT verified.** No `edge-ppe-cd` run has reached the self-hosted runner.
  At capture time the runner was not installed on this host (`~/actions-runner-edgeppe`
  absent, no `Runner.Listener` process) and `edge-ppe-cd #1`'s `deploy` job had been
  sitting `queued` — which is itself proof that no runner with the required labels
  was online, since GitHub would otherwise have assigned it immediately.
- **The only image in GHCR belongs to a failed commit.** `ghcr.io/shivakushwah143/edge-ppe-lab:422afe85…`
  is publicly pullable, but commit `422afe85` had a **failing** CI run and CD still
  built and pushed it. That is precisely the ungated behaviour the new `workflow_run`
  gate closes. No image exists yet for the green commit `0fb3e11c`.
- **Observability shots 08/09 use a locally started container.** To make the
  Prometheus target real, the Docker demo instance `edgeppe-api` was started on
  `:18000` from the existing local image `edge-ppe-lab:373fd26c…` with the qualified
  v1 ONNX artifact mounted read-only, per `docs/DEMO_END_TO_END.md` §7. **This is a
  local demo instance, not a CD deployment** — CD deploys this same container name
  only from the self-hosted runner.
- **GitHub logs are not in shots 10/12.** For a public repository GitHub shows the
  run status, job status and step names without authentication, but step **logs**
  are behind `Sign in to view logs`. Step names and the green status are the evidence
  captured; the green *Release contract gate* step is independently evidenced by 11.
- **CI runs on `:8000` (systemd), Docker on `:18000`.** Same application, separate
  processes with independent metric counters. Shots 06/07 are the systemd instance;
  08/09 scrape the Docker instance.
- The capture harness lives outside the repository (Windows scratch dir) and the
  compile/contract gates are unaffected by this pack.
