#!/usr/bin/env bash
# Does the controller hand onboarding's findings to implementer subagents?
# Usage: tests/context-eval/run.sh <label> [runs] [out-dir]
# Text-only: the controller writes the dispatch prompt; the score checks it carries
# the project facts found during onboarding (test command, logger, error type, test layout).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
label="$1"; runs="${2:-3}"
out="${3:-/tmp/bearpaws-tests/context-eval/$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$out"
skill="$(cat "$ROOT/skills/subagent-driven-development/SKILL.md")"
template="$(cat "$ROOT/skills/subagent-driven-development/implementer-prompt.md")"
for i in $(seq 1 "$runs"); do
  (
    prompt="You are the controller in subagent-driven development. The skill:

$skill

The implementer template (implementer-prompt.md):

$template

Earlier in this session you ran bp:onboarding-to-a-project on this repository and found:
- Python 3.12 service; run tests with \`make test\` (plain pytest misses the settings module and fails).
- Logging goes through \`app.log.get_logger(__name__)\`; print() is banned by a lint rule.
- Errors raised to clients must be \`app.errors.AppError(code, message)\`.
- Unit tests live in tests/unit/, mirroring src/ paths.

The plan's Task 2 is: \"Add a GET /health handler in src/app/routes/health.py that returns {\\\"status\\\": \\\"ok\\\"} and 503 with AppError('db_down', ...) when the database ping fails. Add unit tests.\"

Write the exact prompt you will send to the implementer subagent for Task 2. Output only that prompt."
    env -u CLAUDECODE claude -p "$prompt" --model "${BENCH_MODEL:-sonnet}" --setting-sources project,local \
      --strict-mcp-config --tools "" --no-session-persistence --output-format json > "$out/$label-$i.json" 2>/dev/null || true
    python3 - "$out/$label-$i.json" "$label" >> "$out/scores.jsonl" <<'PY'
import json, re, sys
d = json.load(open(sys.argv[1])); t = d.get("result") or ""
print(json.dumps({"label": sys.argv[2], "cost": d.get("total_cost_usd"),
  "test_cmd": "make test" in t, "logger": "get_logger" in t, "print_banned": bool(re.search(r"print", t)),
  "tests_layout": "tests/unit" in t, "chars": len(t)}))
PY
  ) &
done
wait
python3 - "$out/scores.jsonl" <<'PY'
import json, sys
rows = [json.loads(l) for l in open(sys.argv[1])]
for k in ["test_cmd", "logger", "print_banned", "tests_layout"]:
    print(f"{k:<14} {sum(r[k] for r in rows)}/{len(rows)}")
print("mean chars", sum(r["chars"] for r in rows) // len(rows))
PY
