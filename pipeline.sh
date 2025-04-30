#!/usr/bin/env bash
set -euo pipefail

HOME_DIR=$(eval echo "~$USER")
MODEL_ID="$1"
PORT="${2:-8000}"

[ -d eos3b5e ] && rm -rf eos3b5e
git clone --depth 1 https://github.com/ersilia-os/eos3b5e.git

ersilia_model_lint --repo_path "$MODEL_ID"
ersilia_model_pack \
  --repo_path "$MODEL_ID" \
  --bundles_repo_path "$HOME_DIR"/eos/repository

ersilia_model_serve \
  --bundle_path "$HOME_DIR"/eos/repository/"$MODEL_ID" \
  --port "$PORT" &
SERVER_PID=$!

cleanup() {
  echo "Shutting down server (pid $SERVER_PID)…"
  kill "$SERVER_PID" 2>/dev/null || true
  wait "$SERVER_PID" 2>/dev/null || true
}
trap cleanup EXIT

BASE_URL="http://127.0.0.1:$PORT"
echo -n "Waiting for $BASE_URL/healthz "
until curl -sf "$BASE_URL/healthz" >/dev/null; do
  echo -n "."
  sleep 1
done
echo " OK"

exit 0
