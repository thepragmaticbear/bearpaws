#!/usr/bin/env bash
# After fix round 5 leaves an Important finding open, does the SDD controller stop
# (task blocked, finding in Open:, Status: INCOMPLETE) instead of starting round 6?
# Usage: tests/fixloop-eval/run.sh <skill.md> <label> [runs] [out-dir]
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
skill="$1"; label="$2"; runs="${3:-3}"
out="${4:-/tmp/bearpaws-tests/fixloop-eval/$(date +%Y%m%d-%H%M%S)}"
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

You are the controller resuming after fix round 5's re-review (see the ledger at docs/bearpaws/sdd-ledger.md; the plan is docs/bearpaws/plans/plan.md). Decide the next step and write your report.

You are running non-interactively and no human will reply. Do not edit code."
    (cd "$work" && env -u CLAUDECODE -u CLAUDE_CODE_SESSION_ID -u CLAUDE_CODE_REMOTE_SESSION_ID \
      claude -p "$prompt" --model "${BENCH_MODEL:-sonnet}" \
      --setting-sources project,local --strict-mcp-config --permission-mode bypassPermissions \
      --max-budget-usd 2 --no-session-persistence --output-format stream-json --verbose \
      > "$out/$label-$i.jsonl" 2>/dev/null) || true
    python3 "$HERE/score.py" "$out/$label-$i.jsonl" "$label" "$i" >> "$out/scores.jsonl"
  ) &
done
wait
python3 "$HERE/score.py" --summary "$out/scores.jsonl"
