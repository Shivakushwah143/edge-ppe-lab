# 08 — MLflow and Model Registry

## First principles

Training creates many attempts. MLflow Tracking answers **what happened in each attempt?** Model Registry answers **which model objects are named, versioned, and eligible for deployment?** They solve different problems.

## Core terms

| Term | EdgePPE meaning |
|---|---|
| Experiment | logical group of PPE training runs |
| Run | one execution with its own params, metrics, tags, artifacts |
| Checkpoint | training-produced file such as `best.pt` |
| Artifact | file/directory attached to a run: checkpoint, plots, manifest, parity report, ONNX, etc. |
| Logged MLflow model | model packaged with MLflow model metadata/flavor so it can be registered/loaded through MLflow APIs |
| Registered model | stable registry name: `edge-ppe-detector` |
| Model version | immutable numbered registry entry, e.g. 1 or 2 |
| Alias | mutable name pointing to one model version, e.g. `champion` |
| Deployment artifact | validated ONNX file selected for runtime |

## What gets stored

### Tracking backend
Stores run metadata such as experiment/run identity, parameters, metrics, tags, status, timestamps, and registry metadata in the configured backend database.

### Artifact store
Stores files produced by a run. For this lab these can include:
- dataset manifest/reference metadata
- training plots
- `best.pt`
- evaluation summaries
- exported `model.onnx`
- parity report
- deployment metadata/hash record

### Model Registry
Adds a durable model name, immutable versions, lineage to the producing logged model/run, tags/descriptions, and deployment-oriented aliases.

## Local server choice

Use one local MLflow server with SQLite as the backend database and a local artifacts directory. This is intentionally a single-user lab design. It is not presented as the production choice for multi-user/high-availability environments.

## Deployment convention

Registered model: `edge-ppe-detector`  
Alias: `champion`

Illustrative identities:
- `models:/edge-ppe-detector/1` — immutable v1
- `models:/edge-ppe-detector/2` — immutable v2
- `models:/edge-ppe-detector@champion` — mutable release pointer

The service should resolve the alias to a **concrete version at startup** and expose that concrete version. It should not periodically change its loaded model merely because the alias moved.

## v1 → v2 flow

1. Train candidate v2 in a new MLflow run.
2. Log evaluation and conversion artifacts.
3. Register new version under the same model name.
4. Mark validation status with model-version tags.
5. Run parity and smoke checks.
6. Only after acceptance, point `champion` to v2.
7. Restart/redeploy the service.
8. Verify `/model-info` says concrete version 2.
9. Verify `/ready`, prediction smoke test, logs, and latency/error metrics.

## Rollback v2 → v1

1. Repoint `champion` to version 1.
2. Restart/redeploy.
3. Verify `/model-info` says version 1.
4. Verify readiness and real prediction.
5. Record incident evidence and keep v2 preserved for investigation rather than deleting it.

## Registry failure behavior

If startup is configured to resolve from MLflow and MLflow is unavailable, fail clearly unless the implementation has an explicitly configured, identity-verified local deployment artifact. Do not silently select “latest” or an arbitrary checkpoint.

## Why not “latest”

Newest is not equivalent to approved. A deterministic deployment should target a concrete version or a controlled alias whose movement is itself part of the release process.
