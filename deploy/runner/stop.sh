#!/usr/bin/env bash
# Stops the background self-hosted runner. Registration is left intact, so
# start.sh can bring it back. Use remove.sh to unregister it from GitHub.
set -euo pipefail

RUNNER_DIR="${RUNNER_DIR:-$HOME/actions-runner-edgeppe}"
PIDFILE="$RUNNER_DIR/runner.pid"

if [[ ! -f "$PIDFILE" ]]; then
  echo "no pidfile at $PIDFILE - runner is not running (or was started elsewhere)"
  exit 0
fi

PID="$(cat "$PIDFILE")"
if kill -0 "$PID" 2>/dev/null; then
  # SIGTERM lets the runner finish and de-register its session cleanly.
  kill "$PID"
  for _ in $(seq 1 20); do
    kill -0 "$PID" 2>/dev/null || break
    sleep 1
  done
  if kill -0 "$PID" 2>/dev/null; then
    echo "runner did not exit; sending SIGKILL"
    kill -9 "$PID" 2>/dev/null || true
  fi
  echo "runner stopped (pid $PID)"
else
  echo "stale pidfile (process $PID is gone)"
fi
rm -f "$PIDFILE"
