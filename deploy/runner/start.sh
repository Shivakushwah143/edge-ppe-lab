#!/usr/bin/env bash
# Starts the already-registered self-hosted runner in the background.
#
# The runner is intentionally started as a plain background process owned by the
# normal user rather than a root systemd service: the deployment job writes into
# ~/projects/edge-ppe-lab, and a root service would create root-owned files there.
set -euo pipefail

RUNNER_DIR="${RUNNER_DIR:-$HOME/actions-runner-edgeppe}"
PIDFILE="$RUNNER_DIR/runner.pid"
LOGFILE="$RUNNER_DIR/runner.log"

[[ -f "$RUNNER_DIR/.runner" ]] || { echo "no runner configured in $RUNNER_DIR (run install.sh)" >&2; exit 1; }

if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  echo "runner already running (pid $(cat "$PIDFILE"))"
  exit 0
fi

cd "$RUNNER_DIR"
nohup ./run.sh >>"$LOGFILE" 2>&1 &
echo $! > "$PIDFILE"
sleep 5

if kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  echo "runner started (pid $(cat "$PIDFILE")), log: $LOGFILE"
  grep -E "Listening for Jobs|Connected to GitHub" "$LOGFILE" | tail -3 || true
else
  echo "runner failed to start; last log lines:" >&2
  tail -20 "$LOGFILE" >&2
  exit 1
fi
