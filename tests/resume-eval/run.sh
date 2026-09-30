#!/usr/bin/env bash
# Does an agent resuming an interrupted plan reconcile checkboxes with git?
# Usage: tests/resume-eval/run.sh <skill.md> <label> [runs] [out-dir]
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
skill="$1"; label="$2"; runs="${3:-3}"
out="${4:-/tmp/bearpaws-tests/resume-eval/$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$out"
for i in $(seq 1 "$runs"); do
  (
    work="$out/$label-$i"
    "$HERE/setup.sh" "$work"
    prompt="Follow this skill:

$(cat "$skill")

$(if [ "${SUMMARY:-0}" = 1 ]; then echo "Summary of the previous session (written before context compaction): Executing docs/plan.md. Tasks 1 and 2 are complete and committed. Next: Task 3, then Task 4."; echo; fi)The previous session executing docs/plan.md was interrupted partway through. Resume executing the plan in this repository and finish it.

You are running non-interactively and no human will reply. Make reasonable decisions yourself and finish in this session. Do not push."
    (cd "$work" && env -u CLAUDECODE claude -p "$prompt" --model "${BENCH_MODEL:-sonnet}" \
      --setting-sources project,local --strict-mcp-config --permission-mode bypassPermissions \
      --max-budget-usd 3 --no-session-persistence --output-format json \
      > "$out/$label-$i.json" 2>/dev/null) || true
    python3 - "$work" "$out/$label-$i.json" "$label" "$i" >> "$out/scores.jsonl" <<'PY'
import json, os, subprocess, sys
work, path, label, run = sys.argv[1:]
try:
    d = json.load(open(path))
except Exception:
    d = {}
def commits(p):
    return int(subprocess.check_output(["git", "rev-list", "--count", "HEAD", "--", p], cwd=work, text=True))
text = d.get("result") or ""
print(json.dumps({
    "label": label, "run": int(run), "cost": round(d.get("total_cost_usd") or 0, 4),
    "task2_done": os.path.exists(os.path.join(work, "src/two.py")),
    "task4_done": os.path.exists(os.path.join(work, "src/four.py")),
    "task3_not_redone": commits("src/three.py") == 1,
    "plan_boxes_all_checked": open(os.path.join(work, "docs/plan.md")).read().count("- [x]") == 4,
    "noticed_mismatch": any(w in text.lower() for w in ["mismatch", "discrepan", "not actually", "wasn't implemented", "was not implemented", "already implemented", "already committed", "already done", "marked complete but", "checked but"]),
}))
PY
  ) &
done
wait
python3 - "$out/scores.jsonl" <<'PY'
import json, sys
from collections import defaultdict
g = defaultdict(list)
for l in open(sys.argv[1]):
    r = json.loads(l); g[r["label"]].append(r)
for label, rows in g.items():
    keys = ["task2_done", "task4_done", "task3_not_redone", "plan_boxes_all_checked", "noticed_mismatch"]
    print(label, {k: f"{sum(r[k] for r in rows)}/{len(rows)}" for k in keys}, f"mean ${sum(r['cost'] for r in rows)/len(rows):.3f}")
PY
