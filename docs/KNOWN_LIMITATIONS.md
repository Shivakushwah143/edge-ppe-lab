# Known Limitations

## Current execution-environment limitations

The build sandbox cannot resolve/download the official Construction-PPE archive or missing PyPI dependencies. As a result, the repository could not produce a real trained checkpoint, MLflow run, registered versions, ONNX artifact, parity report, or real inference result during this build session.

The sandbox also does not provide Docker (`docker` command absent), and `systemctl is-system-running` reports `offline`. Docker and systemd files are therefore implemented but not runtime verified here.

These are environment limitations, not converted into successful verification claims. Exact evidence is under `docs/evidence/`.

## Lab limitations by design

EdgePPE Lab is deliberately a learning lab, not a full industrial fleet platform. Its compact dataset subset and one/two-epoch CPU configurations optimize iteration speed, not model accuracy. A production PPE model would require data-quality review, stronger training/evaluation, threshold calibration, robustness tests, drift monitoring, security hardening, and a deployment environment representative of its target cameras/hardware.

The application processes uploaded still images. RTSP/CCTV decode, tracking, frame scheduling/backpressure, and multi-camera orchestration are intentionally future concepts documented in the source-of-truth package rather than part of this small implementation.

The mandatory runtime is CPU ONNX Runtime. TensorRT, CUDA, NVIDIA GPU telemetry, and Jetson packaging cannot be validated without compatible NVIDIA hardware and remain future extensions.

## MLflow availability behavior

The normal service path depends on MLflow to resolve the `champion` alias and fetch the qualified ONNX artifact. With `EDGE_PPE_STARTUP_STRICT=true` (default), failure to resolve/load the deployment model terminates startup. Setting strict mode false is only a diagnostic/degraded-mode option: `/health` can stay alive, but `/ready` returns 503 until a model is loaded.

For the Docker practice exercise, the exact qualified ONNX artifact is mounted read-only and its concrete model version is provided explicitly. This removes an unnecessary WSL/Docker networking dependency from the container lesson. Registry-alias resolution is still exercised by the normal manual/systemd deployment path.

## Artifact packaging

The release ZIP intentionally omits `.venv`, caches, downloaded raw datasets, full training directories, and model binaries that could not be generated in this sandbox. The repository contains deterministic commands/configuration to regenerate them. Once the user completes the WSL2 lifecycle, `var/releases/v1` and `v2` will contain the local trained/exported evidence but those artifacts remain ignored by Git by default.
