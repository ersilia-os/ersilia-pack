#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

CONDA_ENV="test"

# --- Conda + env checks (no activation needed) ---
if ! command -v conda >/dev/null 2>&1; then
  echo "✗ conda not found in PATH. Make sure Anaconda/Miniconda is installed."
  exit 1
fi

# Verify the env exists and is runnable
if ! conda run -n "$CONDA_ENV" --no-capture-output python -c "import sys" >/dev/null 2>&1; then
  echo "✗ Conda environment '$CONDA_ENV' not found or not runnable."
  exit 1
fi
echo "→ Using conda env '$CONDA_ENV' via conda run"

# Helper: run a command inside the env (no activation)
crun() {
  conda run -n "$CONDA_ENV" --no-capture-output "$@"
}

usage() {
  cat <<EOF
Usage: $0 <MODEL_REPO> [PORT] [PAYLOAD_FILE]
  MODEL_REPO   GitHub repo name under ersilia-os (e.g. eos3b5e)
  PORT         HTTP port to serve on (default: 8000)
  PAYLOAD_FILE JSON file containing an array of SMILES to send to /run
EOF
  exit 1
}

[[ $# -ge 1 ]] || usage
MODEL_ID="$1"
PORT="${2:-8000}"
PAYLOAD_FILE="${3:-tests/data/payload.json}"
LOGFILE="${MODEL_ID}-serve.log"
HOME_REPO="$HOME/eos/repository/$MODEL_ID"

echo "→ CI Runner for '$MODEL_ID' on port $PORT"
echo "→ Using payload: $PAYLOAD_FILE"
echo "→ Logs at   : $LOGFILE"
echo

# Tools that must exist on the host PATH (not necessarily in conda env)
for cmd in git curl jq timeout tee; do
  command -v "$cmd" >/dev/null 2>&1 \
    || { echo "✗ '$cmd' not in PATH"; exit 1; }
done

# Tools expected inside the conda env
for ecmd in ersilia_model_lint ersilia_model_pack ersilia_model_serve; do
  crun command -v "$ecmd" >/dev/null 2>&1 \
    || { echo "✗ '$ecmd' not found in conda env '$CONDA_ENV'"; exit 1; }
done

[[ -d "$MODEL_ID" ]]   && rm -rf "$MODEL_ID"
[[ -d "$HOME_REPO" ]]  && rm -rf "$HOME_REPO"

echo "→ Cloning https://github.com/ersilia-os/$MODEL_ID.git"
git clone --depth 1 "https://github.com/ersilia-os/$MODEL_ID.git" 2>&1 | tee "$LOGFILE"
echo

echo "→ Linting model…"
crun ersilia_model_lint --repo_path "$MODEL_ID" 2>&1 | tee -a "$LOGFILE"
echo

echo "→ Packing model bundle…"
crun ersilia_model_pack \
  --repo_path "$MODEL_ID" \
  --bundles_repo_path "$HOME/eos/repository" \
  2>&1 | tee -a "$LOGFILE"
echo

echo "→ Serving model…"
crun ersilia_model_serve \
  --bundle_path "$HOME/eos/repository/$MODEL_ID" \
  --port "$PORT" \
  2>&1 | tee -a "$LOGFILE" &
SERVER_PID=$!
trap 'echo; echo "→ Killing server…"; kill $SERVER_PID 2>/dev/null || true; exit' EXIT

BASE_URL="http://127.0.0.1:$PORT"

echo -n "→ Waiting up to 30s for $BASE_URL/healthz "
if ! timeout 30s bash -c \
    'until curl -sf '"$BASE_URL"'/healthz >/dev/null; do printf .; sleep 1; done'; then
  echo; echo "✗ healthz never became healthy. Logs:"; cat "$LOGFILE"; exit 1
fi
echo " OK"

echo
echo "→ Testing POST $BASE_URL/run"
resp=$(curl -sSf -X POST "$BASE_URL/run" \
  -H 'Content-Type: application/json' \
  --data-binary @"$PAYLOAD_FILE") || {
    echo "✗ /run failed:"; echo "$resp"; exit 1
  }

echo "$resp" | jq . >/dev/null 2>&1 || {
  echo "✗ /run did not return JSON:"; echo "$resp"; exit 1
}

echo "✅ /run returned valid JSON:"
echo "$resp" | jq

echo
echo "✅ All CI checks passed—shutting down."
