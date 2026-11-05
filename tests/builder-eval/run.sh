#!/usr/bin/env bash
# With a finished design doc, does brainstorming dispatch the builder check only for
# elevated-risk designs, and surface the open single-use question?
# Usage: DESIGN=routine|elevated tests/builder-eval/run.sh <skill.md> <label> [runs] [out-dir]
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
design="${DESIGN:-elevated}"
case "$design" in routine|elevated) ;; *) echo "DESIGN must be routine or elevated" >&2; exit 2 ;; esac
skill="$1"; label="$2"; runs="${3:-3}"
skill_dir="$(cd "$(dirname "$skill")" && pwd)"
out="${4:-/tmp/bearpaws-tests/builder-eval/$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$out"
# Runs cd into a work dir before writing here: keep the out-dir absolute.
out="$(cd "$out" && pwd)"
for i in $(seq 1 "$runs"); do
  (
    work="$out/$label-$design-$i"
    if ! "$HERE/setup.sh" "$work" >/dev/null 2>&1; then
      echo "{\"label\": \"$label\", \"design\": \"$design\", \"run\": $i, \"error\": \"setup failed\"}" >> "$out/scores.jsonl"; exit 0
    fi
    # The Skill tool gives the agent the skill's base directory; so does this prompt.
    prompt="Follow this skill (base directory for this skill: $skill_dir):

$(cat "$skill")

The design at docs/bearpaws/plans/$design-design.md is written and committed, and the user approved each section. Do the next steps up to the user review.

You are running non-interactively and no human will reply."
    (cd "$work" && env -u CLAUDECODE -u CLAUDE_CODE_SESSION_ID -u CLAUDE_CODE_REMOTE_SESSION_ID \
      claude -p "$prompt" --model "${BENCH_MODEL:-sonnet}" \
      --setting-sources project,local --strict-mcp-config --permission-mode bypassPermissions \
      --max-budget-usd 2 --no-session-persistence --output-format stream-json --verbose \
      > "$out/$label-$design-$i.jsonl" 2>/dev/null) || true
    python3 "$HERE/score.py" "$out/$label-$design-$i.jsonl" "$label" "$design" "$i" >> "$out/scores.jsonl"
  ) &
done
wait
python3 "$HERE/score.py" --summary "$out/scores.jsonl"
