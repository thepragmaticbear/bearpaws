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
mkdir -p "$TMP_ROOT/bin"
printf '#!/bin/sh\necho %s\n' "'{\"type\":\"result\",\"result\":\"stub\",\"total_cost_usd\":0}'" > "$TMP_ROOT/bin/claude"
chmod +x "$TMP_ROOT/bin/claude"
failed=0

# check <name> <transcript under out/> <runner args...>: run from a fresh cwd with out-dir "out".
check() {
  local name="$1" want="$2" cwd; shift 2
  cwd="$(mktemp -d "$TMP_ROOT/cwd.XXXXXX")"
  (cd "$cwd" && PATH="$TMP_ROOT/bin:$PATH" VARIANTS=skip "$@" >"$cwd/log" 2>&1)
  if [ -s "$cwd/out/$want" ]; then echo "PASS: $name writes out/$want under the caller's cwd"
  else echo "FAIL: $name did not write out/$want under the caller's cwd"; tail -3 "$cwd/log" | sed 's/^/    /'; failed=$((failed + 1)); fi
}

skill="$ROOT/skills/using-bearpaws/SKILL.md"
check builder-eval      lbl-elevated-1.jsonl "$ROOT/tests/builder-eval/run.sh" "$ROOT/skills/brainstorming/SKILL.md" lbl 1 out
check context-eval      lbl-1.json      "$ROOT/tests/context-eval/run.sh" lbl 1 out
check drift-eval        lbl-1.json      "$ROOT/tests/drift-eval/run.sh" "$skill" lbl 1 out
check resume-eval       lbl-1.json      "$ROOT/tests/resume-eval/run.sh" "$skill" lbl 1 out
check reuse-eval        lbl-1.jsonl     "$ROOT/tests/reuse-eval/run.sh" lbl 1 out
check review-eval       lbl-1.jsonl     "$ROOT/tests/review-eval/run.sh" "$ROOT/skills/requesting-code-review/code-reviewer.md" lbl 1 out
check risk-eval         lbl-1.jsonl     "$ROOT/tests/risk-eval/run.sh" "$skill" lbl 1 out
check verification-eval lbl-skip-1.json "$ROOT/tests/verification-eval/run.sh" "$skill" lbl 1 out

[ "$failed" -eq 0 ] && echo "All eval-runner path checks passed" || { echo "$failed eval-runner path check(s) failed"; exit 1; }
