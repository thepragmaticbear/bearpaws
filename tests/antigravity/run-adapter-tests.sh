#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

echo "=== Running Antigravity Adapter Static Tests ==="

# 1. Validate .antigravity/plugin.json
manifest=".antigravity/plugin.json"
if [[ ! -f "$manifest" ]]; then
  echo "FAIL: $manifest does not exist"
  exit 1
fi

if command -v node >/dev/null 2>&1; then
  plugin_name=$(node -e "const m = JSON.parse(require('fs').readFileSync('$manifest')); console.log(m.name);")
elif command -v python3 >/dev/null 2>&1; then
  plugin_name=$(python3 -c "import json; print(json.load(open('$manifest'))['name'])")
elif command -v jq >/dev/null 2>&1; then
  plugin_name=$(jq -r '.name' "$manifest")
else
  plugin_name=$(grep -o '"name": *"[^"]*"' "$manifest" | cut -d'"' -f4)
fi
if [[ "$plugin_name" != "bearpaws" ]]; then
  echo "FAIL: plugin.json name is '$plugin_name', expected 'bearpaws'"
  exit 1
fi
echo "OK: .antigravity/plugin.json valid and named 'bearpaws'"

# 2. Validate Antigravity rule and repo-local symlink
rule=".antigravity/rules/bearpaws.md"
if [[ ! -f "$rule" ]]; then
  echo "FAIL: $rule does not exist"
  exit 1
fi
if ! grep -qF "@../skills/using-bearpaws/SKILL.md" "$rule"; then
  echo "FAIL: $rule missing import for using-bearpaws/SKILL.md"
  exit 1
fi
if ! grep -qF "@../skills/using-bearpaws/references/antigravity-tools.md" "$rule"; then
  echo "FAIL: $rule missing import for antigravity-tools.md"
  exit 1
fi
if [[ ! -e ".antigravity/rules/../skills/using-bearpaws/SKILL.md" ]]; then
  echo "FAIL: repo-local rule resolution broken for skills/using-bearpaws/SKILL.md"
  exit 1
fi
echo "OK: .antigravity/rules/bearpaws.md exists and imports bootstrap and tool map (resolves locally)"

# 3. Validate antigravity-tools.md
tool_map="skills/using-bearpaws/references/antigravity-tools.md"
if [[ ! -f "$tool_map" ]]; then
  echo "FAIL: $tool_map does not exist"
  exit 1
fi
if ! grep -qF "Momentum does not waive gates." "$tool_map"; then
  echo "FAIL: $tool_map missing 'Momentum does not waive gates.'"
  exit 1
fi
if ! grep -qF "invoke_subagent" "$tool_map"; then
  echo "FAIL: $tool_map missing invoke_subagent mapping"
  exit 1
fi
if ! grep -qF "view_file" "$tool_map" || ! grep -qF "write_to_file" "$tool_map"; then
  echo "FAIL: $tool_map missing explicit native tool mappings (view_file, write_to_file)"
  exit 1
fi
echo "OK: antigravity-tools.md exists and contains capability mapping with concrete tool names"

# 3b. Validate packaged reviewer agent
if [[ ! -f "agents/code-reviewer.md" ]]; then
  echo "FAIL: agents/code-reviewer.md does not exist"
  exit 1
fi
echo "OK: agents/code-reviewer.md exists"

# 4. Validate 15 source skills
EXPECTED_SKILLS=(
  "brainstorming"
  "dispatching-parallel-agents"
  "executing-plans"
  "finishing-a-development-branch"
  "onboarding-to-a-project"
  "receiving-code-review"
  "requesting-code-review"
  "subagent-driven-development"
  "systematic-debugging"
  "test-driven-development"
  "using-bearpaws"
  "using-git-worktrees"
  "verification-before-completion"
  "writing-plans"
  "writing-skills"
)

skill_count=0
for skill in "${EXPECTED_SKILLS[@]}"; do
  skill_file="skills/$skill/SKILL.md"
  if [[ ! -f "$skill_file" ]]; then
    echo "FAIL: Missing skill file $skill_file"
    exit 1
  fi
  ((skill_count++))
done
if [[ "$skill_count" -ne 15 ]]; then
  echo "FAIL: Expected 15 skills, found $skill_count"
  exit 1
fi
echo "OK: All 15 source skills exist with SKILL.md"

# 5. Validate using-bearpaws bootstrap content
bootstrap="skills/using-bearpaws/SKILL.md"
if ! grep -qF "**In Antigravity:**" "$bootstrap"; then
  echo "FAIL: $bootstrap missing '**In Antigravity:**' step"
  exit 1
fi
if ! grep -qF "## Pace Control" "$bootstrap"; then
  echo "FAIL: $bootstrap missing '## Pace Control'"
  exit 1
fi
if ! grep -qF "Momentum does not waive gates." "$bootstrap"; then
  echo "FAIL: $bootstrap missing 'Momentum does not waive gates.'"
  exit 1
fi
if ! grep -qF '"I know where this is going"' "$bootstrap"; then
  echo "FAIL: $bootstrap missing '\"I know where this is going\"' red flag"
  exit 1
fi
if grep -qF "activate_skill" "$bootstrap"; then
  echo "FAIL: $bootstrap contains retired activate_skill"
  exit 1
fi
echo "OK: using-bearpaws has Pace Control, Red Flag, Antigravity step, and no activate_skill"

# 6. Validate absence of active Gemini CLI surfaces
if [[ -f "gemini-extension.json" ]]; then
  echo "FAIL: gemini-extension.json should be removed"
  exit 1
fi
if [[ -f "GEMINI.md" ]]; then
  echo "FAIL: root GEMINI.md should be removed"
  exit 1
fi
if [[ -f "skills/using-bearpaws/references/gemini-tools.md" ]]; then
  echo "FAIL: gemini-tools.md should be removed"
  exit 1
fi

# 7. Validate .version-bump.json no longer references gemini-extension.json
if grep -qF "gemini-extension.json" ".version-bump.json"; then
  echo "FAIL: .version-bump.json still references gemini-extension.json"
  exit 1
fi
echo "OK: Retired Gemini CLI adapter files are cleanly removed"

echo "ALL ANTIGRAVITY ADAPTER TESTS PASSED"
