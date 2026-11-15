#!/usr/bin/env bash
# Measure bootstrap and skill-body UTF-8 byte counts and approximate token estimates.
# Output JSON for diff-friendly tracking.
#
# Usage: tests/token-measurement/measure.sh
# Output: JSON to stdout. Run from repo root.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

approx_tokens() {
  # Approximate ~4 UTF-8 bytes per token (half-up integer division).
  echo $(( ($1 + 2) / 4 ))
}

# 1. Bootstrap: the actual additionalContext payload SessionStart injects (UTF-8 bytes),
#    with the machine-specific plugin root in the skill-dir line normalized to /plugin-root.
bootstrap_bytes=$(CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash hooks/session-start \
  | python3 -c "import json,re,sys; ctx=json.load(sys.stdin)['hookSpecificOutput']['additionalContext']; ctx=re.sub(r'(using-bearpaws skill dir \(resolve references/\.\.\. here\): ).*', r'\1/plugin-root/skills/using-bearpaws', ctx); print(len(ctx.encode('utf-8')))")
bootstrap_tokens=$(approx_tokens "$bootstrap_bytes")

# 2. Per-skill SKILL.md UTF-8 bytes.
declare -a skill_lines=()
total_skill_md=0
for f in skills/*/SKILL.md; do
  bytes=$(wc -c < "$f" | tr -d ' ')
  total_skill_md=$((total_skill_md + bytes))
  name=$(basename "$(dirname "$f")")
  skill_lines+=("    \"${name}\": ${bytes}")
done
skills_json=$(printf '%s,\n' "${skill_lines[@]}" | sed '$ s/,$//')
total_skill_md_tokens=$(approx_tokens "$total_skill_md")

# 3. Total skills/ payload (SKILL.md + sibling content, UTF-8 bytes).
total_payload=$(find skills -type f \( -name "*.md" -o -name "*.html" -o -name "*.sh" -o -name "*.js" -o -name "*.json" -o -name "*.txt" \) -exec cat {} + 2>/dev/null | wc -c | tr -d ' ')
total_payload_tokens=$(approx_tokens "$total_payload")

# 4. Typical session: bootstrap + skills loaded in a common feature workflow
#    (onboard -> brainstorm -> plan -> TDD implement -> code review -> verify).
typical_skills=(
  onboarding-to-a-project
  brainstorming
  writing-plans
  test-driven-development
  requesting-code-review
  verification-before-completion
)
typical_bytes=$bootstrap_bytes
declare -a typical_skill_lines=()
for skill in "${typical_skills[@]}"; do
  skill_file="skills/${skill}/SKILL.md"
  [ -f "$skill_file" ] || { echo "missing typical session skill: $skill_file" >&2; exit 1; }
  sb=$(wc -c < "$skill_file" | tr -d ' ')
  typical_bytes=$((typical_bytes + sb))
  typical_skill_lines+=("    \"${skill}\"")
done
typical_skills_json=$(printf '%s,\n' "${typical_skill_lines[@]}" | sed '$ s/,$//')
typical_tokens=$(approx_tokens "$typical_bytes")

cat <<JSON
{
  "bootstrap_additional_context_bytes": ${bootstrap_bytes},
  "bootstrap_additional_context_approx_tokens": ${bootstrap_tokens},
  "skills_skill_md_total_bytes": ${total_skill_md},
  "skills_skill_md_total_approx_tokens": ${total_skill_md_tokens},
  "skills_full_payload_bytes": ${total_payload},
  "skills_full_payload_approx_tokens": ${total_payload_tokens},
  "typical_session_bytes": ${typical_bytes},
  "typical_session_approx_tokens": ${typical_tokens},
  "typical_session_skills": [
${typical_skills_json}
  ],
  "per_skill_skill_md_bytes": {
${skills_json}
  }
}
JSON
