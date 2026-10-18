#!/bin/sh
# Run every fixture in <eval_root>/runs through Claude Code inside the isolated image.
# Usage: ANTHROPIC_API_KEY=... evaluations/harness/run.sh <eval_root> [model]
#    or: EVAL_ENV_FILE=/path/to/key.env evaluations/harness/run.sh <eval_root> [model]
# The env file holds one line, ANTHROPIC_API_KEY=..., and is read only by Docker.
# Use a dedicated, spend-limited key and revoke it afterwards: agents in the container
# can read their own environment. Existing traces are kept, so reruns resume.
set -eu

ROOT=$(cd "$1" && pwd)
MODEL=${2:-claude-opus-5-5}
IMAGE=${EVAL_IMAGE:-clean-code-eval:2.1.289}
if [ -n "${EVAL_ENV_FILE:-}" ]; then
  [ -f "$EVAL_ENV_FILE" ] || { echo "EVAL_ENV_FILE not found" >&2; exit 1; }
  set -- --env-file "$EVAL_ENV_FILE"
else
  : "${ANTHROPIC_API_KEY:?set ANTHROPIC_API_KEY or EVAL_ENV_FILE to a dedicated evaluation key}"
  set -- -e ANTHROPIC_API_KEY
fi

docker image inspect "$IMAGE" >/dev/null 2>&1 || {
  echo "Build the image first: docker build -t $IMAGE evaluations/harness" >&2
  exit 1
}

for run in "$ROOT"/runs/*/; do
  name=$(basename "$run")
  trace="$ROOT/runs/$name.trace.jsonl"
  if [ -s "$trace" ]; then
    echo "skip $name (trace exists)"
    continue
  fi
  echo "run $name"
  docker run --rm "$@" \
    --mount "type=bind,src=$ROOT/runs/$name,dst=/work" \
    --cap-drop ALL --security-opt no-new-privileges \
    --pids-limit 256 --memory 2g --cpus 2 \
    "$IMAGE" claude -p "$(cat "$ROOT/runs/$name.prompt.txt")" \
      --model "$MODEL" --output-format stream-json --verbose --max-turns 60 \
      --allowedTools "Bash,Read,Write,Edit,Glob,Grep" \
    > "$trace" 2> "$ROOT/runs/$name.stderr.txt" || echo "  $name exited with status $?"
done
