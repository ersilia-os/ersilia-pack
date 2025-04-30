#!/bin/bash
set -euo pipefail

HOME_DIR=$(eval echo ~$USER)
MODEL_ID="$1"
PORT="${2:-8000}"

[ -d eos3b5e ] && rm -rf eos3b5e
git clone --depth 1 https://github.com/ersilia-os/eos3b5e.git

ersilia_model_lint --repo_path "$MODEL_ID"
ersilia_model_pack --repo_path "$MODEL_ID" --bundles_repo_path "$HOME_DIR"/eos/repository
ersilia_model_serve --bundle_path "$HOME_DIR"/eos/repository/"$MODEL_ID" --port "$PORT" &
SERVER_PID=$!

BASE_URL="http://127.0.0.1:$PORT"
until curl -sf "$BASE_URL/healthz"; do sleep 1; done

kill $SERVER_PID || { kill $SERVER_PID; exit 1; }

wait $SERVER_PID 2>/dev/null
