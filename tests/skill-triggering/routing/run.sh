#!/usr/bin/env bash
# Which workflow does the bootstrap lead an agent to plan for each request?
# Usage: tests/skill-triggering/routing/run.sh <bootstrap-skill.md> <label> [runs] [out-dir]
# Text-only: the agent names the skills it would invoke; nothing is executed.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
boot="$(cat "$1")"; label="$2"; runs="${3:-3}"
out="${4:-/tmp/bearpaws-tests/routing-eval/$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$out"
while IFS='|' read -r name expect request; do
  [ -z "$name" ] && continue
  for i in $(seq 1 "$runs"); do
    (
      prompt="<warning level=\"hard\">
You have bearpaws. Your bootstrap skill:

$boot
</warning>

Available bearpaws skills: bp:onboarding-to-a-project, bp:brainstorming, bp:writing-plans, bp:executing-plans, bp:subagent-driven-development, bp:test-driven-development, bp:systematic-debugging, bp:requesting-code-review, bp:verification-before-completion, bp:finishing-a-development-branch.

You are in an existing Python web service repository. The user writes:
\"$request\"

Do not do the work. List every bearpaws skill you will invoke for this request, in order, one per line as 'SKILL: bp:name'. Then a line 'ROUTE: ' with one word describing the workflow size (probe, patch, or build) and a line 'RISK: routine' or 'RISK: elevated'."
      env -u CLAUDECODE claude -p "$prompt" --model "${BENCH_MODEL:-sonnet}" --setting-sources project,local \
        --strict-mcp-config --tools "" --no-session-persistence --output-format json > "$out/$label-$name-$i.json" 2>/dev/null || true
      python3 - "$out/$label-$name-$i.json" "$label" "$name" "$expect" >> "$out/scores.jsonl" <<'PY'
import json, re, sys
path, label, name, expect = sys.argv[1:]
t = (json.load(open(path)).get("result") or "")
skills = re.findall(r"SKILL:\s*(bp:[\w-]+)", t)
route = (re.search(r"ROUTE:\s*(\w+)", t) or [None, "?"])[1].lower()
risk = (re.search(r"RISK:\s*(\w+)", t) or [None, "?"])[1].lower()
print(json.dumps({"label": label, "case": name, "expect": expect, "skills": skills, "route": route, "risk": risk}))
PY
    ) &
  done
done < "$HERE/cases.txt"
wait
python3 - "$out/scores.jsonl" <<'PY'
import json, sys
from collections import defaultdict
g = defaultdict(list)
for l in open(sys.argv[1]):
    r = json.loads(l); g[(r["label"], r["case"])].append(r)
for (label, case), rows in sorted(g.items()):
    exp_route, exp_risk, must = rows[0]["expect"].split(",", 2) if rows[0]["expect"].count(",") >= 2 else (*rows[0]["expect"].split(","), "")
    ok = 0
    for r in rows:
        need = [s for s in must.split("+") if s]
        good = r["route"] == exp_route and r["risk"] == exp_risk and all(s in r["skills"] for s in need)
        ok += good
    print(f"{label} {case:<14} ok {ok}/{len(rows)}  expect {exp_route}/{exp_risk} needs {must or '-'}")
    for r in rows:
        print(f"    {r['route']}/{r['risk']} {r['skills']}")
PY
