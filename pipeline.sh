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

curl --fail \
     -H "Content-Type: application/json" \
     -d '[
       {"key": "0", "input": "Nc1cccc(c1)-c1cc2c(Oc3cccc(O)c3)ncnc2[nH]1"},
       {"key": "1", "input": "C1=CN=CC=C1C(=O)NN"},
       {"key": "2", "input": "CC(CN1C=NC2=C(N=CN=C21)N)OCP(=O)(O)O"}
     ]' \
     "$BASE_URL/run" \
  && kill $SERVER_PID || { kill $SERVER_PID; exit 1; }

wait $SERVER_PID 2>/dev/null
