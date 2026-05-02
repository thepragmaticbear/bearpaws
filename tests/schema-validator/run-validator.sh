#!/usr/bin/env bash
# Schema validator: greps skills/ for unknown tags, fails on violations.
#
# Whitelist source of truth: skills/writing-skills/SKILL.md "## XML schema" section.
# Run from repo root.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

# Whitelist (must match writing-skills/SKILL.md "## XML schema" §Tag whitelist)
WHITELIST=(
  "skill" "purpose" "triggers" "rules" "rule" "process" "step"
  "flow" "example" "antipattern" "warning" "gate" "subagent-stop"
  "include" "see" "placeholder"
)

violations=0

# Find all opening tags in skill bodies, strip self-closing and attributes,
# compare against whitelist.
while IFS= read -r line; do
  file=$(echo "$line" | cut -d: -f1)
  lineno=$(echo "$line" | cut -d: -f2)
  tag=$(echo "$line" | grep -oE '<[a-zA-Z][a-zA-Z0-9_-]*' | head -1 | tr -d '<')
  [[ -z "$tag" ]] && continue
  if ! [[ " ${WHITELIST[*]} " =~ \ ${tag}\  ]]; then
    echo "VIOLATION: ${file}:${lineno}: unknown tag <${tag}>"
    violations=$((violations + 1))
  fi
done < <(grep -rEn '<[a-zA-Z][a-zA-Z0-9_-]*' skills/*/SKILL.md 2>/dev/null \
         || true)

if [[ $violations -gt 0 ]]; then
  echo ""
  echo "FAIL: ${violations} schema violation(s)"
  echo "Whitelist defined in skills/writing-skills/SKILL.md '## XML schema'"
  exit 1
fi

echo "OK: no schema violations in skills/"

# Adversarial gate check: ensure code-reviewer agent and dispatching skill stay aligned.
# Both files must reference the same four gate names. A reformat that strips a gate
# marker, or a rename in one file without the other, fails here.
GATE_NAMES=(
  "Failure Mode Enumeration"
  "What would have to be true for this to be wrong"
  "What I didn't check and why"
  "Break Attempts"
)

gate_violations=0
agent_file="agents/code-reviewer.md"
skill_file="skills/requesting-code-review/SKILL.md"
template_file="skills/requesting-code-review/code-reviewer.md"

# Section-header pattern: matches "[GATE] FollowedByCapitalizedName" but NOT the
# preamble "Sections marked [GATE] are adversarial checkpoints" (lowercase "are").
GATE_SECTION_PATTERN='\[GATE\] [A-Z]'

# Agent file must contain all four gate names AND four gate-section markers
if [[ -f "$agent_file" ]]; then
  marker_count=$(grep -cE "$GATE_SECTION_PATTERN" "$agent_file" || true)
  if [[ "$marker_count" -ne 4 ]]; then
    echo "GATE VIOLATION: ${agent_file}: expected 4 gate-section markers, found ${marker_count}"
    gate_violations=$((gate_violations + 1))
  fi
  for name in "${GATE_NAMES[@]}"; do
    if ! grep -qF "$name" "$agent_file"; then
      echo "GATE VIOLATION: ${agent_file}: missing gate '${name}'"
      gate_violations=$((gate_violations + 1))
    fi
  done
else
  echo "GATE VIOLATION: ${agent_file}: file not found"
  gate_violations=$((gate_violations + 1))
fi

# Dispatching skill must reference all four gate concepts in its validation step
if [[ -f "$skill_file" ]]; then
  for name in "${GATE_NAMES[@]}"; do
    if ! grep -qF "$name" "$skill_file"; then
      echo "GATE VIOLATION: ${skill_file}: validation step missing reference to '${name}'"
      gate_violations=$((gate_violations + 1))
    fi
  done
else
  echo "GATE VIOLATION: ${skill_file}: file not found"
  gate_violations=$((gate_violations + 1))
fi

# User-message template must contain all four gate-section markers
if [[ -f "$template_file" ]]; then
  template_marker_count=$(grep -cE "$GATE_SECTION_PATTERN" "$template_file" || true)
  if [[ "$template_marker_count" -ne 4 ]]; then
    echo "GATE VIOLATION: ${template_file}: expected 4 gate-section markers, found ${template_marker_count}"
    gate_violations=$((gate_violations + 1))
  fi
  for name in "${GATE_NAMES[@]}"; do
    if ! grep -qF "$name" "$template_file"; then
      echo "GATE VIOLATION: ${template_file}: missing gate '${name}'"
      gate_violations=$((gate_violations + 1))
    fi
  done
else
  echo "GATE VIOLATION: ${template_file}: file not found"
  gate_violations=$((gate_violations + 1))
fi

if [[ $gate_violations -gt 0 ]]; then
  echo ""
  echo "FAIL: ${gate_violations} adversarial gate violation(s)"
  echo "Gate names defined in tests/schema-validator/run-validator.sh"
  exit 1
fi

echo "OK: adversarial gates aligned across agent, skill, and template"
exit 0
