# 01 — Problem and Learning Objectives

## Problem

A developer can train a YOLO model in a notebook and still be unable to operate it in production. The gap is the **model lifecycle around the model**: reproducibility, artifacts, deployment contracts, Linux operations, observability, failure diagnosis, controlled version changes, and rollback.

EdgePPE Lab solves that learning problem with one tiny real computer-vision use case: detect `Person`, `Hardhat`, and `NO-Hardhat` from images using a small YOLO model, then move that model through a production-minded lifecycle on Ubuntu Linux.

## First principles

A production ML system is a chain of contracts. Training creates an artifact. Deployment consumes a specific artifact. The runtime must expose which artifact it loaded. Monitoring must tell us whether the runtime is healthy. Versioning must make changes reversible. Linux provides the process, filesystem, permissions, networking, logs, and resource model underneath all of it.

## Learning objectives

By completing the project, the learner must be able to personally perform and explain:

1. Prepare a small labeled PPE dataset and record its version/identity.
2. Train a small YOLO detector and locate the generated checkpoint.
3. Record parameters, metrics, and artifacts in an MLflow run.
4. Register a deployable model as `edge-ppe-detector` version 1.
5. Export the selected checkpoint to ONNX.
6. Validate PyTorch/YOLO and ONNX outputs on the same images before deployment.
7. Start a real inference API and prove `/predict` returns real detections.
8. Inspect the Linux process, port, logs, environment, file permissions, CPU, RAM, and storage.
9. Run the API as a supervised Linux service when systemd is available.
10. Containerize and operate the same service through Docker.
11. Expose health, readiness, model identity, request/error/latency metrics.
12. Run a small CI pipeline that validates Python/model contracts and builds a versioned image.
13. Create model v2, deploy it, intentionally make it fail, diagnose evidence, and rollback to v1.
14. Explain where TensorRT, CUDA, NVIDIA GPU, Jetson, RTSP, and CCTV would fit later without pretending they are locally validated.

## Explicit non-goals

- No multi-camera fleet control plane.
- No Kubernetes.
- No distributed message bus.
- No UI frontend.
- No cloud architecture implementation.
- No requirement for NVIDIA hardware.
- No attempt to optimize the detector to production accuracy.
- No attempt to imitate a target employer's private design.

## Evidence-based learning rule

Every major concept must end with evidence. Examples: a run ID in MLflow, an ONNX parity report, a PID, a listening socket, a curl response, a model version in `/model-info`, a Prometheus metric, a Docker image tag, a journal entry, or a rollback verification response.
