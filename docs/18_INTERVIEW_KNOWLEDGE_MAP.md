# 18 — Interview Knowledge Map

| Interview question | First-principles answer anchor | EdgePPE evidence |
|---|---|---|
| How do you deploy a model? | turn a validated training artifact into an immutable deployment artifact, load it in a controlled runtime, expose health/identity, observe it | checkpoint → ONNX → parity → FastAPI → Linux/Docker |
| How do you version models? | separate run identity, registered model version, artifact hash, and deployed runtime identity | MLflow v1/v2 + SHA-256 + `/model-info` |
| What is ONNX? | portable computation graph + I/O contract between training and inference runtimes | exported `model.onnx` and runtime session |
| Why use a model registry? | stable name, immutable versions, lineage, metadata, controlled aliases | `edge-ppe-detector` v1/v2 and `champion` |
| Why isn't export success enough? | conversion can change numerics/operators/shapes/pre/postprocessing | PT ↔ ONNX parity report |
| How do you debug a Linux inference service? | inspect process, port, config, files/permissions, logs, resources | `ps`, `ss`, `env`, `ls -l`, journal/logs, top/free/df |
| What happens if service crashes? | supervisor records exit and may restart; permanent startup faults remain until fixed | systemd crash exercise + journal |
| How do you rollback a model? | restore known-good immutable version, replace runtime, verify actual loaded version | alias `champion` → v1 + redeploy + `/model-info` |
| How do you monitor inference? | distinguish model quality from online SRE-style health | mAP/precision/recall vs latency/errors/availability/version |
| How does Docker help? | packages dependencies/config into an image and launches isolated processes | versioned image + container operations |
| Why does Docker not replace Linux? | containers share/consume host kernel primitives | port/process/resources/device debugging still Linux-based |
| How would this move to Jetson? | optimize validated ONNX toward TensorRT, benchmark FP16, package for ARM/NVIDIA runtime, preserve identity/monitoring | future path doc 20 |
| Where does TensorRT fit? | after ONNX validation as NVIDIA-specific inference optimization | ONNX → TensorRT → FP16 benchmark |
| How would you diagnose GPU problems? | separate host driver visibility, CUDA/runtime compatibility, device allocation, VRAM/utilization, app logs | future `nvidia-smi`/runtime checklist |
| How would CCTV/RTSP connect? | stream ingest/decode produces frames; detector consumes frames; tracking/rules are downstream | future CCTV → RTSP → decode → detector → tracker architecture |

## Strong explanation pattern

For any component answer five things:

1. **Problem:** what failure/need exists without it?
2. **Contract:** what input does it consume and output does it produce?
3. **Runtime:** where does it run?
4. **Evidence:** how do you verify it works?
5. **Failure:** how does it break and how do you diagnose it?

This pattern demonstrates systems understanding rather than memorized definitions.
