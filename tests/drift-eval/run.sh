#!/usr/bin/env bash
# Does an agent finishing a branch notice code that drifted from its checked-off plan?
# Usage: [CLEAN=1] tests/drift-eval/run.sh <skill.md> <label> [runs] [out-dir]
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
skill="$1"; label="$2"; runs="${3:-3}"
out="${4:-/tmp/bearpaws-tests/drift-eval/$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$out"
# Runs cd into a work dir before writing here: keep the out-dir absolute.
out="$(cd "$out" && pwd)"
for i in $(seq 1 "$runs"); do
  (
    work="$out/$label-$i"
    if ! "$HERE/setup.sh" "$work" >/dev/null 2>&1; then
      echo "{\"label\": \"$label\", \"run\": $i, \"error\": \"setup failed\"}" >> "$out/scores.jsonl"; exit 0
    fi
    prompt="Follow this skill:

$(cat "$skill")

Implementation of docs/bearpaws/plans/2026-11-01-slugify.md on branch feat/slugify is complete and every task is checked off. Finish the branch. When you reach the options, choose option 3 (keep the branch as-is).

You are running non-interactively and no human will reply. Make reasonable decisions yourself and finish in this session. Do not push, merge, or edit files."
    (cd "$work" && env -u CLAUDECODE claude -p "$prompt" --model "${BENCH_MODEL:-sonnet}" \
      --setting-sources project,local --strict-mcp-config --permission-mode bypassPermissions \
      --max-budget-usd 2 --no-session-persistence --output-format json \
      > "$out/$label-$i.json" 2>/dev/null) || true
    python3 "$HERE/score.py" "$out/$label-$i.json" "$label" "$i" >> "$out/scores.jsonl"
  ) &
done
wait
python3 "$HERE/score.py" --summary "$out/scores.jsonl"
