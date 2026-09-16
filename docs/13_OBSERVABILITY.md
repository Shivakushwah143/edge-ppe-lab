# 13 — Observability

## Two different kinds of metrics

### ML quality metrics
Measured primarily during validation/evaluation:
- precision
- recall
- mAP
- class-specific errors

These answer: **How good is the model on a labeled evaluation dataset?**

### Production service metrics
Measured while serving:
- request rate
- failures
- latency
- throughput
- CPU/RAM context
- service availability/readiness
- loaded model version

These answer: **Is the deployed service operating correctly now?**

High mAP does not guarantee low latency. Low error rate does not guarantee good detection accuracy.

## Required application metrics

Suggested Prometheus names:
- `inference_requests_total`
- `inference_failures_total`
- `inference_latency_seconds` histogram
- `detections_total` (optional but useful)
- `model_info{model_name="...",model_version="...",artifact_format="onnx",...} 1`

Avoid creating an unbounded label such as request ID or filename in metrics. Model version is bounded and useful.

## Health vs readiness

`/health`: process is alive.  
`/ready`: model/runtime is loaded and traffic can be served.

A process can be healthy but not ready while startup/model loading is incomplete or failed.

## Minimum release dashboard mindset

For v1 and v2, inspect:
- readiness
- request/error counts
- p50/p95 latency computed from histogram data or test measurements
- concrete model version
- process/container resource usage

## Logs

Startup log must include:
- application start
- model source selection
- concrete model version
- ONNX hash when available
- ONNX Runtime execution provider
- successful readiness transition

Error logs must include enough context to identify failing operation without leaking secrets.

## Model drift is out of scope for v1

This lab focuses on runtime monitoring and model lifecycle. Full production drift detection requires representative data, feedback/ground truth, and domain-specific thresholds. It is a future topic, not a fake metric in this project.
