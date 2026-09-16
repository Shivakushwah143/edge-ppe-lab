# 05 — Architecture

## Architecture principle

EdgePPE Lab has one training path and one inference service. MLflow provides tracking/registry; ONNX is the deployment representation; Linux is the runtime substrate. Docker is an alternative packaging/runtime layer after the manual Linux path is understood.

## 1. Development and training

```mermaid
flowchart LR
  D[Small PPE Dataset] --> T[Ultralytics YOLO / PyTorch Training]
  T --> C[best.pt checkpoint]
  T --> M[MLflow Run: params metrics artifacts]
  C --> M
  M --> R[MLflow Model Registry\nedge-ppe-detector v1/v2]
  C --> O[ONNX Export]
  O --> P[PT vs ONNX Parity Validation]
  P -->|pass| A[Validated Deployment Artifact]
  A --> F[FastAPI + ONNX Runtime]
```

## 2. Linux runtime

```mermaid
flowchart LR
  U[Ubuntu / WSL2] --> P[Linux Process or systemd Service]
  P --> F[FastAPI / Uvicorn]
  F --> ORT[ONNX Runtime CPU]
  ORT --> O[Validated model.onnx]
  F --> E[HTTP Endpoints]
  F --> L[stdout/journal logs]
  F --> X[Prometheus metrics]
```

## 3. Docker runtime

```mermaid
flowchart LR
  L[Linux Kernel / WSL2 Integration] --> D[Docker Engine]
  D --> I[Versioned EdgePPE Image]
  I --> C[Inference Container]
  C --> F[FastAPI + ONNX Runtime]
  C --> M[Mounted or baked validated model artifact]
```

Docker packages user space; it does not replace the Linux kernel, Linux networking, filesystems, process concepts, or host resource constraints.

## 4. Version lifecycle

```mermaid
stateDiagram-v2
  [*] --> V1: register + validate
  V1 --> ProdV1: champion -> v1 / deploy
  ProdV1 --> V2: train + register v2
  V2 --> ProdV2: parity + smoke pass / champion -> v2 / redeploy
  ProdV2 --> Failure: intentional bad v2 scenario
  Failure --> ProdV1: champion -> v1 / redeploy / verify
```

## 5. Future production extension — illustrative, not employer-specific

```mermaid
flowchart LR
  CCTV[CCTV Cameras] --> RTSP[RTSP Streams]
  RTSP --> DEC[Decode: CPU/NVDEC depending platform]
  DEC --> DET[YOLO or RT-DETR Detector]
  DET --> TRK[Tracking e.g. ByteTrack]
  TRK --> OPT[ONNX / TensorRT Engine]
  OPT --> EDGE[Jetson or Linux GPU Edge Node]
  EDGE --> MON[Logs Metrics Model Identity]
```

This final diagram only shows a **publicly common production pattern**. It is not a claim about any company's private architecture.

## Artifact flow

| Artifact | Created by | Consumed by | Why it exists |
|---|---|---|---|
| Dataset version | data preparation | training | reproducible training input |
| `best.pt` | YOLO training | evaluation/export | selected training checkpoint |
| MLflow run | training workflow | registry/audit | params, metrics, lineage, artifacts |
| Registered version | MLflow Registry | release workflow | immutable model identity |
| `model.onnx` | export step | parity + serving | portable deployment graph |
| Parity report | validation | release gate | conversion evidence |
| Docker image | CI/local build | Docker runtime | versioned application package |
| Running process | Linux/systemd/Docker | HTTP client | actual inference runtime |
