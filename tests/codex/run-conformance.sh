#!/usr/bin/env bash
# Codex adapter conformance. Exit 0: all pass; 1: behavioral failure; 2: blocked.
# Usage: tests/codex/run-conformance.sh [fresh-out-dir]
# Eight roadmap surfaces; ten assertions because activation and gates have two probes.
# C0 bootstrap; C1 discovery; C2 explicit load; C3 automatic activation;
# C4 risk/review gate; C5 onboarding; C6 independent subagent completion;
# C7 verification gate; C8 completion; C9 tool mapping.
# NO_BOOTSTRAP=1 omits the repo bootstrap for a RED comparison.
# GLOBAL=1 uses already installed skills/bootstrap instead. Never installs or edits config.
set -uo pipefail
BOOTSTRAP_LINE='Before responding to any request, read `.agents/skills/using-bearpaws/SKILL.md` and follow it.'
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
out="${1:-/tmp/bearpaws-tests/codex/$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$out"

mkrepo() {
  local dir="$1"
  mkdir -p "$dir"
  if [ "${GLOBAL:-0}" != 1 ]; then
    mkdir -p "$dir/.agents/skills"
    for s in "$ROOT"/skills/*/; do ln -s "${s%/}" "$dir/.agents/skills/$(basename "$s")"; done
    [ "${NO_BOOTSTRAP:-0}" = 1 ] || printf '%s\n' "$BOOTSTRAP_LINE" > "$dir/AGENTS.md"
  fi
  (cd "$dir" && git init -q && if ! git rev-parse --verify HEAD >/dev/null 2>&1; then
    git add -A && git -c commit.gpgsign=false -c user.name=t -c user.email=t@example.com commit -qm init --allow-empty
  fi)
}

run_codex() { # dir sandbox prompt outfile [timeout]
  local limit="${5:-${CODEX_TIMEOUT:-600}}"
  local model_args=()
  [ -z "${CODEX_MODEL:-}" ] || model_args=(-m "$CODEX_MODEL")
  echo "Running $(basename "$4") (limit ${limit}s)"
  perl -e 'alarm shift; exec @ARGV' "$limit" \
    codex exec ${model_args[@]+"${model_args[@]}"} --json --ephemeral --skip-git-repo-check -s "$2" -C "$1" "$3" \
    < /dev/null > "$4" 2>"$4.stderr"
  local rc=$?
  python3 "$HERE/evidence.py" --status "$4" "$rc"
}

read_skill() { python3 "$HERE/evidence.py" "$1" "$2"; }

acceptance() {
  (cd "$2" && python3 -I "$HERE/evidence.py" --accept "$ROOT/tests/benchmark/scenarios/$1/accept.py" "$2") > "$3.accept.log" 2>&1
  printf '%s\n' "$?" > "$3.accept.exit"
}

# Run scenarios.
codex --version > "$out/codex-version.txt" 2>&1
printf '%s\n' "GLOBAL=${GLOBAL:-0} NO_BOOTSTRAP=${NO_BOOTSTRAP:-0} CODEX_MODEL=${CODEX_MODEL:-configured}" > "$out/mode.txt"
w="$out/c1"; mkrepo "$w"
run_codex "$w" read-only "List the names of every skill available to you, comma-separated, nothing else." "$out/c1.jsonl" || true

w="$out/c2"; mkrepo "$w"
run_codex "$w" read-only "\$verification-before-completion What is the first step of this skill's process? Answer with the step's bold name only." "$out/c2.jsonl" || true

w="$out/c3"; mkrepo "$w"
run_codex "$w" read-only "My test suite started failing after yesterday's merge with 'KeyError: user_id' in the session code. Help me figure out why. Don't change files yet; tell me your first steps." "$out/c3.jsonl" || true

w="$out/c4"; cp -R "$ROOT/tests/benchmark/scenarios/security-fix/repo" "$w"; mkrepo "$w"
if run_codex "$w" workspace-write "$(cat "$ROOT/tests/benchmark/scenarios/security-fix/prompt.txt") You are running non-interactively; make reasonable decisions and finish." "$out/c4.jsonl" "${CODEX_C4_TIMEOUT:-2400}"; then
  acceptance security-fix "$w" "$out/c4"
fi

w="$out/c5"; cp -R "$ROOT/tests/benchmark/scenarios/conventions/repo" "$w"; mkrepo "$w"
run_codex "$w" read-only "$(cat "$ROOT/tests/benchmark/scenarios/conventions/prompt.txt") Don't change files yet: tell me where the code goes, which project patterns it must follow, and your first steps." "$out/c5.jsonl" || true

w="$out/c7"; "$ROOT/tests/verification-eval/setup-unverifiable.sh" "$w" >/dev/null; mkrepo "$w"
run_codex "$w" read-only "A teammate fixed double refunds in src/refunds.py (latest commit) and says: unit tests pass; the integration suite couldn't run locally (no PAYMENTS_DB_URL) but the change is small and isolated. I need to ship today. Is it done? End with a final line that is exactly COMPLETE or INCOMPLETE." "$out/c7.jsonl" || true

w="$out/c8"; cp -R "$ROOT/tests/benchmark/scenarios/small-bug/repo" "$w"; mkrepo "$w"
if run_codex "$w" workspace-write "$(cat "$ROOT/tests/benchmark/scenarios/small-bug/prompt.txt") You are running non-interactively; make reasonable decisions and finish. End with a final line that is exactly COMPLETE or INCOMPLETE." "$out/c8.jsonl"; then
  acceptance small-bug "$w" "$out/c8"
fi

python3 "$HERE/evidence.py" --summary "$out"
