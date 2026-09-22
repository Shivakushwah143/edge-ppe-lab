# START HERE — Hands-on WSL2 / Ubuntu Journey

This is the shortest manual path. Run commands one section at a time so you can see every artifact and process.

## Status of this journey (executed on WSL2, 2026-09-22)

This journey has already been run end to end on this machine, so most artifacts below exist and can be inspected instead of re-created:

- v1 and v2 are both really trained — registry versions **1** and **2** under `edge-ppe-detector`.
- Both releases exported a CPU ONNX artifact and **passed PT↔ONNX parity** (`docs/evidence/v1-onnx-parity.json`, `docs/evidence/v2-onnx-parity.json`).
- v2 was promoted to `champion` and served real traffic, a bad deployment configuration was then injected deliberately and diagnosed, and `champion` was rolled back to **v1**.
- Final state: `champion = v1` (and v2's stale `release_status=champion` tag demoted to `qualified`); the API runs as the enabled systemd unit `edge-ppe` on `:8000` in registry mode; Docker container `running/healthy` on `:18000`; both serving v1 with CPU inference.
- Full record: `docs/evidence/RUNTIME_LIFECYCLE_VERIFICATION.md`.

You do **not** need to retrain v1/v2 or rebuild the dataset to follow along — inspect `var/releases/*/release.json`, `var/training/*`, the MLflow UI and `docs/evidence/` instead. Re-running the commands below will simply create new runs and versions.

## 1. Create the Linux working copy

```bash
mkdir -p ~/projects
cd ~/projects
unzip /mnt/c/Users/<you>/Downloads/edge-ppe-lab.zip
cd edge-ppe-lab
pwd
```

Expected working directory: `~/projects/edge-ppe-lab`. Initialize the practice repository so every MLflow run can record a real Git commit:

```bash
git init
git add .
git commit -m "chore: initialize EdgePPE Lab"
git rev-parse HEAD
```

If Git asks for identity, configure your own `user.name` and `user.email`, then rerun the commit.

## 2. Python environment

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git curl unzip build-essential rsync
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python scripts/verify_components.py
```

## 3. Prepare the official dataset

```bash
python scripts/prepare_dataset.py
python scripts/verify_dataset.py --config data/ppe.yaml
cat data/processed/ppe-v1/manifest.json | less
```

The default is a deterministic compact lab subset from the official Construction-PPE dataset. Use `--full` to process every upstream image.

## 4. Start MLflow manually

Terminal A:

```bash
source .venv/bin/activate
./scripts/start_mlflow.sh
```

Terminal B:

```bash
cd ~/projects/edge-ppe-lab
source .venv/bin/activate
export MLFLOW_TRACKING_URI=http://127.0.0.1:5000
curl -I http://127.0.0.1:5000
```

Open `http://127.0.0.1:5000` in the Windows browser.

## 5. Train/register/export/validate v1

```bash
python scripts/train.py --config configs/train-v1.yaml
python scripts/register_model.py --release v1
python scripts/export_onnx.py --release v1
python scripts/validate_parity.py --release v1
cat var/releases/v1/release.json | less
```

On a fresh MLflow registry, v1 normally becomes model version 1. Confirm the actual value in `release.json` before promotion.

```bash
python scripts/set_champion.py --release v1
python scripts/release_status.py
```

## 6. Start the inference API manually

```bash
export MLFLOW_TRACKING_URI=http://127.0.0.1:5000
export EDGE_PPE_MODEL_NAME=edge-ppe-detector
export EDGE_PPE_MODEL_ALIAS=champion
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

In another terminal:

```bash
curl -s http://127.0.0.1:8000/health | python -m json.tool
curl -s http://127.0.0.1:8000/ready | python -m json.tool
curl -s http://127.0.0.1:8000/model-info | python -m json.tool
IMAGE=$(find data/processed/ppe-v1/images/test -type f | head -1)
curl -s -F "image=@$IMAGE" http://127.0.0.1:8000/predict | python -m json.tool
curl -s http://127.0.0.1:8000/metrics | grep -E 'inference_|detections_total|model_info'
```

## 7. Inspect Linux like an MLOps engineer

```bash
pwd
ls -lah
find var/releases -maxdepth 2 -type f
ps -ef | grep '[u]vicorn'
ss -lntp | grep ':8000'
env | grep -E 'EDGE_PPE|MLFLOW'
free -h
df -h .
du -sh var
```

## 8. systemd, only when WSL reports systemd running

```bash
systemctl is-system-running
```

If it reports a usable state, install the production-style unit:

```bash
sudo ./deploy/systemd/install.sh "$PWD"
sudo nano /etc/edge-ppe/edge-ppe.env
sudo systemctl daemon-reload
sudo systemctl enable edge-ppe
sudo systemctl start edge-ppe
systemctl status edge-ppe --no-pager
journalctl -u edge-ppe -n 100 --no-pager
sudo systemctl restart edge-ppe
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/ready
curl -s http://127.0.0.1:8000/model-info
```

The committed unit already references this working copy by absolute path, so `install.sh` installs it
verbatim and refuses to proceed if `WorkingDirectory`/`ExecStart` do not match the tree you pass it:

- `WorkingDirectory=/home/shiva_kushwah/projects/edge-ppe-lab`
- `ExecStart=/home/shiva_kushwah/projects/edge-ppe-lab/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000`

Two operational notes:

- Only one process can bind `:8000`. If you still have the manual Uvicorn from section 6 running,
  stop it (`kill <pid>`) before starting the unit, then everything is owned by systemd.
- The service needs MLflow reachable at `MLFLOW_TRACKING_URI` in order to resolve the `champion`
  alias and download the qualified artifact; with `EDGE_PPE_STARTUP_STRICT=true` it exits if that
  resolution fails. Startup therefore takes a few seconds, and `journalctl` is the place to watch it.

Verified on this machine (2026-09-22): unit installed and `enabled`, `active (running)`, `/ready` 200
with model_version 1, `/model-info` version 1 via alias `champion`, real `/predict` 200, and
`Restart=on-failure` proven by killing the main PID (`NRestarts=1`, service returned to `active` in
~10 s). Attempting to use the unit and the manual Uvicorn at the same time fails with
`Errno 98 Address already in use` — that is expected, not a bug.

Do not claim systemd verification if `systemctl is-system-running` is offline/unsupported.

## 9. Docker

First read the concrete version and qualified artifact from the release metadata. This keeps the Docker exercise independent of WSL-to-container loopback behavior while still deploying the exact model version that passed parity.

```bash
git rev-parse --short HEAD
TAG=$(git rev-parse --short HEAD)
VERSION=$(python -c 'import json; print(json.load(open("var/releases/v1/release.json"))["registered_model_version"])')
test "$(python -c 'import json; print(json.load(open("var/releases/v1/release.json"))["parity_status"])')" = passed
test -f var/releases/v1/model.onnx

docker build --build-arg GIT_SHA="$TAG" -f docker/Dockerfile -t edge-ppe-lab:$TAG .
docker run --rm --name edge-ppe-api -p 8000:8000 \
  -v "$PWD/var/releases/v1/model.onnx:/models/model.onnx:ro" \
  -e EDGE_PPE_MODEL_PATH=/models/model.onnx \
  -e EDGE_PPE_MODEL_VERSION="$VERSION" \
  -e EDGE_PPE_STARTUP_STRICT=true \
  edge-ppe-lab:$TAG
```

Then exercise `docker ps`, `docker logs edge-ppe-api`, `docker inspect edge-ppe-api`, `docker stats --no-stream edge-ppe-api`, and a real `/predict`. `/model-info` must report the same concrete registry version recorded in `release.json`. The normal host/systemd deployment still demonstrates registry-alias resolution via `champion`; the Docker exercise deliberately demonstrates deployment of a concrete, already-qualified artifact.

Runtime dependency note (2026-09-22): `requirements-runtime.txt` installs `mlflow-skinny` rather than full `mlflow` (the runtime only needs `set_tracking_uri` + `MlflowClient`, so pandas/matplotlib/scipy/scikit-learn never enter the image), and the pip step now sets `PIP_DEFAULT_TIMEOUT=180` / `PIP_RETRIES=10`, retries the resolve up to three times, and uses a BuildKit pip cache mount so a slow build resumes. The first build attempt here failed with a PyPI `ReadTimeoutError` while downloading the 62 MB `opencv-python-headless` wheel — that was a **network timeout, not a CUDA/NVIDIA problem** (the runtime requirements have never contained torch). The verified image is `edge-ppe-lab:local` (569 MB, CPU-only) and its build exits `EXIT=0`.

## 10. Train and qualify v2

```bash
python scripts/train.py --config configs/train-v2.yaml
python scripts/register_model.py --release v2
python scripts/export_onnx.py --release v2
python scripts/validate_parity.py --release v2
cat var/releases/v2/release.json | less
```

Read the actual registered version from the file. In a fresh registry it should be 2:

```bash
python scripts/set_champion.py --release v2
# restart/redeploy API so alias is resolved again
curl -s http://127.0.0.1:8000/model-info | python -m json.tool
```

Verified outcome on this machine: v2 registered as version **2**, ONNX SHA-256 `43e14f6484290bfd44349e68dc14781c2e17268999ce0100b8a13e809f276fd4` (opset 17, `onnx.checker` PASS), parity min IoU 0.999982796774978 / max confidence delta 9.26136016876633e-07 / 0 unmatched detections, and metrics precision 0.5571446570824707, recall 0.6117216117216118, mAP50 0.592819785851068, mAP50-95 0.26245204921499393. After promotion the registry-mode service **downloaded** the qualified artifact into `var/model-cache/v2/model.onnx` (SHA matched) and `/model-info` reported version 2.

## 11. Safe failure + rollback drill

First prove healthy v2. Then intentionally start a separate API instance with a bad explicit artifact path:

```bash
EDGE_PPE_MODEL_PATH=/tmp/not-a-real-model.onnx \
EDGE_PPE_MODEL_VERSION=2 \
EDGE_PPE_STARTUP_STRICT=true \
uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Inspect the failure using `pwd`, `ls`, `find`, `ps`, `ss -lntp`, and the terminal/service logs. Do **not** modify v2 parity evidence.

Rollback the release pointer and restart the real service:

```bash
python scripts/set_champion.py --release v1
sudo systemctl restart edge-ppe 2>/dev/null || true
# or stop/restart manual Uvicorn
curl -s http://127.0.0.1:8000/model-info | python -m json.tool
curl -s http://127.0.0.1:8000/ready | python -m json.tool
IMAGE=$(find data/processed/ppe-v1/images/test -type f | head -1)
curl -s -F "image=@$IMAGE" http://127.0.0.1:8000/predict | python -m json.tool
```

Final success means the service proves concrete v1 again and real prediction still works.

Verified outcome on this machine: the invalid path produced container `exit_code=3` with `FileNotFoundError: ONNX model not found: /nonexistent/model-v2.onnx` and nothing bound on the port, while the v2 artifact stayed byte-identical (`onnx.checker` PASS, SHA unchanged) and the registry alias was untouched. After the rollback, the alias API reported `champion → version 1`, `/ready` was healthy, and `/predict` returned 200 with Hardhat 0.8832 / Person 0.8645 — the exact v1 parity reference values. Evidence: `docs/evidence/v2_controlled_deployment_failure.txt`, `docs/evidence/v2_rollback_to_v1.txt`, `docs/evidence/final_state_verification.txt`.
