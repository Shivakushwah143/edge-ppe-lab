# Known Limitations

## Verification scope

The CPU model lifecycle is now runtime-verified on WSL2 Ubuntu: dataset preparation, v1 and v2
training, MLflow tracking and registry versions, ONNX export, PT↔ONNX parity, promotion, CPU
inference, a controlled deployment failure, a real rollback to v1, and the API running as an
**enabled systemd service** with a verified supervised restart. Evidence index:
`docs/evidence/RUNTIME_LIFECYCLE_VERIFICATION.md`, plus
`docs/evidence/systemd_runtime_verification.txt` and `docs/evidence/registry_tag_hygiene.txt`.

Two things are deliberately **not** claimed as verified:

1. **GitHub Actions CI** — the workflow is validated locally and never executed on a hosted runner.
2. **GPU / TensorRT / Jetson** — no NVIDIA GPU is present (`nvidia-smi` absent,
   `torch.cuda.is_available() == False`), so those paths remain documentation only.

## Operational limitations observed

- **Model is loaded once at startup; there is no hot reload.** Promoting a new champion while the
  service is running does not change what it serves. Redeploy/restart is required. This was observed
  directly: after promoting v2, the running service still reported v1 until it was restarted. This is
  intended immutable-load semantics, and the rollback procedure depends on it.
- **Registry tag hygiene is now enforced (previously a wart).** `scripts/set_champion.py` used to set
  `release_status=champion` on the newly promoted version without clearing it from the previously
  promoted version, so v1 and v2 both carried the tag while the alias pointed at v1. Promotion now
  demotes every other version that still claims `release_status=champion` to `release_status=qualified`
  before tagging the promoted version `champion`, so exactly one version claims it and the metadata can
  no longer contradict the mutable `champion` alias. Deprecated MLflow *stages* are not used anywhere —
  aliases and version tags only. Verified in `docs/evidence/registry_tag_hygiene.txt`
  (alias → 1, v1 = `champion`, v2 = `qualified`).
- **The Docker exercise delivers a concrete qualified artifact, not registry resolution.** The
  container mounts the parity-qualified ONNX read-only and receives `EDGE_PPE_MODEL_VERSION`, which
  avoids depending on WSL→container loopback networking to MLflow. Registry-alias resolution is
  demonstrated by the manual/systemd (host) path instead. Containerising the registry path would need
  host networking or a reachable MLflow endpoint.
- **Redeploy is manual.** There is no orchestrator; `sudo systemctl restart edge-ppe` (or recreating
  the container) is a hand-run step, and during the drill the service was briefly unavailable between
  stop and start. With systemd in place the restart itself is now supervised rather than bespoke.
- **Runtimes are per-process.** Prometheus counters reset when the service or container restarts;
  metric deltas must be compared within one process lifetime.
- **The build is bandwidth-sensitive.** A slow PyPI link (~300 KB/s here) previously aborted the image
  build with a `ReadTimeoutError` on the 62 MB OpenCV wheel. The Dockerfile now retries and uses a
  BuildKit pip cache mount, which keeps partial downloads across attempts and makes the build
  resumable. That cache mount also means builds are faster when repeated, but it is BuildKit-specific.

## Lab limitations by design

EdgePPE Lab is deliberately a learning lab, not an industrial fleet platform. Its compact dataset
subset (180 train / 60 val / 60 test images) and small CPU configurations (10 and 12 epochs at
`imgsz=320`) optimise iteration speed, not model accuracy. Both trained models are modest detectors:
v2 mAP50 0.5928 / mAP50-95 0.2625, v1 mAP50 0.5641 / mAP50-95 0.2550. v2 improves recall
(0.5049 → 0.6117) and mAP while **reducing** precision (0.6529 → 0.5571); promotion was decided on
the fitness/mAP-95 metric and recall, which is a real quality trade-off rather than a strict
improvement. A production PPE model would require data-quality review, stronger training/evaluation,
threshold calibration, robustness tests, drift monitoring, security hardening, and a deployment
environment representative of its target cameras/hardware.

The application processes uploaded still images. RTSP/CCTV decode, tracking, frame
scheduling/backpressure, and multi-camera orchestration are intentionally future concepts documented
in the source-of-truth package rather than part of this small implementation.

The mandatory runtime is CPU ONNX Runtime. TensorRT, CUDA, NVIDIA GPU telemetry, and Jetson packaging
cannot be validated without compatible NVIDIA hardware and remain future extensions.

## MLflow availability behaviour

The normal host service path depends on MLflow to resolve the `champion` alias and fetch the
qualified ONNX artifact. With `EDGE_PPE_STARTUP_STRICT=true` (default), failure to resolve/load the
deployment model terminates startup — which is exactly what the controlled failure drill confirmed.
Setting strict mode false is only a diagnostic/degraded-mode option: `/health` can stay alive, but
`/ready` returns 503 until a model is loaded.

## systemd unit specifics (WSL2 lab deployment)

- The committed unit hardcodes the verified deployment root `/home/shiva_kushwah/projects/edge-ppe-lab`
  and that tree's own interpreter `.venv/bin/uvicorn`, because systemd does not activate a virtualenv
  or expand `~`. `deploy/systemd/install.sh` refuses to install the unit unless `WorkingDirectory`
  matches the tree it was given and the interpreter is executable, so the installed unit cannot
  silently point at a different copy of the code.
- The unit runs as `shiva_kushwah`, the owner of the tree, rather than the `edgeppe` service account the
  original `/opt`-style installer created: the deployment root is inside `/home`, and creating a
  service account would have required loosening the home directory (currently `0750`). Moving the tree
  to `/opt` with a dedicated account is the hardening upgrade path.
- `ProtectHome=false` is deliberate for the same reason: with the code inside `/home`, a read-only or
  hidden home would make the service unable to read its own files. `ProtectSystem=full`,
  `NoNewPrivileges=true`, `PrivateTmp=true` and `ReadWritePaths=<tree>/var` are still applied, so the
  process can only write inside the project's `var/` directory.
- `systemctl enable edge-ppe` succeeds, but whether a WSL distro starts units at boot still depends on
  the WSL/systemd lifecycle; the verified property is supervision, not a production boot guarantee.

## Artifact packaging

`edge-ppe-lab-final-verified.zip` (121 members, 17.7 MiB) is the packaged release. Exact inventory
and checksum: `docs/evidence/release_package_manifest.txt`, which is committed and published
alongside the archive. That manifest is deliberately **not** a member of the archive — an archive
cannot contain its own checksum — so it is the one tracked file the archive omits.

**Included:** source (`app/`, `scripts/`, `tests/`), configuration (`configs/`, `data/ppe.yaml`,
`requirements*.txt`, `Makefile`, `.dockerignore`, `.env.example`), documentation (`docs/`, including
every raw evidence capture), the qualified deployment artifacts `var/releases/v1/model.onnx` and
`var/releases/v2/model.onnx`, the per-release metadata (`release.json`, `parity_report.json`,
`onnx_contract.json`, `environment.json`), the release pointer `var/deployment/champion.json`, the
dataset-verification snapshots `var/dataset-v1|v2.yaml`, the Docker build evidence in `var/docker/`,
and the Docker/systemd deployment configuration.

**Excluded, with the reason:** `.git/` and `.venv/` (6.8 GB of third-party packages); the raw
Construction-PPE archive and the derived `data/processed/` dataset (350 MB + 37 MB, both
reproducible with `python scripts/prepare_dataset.py`); caches (`__pycache__`, `.pytest_cache`,
`var/model-cache/`, a runtime artifact download cache the service recreates at startup); the MLflow
backend store and artifact store (`var/mlflow/`, live SQLite runtime state — the registry state it
holds is captured verbatim in the evidence files instead); full training run directories
(`var/training/`); the raw-export duplicate `best.onnx` (byte-identical to `model.onnx`, verified by
SHA-256) and the PyTorch checkpoints/base weights (`*.pt`), which the repository deliberately keeps
out of Git too; and the temporary hand-run service logs (`var/api.log*`, `var/api.exit`), which were
deleted rather than shipped.

The two packaged ONNX artifacts were verified **from inside the archive**: `unzip -t` reports no
errors, each extracted `model.onnx` hashes to the exact `onnx_sha256` recorded in its `release.json`,
and `onnx.checker` passes on both (opset 17, IR 8).

`var/releases/*/best.pt` and `*.onnx` remain ignored by Git by design, so the Git commit carries the
release *metadata* while the archive carries the *artifacts*. `var/model-cache/v1|v2/model.onnx` and
`var/mlflow/` are runtime state created by the service, not release artifacts.
