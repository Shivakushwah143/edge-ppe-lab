# 07 — Domain and Model Contracts

## Detection domain

Primary classes are exactly:

1. `Person`
2. `Hardhat`
3. `NO-Hardhat`

The build phase must verify the actual dataset class IDs and create one canonical class mapping used by training, parity validation, and API postprocessing. Do not assume arbitrary numeric IDs.

## Dataset contract

Every dataset version should record:
- human-readable version, e.g. `ppe-dataset-v1`
- source/provenance note
- class names and IDs
- train/validation split definition
- image count per split and class where practical
- labeling format
- a manifest or content hash when practical

A dataset change capable of changing model behavior creates a new dataset version, even when source code is unchanged.

## Training contract

At minimum record:
- base model / checkpoint name
- image size
- epochs
- batch size
- learning configuration used by YOLO
- random seed where practical
- dataset version
- Git commit
- resulting selected checkpoint path
- validation metrics including precision, recall, and mAP reported by the training framework

## ONNX input contract

The build phase must discover and record the exported model's actual contract. Expected elements:
- input name
- dtype (normally floating point)
- tensor layout (`NCHW` if exported that way)
- image size, e.g. 640×640 if locked by export
- dynamic vs static batch/spatial dimensions
- normalization scale
- channel order
- letterbox/resize behavior

Do not write postprocessing from memory; verify the exact export output shape/semantics.

## Detection response contract

Each returned detection must include:
- `class_id`
- `class_name`
- `confidence`
- `bbox` with clearly documented order and coordinate system

The top-level response must also identify the concrete deployed model version.

## Parity contract

Compare PyTorch/YOLO and ONNX on a small fixed validation set. The release report must compare:
- detected classes
- confidence differences
- bounding-box overlap using IoU
- count of matched/unmatched detections

A practical starting tolerance for the lab may be defined during implementation (for example confidence delta and IoU thresholds), but it must be documented and justified after observing the actual export. The essential rule is fixed: **export success alone is never deployment approval**.



## Locked build-phase command surface

To make the zero-assumption journey executable, the later implementation must provide these command entry points (exact filenames may be implemented as thin wrappers around real modules, but these user-facing commands must work from the repository root):

```bash
python scripts/verify_dataset.py --config data/ppe.yaml
python scripts/train.py --config configs/train-v1.yaml
python scripts/register_model.py --release v1
python scripts/export_onnx.py --release v1
python scripts/validate_parity.py --release v1
python scripts/set_champion.py --version 1
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

For v2 the same lifecycle uses `configs/train-v2.yaml`, `--release v2`, and finally `python scripts/set_champion.py --version 2`. Each lifecycle command must persist enough release metadata under a versioned `var/releases/vN/` directory that the next command does not depend on copy-pasting opaque IDs from terminal output. The release metadata must include the MLflow run ID and, after registration, the concrete model version.

This command surface is a documentation contract, not application source code. The build phase may structure internals cleanly behind these entry points.

## Artifact identity contract

For every deployed ONNX artifact, record:
- registered model name
- MLflow model version
- producing run ID
- dataset version
- SHA-256 of the ONNX file when practical
- validation/parity status
- Docker image tag if containerized

This identity is what connects training history to a running process.
