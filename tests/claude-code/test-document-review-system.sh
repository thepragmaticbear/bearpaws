#!/usr/bin/env bash
# Integration Test: Document Review System
# Actually runs the brainstorming builder check and verifies it catches open questions
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

echo "========================================"
echo " Integration Test: Document Review System"
echo "========================================"
echo ""
echo "This test verifies the document review system by:"
echo "  1. Creating a spec with intentional errors"
echo "  2. Running the builder check (skills/brainstorming/builder-check-prompt.md)"
echo "  3. Verifying the builder raises the open questions"
echo ""

# Create test project
TEST_PROJECT=$(create_test_project)
echo "Test project: $TEST_PROJECT"

# Trap to cleanup
trap "cleanup_test_project $TEST_PROJECT" EXIT

cd "$TEST_PROJECT"

# Create directory structure
mkdir -p docs/bearpaws/specs

# Create a spec document WITH INTENTIONAL GAPS for the builder to catch
cat > docs/bearpaws/specs/test-feature-design.md <<'EOF'
# Test Feature Design

## Overview

This is a test feature that does something useful.

## Requirements

1. The feature should work correctly
2. It should be fast
3. TODO: Add more requirements here

## Architecture

The feature will use a simple architecture with:
- A frontend component
- A backend service
- Error handling will be specified later once we understand the failure modes better

## Data Flow

Data flows from the frontend to the backend.

## Testing Strategy

Tests will be written to cover the main functionality.
EOF

# Initialize git repo
git init --quiet
git config user.email "test@test.com"
git config user.name "Test User"
git add .
git commit -m "Initial commit with test spec" --quiet

echo ""
echo "Created test spec with intentional errors:"
echo "  - TODO placeholder in Requirements section"
echo "  - 'specified later' deferral in Architecture section"
echo ""
echo "Running builder check..."
echo ""

# Run Claude to review the spec
OUTPUT_FILE="$TEST_PROJECT/claude-output.txt"

PROMPT="You are testing the brainstorming builder check.

Read the builder-check-prompt.md template in skills/brainstorming/ and act as the builder it describes.

The document is $TEST_PROJECT/docs/bearpaws/specs/test-feature-design.md.

Output your questions in the format specified in the template."

# Portable timeout: prefer GNU timeout (Linux) → gtimeout (macOS coreutils) → no-op fallback
portable_timeout() {
    local duration=$1
    shift
    if command -v timeout >/dev/null 2>&1; then
        timeout "$duration" "$@"
    elif command -v gtimeout >/dev/null 2>&1; then
        gtimeout "$duration" "$@"
    else
        "$@"
    fi
}

echo "================================================================================"
cd "$SCRIPT_DIR/../.." && portable_timeout 120 claude -p "$PROMPT" --plugin-dir "$(cd "$SCRIPT_DIR/../.." && pwd)" --permission-mode bypassPermissions 2>&1 | tee "$OUTPUT_FILE" || {
    echo ""
    echo "================================================================================"
    echo "EXECUTION FAILED (exit code: $?)"
    exit 1
}
echo "================================================================================"

echo ""
echo "Analyzing builder output..."
echo ""

# Verification tests
FAILED=0

echo "=== Verification Tests ==="
echo ""

# Test 1: Builder asked about the missing requirements (the TODO)
echo "Test 1: Builder raised the missing requirements..."
if grep -qi "requirement" "$OUTPUT_FILE"; then
    echo "  [PASS] Builder raised the missing requirements"
else
    echo "  [FAIL] Builder did not raise the missing requirements"
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 2: Builder raised the "specified later" deferral
echo "Test 2: Builder raised 'specified later' deferral..."
if grep -qi "specified later\|later\|defer\|incomplete\|error handling" "$OUTPUT_FILE"; then
    echo "  [PASS] Builder raised the deferred content"
else
    echo "  [FAIL] Builder did not raise the deferred content"
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 3: Builder output uses the template's numbered entries ("1. [question] — [why]")
echo "Test 3: Builder output format..."
if grep -Eq '^[[:space:]*]*[0-9]+\.[[:space:]].*\?' "$OUTPUT_FILE"; then
    echo "  [PASS] Builder lists numbered questions"
else
    echo "  [FAIL] Builder lists no numbered questions"
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 4: Builder did NOT clear the spec
echo "Test 4: Builder verdict..."
if grep -qi "nothing important left" "$OUTPUT_FILE"; then
    echo "  [FAIL] Builder said nothing important left for a spec with gaps"
    FAILED=$((FAILED + 1))
else
    echo "  [PASS] Builder did not clear the spec"
fi
echo ""

# Summary
echo "========================================"
echo " Test Summary"
echo "========================================"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "STATUS: PASSED"
    echo "All verification tests passed!"
    echo ""
    echo "The builder check correctly:"
    echo "  ✓ Raised the missing requirements"
    echo "  ✓ Found 'specified later' deferral"
    echo "  ✓ Listed numbered questions"
    echo "  ✓ Did not clear a spec with gaps"
    exit 0
else
    echo "STATUS: FAILED"
    echo "Failed $FAILED verification tests"
    echo ""
    echo "Output saved to: $OUTPUT_FILE"
    echo ""
    echo "Review the output to see what went wrong."
    exit 1
fi
