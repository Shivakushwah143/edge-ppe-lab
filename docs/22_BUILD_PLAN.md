# 22 — Build Plan

## Build principle

Use vertical slices and prove each slice before adding the next. Do not scaffold every tool first.

## Phase 0 — repository and environment
Deliverables: Linux-first repo, dependency lock/requirements, configuration template, basic docs.  
Gate: clean install/import on WSL2 CPU.

## Phase 1 — data and real training
Deliverables: dataset validation, canonical class map, tiny training command, evaluation output.  
Gate: reproducible `best.pt` and recorded dataset/training identity.

## Phase 2 — MLflow tracking + registry
Deliverables: local server config, experiment logging, model registration, v1 metadata.  
Gate: UI/API shows run → registered model lineage.

## Phase 3 — ONNX export + parity
Deliverables: exporter, contract inspector, parity validator/report.  
Gate: ONNX loads on CPU and defined parity passes.

## Phase 4 — inference API
Deliverables: health/readiness/model-info/predict/metrics, real preprocessing/postprocessing.  
Gate: known image returns real predictions and correct model version.

## Phase 5 — Linux operations
Deliverables: runbook for process/port/env/logs/permissions/resources; failure drills.  
Gate: learner can diagnose wrong path, missing env, permission issue, port conflict.

## Phase 6 — systemd
Deliverables: service unit + env file pattern + journal runbook.  
Gate: supervised restart and intentional startup failure diagnosis where systemd is available.

## Phase 7 — Docker
Deliverables: compact Docker image + runtime command.  
Gate: container serves identical API and can be diagnosed after forced failure.

## Phase 8 — CI
Deliverables: GitHub Actions validation + Docker candidate build.  
Gate: failing tests/contract validation block candidate; successful run emits immutable image identity.

## Phase 9 — v2 + rollback drill
Deliverables: second MLflow model version, successful deployment, deliberate failure, rollback report.  
Gate: final runtime proves version 1 restored.

## Phase 10 — evidence and packaging
Deliverables: `START_HERE.md`, implementation report, verification report, known limitations, screenshots/evidence references, runnable ZIP.  
Gate: all `21_ACCEPTANCE_CRITERIA.md` P0 checks complete or explicitly marked blocked with evidence.

## Complexity guardrail

If implementation begins introducing Kubernetes, queues, fleet managers, a React frontend, multiple independent backend services, or an unrelated RAG/agent layer, stop: the build has drifted away from EdgePPE Lab.
