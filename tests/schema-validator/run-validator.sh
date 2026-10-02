#!/usr/bin/env bash
# Schema validator: XML tag whitelist, Agent Skills frontmatter spec, .agents/skills links, and adversarial gates.
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

# Agent Skills spec check (agentskills.io; same rules OpenCode enforces at load time).
validate_skill_frontmatter() {
  local f="$1"
  local dir="$2"
  if command -v ruby >/dev/null 2>&1; then
    ruby -e '
      require "yaml"
      f, dir = ARGV
      content = File.read(f, encoding: "UTF-8")
      parts = content.split(/^---\s*$/, 3)
      if parts.size < 3 || !content.start_with?("---")
        puts "SPEC VIOLATION: #{f}: frontmatter must start and end with ---"
        exit 1
      end
      raw_fm = parts[1]
      begin
        data = YAML.safe_load(raw_fm)
      rescue => e
        puts "SPEC VIOLATION: #{f}: malformed YAML frontmatter: #{e.message.lines.first.strip}"
        exit 1
      end
      unless data.is_a?(Hash)
        puts "SPEC VIOLATION: #{f}: frontmatter must be a YAML mapping"
        exit 1
      end
      name = data["name"]
      desc = data["description"]

      unless name.is_a?(String) && name =~ /^[a-z0-9]+(-[a-z0-9]+)*$/ && name.length <= 64 && name == dir
        puts "SPEC VIOLATION: #{f}: name #{name.inspect} must equal folder #{dir.inspect}, match ^[a-z0-9]+(-[a-z0-9]+)*$, and be <=64 chars"
        exit 1
      end

      if raw_fm =~ /^description:\s*[>|]/
        puts "SPEC VIOLATION: #{f}: description must be a single line of 1-1024 chars (got #{desc.is_a?(String) ? desc.length : 0}; block scalars > | not supported)"
        exit 1
      end

      unless desc.is_a?(String) && !desc.empty? && desc.length <= 1024 && !desc.include?("\n")
        puts "SPEC VIOLATION: #{f}: description must be a single line of 1-1024 chars (got #{desc.is_a?(String) ? desc.length : desc.inspect}; block scalars > | not supported)"
        exit 1
      end
    ' "$f" "$dir"
  elif command -v python3 >/dev/null 2>&1 && python3 -c 'import yaml' >/dev/null 2>&1; then
    python3 -c '
import sys, re, yaml
f, dir_name = sys.argv[1], sys.argv[2]
with open(f, "r", encoding="utf-8") as fp:
    content = fp.read()
parts = re.split(r"^---\s*$", content, maxsplit=2, flags=re.MULTILINE)
if len(parts) < 3 or not content.startswith("---"):
    print(f"SPEC VIOLATION: {f}: frontmatter must start and end with ---")
    sys.exit(1)
raw_fm = parts[1]
try:
    data = yaml.safe_load(raw_fm)
except Exception as e:
    first_line = str(e).splitlines()[0] if str(e).splitlines() else str(e)
    print(f"SPEC VIOLATION: {f}: malformed YAML frontmatter: {first_line}")
    sys.exit(1)
if not isinstance(data, dict):
    print(f"SPEC VIOLATION: {f}: frontmatter must be a YAML mapping")
    sys.exit(1)
name = data.get("name")
desc = data.get("description")
name_pattern = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
if not isinstance(name, str) or not name_pattern.match(name) or len(name) > 64 or name != dir_name:
    print(f"SPEC VIOLATION: {f}: name {repr(name)} must equal folder {repr(dir_name)}, match ^[a-z0-9]+(-[a-z0-9]+)*$, and be <=64 chars")
    sys.exit(1)
if re.search(r"^description:\s*[>|]", raw_fm, flags=re.MULTILINE):
    got = len(desc) if isinstance(desc, str) else 0
    print(f"SPEC VIOLATION: {f}: description must be a single line of 1-1024 chars (got {got}; block scalars > | not supported)")
    sys.exit(1)
if not isinstance(desc, str) or len(desc) == 0 or len(desc) > 1024 or "\n" in desc:
    got = len(desc) if isinstance(desc, str) else repr(desc)
    print(f"SPEC VIOLATION: {f}: description must be a single line of 1-1024 chars (got {got}; block scalars > | not supported)")
    sys.exit(1)
' "$f" "$dir"
  else
    echo "FAIL: YAML parser required for frontmatter validation (ruby or python3 with pyyaml)"
    exit 1
  fi
}

spec_violations=0
for f in skills/*/SKILL.md; do
  dir=$(basename "$(dirname "$f")")
  if ! out=$(validate_skill_frontmatter "$f" "$dir"); then
    echo "$out"
    spec_violations=$((spec_violations + 1))
  fi
done

if [[ $spec_violations -gt 0 ]]; then
  echo ""
  echo "FAIL: ${spec_violations} Agent Skills spec violation(s)"
  exit 1
fi

echo "OK: skills match the Agent Skills frontmatter spec"

# .agents/skills layout check: Codex ignores a symlinked skills directory, so
# .agents/skills must be a real directory holding one symlink per skill.
agents_violations=0
if [[ -L .agents/skills ]] || [[ ! -d .agents/skills ]]; then
  echo "AGENTS VIOLATION: .agents/skills must exist as a real directory (not a symlink)"
  agents_violations=$((agents_violations + 1))
else
  for d in skills/*/; do
    n=$(basename "$d")
    p=".agents/skills/$n"
    if [[ -L "$p" ]] && [[ "$(readlink "$p")" == "../../skills/$n" ]] && [[ -d "$p" ]]; then
      :
    else
      echo "AGENTS VIOLATION: ${p} must be a symlink to ../../skills/${n} (Windows: enable core.symlinks)"
      agents_violations=$((agents_violations + 1))
    fi
  done
  # Dotfiles (e.g. .DS_Store) are ignored; only non-dot entries are checked for extras.
  for e in .agents/skills/*; do
    if [[ -e "$e" || -L "$e" ]] && [[ ! -d "skills/$(basename "$e")" ]]; then
      echo "AGENTS VIOLATION: ${e} has no matching skills/ directory"
      agents_violations=$((agents_violations + 1))
    fi
  done
fi

if [[ $agents_violations -gt 0 ]]; then
  echo ""
  echo "FAIL: ${agents_violations} .agents/skills violation(s)"
  exit 1
fi

echo "OK: .agents/skills mirrors skills/ with per-skill links"

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
