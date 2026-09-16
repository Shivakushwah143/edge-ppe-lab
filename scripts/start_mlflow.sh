#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p var/mlflow/artifacts
exec mlflow server \
  --backend-store-uri sqlite:///var/mlflow/mlflow.db \
  --artifacts-destination "$(pwd)/var/mlflow/artifacts" \
  --host 127.0.0.1 \
  --port 5000
