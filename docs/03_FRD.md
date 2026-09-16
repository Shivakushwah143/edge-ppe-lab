# 03 — Functional Requirements Detail

## Component boundaries

### Training workflow
**Input:** labeled PPE dataset + training configuration.  
**Output:** checkpoint, training/evaluation metrics, run metadata.  
**Verification:** selected checkpoint exists and MLflow run references the same training session.

### Tracking and registry workflow
**Input:** run metadata + model/checkpoint artifacts.  
**Output:** MLflow run ID, registered model version, aliases/tags, lineage.  
**Verification:** registry UI/API can trace the registered version back to its run.

### Conversion workflow
**Input:** selected `best.pt`.  
**Output:** `model.onnx` + conversion metadata + parity report.  
**Verification:** test images produce acceptably equivalent class/confidence/box results.

### Serving workflow
**Input:** a resolved deployment target (`edge-ppe-detector@champion` resolves to concrete version N) and its validated ONNX artifact.  
**Output:** running HTTP process.  
**Verification:** health/readiness/model-info/predict/metrics endpoints behave as specified.

## Endpoint contracts

### `GET /health`
Purpose: prove the process is alive. It may remain healthy even if the model is not ready.  
Expected result: small JSON with application health status.

### `GET /ready`
Purpose: prove the service can accept inference traffic.  
Readiness requires model load success and runtime initialization.  
A missing/unreadable/invalid model must make readiness fail clearly.

### `GET /model-info`
Must expose at least:
- registered model name
- concrete model version
- deployment alias used at startup, if any
- artifact format (`onnx`)
- model content hash when practical
- loaded timestamp
- runtime/provider (`onnxruntime`, CPU provider locally)
- input shape/size when known

### `POST /predict`
Accepts an image upload. Validation must reject unsupported/empty payloads. Response detections should contain class identity, confidence, and bounding box coordinates in a documented coordinate system. It must report which concrete model version produced the result.

### `GET /metrics`
Prometheus text exposition. Required metrics are defined in `13_OBSERVABILITY.md`.

## Startup behavior

1. Read configuration from environment.
2. Resolve model deployment selection.
3. Resolve/copy/download the exact validated ONNX artifact.
4. Verify expected artifact identity/hash if configured.
5. Initialize ONNX Runtime session.
6. Run a startup/smoke validation if practical.
7. Mark readiness true only after successful model initialization.
8. Log model name/version/hash/provider exactly once at startup.

## Failure behavior

- Missing configuration: exit non-zero with actionable error.
- Registry unavailable during required startup resolution: fail clearly; do not silently use an unrelated model.
- Model file missing or unreadable: fail readiness/startup clearly.
- Bad ONNX graph/runtime incompatibility: fail startup and log root exception.
- Invalid request: 4xx, not 500.
- Inference runtime error: 5xx + failure metric increment.

## Deployment switching behavior

A deployment switch is controlled, not magical. Repointing `champion` changes the desired model selection, but a currently running process retains the model it already loaded. A restart/redeploy resolves the alias again, loads a concrete version, and reports it in `/model-info`. This makes runtime identity observable and rollback deterministic.
