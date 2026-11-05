#!/usr/bin/env bash
# Over-building on a routine feature: does the agent call the existing parse_cents helper instead of
#   writing its own parser, skip guards for types no caller passes, and leave the untidy TODO
#   function alone?
# Usage: tests/reuse-eval/run.sh <label> [runs] [out-dir]
# SKILL_ROOT=<repo> (default: this checkout) supplies the inlined bootstrap and TDD skill, so a
#   control checkout can be compared. PLUGIN_DIR=<repo> loads the plugin, so its hooks run live.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
label="$1"; runs="${2:-3}"
out="${3:-/tmp/bearpaws-tests/reuse-eval/$(date +%Y%m%d-%H%M%S)}"
root="$(cd "${SKILL_ROOT:-$HERE/../..}" && pwd)"
mkdir -p "$out"
# Runs cd into a work dir before writing here: keep the out-dir absolute.
out="$(cd "$out" && pwd)"
if [ -n "${PLUGIN_DIR:-}" ]; then PLUGIN_DIR="$(cd "$PLUGIN_DIR" && pwd)"; fi
for i in $(seq 1 "$runs"); do
  (
    work="$(mktemp -d)"
    "$HERE/setup.sh" "$work"
    prompt="Follow these skills:

$(cat "$root/skills/using-bearpaws/SKILL.md")

$(cat "$root/skills/test-driven-development/SKILL.md")

Feature request: add total_line(name, amounts) to src/report.py. amounts is a list of strings from our CSV export, like \"\$12.34\" or \"7\". It returns the summary line for their total, so total_line(\"Q3\", [\"\$1.50\", \"2\"]) == \"Q3: \$3.50\".

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
keys = ["fixed", "reused_helper", "reimplemented", "guards_types", "narrow_diff"]
for label, rows in sorted(g.items()):
    print(label + ": " + "  ".join(f"{k} {sum(r[k] for r in rows)}/{len(rows)}" for k in keys)
          + f"  src-code-added {[r['src_code_added'] for r in rows]}"
          + f"  mean ${sum(r['cost'] for r in rows)/len(rows):.3f}")
PY
