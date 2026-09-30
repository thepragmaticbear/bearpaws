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
#   label=/dir   any plugin directory under a custom label (e.g. to compare two versions)
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
ALLOW_UNISOLATED=false
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
        --allow-unisolated) ALLOW_UNISOLATED=true; shift ;;
        -h|--help) sed -n 2,15p "$0"; exit 0 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

CHECKER_ISOLATION=macos_seatbelt
if [[ "$ALLOW_UNISOLATED" == true ]]; then
    CHECKER_ISOLATION=integrity_only
elif [[ "$(uname -s)" != Darwin || ! -x /usr/bin/sandbox-exec ]]; then
    echo "Checker isolation unavailable; use --allow-unisolated for integrity-only runs." >&2
    exit 1
fi

# One claude -p session; appends to <rdir>/stream.jsonl. Uses plugin_args from the caller.
session() {
    local work="$1" prompt="$2" rdir="$3"; shift 3
    (set -o pipefail
     cd "$work" || exit 1
     ${isolation_args[@]+"${isolation_args[@]}"} env -u CLAUDECODE claude -p "$prompt" \
        --model "$MODEL" \
        --setting-sources project,local \
        --strict-mcp-config \
        --permission-mode bypassPermissions \
        --max-budget-usd "$BUDGET" \
        --no-session-persistence \
        --output-format stream-json --verbose \
        ${plugin_args[@]+"${plugin_args[@]}"} "$@" \
        2> >(cat >> "$rdir/stderr.txt") | cat >> "$rdir/stream.jsonl")
}

run_one() {
    local scenario="$1" arm="$2" run="$3"
    # An arm may be label=/plugin/dir to compare any two plugin checkouts.
    local arm_dir=""
    if [[ "$arm" == *=* ]]; then arm_dir="${arm#*=}"; arm="${arm%%=*}"; fi
    local sdir="$SCRIPT_DIR/scenarios/$scenario"
    local rdir="$OUT/runs/$scenario/$arm/$run"
    local work="$rdir/work"
    mkdir -p "$(dirname "$rdir")"
    if ! mkdir "$rdir"; then
        echo "Refusing existing run directory: $rdir" >&2
        return 1
    fi
    cp -R "$sdir/repo" "$work"
    (cd "$work" && git init -q && git add -A && git -c commit.gpgsign=false -c user.name=bench -c user.email=bench@example.com commit -qm "initial")
    # Optional scenarios/<name>/setup.sh seeds extra history (e.g. an interrupted plan).
    [ -x "$sdir/setup.sh" ] && (cd "$work" && "$sdir/setup.sh")

    local plugin_args=()
    if [ -n "$arm_dir" ]; then
        plugin_args=(--plugin-dir "$arm_dir")
    else
        case "$arm" in
            baseline) ;;
            bearpaws) plugin_args=(--plugin-dir "$REPO_ROOT") ;;
            superpowers)
                [ -n "${SUPERPOWERS_DIR:-}" ] || { echo "SUPERPOWERS_DIR not set" >&2; return 1; }
                plugin_args=(--plugin-dir "$SUPERPOWERS_DIR") ;;
            *) echo "Unknown arm: $arm" >&2; return 1 ;;
        esac
    fi

    # Snapshot before the agent starts; digest stays in the controller's shell.
    # This detects persistent tampering; bypassPermissions is not OS isolation.
    local hidden fixture_before fixture_after fixture_integrity=false
    hidden="$(mktemp -d)"
    cp "$sdir/accept.py" "$hidden/accept_hidden.py"
    chmod 400 "$hidden/accept_hidden.py"
    fixture_before=$(python3 "$SCRIPT_DIR/summarize.py" --fingerprint "$sdir" "$hidden/accept_hidden.py")
    local isolation_args=()
    if [[ "$CHECKER_ISOLATION" == macos_seatbelt ]]; then
        isolation_args=(/usr/bin/sandbox-exec -p "$(python3 "$SCRIPT_DIR/summarize.py" --sandbox-profile "$SCRIPT_DIR" "$hidden" "$OUT" "$work")")
    fi
    local start end cli_exit_code=0
    start=$(date +%s)
    session "$work" "$(cat "$sdir/prompt.txt")$SUFFIX" "$rdir" || cli_exit_code=$?
    end=$(date +%s)

    # Load the exact snapshot path: work/accept_hidden.py must not shadow it.
    local accept_ok=false
    if (cd "$work" && python3 -I -c '
import importlib.util, sys, unittest
sys.path.insert(0, sys.argv[2])
spec = importlib.util.spec_from_file_location("accept_hidden", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
result = unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromModule(module))
sys.exit(not result.wasSuccessful() or result.testsRun == 0 or bool(result.skipped) or bool(result.expectedFailures))
' "$hidden/accept_hidden.py" "$work" > "$rdir/accept.txt" 2>&1); then
        accept_ok=true
    fi

    # Regression check: the repo's own (visible) suite must still pass at the end.
    local visible_ok=false
    if (cd "$work" && python3 -I -c '
import os, sys, unittest
sys.path.insert(0, os.getcwd())
result = unittest.TextTestRunner().run(unittest.defaultTestLoader.discover("tests", top_level_dir="."))
sys.exit(not result.wasSuccessful() or result.testsRun == 0)
' > "$rdir/visible.txt" 2>&1); then
        visible_ok=true
    fi
    fixture_after=$(python3 "$SCRIPT_DIR/summarize.py" --fingerprint "$sdir" "$hidden/accept_hidden.py")
    [[ "$fixture_before" == "$fixture_after" ]] && fixture_integrity=true
    rm -rf "$hidden"

    # Existing test files that lost lines (deleted or edited assertions). Added tests are fine.
    local tests_touched
    tests_touched=$(cd "$work" && git diff --numstat "$(git rev-list --max-parents=0 HEAD)" -- tests | awk '$2 > 0' | wc -l | tr -d ' ')

    python3 "$SCRIPT_DIR/summarize.py" --record \
        --scenario "$scenario" --arm "$arm" --run "$run" \
        --stream "$rdir/stream.jsonl" --accepted "$accept_ok" \
        --accept-log "$rdir/accept.txt" --visible-ok "$visible_ok" \
        --cli-exit-code "$cli_exit_code" --fixture-integrity "$fixture_integrity" \
        --checker-isolation "$CHECKER_ISOLATION" \
        --elevated "$([ -f "$sdir/elevated" ] && echo true || echo false)" \
        --seconds $((end - start)) --tests-touched "$tests_touched" \
        >> "$OUT/results.jsonl"
    echo "$scenario/$arm/$run accepted=$accept_ok"
}
export -f run_one session
export SCRIPT_DIR REPO_ROOT OUT MODEL BUDGET SUFFIX CHECKER_ISOLATION

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
