#!/usr/bin/env bash
# Model-free path checks for the eval runners (tests/*-eval/run.sh): each one, run from an
# unrelated cwd with a relative out-dir, must write its transcript under that cwd. The runners
# cd into a work dir before claude runs, so a relative out-dir used there lands nowhere.
# A stub claude stands in for the model. tests/benchmark/test_integrity.py covers tests/benchmark/run.sh.
# Usage: tests/eval-runners/run-path-tests.sh
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT
# The runners' own mktemp work dirs land inside TMP_ROOT, so the trap cleans them too.
# macOS mktemp -d ignores TMPDIR, so a shim on the stub PATH passes it a template.
export TMPDIR="$TMP_ROOT"
mkdir -p "$TMP_ROOT/bin"
real_mktemp="$(command -v mktemp)"
printf '#!/bin/sh
if [ "$*" = "-d" ]; then exec %s -d "$TMPDIR/tmp.XXXXXXXXXX"; fi
exec %s "$@"
' "$real_mktemp" "$real_mktemp" > "$TMP_ROOT/bin/mktemp"
chmod +x "$TMP_ROOT/bin/mktemp"
printf '#!/bin/sh\necho %s\n' "'{\"type\":\"result\",\"result\":\"stub\",\"total_cost_usd\":0}'" > "$TMP_ROOT/bin/claude"
chmod +x "$TMP_ROOT/bin/claude"
failed=0

# check <name> <transcript under out/> <runner args...>: run from a fresh cwd with out-dir "out".
check() {
  local name="$1" want="$2" cwd; shift 2
  cwd="$(mktemp -d "$TMP_ROOT/cwd.XXXXXX")"
  # Unset caller env that changes runner behaviour, so only the defaults are checked.
  (unset PLUGIN_DIR SKILL_ROOT FIXTURE AGENT_PROMPT PRESSURE SUMMARY CLEAN DESIGN BENCH_MODEL
   cd "$cwd" && PATH="$TMP_ROOT/bin:$PATH" VARIANTS=skip "$@" >"$cwd/log" 2>&1)
  if [ -s "$cwd/out/$want" ]; then echo "PASS: $name writes out/$want under the caller's cwd"
  else echo "FAIL: $name did not write out/$want under the caller's cwd"; tail -3 "$cwd/log" | sed 's/^/    /'; failed=$((failed + 1)); fi
}

skill="$ROOT/skills/using-bearpaws/SKILL.md"
check builder-eval      lbl-elevated-1.jsonl "$ROOT/tests/builder-eval/run.sh" "$ROOT/skills/brainstorming/SKILL.md" lbl 1 out
check context-eval      lbl-1.json      "$ROOT/tests/context-eval/run.sh" lbl 1 out
check diagnose-eval    lbl-1.jsonl     "$ROOT/tests/diagnose-eval/run.sh" none lbl 1 out
check drift-eval        lbl-1.json      "$ROOT/tests/drift-eval/run.sh" "$skill" lbl 1 out
check fixloop-eval      lbl-1.jsonl     "$ROOT/tests/fixloop-eval/run.sh" "$ROOT/skills/subagent-driven-development/SKILL.md" lbl 1 out
check resume-eval       lbl-1.json      "$ROOT/tests/resume-eval/run.sh" "$skill" lbl 1 out
check reuse-eval        lbl-1.jsonl     "$ROOT/tests/reuse-eval/run.sh" lbl 1 out
check review-eval       lbl-1.jsonl     "$ROOT/tests/review-eval/run.sh" "$ROOT/skills/requesting-code-review/code-reviewer.md" lbl 1 out
check risk-eval         lbl-1.jsonl     "$ROOT/tests/risk-eval/run.sh" "$skill" lbl 1 out
check verification-eval lbl-skip-1.json "$ROOT/tests/verification-eval/run.sh" "$skill" lbl 1 out

[ "$failed" -eq 0 ] && echo "All eval-runner path checks passed" || { echo "$failed eval-runner path check(s) failed"; exit 1; }
