FROM python:3.11-slim AS runtime

ARG GIT_SHA=unknown
LABEL org.opencontainers.image.title="EdgePPE Lab" \
      org.opencontainers.image.description="CPU ONNX PPE inference service" \
      org.opencontainers.image.revision="$GIT_SHA"

# This image is CPU-only by design: no torch, no CUDA, no NVIDIA runtime.
# Inference is onnxruntime CPUExecutionProvider (see app/model_runtime.py).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=180 \
    PIP_RETRIES=10 \
    PIP_CACHE_DIR=/root/.cache/pip \
    EDGE_PPE_MODEL_CACHE=/app/var/model-cache

WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-runtime.txt .
# Large wheels (opencv-python-headless ~62 MB, onnxruntime ~24 MB) over a slow
# link can exceed pip's default socket timeout and abort the whole build, so
# retry the whole resolve a few times instead of failing on one transient read.
# The pip cache is a BuildKit cache mount, so it survives an aborted build and
# keeps the wheels out of the image layers (same intent as --no-cache-dir).
RUN --mount=type=cache,target=/root/.cache/pip \
    set -eu; \
    for attempt in 1 2 3; do \
        if pip install --retries 10 --timeout 180 -r requirements-runtime.txt; then \
            exit 0; \
        fi; \
        echo "pip install attempt ${attempt} failed; retrying in 10s"; \
        sleep 10; \
    done; \
    echo "pip install failed after 3 attempts"; \
    exit 1
COPY app ./app

RUN useradd --create-home --uid 10001 edgeppe \
    && mkdir -p /app/var/model-cache \
    && chown -R edgeppe:edgeppe /app
USER edgeppe

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/ready || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
