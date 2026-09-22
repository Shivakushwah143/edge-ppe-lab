#!/usr/bin/env bash
# Installs the EdgePPE Lab systemd unit for the in-place deployment of this repository.
#
# The unit hardcodes absolute paths, so the paths in the unit and the tree that actually
# runs must be the same tree. This installer refuses to install a unit whose
# WorkingDirectory/ExecStart do not match the tree it was pointed at, which keeps
# "the service runs the code you are looking at" true instead of aspirational.
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo 'run with sudo' >&2
  exit 1
fi

SOURCE="${1:-$PWD}"
SOURCE="$(cd "$SOURCE" && pwd)"

UNIT_SRC="$SOURCE/deploy/systemd/edge-ppe.service"
UNIT_DST=/etc/systemd/system/edge-ppe.service
ENV_DIR=/etc/edge-ppe
ENV_FILE="$ENV_DIR/edge-ppe.env"

[[ -f "$UNIT_SRC" ]] || { echo "unit file not found: $UNIT_SRC" >&2; exit 1; }

WORKDIR="$(sed -n 's/^WorkingDirectory=//p' "$UNIT_SRC" | head -1)"
EXECSTART="$(sed -n 's/^ExecStart=//p' "$UNIT_SRC" | head -1)"
EXECBIN="${EXECSTART%% *}"

if [[ "$WORKDIR" != "$SOURCE" ]]; then
  echo "refusing to install: unit WorkingDirectory=$WORKDIR does not match $SOURCE" >&2
  echo "update deploy/systemd/edge-ppe.service for this deployment root, then rerun" >&2
  exit 1
fi
if [[ ! -x "$EXECBIN" ]]; then
  echo "refusing to install: ExecStart interpreter is not executable: $EXECBIN" >&2
  echo "create the project environment first: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

install -d -m 0755 "$ENV_DIR"
if [[ ! -f "$ENV_FILE" ]]; then
  sed "s#^EDGE_PPE_MODEL_CACHE=.*#EDGE_PPE_MODEL_CACHE=$WORKDIR/var/model-cache#" \
    "$SOURCE/deploy/systemd/edge-ppe.env.example" > "$ENV_FILE"
  chmod 0640 "$ENV_FILE"
fi
install -m 0644 "$UNIT_SRC" "$UNIT_DST"
systemctl daemon-reload

echo "installed $UNIT_DST"
echo "run as:  $(sed -n 's/^User=//p' "$UNIT_SRC" | head -1)"
echo "tree:    $WORKDIR"
echo "python:  $EXECBIN"
echo "env:     $ENV_FILE"
echo 'next:    sudo systemctl enable --now edge-ppe && systemctl status edge-ppe'
