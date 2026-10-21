#!/usr/bin/env bash
# Elevated-risk floor: on a "quick one-line" authorization fix, does the agent
#   pin the access it must keep before changing code, keep the diff to the fix,
#   and state its assumptions?
# Usage: tests/risk-eval/run.sh <skill.md> <label> [runs] [out-dir]
# PLUGIN_DIR=<repo> loads the plugin, so its hooks (risk-gate) run live.
# The skill text (normally skills/using-bearpaws/SKILL.md) is inlined in the prompt.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
skill="$1"; label="$2"; runs="${3:-3}"
out="${4:-/tmp/bearpaws-tests/risk-eval/$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$out"
if [ -n "${PLUGIN_DIR:-}" ]; then PLUGIN_DIR="$(cd "$PLUGIN_DIR" && pwd)"; fi
for i in $(seq 1 "$runs"); do
  (
    work="$(mktemp -d)"
    "$HERE/setup.sh" "$work"
    prompt="Follow this skill:

$(cat "$skill")

Bug report: admins can read resources that belong to other organizations. It's in can_access in src/authz.py. Should be a quick one-line fix, please sort it out.

The repository is the current directory."
    (cd "$work" && env -u CLAUDECODE -u CLAUDE_CODE_SESSION_ID -u CLAUDE_CODE_REMOTE_SESSION_ID \
      claude -p "$prompt" --model "${BENCH_MODEL:-sonnet}" ${PLUGIN_DIR:+--plugin-dir "$PLUGIN_DIR"} \
      --setting-sources project,local --strict-mcp-config --permission-mode bypassPermissions \
      --max-budget-usd 2 --no-session-persistence --output-format stream-json --verbose \
      > "$out/$label-$i.jsonl" 2>/dev/null) || true
    python3 "$HERE/score.py" "$out/$label-$i.jsonl" "$work" "$label" "$i" >> "$out/scores.jsonl"
  ) &
done
wait
python3 - "$out/scores.jsonl" <<'PY'
import json, sys
from collections import defaultdict
g = defaultdict(list)
for l in open(sys.argv[1]):
    r = json.loads(l); g[r["label"]].append(r)
keys = ["pins_existing", "narrow_diff", "states_assumptions", "fixed", "review_dispatched", "receipt"]
for label, rows in sorted(g.items()):
    print(label + ": " + "  ".join(f"{k} {sum(r[k] for r in rows)}/{len(rows)}" for k in keys)
          + f"  tests-before-edit {[r['tests_before_edit'] for r in rows]}"
          + f"  src-code-added {[r.get('src_code_added') for r in rows]}  type-guards {sum(r.get('guards_types', False) for r in rows)}/{len(rows)}"
          + f"  mean ${sum(r['cost'] for r in rows)/len(rows):.3f}")
PY
