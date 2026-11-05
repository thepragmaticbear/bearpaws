#!/usr/bin/env bash
# Given a session that claimed COMPLETE over a piped test failure and an open Important review
# finding, does the diagnosis find both, cite path:line for every finding, and leave the
# transcripts untouched?
# Usage: tests/diagnose-eval/run.sh <skill.md|none> <label> [runs] [out-dir]
#   none: the same prompt with no skill text (RED baseline).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
skill="$1"; label="$2"; runs="${3:-3}"
skill_dir=""
[ "$skill" = none ] || skill_dir="$(cd "$(dirname "$skill")" && pwd)"
out="${4:-/tmp/bearpaws-tests/diagnose-eval/$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$out"
# Runs cd into a work dir before writing here: keep the out-dir absolute.
out="$(cd "$out" && pwd)"
for i in $(seq 1 "$runs"); do
  (
    work="$out/$label-$i"
    if ! "$HERE/setup.sh" "$work" >/dev/null 2>&1; then
      echo "{\"label\": \"$label\", \"run\": $i, \"error\": \"setup failed\"}" >> "$out/scores.jsonl"; exit 0
    fi
    sid="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["session_id"])' "$work/planted.json")"
    task="My last session said COMPLETE but I think the tests failed. The session transcript is under $work/projects; session id $sid. Diagnose it. Write the report to $work/workspace/report.md.

Non-interactive: treat this message as the problem statement. No human will reply."
    if [ "$skill" = none ]; then
      prompt="$task"
    else
      # The Skill tool gives the agent the skill's base directory; so does this prompt.
      prompt="Follow this skill (base directory for this skill: $skill_dir):

$(cat "$skill")

$task"
    fi
    (cd "$work/workspace" && env -u CLAUDECODE -u CLAUDE_CODE_SESSION_ID -u CLAUDE_CODE_REMOTE_SESSION_ID \
      claude -p "$prompt" --model "${BENCH_MODEL:-sonnet}" \
      --setting-sources project,local --strict-mcp-config --permission-mode bypassPermissions \
      --max-budget-usd 5 --no-session-persistence --output-format stream-json --verbose \
      > "$out/$label-$i.jsonl" 2>/dev/null) || true
    python3 "$HERE/score.py" "$out/$label-$i.jsonl" "$label" "$i" "$work" >> "$out/scores.jsonl"
  ) &
done
wait
python3 "$HERE/score.py" --summary "$out/scores.jsonl"
