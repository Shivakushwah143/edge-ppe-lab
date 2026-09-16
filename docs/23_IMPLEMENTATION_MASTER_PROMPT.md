# 23 — Implementation Master Prompt

Use the following prompt in the next build conversation.

---

**CONTINUATION / BUILD MODE — EDGE PPE LAB**

Treat the attached `edge-ppe-lab-documentation.zip` as the complete source of truth.

Your task is to **build the full working EdgePPE Lab project end-to-end**, not redesign it.

Read `README.md` and every file under `docs/` before implementation. Preserve the locked architecture, scope, terminology, model lifecycle, API contracts, Linux-first workflow, MLflow registry convention, ONNX parity gate, observability requirements, versioning semantics, and acceptance criteria.

Priority rule if documents appear ambiguous:

`06_LOCKED_TECH_STACK.md` → `07_DOMAIN_AND_MODEL_CONTRACTS.md` → `21_ACCEPTANCE_CRITERIA.md` → numbered documents in order.

Build only the intentionally small project:

`dataset → YOLO/PyTorch training → MLflow Tracking → MLflow Model Registry → edge-ppe-detector v1 → ONNX export → PT↔ONNX parity validation → FastAPI/ONNX Runtime → Linux operation → systemd where supported → Docker → Prometheus metrics → simple GitHub Actions CI → train/register/deploy v2 → deliberate failure → rollback v1`

Constraints:
- Windows host, WSL2 Ubuntu is the primary environment.
- Python 3.11+.
- CPU path must work without NVIDIA hardware.
- Primary classes: Person, Hardhat, NO-Hardhat; verify canonical IDs from the actual dataset.
- Use a small Ultralytics YOLO model.
- Use MLflow practically for runs, artifacts, registry lineage, versions, tags, and `champion` alias.
- Use current MLflow APIs; do not center the implementation on obsolete stage-based promotion.
- Resolve alias to a concrete version on service startup and expose the concrete loaded version.
- Never deploy ONNX only because export succeeded; parity validation is mandatory.
- `/predict` must run real inference; no fake detections.
- Required endpoints: `/health`, `/ready`, `/model-info`, `/predict`, `/metrics`.
- Keep model quality metrics separate from production/runtime metrics.
- Do not add Kubernetes, Kafka, Redis, React, RAG, agents, microservice sprawl, or complex cloud infrastructure.
- TensorRT/CUDA/NVIDIA/Jetson are future-path documentation only unless the current machine actually supports them.

Execution requirements:
1. Inspect the machine/environment first.
2. Create the repository and implementation according to the docs.
3. Install dependencies instead of stopping at generated files.
4. Run each vertical slice.
5. Execute real training on a deliberately small dataset/config practical for the available CPU.
6. Start and inspect MLflow; create and verify v1 registry lineage.
7. Export ONNX and generate a real parity report.
8. Run the FastAPI service and exercise all endpoints with real input.
9. Demonstrate Linux process, port, env, permissions, logs, CPU/RAM/storage diagnostics.
10. Exercise systemd only if supported/enabled; otherwise document the exact limitation without faking success.
11. Build/run/inspect the Docker container.
12. Exercise metrics with real requests.
13. Implement the small GitHub Actions CI workflow.
14. Create/register v2, deploy it, verify it, then execute a safe intentional failure scenario.
15. Diagnose the failure with evidence and rollback to v1.
16. Prove final `/model-info` shows v1 and real prediction works.
17. Fix any failures encountered and rerun verification.
18. Do not leave P0 core behavior as TODO, fake, mocked, or placeholder.

Create these build-phase evidence documents:
- `START_HERE.md`
- `docs/IMPLEMENTATION_REPORT.md`
- `docs/VERIFICATION_REPORT.md`
- `docs/KNOWN_LIMITATIONS.md`
- `docs/REQUIREMENTS_TRACEABILITY.md`
- `docs/FAILURE_VERIFICATION.md`

The verification report must include commands and decisive outputs/evidence for all P0 acceptance criteria. Clearly label anything blocked by actual hardware/environment constraints.

Before final delivery:
- run the project from a clean documented path
- rerun key tests/checks
- verify model v1/v2 registry lineage
- verify ONNX parity
- verify all API endpoints
- verify Linux diagnostics
- verify Docker runtime
- verify v2 failure and v1 rollback
- inspect generated files for consistency
- remove accidental secrets, caches, unnecessary large artifacts where appropriate
- preserve only necessary reproducible assets/instructions

Finally package the complete runnable project as:

`edge-ppe-lab.zip`

Return the ZIP plus a concise verification summary, exact commands to start from WSL2 Ubuntu, known limitations, and the evidence that final rollback restored v1.

Do not stop at scaffolding. Do not merely describe commands. Build, run, test, observe, fix, retest, and package the working project.

---
