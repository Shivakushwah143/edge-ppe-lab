#!/usr/bin/env bash
# EdgePPE Lab continuous deployment: deploy one immutable image with a real
# runtime health gate, and automatically restore the previous image if the
# candidate does not become healthy.
#
# Run by .github/workflows/cd.yml on the self-hosted runner. It is a normal shell
# script so it can also be run by hand when diagnosing (see docs/evidence/).
#
# Design rules, deliberately chosen:
#   * The candidate is addressed by an immutable reference (git-SHA tag), never by
#     a floating tag. The reference that was deployed is recorded in the state file.
#   * "Deployed" means verified at runtime: /health, /ready, /model-info and a real
#     /predict must all pass. A container that merely started is not a deployment.
#   * The currently running image is recorded BEFORE anything is replaced, so a
#     rollback always has an exact, previously verified target.
#   * Fault injection only ever changes a container environment variable. It never
#     writes to, moves or deletes a qualified model artifact.
#   * A failed candidate deployment exits non-zero even when the rollback succeeds:
#     the release genuinely did not deploy, and that must be visible in Actions.
#
# Environment:
#   IMAGE              (required) immutable candidate ref, e.g. ghcr.io/o/r:sha
#   CONTAINER          (default edgeppe-api)
#   HOST_PORT          (default 18000)
#   DEPLOY_ROOT        (default $HOME/projects/edge-ppe-lab) the real deployment tree
#   RELEASE            (default v1) release directory holding the qualified model
#   FAULT_INJECTION    (default none) "bad_model_path" to exercise rollback on purpose
#   CANDIDATE_SHA, GITHUB_SHA, GITHUB_RUN_ID, GITHUB_REF_NAME  optional provenance
set -uo pipefail

CONTAINER="${CONTAINER:-edgeppe-api}"
HOST_PORT="${HOST_PORT:-18000}"
DEPLOY_ROOT="${DEPLOY_ROOT:-$HOME/projects/edge-ppe-lab}"
RELEASE="${RELEASE:-v1}"
FAULT_INJECTION="${FAULT_INJECTION:-none}"
IMAGE="${IMAGE:-}"

CONTAINER_MODEL_PATH="/app/models/model.onnx"
CONTAINER_BROKEN_MODEL_PATH="/app/models/does-not-exist.onnx"

STATE_DIR="$DEPLOY_ROOT/var/deployment"
STATE_FILE="$STATE_DIR/cd_state.json"
PREVIOUS_FILE="$STATE_DIR/previous_image.txt"
LOG_FILE="$STATE_DIR/cd_deploy.log"

HEALTH_TIMEOUT=60
READY_TIMEOUT=90
PYTHON_BIN="$DEPLOY_ROOT/.venv/bin/python"
[[ -x "$PYTHON_BIN" ]] || PYTHON_BIN="$(command -v python3)"

mkdir -p "$STATE_DIR"
: > "$LOG_FILE"

log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "$LOG_FILE"; }
fail() { log "FATAL: $*"; exit 1; }

# ---------------------------------------------------------------- preflight ----
log "=== EdgePPE CD deploy ==="
log "candidate image : ${IMAGE:-<unset>}"
log "deploy root     : $DEPLOY_ROOT"
log "release         : $RELEASE"
log "fault injection : $FAULT_INJECTION"

[[ -n "$IMAGE" ]] || fail "IMAGE is required (immutable reference, e.g. ghcr.io/owner/repo:<git-sha>)"
[[ -d "$DEPLOY_ROOT" ]] || fail "deployment root does not exist: $DEPLOY_ROOT"

RELEASE_JSON="$DEPLOY_ROOT/var/releases/$RELEASE/release.json"
[[ -f "$RELEASE_JSON" ]] || fail "release metadata missing: $RELEASE_JSON"

RELEASE_INFO=$("$PYTHON_BIN" - "$RELEASE_JSON" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
print(d["onnx_path"])
print(d["registered_model_version"])
print(d["onnx_sha256"])
PY
) || fail "could not read $RELEASE_JSON"
MODEL_REL_PATH="$(sed -n 1p <<<"$RELEASE_INFO")"
MODEL_VERSION="$(sed -n 2p <<<"$RELEASE_INFO")"
MODEL_SHA="$(sed -n 3p <<<"$RELEASE_INFO")"
MODEL_HOST_PATH="$DEPLOY_ROOT/$MODEL_REL_PATH"

# The health gate needs one real image to run a real inference. The qualified
# artifact and the derived dataset live in the deployment root, not in git.
PROBE_IMAGE="$(find "$DEPLOY_ROOT/data/processed/ppe-v1/images/test" -type f \
  \( -name '*.jpg' -o -name '*.jpeg' -o -name '*.png' \) 2>/dev/null | sort | head -1)"

log "qualified model : $MODEL_HOST_PATH (registry version $MODEL_VERSION, sha256 ${MODEL_SHA:0:12}…)"
[[ -f "$MODEL_HOST_PATH" ]] || fail "qualified ONNX artifact missing: $MODEL_HOST_PATH"
[[ -n "$PROBE_IMAGE" ]] || fail "no real test image available under $DEPLOY_ROOT/data/processed/ppe-v1/images/test (the health gate performs a real inference)"
log "probe image     : $PROBE_IMAGE"

# Record what is running right now, before anything is replaced.
PREVIOUS_IMAGE="$(docker inspect "$CONTAINER" --format '{{.Config.Image}}' 2>/dev/null || true)"
[[ -n "$PREVIOUS_IMAGE" ]] || PREVIOUS_IMAGE="none"
log "previous image  : $PREVIOUS_IMAGE"
printf '%s\n' "$PREVIOUS_IMAGE" > "$PREVIOUS_FILE"

log "pulling candidate"
docker pull "$IMAGE" >>"$LOG_FILE" 2>&1 || fail "docker pull failed for $IMAGE"
CANDIDATE_DIGEST="$(docker inspect "$IMAGE" --format '{{index .RepoDigests 0}}' 2>/dev/null || echo 'unknown')"
log "candidate digest: $CANDIDATE_DIGEST"

# ------------------------------------------------------------------- deploy ----
start_container() {
  local image="$1" model_path="$2"
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  docker run -d --name "$CONTAINER" \
    -p "${HOST_PORT}:8000" \
    --mount "type=bind,source=${MODEL_HOST_PATH},target=${CONTAINER_MODEL_PATH},readonly" \
    -e "EDGE_PPE_MODEL_PATH=${model_path}" \
    -e "EDGE_PPE_MODEL_VERSION=${MODEL_VERSION}" \
    -e EDGE_PPE_STARTUP_STRICT=true \
    -l "org.edgeppe.deployed-image=${image}" \
    "$image" >>"$LOG_FILE" 2>&1
}

wait_for_http() {
  # $SECONDS counts from shell start, so it must be baselined to report the wait
  # itself. Reporting it raw made a 4s wait log as "after 66s" once the script had
  # been running for a while, which would have made the deployment log misleading
  # exactly in the evidence it is meant to provide.
  local url="$1" want="$2" timeout="$3" deadline=$((SECONDS + $3)) started=$SECONDS
  while (( SECONDS < deadline )); do
    local code
    code="$(curl -s -o /dev/null -w '%{http_code}' "$url" 2>/dev/null || echo 000)"
    if [[ "$code" == "$want" ]]; then
      log "  OK   $url -> $code (after $((SECONDS - started))s)"
      return 0
    fi
    sleep 2
  done
  log "  FAIL $url never returned $want within ${timeout}s (last: ${code:-000})"
  return 1
}

# The gate. Every step must pass or the deployment is not considered successful.
health_gate() {
  local phase="$1"
  log "--- health gate ($phase) ---"

  local cid
  cid="$(docker inspect "$CONTAINER" --format '{{.Id}}' 2>/dev/null || true)"
  if [[ -z "$cid" ]]; then
    log "  FAIL container $CONTAINER does not exist"
    return 1
  fi

  wait_for_http "http://127.0.0.1:${HOST_PORT}/health" 200 "$HEALTH_TIMEOUT" || return 1
  wait_for_http "http://127.0.0.1:${HOST_PORT}/ready" 200 "$READY_TIMEOUT" || return 1

  local info
  info="$(curl -s "http://127.0.0.1:${HOST_PORT}/model-info" 2>/dev/null || true)"
  local reported
  reported="$(printf '%s' "$info" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin).get("concrete_model_version",""))' 2>/dev/null || echo '')"
  if [[ "$reported" != "$MODEL_VERSION" ]]; then
    log "  FAIL /model-info reports concrete_model_version=${reported:-<none>}, expected $MODEL_VERSION"
    return 1
  fi
  log "  OK   /model-info concrete_model_version=$reported"

  # A real inference with a real image on disk.
  local body code
  body="$(mktemp)"
  code="$(curl -s -o "$body" -w '%{http_code}' -F "image=@${PROBE_IMAGE}" \
    "http://127.0.0.1:${HOST_PORT}/predict" 2>/dev/null || echo 000)"
  if [[ "$code" != "200" ]]; then
    log "  FAIL /predict -> $code"
    sed -n 1,20p "$body" >>"$LOG_FILE" 2>/dev/null
    rm -f "$body"
    return 1
  fi
  local detections
  detections="$("$PYTHON_BIN" -c 'import json,sys; print(len(json.load(open(sys.argv[1])).get("detections",[])))' "$body" 2>/dev/null || echo '?')"
  rm -f "$body"
  log "  OK   /predict -> 200 (real inference, ${detections} detection(s))"

  log "  OK   container $CONTAINER healthy on :${HOST_PORT}"
  return 0
}

record_state() {
  local outcome="$1" deployed="$2" rollback_status="$3"
  "$PYTHON_BIN" - "$STATE_FILE" "$outcome" "$deployed" "$PREVIOUS_IMAGE" "$rollback_status" <<'PY' >>"$LOG_FILE" 2>&1
import json, os, sys
from datetime import datetime, timezone

path, outcome, deployed, previous, rollback = sys.argv[1:6]
entry = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "outcome": outcome,
    "deployed_image": deployed,
    "previous_image": previous,
    "rollback": rollback,
    "candidate_image": os.environ.get("IMAGE"),
    "candidate_digest": os.environ.get("CANDIDATE_DIGEST"),
    "release": os.environ.get("RELEASE", "v1"),
    "model_version": os.environ.get("MODEL_VERSION"),
    "fault_injection": os.environ.get("FAULT_INJECTION", "none"),
    # CANDIDATE_SHA is the commit CI validated and this run deployed. GITHUB_SHA is
    # only a fallback for a hand-run: under a workflow_run event github.sha is the
    # tip of the default branch, which is not necessarily the commit deployed here.
    "git_sha": os.environ.get("CANDIDATE_SHA") or os.environ.get("GITHUB_SHA"),
    "run_id": os.environ.get("GITHUB_RUN_ID"),
    "run_ref": os.environ.get("GITHUB_REF_NAME"),
}
data = {"history": []}
if os.path.exists(path):
    try:
        data = json.load(open(path))
    except json.JSONDecodeError:
        pass
data["last"] = entry
data.setdefault("history", []).append(entry)
json.dump(data, open(path, "w"), indent=2)
PY
  log "state written: $STATE_FILE (outcome=$outcome, rollback=$rollback_status)"
  printf '%s' "$CANDIDATE_DIGEST" > "$STATE_DIR/last_candidate_digest.txt"
  printf '%s' "$deployed" > "$STATE_DIR/deployed_image.txt"
}

# -------------------------------------------------------- candidate rollout ----
CANDIDATE_MODEL_PATH="$CONTAINER_MODEL_PATH"
if [[ "$FAULT_INJECTION" == "bad_model_path" ]]; then
  log "*** FAULT INJECTION ACTIVE: pointing the candidate at an invalid in-container model path ***"
  log "*** the qualified artifact on the host is NOT modified, moved or deleted          ***"
  CANDIDATE_MODEL_PATH="$CONTAINER_BROKEN_MODEL_PATH"
fi

export CANDIDATE_DIGEST RELEASE MODEL_VERSION FAULT_INJECTION IMAGE CANDIDATE_SHA GITHUB_SHA GITHUB_RUN_ID GITHUB_REF_NAME

log "starting candidate container"
start_container "$IMAGE" "$CANDIDATE_MODEL_PATH" || fail "docker run failed for candidate $IMAGE"

if health_gate "candidate $IMAGE"; then
  log "RESULT: candidate deployment SUCCEEDED"
  record_state "success" "$IMAGE" "not_needed"
  {
    echo "## EdgePPE deployment succeeded"
    echo ""
    echo "| field | value |"
    echo "|---|---|"
    echo "| candidate image | \`$IMAGE\` |"
    echo "| image digest | \`$CANDIDATE_DIGEST\` |"
    echo "| model version | \`$MODEL_VERSION\` |"
    echo "| health | \`/health\` 200, \`/ready\` 200 |"
    echo "| inference | real \`/predict\` on \`$(basename "$PROBE_IMAGE")\` |"
    echo "| deployed image | \`$IMAGE\` |"
  } >> "${GITHUB_STEP_SUMMARY:-/dev/null}"
  exit 0
fi

# ------------------------------------------------------------ auto rollback ----
log "candidate deployment FAILED the runtime health gate"
docker logs --tail 40 "$CONTAINER" 2>&1 | tee -a "$LOG_FILE" | sed 's/^/  container| /' >&2

if [[ "$PREVIOUS_IMAGE" == "none" ]]; then
  log "RESULT: ROLLBACK IMPOSSIBLE - no previously running image was recorded"
  record_state "failed" "none" "impossible"
  {
    echo "## EdgePPE deployment FAILED"
    echo ""
    echo "Candidate \`$IMAGE\` failed the health gate and there was no previously running"
    echo "container to roll back to. The deployment is NOT healthy."
  } >> "${GITHUB_STEP_SUMMARY:-/dev/null}"
  exit 1
fi

log "AUTOMATIC ROLLBACK: restoring previous image $PREVIOUS_IMAGE"
docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
if ! docker image inspect "$PREVIOUS_IMAGE" >/dev/null 2>&1; then
  log "previous image not present locally; pulling $PREVIOUS_IMAGE"
  docker pull "$PREVIOUS_IMAGE" >>"$LOG_FILE" 2>&1 || log "WARNING: could not pull $PREVIOUS_IMAGE"
fi

start_container "$PREVIOUS_IMAGE" "$CONTAINER_MODEL_PATH" || {
  log "RESULT: ROLLBACK FAILED to start the previous image"
  record_state "failed" "none" "failed"
  exit 1
}

if health_gate "rollback $PREVIOUS_IMAGE"; then
  log "RESULT: ROLLBACK SUCCEEDED - previous image $PREVIOUS_IMAGE is healthy again"
  record_state "failed" "$PREVIOUS_IMAGE" "succeeded"
  {
    echo "## EdgePPE deployment FAILED - automatic rollback succeeded"
    echo ""
    echo "| field | value |"
    echo "|---|---|"
    echo "| candidate image (failed) | \`$IMAGE\` |"
    echo "| fault injection | \`$FAULT_INJECTION\` |"
    echo "| rolled back to | \`$PREVIOUS_IMAGE\` |"
    echo "| post-rollback health | \`/health\` 200, \`/ready\` 200 |"
    echo "| post-rollback inference | real \`/predict\` succeeded |"
    echo ""
    echo "The run is marked failed because the candidate did not deploy."
  } >> "${GITHUB_STEP_SUMMARY:-/dev/null}"
  # Non-zero on purpose: the release did not deploy. The rollback is proven, but a
  # failed deployment must never look like a green run.
  exit 1
fi

log "RESULT: ROLLBACK FAILED - the previous image $PREVIOUS_IMAGE is not healthy either"
record_state "failed" "none" "failed"
{
  echo "## EdgePPE deployment FAILED and ROLLBACK FAILED"
  echo ""
  echo "Candidate \`$IMAGE\` failed, and restoring \`$PREVIOUS_IMAGE\` did not recover"
  echo "the service. Manual intervention is required."
} >> "${GITHUB_STEP_SUMMARY:-/dev/null}"
exit 1
