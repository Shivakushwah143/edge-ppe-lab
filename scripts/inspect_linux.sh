#!/usr/bin/env bash
set -euo pipefail
PORT="${1:-8000}"
echo '== working directory =='; pwd
echo '== repository files =='; ls -lah | head -30
echo '== model/release files =='; find var/releases -maxdepth 2 -type f -print 2>/dev/null || true
echo '== uvicorn process =='; ps -ef | grep '[u]vicorn' || true
echo "== port ${PORT} =="; ss -lntp 2>/dev/null | grep ":${PORT} " || true
echo '== EdgePPE environment =='; env | grep -E '^(EDGE_PPE|MLFLOW)_' | sed 's/=.*$/=<set>/' || true
echo '== memory =='; free -h
echo '== disk =='; df -h .; du -sh var 2>/dev/null || true
