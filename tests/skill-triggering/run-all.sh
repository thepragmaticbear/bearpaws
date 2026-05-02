#!/usr/bin/env bash
# Run all skill triggering tests
# Usage: ./run-all.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPTS_DIR="$SCRIPT_DIR/prompts"

SKILLS=(
    "onboarding-to-a-project"
    "brainstorming"
    "systematic-debugging"
    "test-driven-development"
    "writing-plans"
    "writing-skills"
    "dispatching-parallel-agents"
    "executing-plans"
    "requesting-code-review"
    "cloud-run"
    "deploying-to-cloud-run"
    "vite"
    "working-with-vite"
    "javascript-typescript"
    "writing-typescript"
    "google-cloud"
    "working-on-google-cloud"
    "google-adk"
    "building-with-adk"
)

echo "=== Running Skill Triggering Tests ==="
echo ""

PASSED=0
FAILED=0
RESULTS=()

for skill in "${SKILLS[@]}"; do
    prompt_file="$PROMPTS_DIR/${skill}.txt"

    if [ ! -f "$prompt_file" ]; then
        echo "⚠️  SKIP: No prompt file for $skill"
        continue
    fi

    echo "Testing: $skill"

    set +e
    "$SCRIPT_DIR/run-test.sh" "$skill" "$prompt_file" 3 2>&1 | tee /tmp/skill-test-$skill.log
    test_exit=${PIPESTATUS[0]}
    set -e
    if [ "$test_exit" -eq 0 ]; then
        PASSED=$((PASSED + 1))
        RESULTS+=("✅ $skill")
    else
        FAILED=$((FAILED + 1))
        RESULTS+=("❌ $skill")
    fi

    echo ""
    echo "---"
    echo ""
done

echo ""
echo "=== Summary ==="
for result in "${RESULTS[@]}"; do
    echo "  $result"
done
echo ""
echo "Passed: $PASSED"
echo "Failed: $FAILED"

if [ $FAILED -gt 0 ]; then
    exit 1
fi
