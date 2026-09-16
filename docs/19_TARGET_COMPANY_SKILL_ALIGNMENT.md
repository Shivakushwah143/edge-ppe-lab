# 19 — Target-Company Skill Alignment

This document maps **publicly relevant Computer Vision / MLOps skills** to **our project implementation** and **future extensions**. It does not claim knowledge of any target company's private architecture.

| Publicly relevant skill | Our project implementation | Future extension |
|---|---|---|
| Python | training, parity, API, tooling | production packaging/optimization tools |
| PyTorch | YOLO training/checkpoint | custom training or optimization |
| YOLO / real-time CV | small PPE detector | larger detector/RT-DETR comparisons |
| ONNX | validated deployment format | hardware-specific optimization input |
| TensorRT concepts | architecture/interview path only | build engine + FP16 benchmark on NVIDIA |
| GPU inference | concepts only on CPU machine | CUDA/TensorRT execution on Linux GPU/Jetson |
| Docker | inference image/container operations | GPU container runtime + registry deployment |
| Linux | filesystem, process, port, env, perms, logs, systemd, resources | remote Linux GPU/edge host operations |
| CI/CD | GitHub Actions validation + image candidate | push to OCI registry and controlled remote rollout |
| Model deployment | FastAPI + ONNX Runtime | edge service integration |
| Experiment tracking | MLflow runs/metrics/artifacts | centralized remote tracking |
| Model registry | versions, tags, alias, lineage | governed registry/environment separation |
| Monitoring | service metrics + model identity | Prometheus server/Grafana/alerts/drift |
| Versioning/rollback | v1/v2 + bad release + rollback | canary/fleet rollout |
| Jetson/edge | documented future architecture | ARM64 image + TensorRT engine + device telemetry |
| CCTV/RTSP | architectural awareness | actual RTSP ingest/decode/stream resilience |

## What this project deliberately proves

It proves familiarity with the lifecycle and operational mechanics around a CV model: reproducibility, registry lineage, conversion, validation, serving, Linux operation, observability, version change, and rollback.

## What it does not prove by itself

It does not prove high-scale multi-camera throughput, production TensorRT tuning, GPU kernel optimization, Jetson fleet operations, or employer-specific deployment infrastructure. Those must be described as future extensions until actually implemented and measured.

## Interview bridge examples

- “I have not just trained YOLO; I can trace a deployed ONNX artifact to its MLflow run and model version.”
- “I validate PyTorch-to-ONNX parity before serving it.”
- “I can identify which PID owns the inference port and diagnose model-file permission failures on Linux.”
- “I practiced a bad-v2 rollback and verified the actual runtime returned to v1 through `/model-info`.”

These are claims the learner should make only after collecting the corresponding evidence.
