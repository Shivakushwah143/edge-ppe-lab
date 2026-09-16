# 04 — User Stories

## Learning and training

- As a learner, I want to train a small real detector so that all later MLOps steps operate on a genuine model artifact.
- As a learner, I want the dataset identity and training configuration recorded so that I can explain reproducibility.
- As a learner, I want MLflow to show runs, parameters, metrics, and artifacts so that experiment tracking is concrete rather than theoretical.

## Registry and deployment

- As a learner, I want `edge-ppe-detector` to have v1 and v2 so that I can distinguish a registered model from a checkpoint file.
- As an operator, I want a `champion` alias so that the intended deployment target can move without deleting historical versions.
- As an operator, I want the running service to reveal its concrete model version so that I never confuse desired state with actual runtime state.

## ONNX

- As an MLOps engineer, I want to export a PyTorch/YOLO checkpoint to ONNX so that the serving runtime is decoupled from the training framework.
- As an MLOps engineer, I want parity validation before deployment so that a successful export is not mistaken for correct inference.

## Linux

- As an operator, I want to identify the service PID and listening port so that I can debug startup and port conflicts.
- As an operator, I want to inspect permissions and ownership on model files so that access failures are diagnosable.
- As an operator, I want to inspect CPU, RAM, and disk so that resource failures are observable.
- As an operator, I want systemd/journal evidence when the service crashes so that supervision behavior is understandable.

## Docker and observability

- As an operator, I want to build and run the same inference service in Docker so that image/container/runtime boundaries are clear.
- As an operator, I want request, failure, latency, model version, and health metrics so that I can separate model-quality problems from production-service problems.

## Version and rollback

- As a release owner, I want to deploy v2 and validate `/ready`, `/model-info`, prediction smoke tests, and metrics before accepting it.
- As a release owner, I want to intentionally break v2 and restore v1 so that rollback is a practiced operation rather than a diagram.
