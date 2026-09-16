# 09 — ONNX Deployment Design

## Why ONNX exists here

PyTorch/YOLO is excellent for training, but deployment benefits from a portable computation-graph representation with a runtime optimized for inference. ONNX acts as the contract between training and serving in this lab.

`best.pt → export → model.onnx → parity validation → ONNX Runtime service`

## Computation graph

An ONNX file contains a graph of operators, tensors, constants/weights, and input/output definitions. It is not merely a renamed PyTorch checkpoint. Conversion can alter graph structure, operator implementations, numerical behavior, and shape assumptions.

## Shapes

A static export fixes dimensions such as batch and spatial size. A dynamic export permits selected dimensions to vary. For this lab, prefer the simplest shape policy that matches the service. A static 640×640 input is acceptable if preprocessing always letterboxes/resizes accordingly; dynamic shapes are only useful if the service actually needs them.

## Opset

The ONNX opset defines versions of operator specifications. Choose an opset supported by both exporter and installed ONNX Runtime. Record it in deployment metadata so runtime incompatibility can be diagnosed.

## Preprocessing consistency

Parity requires the **same effective preprocessing**:
- image decode
- color channel order
- resize/letterbox
- dtype conversion
- normalization
- tensor layout

Different preprocessing can create apparent “model parity” failures even when the graph is correct.

## Postprocessing consistency

The validation implementation must understand the exported model's actual output and consistently apply confidence filtering, class mapping, coordinate transforms, and NMS if NMS is not already embedded in export.

## Mandatory parity flow

1. Select fixed validation images containing positive and negative PPE examples.
2. Run inference through the source YOLO/PyTorch path.
3. Run the same images through ONNX Runtime.
4. Match detections by class and spatial overlap.
5. Compare confidence delta and IoU.
6. Record mismatches.
7. Fail the release gate when tolerance is exceeded.

## Deployment gate

A valid ONNX file must satisfy all of the following before serving:
- loads in ONNX Runtime
- expected input/output contract is observed
- fixed test images run without runtime error
- parity thresholds pass
- artifact hash recorded
- model version/run lineage recorded

## Future TensorRT position

TensorRT is a later optimization step after ONNX correctness. The conceptual path is:

`PyTorch → ONNX → TensorRT engine → FP16 benchmark → NVIDIA GPU/Jetson`

Optimization never removes the need for parity and benchmark validation.
