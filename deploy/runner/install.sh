#!/usr/bin/env bash
# Installs and registers the GitHub Actions self-hosted runner that executes the
# EdgePPE deployment job (see .github/workflows/cd.yml).
#
# This runner is deliberately NOT installed as root and NOT registered with any
# long-lived secret:
#   * it runs as the normal desktop user, so deployment artefacts in
#     ~/projects/edge-ppe-lab stay owned by that user;
#   * registration uses a short-lived runner registration token obtained from the
#     GitHub API at install time. The token is passed to config.sh and is never
#     written to a file in the repository.
#
# Usage:
#   GH_TOKEN=<classic PAT with repo scope> ./deploy/runner/install.sh
#
#   # or, if you would rather copy the token from
#   # Settings -> Actions -> Runners -> New self-hosted runner yourself:
#   RUNNER_TOKEN=<token> ./deploy/runner/install.sh
set -euo pipefail

RUNNER_VERSION="${RUNNER_VERSION:-latest}"
RUNNER_NAME="${RUNNER_NAME:-$(hostname)-edgeppe}"
RUNNER_DIR="${RUNNER_DIR:-$HOME/actions-runner-edgeppe}"
REPO_SLUG="${REPO_SLUG:-Shivakushwah143/edge-ppe-lab}"
REPO_URL="${REPO_URL:-https://github.com/${REPO_SLUG}}"
CUSTOM_LABELS="${CUSTOM_LABELS:-edgeppe-deploy}"

if [[ -f "$RUNNER_DIR/.runner" ]]; then
  echo "a runner is already configured in $RUNNER_DIR"
  echo "to re-register: ./deploy/runner/remove.sh && ./deploy/runner/install.sh"
  exit 1
fi

# ---------------------------------------------------------------- token ------
TOKEN="${RUNNER_TOKEN:-}"
if [[ -z "$TOKEN" ]]; then
  : "${GH_TOKEN:?set GH_TOKEN (repo-scoped PAT) or RUNNER_TOKEN (from the GitHub UI)}"
  echo "requesting a runner registration token for ${REPO_SLUG} via the API"
  TOKEN="$(curl -fsS -X POST \
    -H "Authorization: Bearer ${GH_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/${REPO_SLUG}/actions/runners/registration-token" \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')"
fi
[[ -n "$TOKEN" ]] || { echo "could not obtain a registration token" >&2; exit 1; }

# --------------------------------------------------------------- download ----
if [[ "$RUNNER_VERSION" == "latest" ]]; then
  RUNNER_VERSION="$(curl -fsSL https://api.github.com/repos/actions/runner/releases/latest \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["tag_name"].lstrip("v"))')"
fi
TARBALL="actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz"
URL="https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/${TARBALL}"

mkdir -p "$RUNNER_DIR"
cd "$RUNNER_DIR"
if [[ ! -f "$TARBALL" ]]; then
  echo "downloading $URL"
  curl -fsSL -o "$TARBALL" "$URL"
fi
tar xzf "$TARBALL"
echo "runner ${RUNNER_VERSION} unpacked into $RUNNER_DIR"

# The runner is a .NET application and needs libicu. Ubuntu/WSL images usually
# have it; installdependencies.sh is the official fallback but needs root.
if ! ldd ./bin/Runner.Listener >/dev/null 2>&1 || ! ./bin/Runner.Listener --version >/dev/null 2>&1; then
  echo "runner binary cannot start; attempting dependency install (needs sudo)"
  sudo ./bin/installdependencies.sh || {
    echo "installdependencies.sh failed - install libicu manually and retry" >&2
    exit 1
  }
fi

# --------------------------------------------------------------- register ----
# --labels adds to the automatic self-hosted/linux/x64 labels that GitHub applies.
./config.sh \
  --url "$REPO_URL" \
  --token "$TOKEN" \
  --name "$RUNNER_NAME" \
  --labels "$CUSTOM_LABELS" \
  --work "_work" \
  --unattended \
  --replace

echo
echo "runner registered:"
echo "  name    : $RUNNER_NAME"
echo "  labels  : self-hosted, linux, x64, $CUSTOM_LABELS"
echo "  dir     : $RUNNER_DIR"
echo
echo "next:"
echo "  ./deploy/runner/start.sh    # start it in the background"
echo "  ./deploy/runner/remove.sh   # unregister and delete it"
