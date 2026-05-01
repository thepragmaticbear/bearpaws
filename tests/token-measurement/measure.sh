#!/usr/bin/env bash
# Measure bootstrap and skill-body byte counts. Output JSON for diff-friendly tracking.
#
# Usage: tests/token-measurement/measure.sh
# Output: JSON to stdout. Run from repo root.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

# 1. Bootstrap: the actual additionalContext payload SessionStart injects.
bootstrap_bytes=$(CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash hooks/session-start \
  | python3 -c "import json,sys; print(len(json.load(sys.stdin)['hookSpecificOutput']['additionalContext']))")

# 2. Per-skill SKILL.md bytes.
declare -a skill_lines=()
total_skill_md=0
for f in skills/*/SKILL.md; do
  bytes=$(wc -c < "$f" | tr -d ' ')
  total_skill_md=$((total_skill_md + bytes))
  name=$(basename "$(dirname "$f")")
  skill_lines+=("    \"${name}\": ${bytes}")
done
skills_json=$(printf '%s,\n' "${skill_lines[@]}" | sed '$ s/,$//')

# 3. Total skills/ payload (SKILL.md + sibling content).
total_payload=$(find skills -type f \( -name "*.md" -o -name "*.html" -o -name "*.sh" -o -name "*.js" -o -name "*.json" -o -name "*.txt" \) -exec cat {} + 2>/dev/null | wc -c | tr -d ' ')

cat <<JSON
{
  "bootstrap_additional_context_bytes": ${bootstrap_bytes},
  "skills_skill_md_total_bytes": ${total_skill_md},
  "skills_full_payload_bytes": ${total_payload},
  "per_skill_skill_md_bytes": {
${skills_json}
  }
}
JSON
