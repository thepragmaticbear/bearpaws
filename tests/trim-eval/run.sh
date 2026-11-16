#!/usr/bin/env bash
# Given the subagent-driven-development skill text, which skill does the agent invoke next for a
# situation SDD does not fit (no design, no plan, coupled plan, separate session) and one it does?
# Expectations follow the toolkit's triggers (writing-plans, executing-plans), not the old SDD graph.
# The fit case accepts bp:using-git-worktrees too: SDD's Setup step sets up the workspace first.
# Usage: tests/trim-eval/run.sh <sdd-skill.md> <label> [runs] [out-dir]
# Text-only: nothing is executed.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
skill="$(cat "$1")"; label="$2"; runs="${3:-3}"
out="${4:-/tmp/bearpaws-tests/trim-eval/$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$out"
out="$(cd "$out" && pwd)"
while IFS='|' read -r name expect situation; do
  [ -z "$name" ] && continue
  for i in $(seq 1 "$runs"); do
    (
      prompt="You have bearpaws skills: bp:brainstorming, bp:writing-plans, bp:executing-plans, bp:subagent-driven-development, bp:using-git-worktrees, bp:test-driven-development. One of them, loaded now:

$skill

Situation: $situation

Do not do the work. Reply with exactly one line 'NEXT: bp:<name>' naming the bearpaws skill to invoke next."
      env -u CLAUDECODE claude -p "$prompt" --model "${BENCH_MODEL:-sonnet}" --setting-sources project,local \
        --strict-mcp-config --tools "" --no-session-persistence --output-format json > "$out/$label-$name-$i.json" 2>/dev/null || true
      python3 - "$out/$label-$name-$i.json" "$label" "$name" "$expect" >> "$out/scores.jsonl" <<'PY'
import json, re, sys
path, label, name, expect = sys.argv[1:]
try:
    with open(path) as f:
        d = json.load(f)
except (OSError, ValueError):
    d = {}
t = d.get("result") or ""
m = re.search(r"NEXT:\s*`?(bp:[\w-]+)", t)
got = m.group(1) if m else "?"
print(json.dumps({"label": label, "case": name, "got": got, "pass": got in expect.split(","),
                  "cost": d.get("total_cost_usd") or 0}))
PY
    ) &
  done
done < "$HERE/cases.txt"
wait
python3 - "$out/scores.jsonl" <<'PY'
import json, sys
from collections import defaultdict
g = defaultdict(list)
with open(sys.argv[1]) as f:
    for line in f:
        r = json.loads(line); g[(r["label"], r["case"])].append(r)
total = sum(r["pass"] for rows in g.values() for r in rows); n = sum(len(rows) for rows in g.values())
for (label, case), rows in sorted(g.items()):
    print(f"{label} {case:<9} {sum(r['pass'] for r in rows)}/{len(rows)}  {[r['got'] for r in rows]}")
print(f"total {total}/{n}")
PY
