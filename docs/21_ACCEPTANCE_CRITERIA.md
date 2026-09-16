# 21 — Acceptance Criteria

The build is complete only when every P0 criterion below has evidence.

## P0 — environment
- [ ] Project runs primarily from WSL2 Ubuntu Linux filesystem.
- [ ] Python 3.11+ environment is reproducibly installable.
- [ ] No required NVIDIA hardware.

## P0 — real model
- [ ] Dataset has canonical 3-class mapping.
- [ ] YOLO training produces a real checkpoint.
- [ ] Evaluation produces real metrics.
- [ ] No fake detections anywhere in `/predict`.

## P0 — MLflow
- [ ] Tracking server is reachable.
- [ ] Run records params, metrics, artifacts, dataset/model metadata.
- [ ] `edge-ppe-detector` exists in registry.
- [ ] v1 and v2 are distinct model versions with lineage.
- [ ] `champion` alias can point to v1 or v2.

## P0 — ONNX
- [ ] Selected checkpoint exports successfully.
- [ ] ONNX Runtime loads artifact on CPU.
- [ ] input/output contract recorded.
- [ ] PT ↔ ONNX parity report exists and passes defined tolerance before release.
- [ ] ONNX SHA-256 recorded.

## P0 — API
- [ ] `/health` works.
- [ ] `/ready` reflects model readiness.
- [ ] `/model-info` exposes concrete model version, artifact format, hash if practical, load time, provider.
- [ ] `/predict` returns real detections for real image input.
- [ ] `/metrics` exposes required metrics.

## P0 — Linux operations
- [ ] learner demonstrates process inspection.
- [ ] learner demonstrates port inspection.
- [ ] learner demonstrates env inspection.
- [ ] learner demonstrates file permissions/ownership diagnosis.
- [ ] learner demonstrates CPU/RAM/disk inspection.
- [ ] logs are inspectable.

## P0 — systemd
- [ ] if supported/enabled in WSL, service can start/status/restart/stop.
- [ ] journal logs show service startup and failure evidence.
- [ ] if systemd cannot be enabled, limitation is documented rather than faked.

## P0 — Docker
- [ ] image builds with immutable tag.
- [ ] container runs and serves real inference.
- [ ] logs/inspect/stats are exercised.
- [ ] exited-container failure is diagnosed at least once.

## P0 — release and rollback
- [ ] v1 deployed and `/model-info` proves v1.
- [ ] v2 trained/registered/exported/parity-validated.
- [ ] v2 deployed and `/model-info` proves v2 before the failure drill.
- [ ] deliberate v2 failure produces clear evidence.
- [ ] rollback repoints/redeploys v1.
- [ ] final `/model-info` proves v1.
- [ ] final readiness + prediction prove recovery.

## P1 — CI
- [ ] GitHub Actions validates code/tests.
- [ ] model contract check runs when artifact is available.
- [ ] Docker image candidate builds.
- [ ] candidate identity includes immutable source/image identity.

## Documentation acceptance
- [ ] START_HERE.md created in build phase.
- [ ] implementation report created.
- [ ] verification report includes commands/evidence.
- [ ] known limitations are explicit.
- [ ] final runnable ZIP contains no hidden requirement on paid/cloud services.
