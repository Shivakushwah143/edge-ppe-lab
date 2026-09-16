# 17 — Zero-Assumption End-to-End Journey

This is the primary hands-on document. Perform the flow in order. Commands are intentionally illustrative at the documentation stage; the build phase must make exact project commands match the generated repository.

## Step 1 — Install/verify WSL2 and Ubuntu
**WHAT:** Establish a real Linux userspace on the Windows machine.  
**WHY:** The project is designed to teach Linux operations, not Windows equivalents.  
**COMMAND:** From elevated PowerShell use current WSL installation/verification commands such as `wsl --install`, then `wsl --version` and `wsl -l -v`.  
**EXPECTED RESULT:** Ubuntu exists and runs as WSL version 2.  
**LEARN:** WSL2 provides a Linux kernel environment while Windows remains the physical host OS.  
**COMMON FAILURE:** Old WSL installation does not support expected features.  
**DEBUG:** Update WSL, re-check `wsl --version`, then reopen Ubuntu.

## Step 2 — Verify Ubuntu and system basics
**WHAT:** Enter Ubuntu and identify environment.  
**WHY:** Never assume which shell/user/kernel you are using.  
**COMMAND:** `whoami`, `pwd`, `uname -a`, `cat /etc/os-release`.  
**EXPECTED RESULT:** Ubuntu identity and Linux home directory.  
**LEARN:** Runtime facts are evidence.  
**COMMON FAILURE:** Working from `/mnt/c/...` instead of Linux filesystem.  
**DEBUG:** `cd ~` and create the project under the Linux home filesystem.

## Step 3 — Create the Linux project directory
**WHAT:** Create the repository location.  
**WHY:** Linux filesystem performance/permissions are more representative than developing from a Windows-mounted path.  
**COMMAND:** `mkdir -p ~/projects/edge-ppe-lab && cd ~/projects/edge-ppe-lab && pwd`.  
**EXPECTED RESULT:** path under `/home/<user>/projects/edge-ppe-lab`.  
**LEARN:** filesystem layout and current working directory.  
**COMMON FAILURE:** creating similarly named folders in multiple locations.  
**DEBUG:** `find ~/projects -maxdepth 2 -type d -name 'edge-ppe-lab'`.

## Step 4 — Initialize Git
**WHAT:** Create source history.  
**WHY:** Deployed application versions need traceability to code/config revisions.  
**COMMAND:** initialize repo, configure remote later, make first documentation/build commit.  
**EXPECTED RESULT:** `git status` works and later commits have SHAs.  
**LEARN:** Git version is different from model version.  
**COMMON FAILURE:** accidentally tracking large model/run artifacts.  
**DEBUG:** inspect `.gitignore` and `git status` before commits.

## Step 5 — Create Python virtual environment
**WHAT:** Isolate Python dependencies.  
**WHY:** Reproducible tool versions are part of the runtime contract.  
**COMMAND:** `python3 -m venv .venv` then activate it.  
**EXPECTED RESULT:** `which python` points inside `.venv`.  
**LEARN:** shell environment determines executable resolution.  
**COMMON FAILURE:** missing `venv` package or using system Python accidentally.  
**DEBUG:** `python3 --version`, `which python3`, install distro venv package if required.

## Step 6 — Install locked dependencies
**WHAT:** Install build-defined requirements.  
**WHY:** Training/export/runtime behavior depends on package versions.  
**COMMAND:** `python -m pip install --upgrade pip` then `python -m pip install -r requirements.txt`.  
**EXPECTED RESULT:** imports and version-report command succeed.  
**LEARN:** environment reproducibility.  
**COMMON FAILURE:** network timeout or incompatible Python/package versions.  
**DEBUG:** check Python version, package resolver output, disk space, and network.

## Step 7 — Prepare dataset v1
**WHAT:** Obtain/prepare a small labeled PPE dataset with the three required classes.  
**WHY:** Every later model artifact must trace back to defined data.  
**COMMAND:** `python scripts/verify_dataset.py --config data/ppe.yaml`.  
**EXPECTED RESULT:** train/validation data plus a manifest/class map.  
**LEARN:** dataset version is independent from Git/model version.  
**COMMON FAILURE:** wrong class IDs or broken label/image paths.  
**DEBUG:** inspect dataset YAML/manifest, sample labels/images, class counts.

## Step 8 — Start MLflow tracking server
**WHAT:** Start local tracking + registry service with database-backed backend and local artifacts.  
**WHY:** Training evidence must outlive terminal output and support model registry.  
**COMMAND:** `mkdir -p var/mlflow/artifacts && mlflow server --backend-store-uri sqlite:///var/mlflow/mlflow.db --artifacts-destination "$(pwd)/var/mlflow/artifacts" --host 127.0.0.1 --port 5000`.  
**EXPECTED RESULT:** MLflow HTTP UI is reachable locally.  
**LEARN:** backend metadata store and artifact store are different responsibilities.  
**COMMON FAILURE:** port conflict or wrong artifact/backend path.  
**DEBUG:** `ss -lntp`, server logs, `pwd`, `ls -lah`.

## Step 9 — Open MLflow UI
**WHAT:** Inspect experiments visually.  
**WHY:** Learn how run metadata, metrics, artifacts, and registry relate.  
**COMMAND:** open the configured local MLflow URL in browser; optionally verify with `curl`.  
**EXPECTED RESULT:** UI loads and shows experiment space.  
**LEARN:** tracking server is a service, not a Python object inside training.  
**COMMON FAILURE:** service bound to wrong interface/port.  
**DEBUG:** `ss -lntp`, `curl`, MLflow logs.

## Step 10 — Train YOLO v1
**WHAT:** Train the small detector.  
**WHY:** Produce a real checkpoint and metrics.  
**COMMAND:** `export MLFLOW_TRACKING_URI=http://127.0.0.1:5000` then `python scripts/train.py --config configs/train-v1.yaml`.  
**EXPECTED RESULT:** training completes, `best.pt` exists, MLflow run created.  
**LEARN:** checkpoint is an artifact of a run, not yet a production release.  
**COMMON FAILURE:** dataset path/class mismatch or insufficient resources.  
**DEBUG:** training logs, dataset config, `free -h`, `df -h`.

## Step 11 — Inspect run and evaluation
**WHAT:** Review parameters, precision, recall, mAP, artifacts.  
**WHY:** A registered/deployed model should have evidence.  
**COMMAND:** open `http://127.0.0.1:5000` and inspect the run; from Linux verify the tracking service with `curl -I http://127.0.0.1:5000`.  
**EXPECTED RESULT:** run ID and selected checkpoint are traceable.  
**LEARN:** run vs artifact vs metric.  
**COMMON FAILURE:** metrics logged to wrong run/experiment.  
**DEBUG:** print/log active run ID, check MLflow tracking URI and experiment name.

## Step 12 — Register `edge-ppe-detector` v1
**WHAT:** Create a registry version linked to the selected model/run.  
**WHY:** Registry gives stable naming, immutable versioning, lineage, tags, and aliases.  
**COMMAND:** `python scripts/register_model.py --release v1`.  
**EXPECTED RESULT:** registered model exists with version 1.  
**LEARN:** model registry adds lifecycle identity beyond files.  
**COMMON FAILURE:** registry backend misconfigured or model not properly logged.  
**DEBUG:** MLflow server logs, backend database configuration, run/model URI.

## Step 13 — Export v1 to ONNX
**WHAT:** Convert selected checkpoint to deployment format.  
**WHY:** Serve through ONNX Runtime rather than requiring training framework semantics.  
**COMMAND:** `python scripts/export_onnx.py --release v1`.  
**EXPECTED RESULT:** `model.onnx` plus recorded input/output/opset metadata.  
**LEARN:** conversion creates a new deployment artifact.  
**COMMON FAILURE:** unsupported operator/package mismatch.  
**DEBUG:** exporter logs, package versions, opset/runtime compatibility.

## Step 14 — Validate PyTorch ↔ ONNX parity
**WHAT:** Run identical validation images through both runtimes.  
**WHY:** Successful export does not prove equivalent behavior.  
**COMMAND:** `python scripts/validate_parity.py --release v1`.  
**EXPECTED RESULT:** report with matched classes, confidence deltas, box IoUs, pass/fail.  
**LEARN:** deployment conversion requires evidence.  
**COMMON FAILURE:** preprocessing/postprocessing differs between paths.  
**DEBUG:** compare decoded pixels, resize/letterbox, normalization, output transforms, NMS.

## Step 15 — Point `champion` to v1
**WHAT:** Mark v1 as intended active version.  
**WHY:** Separate approval/deployment selection from chronological “latest.”  
**COMMAND:** `python scripts/set_champion.py --version 1`.  
**EXPECTED RESULT:** registry shows `champion` → v1.  
**LEARN:** alias is mutable; version is immutable.  
**COMMON FAILURE:** alias changed before validation.  
**DEBUG:** query registry alias and version tags; enforce release checklist.

## Step 16 — Start FastAPI manually
**WHAT:** Launch Uvicorn in the Ubuntu shell.  
**WHY:** Understand process behavior before adding systemd/Docker.  
**COMMAND:** set the environment documented in `.env.example`, then run `uvicorn app.main:app --host 0.0.0.0 --port 8000`.  
**EXPECTED RESULT:** foreground process logs concrete model version 1 and provider.  
**LEARN:** application startup resolves configuration and loads the artifact.  
**COMMON FAILURE:** missing env/model path/MLflow URI.  
**DEBUG:** `env`, `echo`, `pwd`, `ls`, startup logs.

## Step 17 — Inspect process and port
**WHAT:** Prove the service exists as a Linux process/listening socket.  
**WHY:** This is foundational production debugging.  
**COMMAND:** `ps aux | grep uvicorn` and `ss -lntp`.  
**EXPECTED RESULT:** PID and expected port are visible.  
**LEARN:** HTTP failures can be process or network-layer failures.  
**COMMON FAILURE:** port already occupied.  
**DEBUG:** identify owner with `ss`/`ps`, stop the correct process.

## Step 18 — Curl health/readiness/model-info
**WHAT:** Exercise operational endpoints.  
**WHY:** Prove actual runtime state, not just process existence.  
**COMMAND:** `curl -s http://127.0.0.1:8000/health`, `curl -s http://127.0.0.1:8000/ready`, and `curl -s http://127.0.0.1:8000/model-info`.  
**EXPECTED RESULT:** health/ready succeed; model-info says `edge-ppe-detector`, version 1, ONNX.  
**LEARN:** desired alias and actual loaded version are separate states.  
**COMMON FAILURE:** health passes while readiness fails.  
**DEBUG:** inspect startup/model logs rather than treating health as full readiness.

## Step 19 — Run a real prediction
**WHAT:** Send a real image to `/predict`.  
**WHY:** End-to-end inference is the final serving proof.  
**COMMAND:** `curl -s -X POST -F "file=@samples/ppe-test.jpg" http://127.0.0.1:8000/predict`.  
**EXPECTED RESULT:** real detection list plus model version.  
**LEARN:** transport, preprocessing, runtime, postprocessing, response all participate.  
**COMMON FAILURE:** wrong content type/image decoding.  
**DEBUG:** API validation error, logs, test with known-good image.

## Step 20 — Inspect logs and metrics
**WHAT:** Observe stdout and `/metrics`.  
**WHY:** Build operational habits before failures happen.  
**COMMAND:** inspect the running terminal, then `curl -s http://127.0.0.1:8000/metrics | head -80`, `top`, and `free -h`.  
**EXPECTED RESULT:** request count/latency/model info visible.  
**LEARN:** ML quality and service health are different.  
**COMMON FAILURE:** high-cardinality metric labels.  
**DEBUG:** inspect metric names/labels; keep labels bounded.

## Step 21 — Run under systemd where supported
**WHAT:** Convert manual process into supervised service.  
**WHY:** Learn restart/status/journal behavior.  
**COMMAND:** verify with `ps -p 1 -o comm=`; install the build-provided `deploy/systemd/edge-ppe.service`, run `sudo systemctl daemon-reload`, `sudo systemctl start edge-ppe`, and `systemctl status edge-ppe`.  
**EXPECTED RESULT:** service active and endpoints healthy.  
**LEARN:** process supervision and service identity.  
**COMMON FAILURE:** systemd not enabled in WSL or service user cannot read model.  
**DEBUG:** verify PID 1/systemd, `systemctl status`, `journalctl`, `ls -l`, `id`.

## Step 22 — Restart and inspect journal
**WHAT:** Practice controlled restart.  
**WHY:** Model/config changes generally require process replacement.  
**COMMAND:** `systemctl restart edge-ppe`; `journalctl -u edge-ppe -n 100`.  
**EXPECTED RESULT:** new startup entry and model identity, service ready.  
**LEARN:** restart creates a new runtime instance even if source files are unchanged.  
**COMMON FAILURE:** restart loop.  
**DEBUG:** stop repeated retries if needed and fix root startup error.

## Step 23 — Build Docker image
**WHAT:** Package the validated app/runtime.  
**WHY:** Reproducible deployment packaging.  
**COMMAND:** `GIT_SHA=$(git rev-parse --short HEAD) && docker build -t edge-ppe:${GIT_SHA} .`.  
**EXPECTED RESULT:** image appears in local image list.  
**LEARN:** image is a package, not a running service.  
**COMMON FAILURE:** huge context, missing dependency, missing intended artifact.  
**DEBUG:** build logs, `.dockerignore`, Dockerfile stages, disk space.

## Step 24 — Run and inspect container
**WHAT:** Start the inference container.  
**WHY:** Practice container runtime operations.  
**COMMAND:** run the image with the build-documented env/model settings and `-p 8000:8000`; then use `docker ps`, `docker logs edge-ppe`, `docker inspect edge-ppe`, and `docker stats edge-ppe --no-stream`.  
**EXPECTED RESULT:** mapped host port responds; model-info identifies v1.  
**LEARN:** container config controls env/mounts/ports.  
**COMMON FAILURE:** bind only to localhost inside container or missing model mount/env.  
**DEBUG:** logs, inspect networking/env/mounts, service bind address.

## Step 25 — Exercise Prometheus metrics
**WHAT:** Generate several prediction requests and inspect metrics.  
**WHY:** See counters/histograms move under real traffic.  
**COMMAND:** send several `curl -X POST -F "file=@samples/ppe-test.jpg" .../predict` requests, then `curl -s http://127.0.0.1:8000/metrics`.  
**EXPECTED RESULT:** request/detection counters and latency buckets change.  
**LEARN:** metrics are measurements of runtime behavior.  
**COMMON FAILURE:** metrics reset after process restart.  
**DEBUG:** understand process-local metric lifetime; persistence is out of scope unless Prometheus server added.

## Step 26 — Train/register v2
**WHAT:** Make a controlled dataset/config/model change and create another run.  
**WHY:** Learn full repeated lifecycle, not manual file replacement.  
**COMMAND:** `python scripts/train.py --config configs/train-v2.yaml && python scripts/register_model.py --release v2 && python scripts/export_onnx.py --release v2 && python scripts/validate_parity.py --release v2`.  
**EXPECTED RESULT:** `edge-ppe-detector` version 2 exists with separate lineage.  
**LEARN:** new run and new model version are distinct identities.  
**COMMON FAILURE:** overwriting v1 artifacts.  
**DEBUG:** use versioned artifact paths and immutable registry history.

## Step 27 — Deploy v2
**WHAT:** Promote candidate only after validation.  
**WHY:** Practice release control.  
**COMMAND:** `python scripts/set_champion.py --version 2`, then restart the selected runtime (manual process, `sudo systemctl restart edge-ppe`, or recreate the Docker container).  
**EXPECTED RESULT:** `/model-info` says version 2; ready/predict pass.  
**LEARN:** alias movement changes desired release; process restart changes actual runtime.  
**COMMON FAILURE:** alias says v2 but old process still serves v1.  
**DEBUG:** trust `/model-info` on the running service, not registry UI alone.

## Step 28 — Break v2 intentionally
**WHAT:** Introduce a documented safe deployment fault.  
**WHY:** Practice incident diagnosis.  
**COMMAND:** use the build-provided failure-lab switch to point the v2 deployment at a deliberately invalid ONNX path, then restart/redeploy; do not corrupt/delete registry history.  
**EXPECTED RESULT:** service/startup/readiness failure with clear evidence.  
**LEARN:** safe failure drills build operational confidence.  
**COMMON FAILURE:** breaking unrelated host state.  
**DEBUG:** keep failure scoped to deployment config/artifact and preserve registry/history.

## Step 29 — Diagnose the v2 incident
**WHAT:** Collect evidence before fixing.  
**WHY:** Production debugging should be hypothesis-driven.  
**COMMAND:** `pwd`, `ls`, `find`, `env`, `ls -l`, `ps`, `ss`, `systemctl`, `journalctl`, Docker commands as applicable.  
**EXPECTED RESULT:** one evidence chain explains the root cause.  
**LEARN:** Linux commands answer specific operational questions.  
**COMMON FAILURE:** changing multiple things before identifying the cause.  
**DEBUG:** use the failure report template in doc 16.

## Step 30 — Roll back to v1
**WHAT:** Restore known-good deployment.  
**WHY:** Recovery speed matters more than debugging v2 in the production path.  
**COMMAND:** `python scripts/set_champion.py --version 1`, then restart/redeploy the same runtime mechanism used for v2.  
**EXPECTED RESULT:** service loads concrete model version 1.  
**LEARN:** rollback is a controlled release, not copying random old files.  
**COMMON FAILURE:** alias changed but process not restarted.  
**DEBUG:** compare registry alias and runtime `/model-info`.

## Step 31 — Verify recovery
**WHAT:** Prove end-to-end restoration.  
**WHY:** “command succeeded” is not enough.  
**COMMAND:** run the exact health/readiness/model-info curls from Step 18, repeat the known-image prediction from Step 19, and inspect logs plus `/metrics`.  
**EXPECTED RESULT:** v1 identity + successful prediction + normal service behavior.  
**LEARN:** recovery requires verification at multiple layers.  
**COMMON FAILURE:** only checking process status.  
**DEBUG:** require all acceptance evidence before closing incident.

## Final learner evidence pack

Keep screenshots/text outputs for: WSL verification, MLflow run + registry versions, ONNX parity report, process/port inspection, v1 model-info, systemd status/journal, Docker inspect/logs/stats, metrics, v2 model-info, failure evidence, v1 rollback model-info, and final successful prediction.
