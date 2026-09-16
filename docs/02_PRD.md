# 02 — Product Requirements Document

## Product name

**EdgePPE Lab — Production Model Lifecycle on Linux**

## Product purpose

A compact local lab that teaches a production-minded computer-vision MLOps lifecycle end to end on WSL2/Ubuntu.

## Primary user

A software engineer preparing for Computer Vision / MLOps work who already understands programming but needs practical Linux and model-deployment depth.

## Core use case

The user trains a tiny PPE detector, tracks the experiment, registers a deployable model version, exports and validates ONNX, serves real predictions, operates the service on Linux, observes it, deploys a second version, induces a failure, and restores the previous version.

## Functional requirements

### FR-P1 Training
- Train a small Ultralytics YOLO model on a small labeled PPE dataset.
- Preserve the selected training checkpoint (`best.pt`) as a traceable artifact.
- Record dataset identity, major hyperparameters, code/Git revision where practical, and evaluation metrics.

### FR-P2 MLflow
- Use an MLflow tracking server, not only local console output.
- Use a database-backed backend suitable for the registry in the local lab.
- Log runs, parameters, metrics, artifacts, and lineage.
- Register a model named `edge-ppe-detector`.
- Use immutable model versions and an alias (`champion`) for the deployment pointer.

### FR-P3 ONNX
- Export the chosen model to ONNX.
- Record the export contract: input dimensions, dtype, layout, output semantics, opset, static/dynamic shape decision.
- Run parity validation on identical images through both runtimes.
- Block deployment when parity tolerances fail.

### FR-P4 Inference API
The service must expose:
- `GET /health`
- `GET /ready`
- `GET /model-info`
- `POST /predict`
- `GET /metrics`

`/predict` must execute real inference and return detections; fake/sample detections are prohibited.

### FR-P5 Linux operation
The same service must be operated first as a foreground/manual Linux process. The learner must inspect process state, port ownership, environment variables, logs, filesystem paths, permissions, CPU/RAM, and storage.

### FR-P6 systemd
Where WSL systemd is supported/enabled, run the service under a systemd unit and practice start/status/restart/stop/log inspection.

### FR-P7 Docker
Build and run a Docker image for the inference service. Practice image/container distinction, logs, inspect, stats, exec, stop, and failure diagnosis.

### FR-P8 Monitoring
Expose at least request count, failures, latency, model identity/version, and process health. Keep ML quality metrics distinct from online service metrics.

### FR-P9 CI/CD
On Git push, perform deliberately small validation: Python checks/tests, model contract/parity check if artifact is available in CI, Docker build, immutable image tag creation, and deployment-candidate output.

### FR-P10 Versioning + rollback
- v1 is deployed and verified.
- v2 is trained/registered and deployed.
- v2 is intentionally made unhealthy or invalid.
- evidence is collected.
- `champion` is restored to v1 and service is restarted/redeployed.
- `/model-info` proves v1 is active again.

## Non-functional requirements

- Small enough to understand every component.
- CPU-capable local path.
- Reproducible commands.
- Clear failures rather than silent fallback.
- Explicit model identity at runtime.
- Immutable version references in deployment evidence.
- No hidden hot reload of production model state.
- No mandatory external paid service.

## Success metrics for the lab

Success is completion of the acceptance criteria, not detector accuracy. The learner must produce terminal evidence of training, registry lineage, conversion parity, a running API, model-info identity, Linux diagnostics, metrics, v2 failure, and verified v1 rollback.
