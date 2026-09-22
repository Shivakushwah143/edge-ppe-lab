#!/usr/bin/env bash
# Unregisters the self-hosted runner from GitHub and deletes its directory.
#
# The runner registration can also be removed from the GitHub UI:
#   Settings -> Actions -> Runners -> <runner> -> Remove
set -euo pipefail

RUNNER_DIR="${RUNNER_DIR:-$HOME/actions-runner-edgeppe}"
REPO_SLUG="${REPO_SLUG:-Shivakushwah143/edge-ppe-lab}"

# Stop it first so the job listener is not killed mid-registration.
"$(dirname "$0")/stop.sh" || true

[[ -d "$RUNNER_DIR" ]] || { echo "nothing to remove: $RUNNER_DIR does not exist"; exit 0; }

TOKEN="${RUNNER_TOKEN:-}"
if [[ -z "$TOKEN" && -n "${GH_TOKEN:-}" ]]; then
  TOKEN="$(curl -fsS -X POST \
    -H "Authorization: Bearer ${GH_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/${REPO_SLUG}/actions/runners/remove-token" \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')"
fi

cd "$RUNNER_DIR"
if [[ -n "$TOKEN" ]]; then
  ./config.sh remove --token "$TOKEN" || echo "config.sh remove failed; remove it from the GitHub UI instead" >&2
else
  echo "no GH_TOKEN/RUNNER_TOKEN provided: skipping unregister, deleting local files only" >&2
  echo "remove the offline runner from Settings -> Actions -> Runners" >&2
fi

cd "$HOME"
rm -rf "$RUNNER_DIR"
echo "removed $RUNNER_DIR"
