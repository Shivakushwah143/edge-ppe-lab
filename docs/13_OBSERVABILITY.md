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

---

## Prometheus monitoring extension (local, verified)

> **Status:** additive observability extension, applied **after** the frozen v1
> release was verified. It does not change training, MLflow, the model registry,
> ONNX artifacts, deployment or rollback logic. The `/metrics` endpoint already
> existed; this section only adds a Prometheus server that scrapes it.

### What exists now

| Piece | Path | Notes |
|---|---|---|
| Scrape config | `monitoring/prometheus.yml` | one job, `edgeppe-api` |
| Start script | `scripts/start_prometheus.sh` | `prom/prometheus:v2.53.3`, matches `scripts/start_mlflow.sh` conventions |
| Evidence | `docs/evidence/prometheus_observability_verification.txt` | real transcript + query results |

Prometheus runs as its own container `edgeppe-prometheus`, published on
`127.0.0.1:9090`. The existing `edgeppe-api` container is left untouched.

### Scrape target and why

Target: `http://host.docker.internal:18000/metrics`, scrape interval 5s.

Prometheus runs *inside* a container while the API is also published on the
host, so `host.docker.internal` (the Docker/WSL gateway) is used rather than a
container DNS name — this needs no network changes to the running API.

### Verified queries

All values below were returned by the live Prometheus HTTP API and recorded in
the evidence file. None are illustrative.

| Metric / expression | Kind | Observed |
|---|---|---|
| `inference_requests_total` | counter | real requests counted |
| `inference_failures_total` | counter | present (0 failures) |
| `detections_total` | counter, by `class_name` | `Person`, `Hardhat` series |
| `model_info` | gauge | `version=1`, `alias=local-explicit`, `format=onnx`, `provider=CPUExecutionProvider`, `sha256=e22e6aeb…` |
| `rate(inference_requests_total[1m])` | request rate | non-zero after traffic |
| `rate(inference_latency_seconds_sum[5m]) / rate(inference_latency_seconds_count[5m])` | mean latency | non-zero |

`model_info` labels agree with the deployed champion (`v1`), so the monitoring
layer cannot silently disagree with the registry.

### How to run / stop

```bash
./scripts/start_prometheus.sh          # start (idempotent: replaces the container)
docker rm -f edgeppe-prometheus       # stop and remove
```

### Explicitly out of scope here

- No Grafana, no dashboards (raw PromQL via the API only).
- No Kubernetes, no service mesh, no new application architecture.
- No alerting rules and no long-term metric storage; the container uses
  Prometheus' default local TSDB and time-based retention.
