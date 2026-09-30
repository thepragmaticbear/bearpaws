#!/usr/bin/env bash
# Full-session benchmark: cost per accepted task, per arm.
#
# Usage: tests/benchmark/run.sh [--runs N] [--arms "baseline bearpaws"] [--scenarios "a b"]
#                               [--model MODEL] [--budget USD] [--jobs N] [--out DIR] [--interactive]
#
# Arms:
#   baseline     no plugins
#   bearpaws     this checkout via --plugin-dir
#   superpowers  requires SUPERPOWERS_DIR=/path/to/superpowers checkout
#
# Each run copies scenarios/<name>/repo into a fresh git repo, runs `claude -p`
# with the scenario prompt, then runs the held-out scenarios/<name>/accept.py
# (never copied into the repo) against the result. Results append to
# <out>/results.jsonl; summarize with tests/benchmark/summarize.py.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

RUNS=3
ARMS="baseline bearpaws"
SCENARIOS="$(ls "$SCRIPT_DIR/scenarios")"
MODEL="${BENCH_MODEL:-sonnet}"
BUDGET=5
JOBS=3
OUT="/tmp/bearpaws-tests/benchmark/$(date +%Y%m%d-%H%M%S)"

# The same suffix goes to every arm: headless runs have nobody to answer questions.
# --interactive drops it to measure how often an arm stops to ask instead of finishing.
SUFFIX="

You are running non-interactively and no human will reply. Make reasonable decisions yourself, treat any approval you would normally ask for as granted, and finish the task in this session. Do not push."

while [[ $# -gt 0 ]]; do
    case $1 in
        --runs) RUNS="$2"; shift 2 ;;
        --arms) ARMS="$2"; shift 2 ;;
        --scenarios) SCENARIOS="$2"; shift 2 ;;
        --model) MODEL="$2"; shift 2 ;;
        --budget) BUDGET="$2"; shift 2 ;;
        --jobs) JOBS="$2"; shift 2 ;;
        --out) OUT="$2"; shift 2 ;;
        --interactive) SUFFIX=""; shift ;;
        -h|--help) sed -n 2,15p "$0"; exit 0 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done


run_one() {
    local scenario="$1" arm="$2" run="$3"
    local sdir="$SCRIPT_DIR/scenarios/$scenario"
    local rdir="$OUT/runs/$scenario/$arm/$run"
    local work="$rdir/work"
    mkdir -p "$rdir"
    cp -R "$sdir/repo" "$work"
    (cd "$work" && git init -q && git add -A && git -c user.name=bench -c user.email=bench@example.com commit -qm "initial")

    local plugin_args=()
    case "$arm" in
        baseline) ;;
        bearpaws) plugin_args=(--plugin-dir "$REPO_ROOT") ;;
        superpowers)
            [ -n "${SUPERPOWERS_DIR:-}" ] || { echo "SUPERPOWERS_DIR not set" >&2; return 1; }
            plugin_args=(--plugin-dir "$SUPERPOWERS_DIR") ;;
        *) echo "Unknown arm: $arm" >&2; return 1 ;;
    esac

    local prompt
    prompt="$(cat "$sdir/prompt.txt")$SUFFIX"
    local start end
    start=$(date +%s)
    (cd "$work" && env -u CLAUDECODE claude -p "$prompt" \
        --model "$MODEL" \
        --setting-sources project,local \
        --strict-mcp-config \
        --permission-mode bypassPermissions \
        --max-budget-usd "$BUDGET" \
        --no-session-persistence \
        --output-format stream-json --verbose \
        ${plugin_args[@]+"${plugin_args[@]}"} \
        > "$rdir/stream.jsonl" 2> "$rdir/stderr.txt") || true
    end=$(date +%s)

    # Held-out acceptance: imported from outside the repo so the agent never saw it.
    local hidden accept_ok=false
    hidden="$(mktemp -d)"
    cp "$sdir/accept.py" "$hidden/accept_hidden.py"
    if (cd "$work" && PYTHONPATH=".:$hidden" python3 -m unittest accept_hidden > "$rdir/accept.txt" 2>&1); then
        accept_ok=true
    fi
    rm -rf "$hidden"

    # Existing test files that lost lines (deleted or edited assertions). Added tests are fine.
    local tests_touched
    tests_touched=$(cd "$work" && git diff --numstat "$(git rev-list --max-parents=0 HEAD)" -- tests | awk '$2 > 0' | wc -l | tr -d ' ')

    python3 "$SCRIPT_DIR/summarize.py" --record \
        --scenario "$scenario" --arm "$arm" --run "$run" \
        --stream "$rdir/stream.jsonl" --accepted "$accept_ok" \
        --seconds $((end - start)) --tests-touched "$tests_touched" \
        >> "$OUT/results.jsonl"
    echo "$scenario/$arm/$run accepted=$accept_ok"
}
export -f run_one
export SCRIPT_DIR REPO_ROOT OUT MODEL BUDGET SUFFIX

mkdir -p "$OUT"
echo "Output: $OUT (model=$MODEL runs=$RUNS arms=[$ARMS])"

# Interleave arms within each run index so drift over time affects all arms alike.
jobs_list=()
for run in $(seq 1 "$RUNS"); do
    for scenario in $SCENARIOS; do
        for arm in $ARMS; do
            jobs_list+=("$scenario $arm $run")
        done
    done
done
printf '%s\n' "${jobs_list[@]}" | xargs -P "$JOBS" -L 1 bash -c 'run_one "$0" "$1" "$2"'

python3 "$SCRIPT_DIR/summarize.py" "$OUT/results.jsonl"
