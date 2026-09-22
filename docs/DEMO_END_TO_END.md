# EdgePPE Lab — End-to-End Demo Runbook

A presenter's script for walking a reviewer through the whole lifecycle: **dataset → train →
registry → ONNX → parity → promotion → systemd → Docker → failure drill → rollback → CI → CD →
observability**.

Everything below is copy-pasteable. Each phase states **what to run**, **what to look at on
screen**, **the expected output**, and **the one sentence worth saying out loud**.

---

## 0. Demo status — read this before presenting

Two facts decide how much of this runbook is demonstrable live:

| Fact | Consequence |
|---|---|
| The deployment target is `/home/shiva_kushwah/projects/edge-ppe-lab` (the copy with the GitHub remote). The Windows-desktop copy is a **stale export** — no remote, different `HEAD`. | Always demo from `~/projects/edge-ppe-lab`, never from the Desktop copy. |
| The self-hosted runner is **not installed** on this machine, and the local `main` is **2 commits ahead of `origin/main`** with the CI/CD files still uncommitted. | Phases 10–12 (GitHub CI, GHCR, automated deploy/rollback) **cannot be shown live** until STEP 1/2 in §13 are done. |

| Phase | Capability | Status today |
|---|---|---|
| 1 | Toolchain + dependency probe | **VERIFIED** |
| 2 | Dataset prepared + contract-checked | **VERIFIED** |
| 3 | MLflow tracking + registry | **VERIFIED** |
| 4 | v1 trained / registered / ONNX / PT↔ONNX parity | **VERIFIED** |
| 5 | Promotion (`champion`) + registry-mode serving (systemd) | **VERIFIED** |
| 6 | Docker image built and serving a qualified artifact | **VERIFIED** |
| 7 | v2 qualified, promoted, then rolled back to v1 | **VERIFIED** |
| 8 | pytest + release contract + shell/YAML lint | **VERIFIED** (7 passed, 61 checks) |
| 9 | Observability (Prometheus scraping `/metrics`) | **VERIFIED** |
| 10 | GitHub-hosted CI (Actions run, green) | **BLOCKED** — needs a push to `origin` |
| 11 | GHCR immutable image publication | **BLOCKED** — needs CI/CD on a trusted push |
| 12 | Self-hosted runner → automated deploy + automatic rollback | **BLOCKED** — runner not installed (§13) |

Phases 10–12 are **implemented and locally verified, but not runtime-verified on GitHub.** Do not
claim otherwise; the blocker and the exact unblocking actions are in §13.

> **Live snapshot when this runbook was written:** MLflow was stopped and no `edgeppe-api`
> container was running, so the `edge-ppe` unit was `active` but not serving — see the MLflow
> ordering note in §1. Re-run §1 preflight immediately before presenting, and start MLflow before
> the API.

---

## 1. Preflight (30 seconds, do this before any audience shows up)

```bash
cd ~/projects/edge-ppe-lab
source .venv/bin/activate

git rev-parse --short HEAD          # expect: b118ce2
git remote -v                       # expect: git@github.com:Shivakushwah143/edge-ppe-lab.git
docker --version
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:5000   # MLflow, may be 000 if stopped
```

Talking point: *"The repository has exactly one remote and one branch, `main`. Everything we deploy
is addressed by an immutable git SHA, never by a floating tag."*

### Start MLflow first, then the API — order matters

`EDGE_PPE_STARTUP_STRICT=true`, so the service resolves the `champion` alias from MLflow at
startup. **If MLflow is not running, the unit reports `active (running)` but never binds `:8000`**
and every `curl` returns `000`. Recover in this order:

```bash
cd ~/projects/edge-ppe-lab && source .venv/bin/activate
./scripts/start_mlflow.sh &                 # or nohup, in its own terminal
until curl -fsS -o /dev/null http://127.0.0.1:5000; do sleep 1; done
sudo systemctl restart edge-ppe             # restart AFTER MLflow is reachable
until curl -fsS -o /dev/null http://127.0.0.1:8000/ready; do sleep 2; done
curl -s http://127.0.0.1:8000/model-info | python -m json.tool
```

Diagnose with `journalctl -u edge-ppe -n 40 --no-pager`: while MLflow is down you will see
`urllib3 ... Connection refused` retries against `127.0.0.1:5000` and no `Uvicorn running on`
line. That log is itself worth showing — it is the strict-startup contract doing its job instead of
serving a stale or missing model.

---

## 2. Phase 1 — Toolchain and dependencies

```bash
python scripts/verify_components.py
```

Expected: a component report showing Python, ONNX Runtime, OpenCV, Ultralytics and MLflow present,
with the ONNX Runtime **CPU** execution providers.

Talking point: *"This stack is CPU-only on purpose — no CUDA, no NVIDIA runtime anywhere in the
image. The probe is the proof, and it is the first gate in the Makefile."*

---

## 3. Phase 2 — Dataset

```bash
python scripts/verify_dataset.py --config data/ppe.yaml
python -c "
import json;m=json.load(open('data/processed/ppe-v1/manifest.json'))
print('classes   :', list(m.get('classes', {})))
print('splits    :', {k: v.get('images') for k, v in m.get('splits', {}).items()})
"
ls data/processed/ppe-v1/images/test | head -3
```

Expected: the deterministic lab subset — **180 train / 60 val / 60 test** images, classes
`Hardhat`, `NO-Hardhat`, `Person`, no missing label files (`var/releases/v1/release.json` records
this same verification).

Talking point: *"The dataset is versioned as `ppe-v1` and its verification result is captured
inside the release metadata, so a model can always be traced back to the exact data contract it
was trained on."*

---

## 4. Phase 3 — MLflow

```bash
./scripts/start_mlflow.sh &      # if not already running
curl -I http://127.0.0.1:5000
```

Open `http://127.0.0.1:5000` in the browser. Point at:

- experiment runs for `edge-ppe-detector`
- the **Models** tab showing versions **1** and **2**
- the **`champion`** alias on version **1**

Talking point: *"MLflow is the system of record. The registry holds two real versions; the
`champion` alias is the single pointer that decides what production serves. Promotion is an alias
move, not a redeploy of code."*

---

## 5. Phase 4 — Train, register, export, prove parity (v1)

Show the artifact, don't retrain (retraining creates a new version and invalidates the numbers on
the slides).

```bash
python scripts/release_status.py
cat var/releases/v1/release.json | python -c "
import json,sys;d=json.load(sys.stdin)
print('registered version :', d['registered_model_version'])
print('onnx sha256        :', d['onnx_sha256'][:16] + '…')
print('export opset       :', d['export_opset'])
print('parity status      :', d['parity_status'])
print('mAP50 / mAP50-95   :', round(d['metrics']['metrics/mAP50(B)'],4), '/', round(d['metrics']['metrics/mAP50-95(B)'],4))
print('git commit         :', d['git_commit'][:8])
"
python -c "
import json;print('parity:', {k: v for k, v in json.load(open('var/releases/v1/parity_report.json')).items() if 'min_iou' in k or 'unmatched' in k or 'confidence' in k})
"
```

Expected for v1: registry version `1`, opset `17`, `parity_status: passed`, mAP50 ≈ `0.5641`.

Then show the parity command that produced it:

```bash
python scripts/validate_parity.py --release v1
```

Talking point: *"Exporting to ONNX is not a deployment. It becomes a deployment candidate only
after a PT↔ONNX parity run proves the exported graph reproduces the PyTorch detections — min IoU
above 0.999 and zero unmatched detections. That gate is what makes ONNX safe to ship."*

---

## 6. Phase 5 — Promotion + registry-mode serving under systemd

```bash
python scripts/release_status.py
cat var/deployment/champion.json
systemctl status edge-ppe --no-pager | head -8

curl -s http://127.0.0.1:8000/health     | python -m json.tool
curl -s http://127.0.0.1:8000/ready      | python -m json.tool
curl -s http://127.0.0.1:8000/model-info | python -m json.tool
```

Expected: unit `edge-ppe` **active (running)**; `/model-info` reports `concrete_model_version: 1`
resolved through alias **`champion`**.

Then a **real** inference, not a synthetic request:

```bash
IMAGE=$(find data/processed/ppe-v1/images/test -type f | sort | head -1)
echo "probe: $IMAGE"
curl -s -F "image=@$IMAGE" http://127.0.0.1:8000/predict | python -m json.tool | head -40
```

Expected: HTTP 200 with real detections (e.g. `Hardhat 0.8832`, `Person 0.8645` — the v1 parity
reference values).

Talking point: *"`/health` means the process is alive. `/ready` means a model is loaded and traffic
may be accepted. `/model-info` proves **which** model. And `/predict` proves it actually infers.
A container that merely started is not a deployment."*

---

## 7. Phase 6 — Docker

```bash
TAG=$(git rev-parse --short HEAD)
docker build --build-arg GIT_SHA="$TAG" -f docker/Dockerfile -t edge-ppe-lab:$TAG .

docker run -d --name edgeppe-api -p 18000:8000 \
  --mount "type=bind,source=$PWD/var/releases/v1/model.onnx,target=/app/models/model.onnx,readonly" \
  -e EDGE_PPE_MODEL_PATH=/app/models/model.onnx \
  -e EDGE_PPE_MODEL_VERSION=1 \
  -e EDGE_PPE_STARTUP_STRICT=true \
  edge-ppe-lab:$TAG

docker ps --filter name=edgeppe-api --format '{{.Names}} | {{.Status}} | {{.Image}}'
docker inspect --format 'user={{.Config.User}} digest={{index .RepoDigests 0}}' edgeppe-api
```

Then the same four-endpoint gate against `:18000`:

```bash
for ep in health ready model-info; do
  echo "$ep -> $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:18000/$ep)"
done
IMAGE=$(find data/processed/ppe-v1/images/test -type f | sort | head -1)
curl -s -F "image=@$IMAGE" http://127.0.0.1:18000/predict | python -m json.tool | head -20
docker stats --no-stream edgeppe-api
```

Talking point: *"The image runs as UID **10001**, non-root, and carries an OCI revision label with
the git SHA. It contains **no model** — the qualified artifact is mounted read-only at deploy time,
so the same image is deployable to a different model version without a rebuild."*

Clean up before the next phase:

```bash
docker rm -f edgeppe-api
```

---

## 8. Phase 7 — A second version, then a controlled failure and rollback

### 8a. v2 is a real, qualified version

```bash
cat var/releases/v2/release.json | python -c "
import json,sys;d=json.load(sys.stdin)
print('registered version :', d['registered_model_version'])
print('onnx sha256        :', d['onnx_sha256'])
print('parity status      :', d['parity_status'])
print('mAP50 / mAP50-95   :', round(d['metrics']['metrics/mAP50(B)'],4), '/', round(d['metrics']['metrics/mAP50-95(B)'],4))
"
python -c "
import json;p=json.load(open('var/releases/v2/parity_report.json'))
print('min IoU:', p.get('min_iou'), 'unmatched:', p.get('unmatched_detections'))
"
```

Expected: version **2**, SHA `43e14f64…`, parity passed (min IoU ≈ `0.99998`), mAP50 ≈ `0.5928` —
better than v1 on paper.

### 8b. The failure that was diagnosed and reverted

Present from evidence rather than re-breaking the running service:

```bash
cat docs/evidence/v2_controlled_deployment_failure.txt
cat docs/evidence/v2_rollback_to_v1.txt
```

Narrate: an explicit invalid model path was injected (`EDGE_PPE_STARTUP_STRICT=true`), the
container exited with a `FileNotFoundError: ONNX model not found`, nothing bound the port, and
critically **the v2 artifact stayed byte-identical** — the failure was a configuration fault, not
artifact corruption. The alias was then moved back to v1 and the service recovered.

### 8c. Prove the rollback landed

```bash
cat var/deployment/champion.json      # champion -> concrete version 1, v2 demoted to qualified
python scripts/release_status.py
curl -s http://127.0.0.1:8000/model-info | python -m json.tool
```

Talking point: *"This is the difference between a reboot and a rollback. The previous state is
re-proven, end to end, including a real inference — not just assumed."*

---

## 9. Phase 8 — The automated gates (this is what CI runs)

```bash
pytest -q
python scripts/verify_release_contract.py
bash -n scripts/*.sh deploy/systemd/install.sh deploy/runner/*.sh
python -c "
import pathlib, yaml
for p in sorted(pathlib.Path('.github/workflows').glob('*.yml')):
    yaml.safe_load(p.read_text()); print('yaml ok:', p)
"
```

Expected today:

```
7 passed
CONTRACT GATE PASSED: 61 checks
bash syntax OK
yaml ok: .github/workflows/cd.yml
yaml ok: .github/workflows/ci.yml
```

Talking point: *"`pytest -q` is deliberately kept as the bare invocation in CI, because that exact
command is the regression test for a real collection failure — `ModuleNotFoundError: No module named
'app'`, exit code 2 — whose fix lives in `pytest.ini`. The gate that caught it is the gate that
still runs it."*

---

## 10. Phase 9 — Observability

```bash
./scripts/start_prometheus.sh
curl -s http://127.0.0.1:18000/metrics | grep -E 'inference_|detections_total|model_info'
```

Open the Prometheus UI and show the `edgeppe-api` target as **UP**, then a rate query over the
inference histogram.

Talking point: *"Scraping the published Docker port via `host.docker.internal` is deliberate — it
works identically on Docker Desktop/WSL2 and native Linux Docker. `monitoring/prometheus.yml`
documents the systemd instance as a second, commented-out target."*

---

## 11. Phase 10 — GitHub-hosted CI (BLOCKED)

What the audience would see once §13 is unblocked:

1. Actions tab → workflow **`edge-ppe-ci`** → the run for the pushed SHA.
2. Steps in order: checkout → Python 3.12 → install → `python -m compileall` → `pytest -q` →
   release contract → shell syntax → workflow YAML → **Docker build** → **image boot smoke test**.
3. Point at the smoke test: it boots the image with `EDGE_PPE_STARTUP_STRICT=false` and asserts
   `/health → 200` **and** `/ready → 503`.

Talking point for the 503: *"That assertion is the readiness contract, verified for real. The image
contains no model by design, so a correctly-built image must serve health but **refuse** traffic."*

Safety properties to call out by reading `ci.yml`: `permissions: contents: read` only, no `secrets.*`
reference anywhere, and `pull_request` + `push: [main, tags]` triggers. *"A forked PR gets nothing it
could exfiltrate, and it can never reach the deployment."*

---

## 12. Phase 11/12 — GHCR + automated deploy + automatic rollback (BLOCKED)

What the audience would see once §13 is unblocked, from `.github/workflows/cd.yml`:

| Step | Evidence to point at |
|---|---|
| `build-and-push` job | `ghcr.io/<owner>/edge-ppe-lab:<git-sha>` pushed; job summary prints the immutable reference |
| Image digest | recorded via `docker inspect .RepoDigests` and surfaced in the run summary |
| `deploy` job | runs on `[self-hosted, linux, x64, edgeppe-deploy]` — confirm the label row |
| Health gate | `scripts/cd_deploy.sh` logs `/health` 200, `/ready` 200, `/model-info` version match, real `/predict` 200 |
| State file | `var/deployment/cd_state.json` — deployed image, digest, previous image, fault value, run id |
| Automatic rollback | re-run via **Run workflow** with `fault_injection: bad_model_path` → candidate fails gate → previous immutable image restored → gate re-passed → run still marked **failed** |

Talking point on the red run: *"The run exits non-zero even though the rollback succeeded. A failed
release must never look green — the rollback is proven, but nothing was deployed."*

Talking point on security: *"There is no `pull_request` trigger in `cd.yml` **at all**, and the
deploy job additionally guards on `github.event_name != 'pull_request'`. Fault injection is only
honoured for `workflow_dispatch`, which requires write access. GHCR needs no long-lived secret —
the ephemeral `github.token` is scoped per job (`packages:write` to publish, `packages:read` to
pull) and piped to `docker login` over stdin."*

---

## 13. The exact blocker, and how to unblock it

Phases 10–12 need two things that only the repository owner can authorise.

### STEP 1 — push the CI/CD implementation

Confirm the target first (do not push to an unverified remote):

```bash
cd ~/projects/edge-ppe-lab
git remote -v
```

Expected: `origin git@github.com:Shivakushwah143/edge-ppe-lab.git`.

Then, after reviewing `git status` / `git diff`, commit **only** the intended CI/CD files —
`.github/workflows/ci.yml`, `.github/workflows/cd.yml`, `deploy/runner/`, `scripts/cd_deploy.sh`,
`scripts/verify_release_contract.py`, `pytest.ini`, `requirements-ci.txt` — and **never**
`edge-ppe-lab-final-verified.zip`, `.env`, any runner credentials, or `var/` runtime state.

Then `git push origin main` (currently 2 commits ahead of `origin/main`).

### STEP 2 — install the self-hosted runner

Not installed yet: `~/actions-runner-edgeppe` does not exist and no `Runner.Listener` process is
running. This needs a **short-lived runner registration token**, which only the GitHub UI can mint:

> **GitHub → `Shivakushwah143/edge-ppe-lab` → Settings → Actions → Runners → New self-hosted runner
> → Linux → copy the token from the `./config.sh --token <TOKEN>` line.**

Then:

```bash
cd ~/projects/edge-ppe-lab
RUNNER_TOKEN=<paste token> ./deploy/runner/install.sh
./deploy/runner/start.sh
tail -5 ~/actions-runner-edgeppe/runner.log
```

Expected labels: `self-hosted, linux, x64, edgeppe-deploy`, and the runner shows **Idle** under
Settings → Actions → Runners.

Security notes to state, not just imply: the token is used in-memory by `config.sh` and is never
written into the repository; the runner is deliberately **not** root, so deployment artefacts keep
the desktop user's ownership; and anything able to push to `main` can run code on this host — which
is precisely why `cd.yml` has no `pull_request` trigger.

---

## 14. 5-minute version (if time is short)

1. `python scripts/release_status.py` — two real versions, `champion = v1`.
2. `curl -s http://127.0.0.1:8000/model-info` — what production reports.
3. Real `/predict` on a real Construction-PPE image — 200 with detections.
4. `cat docs/evidence/v2_controlled_deployment_failure.txt` + `v2_rollback_to_v1.txt` — the failure and the recovery.
5. `pytest -q` and `python scripts/verify_release_contract.py` — 7 passed, 61 checks.
6. `cat .github/workflows/ci.yml` + `cd.yml` — read the security posture out loud, plus the honest
   status that GitHub execution is **BLOCKED** pending §13.

---

## 15. Honest limitations to volunteer

- GitHub-hosted CI, GHCR publication and the self-hosted deploy/rollback jobs are
  **IMPLEMENTED — NOT RUNTIME VERIFIED**, because `origin/main` is behind local `main` and the
  runner is not registered. See `docs/KNOWN_LIMITATIONS.md`.
- The Desktop copy of this repository is stale and has no remote; it must never be used as the
  deployment source.
- Docker is demoed on `:18000`, systemd on `:8000`. They are the same application and **each keeps
  its own metric counters**, so the two instances report independent series.
- `latest` is published for convenience only and is never used as deployment evidence; every
  deployment is addressed by immutable SHA tag.

See also: `START_HERE.md`, `docs/17_ZERO_ASSUMPTION_END_TO_END_JOURNEY.md`,
`docs/evidence/RUNTIME_LIFECYCLE_VERIFICATION.md`.
