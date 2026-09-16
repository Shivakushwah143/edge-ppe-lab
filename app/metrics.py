from prometheus_client import Counter, Gauge, Histogram

INFERENCE_REQUESTS = Counter("inference_requests_total", "Total inference requests")
INFERENCE_FAILURES = Counter("inference_failures_total", "Failed inference requests")
INFERENCE_LATENCY = Histogram("inference_latency_seconds", "End-to-end inference request latency")
DETECTIONS_TOTAL = Counter("detections_total", "Detected objects", ["class_name"])
MODEL_INFO = Gauge(
    "model_info",
    "Loaded model identity",
    ["registered_model", "version", "alias", "format", "sha256", "provider"],
)
