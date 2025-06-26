#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

usage() {
  cat <<EOF
Usage: $0 <MODEL_REPO> [PORT] [PAYLOAD_FILE] [TIMEOUT] [INTERVAL]
  MODEL_REPO   GitHub repo name under ersilia-os (e.g. eos3b5e)
  PORT         HTTP port to serve on (default: 8000)
  PAYLOAD_FILE JSON file with SMILES list (default: tests/data/payload.json)
  TIMEOUT      Max seconds to wait for job completion (default: 60)
  INTERVAL     Seconds between status polls (default: 2)
EOF
  exit 1
}

[[ $# -ge 1 ]] || usage
MODEL_ID="$1"
PORT="${2:-8000}"
PAYLOAD_FILE="${3:-tests/data/payload.json}"
TIMEOUT="${4:-60}"
INTERVAL="${5:-2}"

LOGFILE="${MODEL_ID}-serve.log"
HOME_REPO="$HOME/eos/repository"
BASE_URL="http://127.0.0.1:$PORT"

echo "→ CI Async-Endpoint Tester for '$MODEL_ID' on port $PORT"
echo "→ Payload   : $PAYLOAD_FILE"
echo "→ Timeout   : ${TIMEOUT}s, Interval: ${INTERVAL}s"
echo "→ Logs      : $LOGFILE"
echo

for cmd in git ersilia_model_lint ersilia_model_pack ersilia_model_serve curl jq timeout; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "✗ '$cmd' not found"; exit 1; }
done

[[ -d "$MODEL_ID" ]] && rm -rf "$MODEL_ID"
[[ -d "$HOME_REPO" ]] && rm -rf "$HOME_REPO"

echo "→ Cloning https://github.com/ersilia-os/$MODEL_ID.git"
git clone --depth 1 "https://github.com/ersilia-os/$MODEL_ID.git" 2>&1 | tee "$LOGFILE"

echo "→ Linting model…"
ersilia_model_lint --repo_path "$MODEL_ID" 2>&1 | tee -a "$LOGFILE"

echo "→ Packing model bundle…"
ersilia_model_pack \
  --repo_path "$MODEL_ID" \
  --bundles_repo_path "$HOME_REPO" \
  2>&1 | tee -a "$LOGFILE"

echo "→ Serving model…"
ersilia_model_serve \
  --bundle_path "$HOME_REPO/$MODEL_ID" \
  --port "$PORT" \
  2>&1 | tee -a "$LOGFILE" &

cleanup() {
  echo
  echo "→ Cleaning up background jobs…"
  jobs -p | xargs -r kill
  echo "→ Done."
}
trap cleanup EXIT

echo -n "→ Waiting up to 30s for $BASE_URL/healthz "
if ! timeout 30s bash -c \
     'until curl -sf '"$BASE_URL"'/healthz >/dev/null; do printf .; sleep 1; done'; then
  echo
  echo "✗ healthz failed. Logs:"
  cat "$LOGFILE"
  exit 1
fi
echo " OK"

echo
echo "→ POST $BASE_URL/job/submit"
submit_resp=$(curl -sSf -X POST "$BASE_URL/job/submit" \
  -H 'Content-Type: application/json' \
  --data-binary @"$PAYLOAD_FILE") || {
    echo "✗ /job/submit error:"; echo "$submit_resp"; exit 1
  }
job_id=$(echo "$submit_resp" | jq -r '.job_id')
[[ -n "$job_id" && "$job_id" != "null" ]] || {
  echo "✗ invalid job_id:"; echo "$submit_resp"; exit 1
}
echo "✅ job_id = $job_id"

echo
echo "→ Polling status every ${INTERVAL}s (timeout ${TIMEOUT}s)"
elapsed=0
while (( elapsed < TIMEOUT )); do
  status=$(curl -sSf "$BASE_URL/job/status/$job_id" | jq -r '.status')
  echo "  [${elapsed}s] status = $status"
  if [[ "$status" == "completed" ]]; then
    echo "✅ Job completed after ${elapsed}s"
    break
  elif [[ "$status" == "failed" ]]; then
    echo "✗ Job failed"; exit 1
  fi
  sleep "$INTERVAL"
  elapsed=$(( elapsed + INTERVAL ))
done

if [[ "$status" != "completed" ]]; then
  echo "✗ Timeout (${TIMEOUT}s) without completion"; exit 1
fi

echo
echo "→ GET $BASE_URL/job/result/$job_id"
result=$(curl -sSf "$BASE_URL/job/result/$job_id") || {
  echo "✗ /job/result error"; exit 1
}
echo "$result" | jq

echo
echo "✅ All async-endpoint checks passed!"
exit 0
