FROM python:3.11-slim AS runtime

ARG GIT_SHA=unknown
LABEL org.opencontainers.image.title="EdgePPE Lab" \
      org.opencontainers.image.description="CPU ONNX PPE inference service" \
      org.opencontainers.image.revision="$GIT_SHA"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-runtime.txt .
RUN pip install --no-cache-dir -r requirements-runtime.txt
COPY app ./app

RUN useradd --create-home --uid 10001 edgeppe \
    && mkdir -p /app/var/model-cache \
    && chown -R edgeppe:edgeppe /app
USER edgeppe

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/ready || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
