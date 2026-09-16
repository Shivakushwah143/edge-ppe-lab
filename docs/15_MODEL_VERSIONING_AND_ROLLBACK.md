# 15 — Model Versioning and Rollback

## Versions are not interchangeable

| Version type | Example | What it identifies |
|---|---|---|
| Git version | commit SHA | source/config revision |
| Dataset version | `ppe-dataset-v1` | training data identity |
| MLflow run | run ID | one experiment execution |
| Model version | `edge-ppe-detector` v1 | registry identity |
| ONNX artifact | SHA-256 | exact deployment file |
| Docker image version | image tag/digest | application package |
| Deployed version | `/model-info` evidence | what the running process actually loaded |

## v1 release

1. Train and evaluate dataset/model v1.
2. Register model version 1.
3. Export + parity validate ONNX.
4. Tag validation status as passed.
5. Point `champion` to v1.
6. Start/redeploy service.
7. Verify `/model-info` is version 1.
8. Verify ready/predict/metrics.

## v2 release

Repeat the full lifecycle. A new registry version is not automatically production. Only after parity and smoke validation does the release owner move `champion` to v2 and redeploy.

## Intentional bad-v2 exercise

Use a safe, deterministic failure such as a wrong model path, corrupted/invalid deployment artifact copy, or deliberately incompatible startup configuration. The objective is to create an observable deployment failure, not to destroy registry history.

Expected evidence:
- v2 release attempted
- `/ready` fails or service fails startup
- logs identify the concrete reason
- process/systemd/container state corroborates it
- no ambiguous “maybe v1 is still running” state

## Rollback

1. Point `champion` back to v1.
2. Redeploy/restart using the same documented mechanism.
3. Verify `/model-info` reports v1.
4. Verify `/ready` and prediction.
5. Verify error/latency metrics normalize.
6. Record incident timeline/root cause.

## Why keep v2

Do not delete failed v2. Immutable history supports diagnosis and interview discussion: what changed, what failed, what evidence triggered rollback, and how recovery was verified.
