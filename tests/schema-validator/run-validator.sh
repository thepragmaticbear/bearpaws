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
done < <(grep -rEn '<[a-zA-Z][a-zA-Z0-9_-]*' skills/*/SKILL.md skills/_shared/*.md 2>/dev/null \
         || true)

if [[ $violations -eq 0 ]]; then
  echo "OK: no schema violations in skills/"
  exit 0
else
  echo ""
  echo "FAIL: ${violations} schema violation(s)"
  echo "Whitelist defined in skills/writing-skills/SKILL.md '## XML schema'"
  exit 1
fi
