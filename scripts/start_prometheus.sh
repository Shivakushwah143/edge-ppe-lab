#!/usr/bin/env bash
# Start the minimal local Prometheus that scrapes the running EdgePPE API.
#
# Observability extension only: this does not touch the application, the model
# registry, ONNX artifacts, the systemd unit or the existing API container.
set -euo pipefail
cd "$(dirname "$0")/.."

PROM_IMAGE="${PROM_IMAGE:-prom/prometheus:v2.53.3}"
PROM_NAME="${PROM_NAME:-edgeppe-prometheus}"
PROM_PORT="${PROM_PORT:-9090}"

if docker ps -a --format '{{.Names}}' | grep -qx "$PROM_NAME"; then
  echo "container '$PROM_NAME' already exists; recreating it"
  docker rm -f "$PROM_NAME" >/dev/null
fi

# Bound TSDB growth: this is a local lab, not a production monitoring stack.
docker run -d \
  --name "$PROM_NAME" \
  --restart unless-stopped \
  --add-host=host.docker.internal:host-gateway \
  -p "127.0.0.1:${PROM_PORT}:9090" \
  -v "$(pwd)/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro" \
  "$PROM_IMAGE" \
  --config.file=/etc/prometheus/prometheus.yml \
  --storage.tsdb.path=/prometheus \
  --storage.tsdb.retention.time=24h

echo "Prometheus starting on http://localhost:${PROM_PORT}"
