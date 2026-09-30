#!/usr/bin/env bash
# Run one reviewer template against the planted-defect fixture N times.
# Usage: tests/review-eval/run.sh <template.md> <label> [runs] [out-dir]
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
template="$1"; label="$2"; runs="${3:-3}"
out="${4:-/tmp/bearpaws-tests/review-eval/$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$out"
for i in $(seq 1 "$runs"); do
  (
    work="$(mktemp -d)"
    "$HERE/setup.sh" "$work"
    prompt="$(python3 "$HERE/render.py" "$template" "$work")"
    (cd "$work" && env -u CLAUDECODE claude -p "$prompt" --model "${BENCH_MODEL:-sonnet}" \
      --setting-sources project,local --strict-mcp-config --permission-mode bypassPermissions \
      --max-budget-usd 3 --no-session-persistence --output-format stream-json --verbose \
      > "$out/$label-$i.jsonl" 2>/dev/null) || true
    python3 "$HERE/score.py" --label "$label" --run "$i" "$out/$label-$i.jsonl" >> "$out/scores.jsonl"
  ) &
done
wait
python3 "$HERE/score.py" --summary "$out/scores.jsonl"
