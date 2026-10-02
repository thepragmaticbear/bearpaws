#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT
trap 'echo "FAIL: line $LINENO: $BASH_COMMAND"' ERR

WORK="$TMP_ROOT/bearpaws"
mkdir -p "$WORK"

cp "$REPO_ROOT/install.sh" "$WORK/install.sh"
mkdir -p "$WORK/skills/alpha" "$WORK/skills/beta" "$WORK/skills/using-bearpaws"
touch "$WORK/skills/alpha/SKILL.md" "$WORK/skills/beta/SKILL.md" "$WORK/skills/using-bearpaws/SKILL.md"

REJECT_HOME="$TMP_ROOT/reject-home"
mkdir -p "$REJECT_HOME"

if out="$( cd "$WORK" && HOME="$REJECT_HOME" ./install.sh 2>&1 )"; then
  echo "FAIL: install with no platform flag should exit non-zero"
  exit 1
fi
if ! grep -qF "No platform given" <<<"$out"; then
  echo "FAIL: no-flag install should fail with 'No platform given', got: $out"
  exit 1
fi
for retired in --codex --devin --windsurf --all; do
  if out="$( cd "$WORK" && HOME="$REJECT_HOME" ./install.sh "$retired" 2>&1 )"; then
    echo "FAIL: retired flag $retired should be rejected"
    exit 1
  fi
  if ! grep -qF "Unknown option" <<<"$out"; then
    echo "FAIL: retired flag $retired should fail with 'Unknown option', got: $out"
    exit 1
  fi
done

echo "OK: no-flag and retired flags are rejected"

# ========== Antigravity Installer Tests ==========
TEST_HOME="$TMP_ROOT/home"
mkdir -p "$TEST_HOME"

mkdir -p "$WORK/.antigravity/rules" "$WORK/agents"
cat << 'EOF' > "$WORK/.antigravity/plugin.json"
{
  "$schema": "https://antigravity.google/schemas/v1/plugin.json",
  "name": "bearpaws",
  "description": "Test manifest"
}
EOF
cat << 'EOF' > "$WORK/.antigravity/rules/bearpaws.md"
# BearPaws
@../skills/using-bearpaws/SKILL.md
EOF
cat << 'EOF' > "$WORK/agents/code-reviewer.md"
# Code Reviewer Agent
EOF

# Verify --antigravity fails without --global
if ( cd "$WORK" && HOME="$TEST_HOME" ./install.sh --antigravity ) >/dev/null 2>&1; then
  echo "FAIL: install should require --global for antigravity"
  exit 1
fi

# Run install with --antigravity --global
( cd "$WORK" && HOME="$TEST_HOME" ./install.sh --antigravity --global ) >"$TMP_ROOT/bearpaws-install-antigravity.log" 2>&1

PLUGIN="$TEST_HOME/.gemini/config/plugins/bearpaws"

test -f "$PLUGIN/plugin.json"
test -f "$PLUGIN/rules/bearpaws.md"
test -d "$PLUGIN/skills/alpha"
test -f "$PLUGIN/skills/alpha/SKILL.md"
test -d "$PLUGIN/skills/using-bearpaws"
test -f "$PLUGIN/skills/using-bearpaws/SKILL.md"
test -f "$PLUGIN/agents/code-reviewer.md"

# Assert real directories/files, not symlinks
test ! -L "$PLUGIN/skills/alpha"
test ! -L "$PLUGIN/skills/using-bearpaws"
test ! -L "$PLUGIN/rules"
test ! -L "$PLUGIN/agents"

# Idempotency: run install a second time
( cd "$WORK" && HOME="$TEST_HOME" ./install.sh --antigravity --global ) >>"$TMP_ROOT/bearpaws-install-antigravity.log" 2>&1
test -f "$PLUGIN/plugin.json"
test -f "$PLUGIN/rules/bearpaws.md"
test -f "$PLUGIN/skills/alpha/SKILL.md"

# Update reconciliation: add a new skill and remove an old one from source
mkdir -p "$WORK/skills/gamma"
touch "$WORK/skills/gamma/SKILL.md"
rm -rf "$WORK/skills/alpha"

( cd "$WORK" && HOME="$TEST_HOME" ./install.sh --antigravity --global ) >>"$TMP_ROOT/bearpaws-install-antigravity.log" 2>&1

test -f "$PLUGIN/skills/gamma/SKILL.md"
test ! -e "$PLUGIN/skills/alpha"

echo "OK: Antigravity plugin installer (real files, idempotency, update reconciliation)"

# ========== Agents Installer Tests ==========
AGENTS_HOME_DIR="$TMP_ROOT/agents-home"
AGENTS_SKILLS="$AGENTS_HOME_DIR/.agents/skills"
mkdir -p "$AGENTS_SKILLS" "$TMP_ROOT/unrelated-skill"
ln -s "$TMP_ROOT/unrelated-skill" "$AGENTS_SKILLS/unrelated"
ln -s "$TMP_ROOT/missing-skill" "$AGENTS_SKILLS/broken"
ln -s "$WORK/skills/removed" "$AGENTS_SKILLS/removed"

# Name collisions with skills present in source: beta (real dir), delta (plain file), zeta (foreign link), eta (dangling foreign link)
mkdir -p "$WORK/skills/delta" "$WORK/skills/zeta" "$WORK/skills/eta"
touch "$WORK/skills/delta/SKILL.md" "$WORK/skills/zeta/SKILL.md" "$WORK/skills/eta/SKILL.md"
mkdir -p "$AGENTS_SKILLS/beta"
echo mine > "$AGENTS_SKILLS/beta/mine.txt"
echo mine > "$AGENTS_SKILLS/delta"
ln -s "$TMP_ROOT/unrelated-skill" "$AGENTS_SKILLS/zeta"
ln -s "$TMP_ROOT/missing-foreign-target" "$AGENTS_SKILLS/eta"

if ( cd "$WORK" && HOME="$AGENTS_HOME_DIR" ./install.sh --agents ) >/dev/null 2>&1; then
  echo "FAIL: install should require --global for agents"
  exit 1
fi

( cd "$WORK" && HOME="$AGENTS_HOME_DIR" ./install.sh --agents --global ) >"$TMP_ROOT/bearpaws-install-agents.log" 2>&1

test -L "$AGENTS_SKILLS/gamma"
test -f "$AGENTS_SKILLS/using-bearpaws/SKILL.md"
test -L "$AGENTS_SKILLS/unrelated"   # shared dir: valid foreign links survive
test -L "$AGENTS_SKILLS/broken"      # shared dir: foreign dangling links survive
test ! -L "$AGENTS_SKILLS/removed"   # broken Bearpaws links are cleaned up

# Collisions with non-Bearpaws entries are skipped, never clobbered
test ! -L "$AGENTS_SKILLS/beta"
test -f "$AGENTS_SKILLS/beta/mine.txt"
test ! -e "$AGENTS_SKILLS/beta/beta"
test -f "$AGENTS_SKILLS/delta"
test ! -L "$AGENTS_SKILLS/delta"
grep -qx mine "$AGENTS_SKILLS/delta"
test "$(readlink "$AGENTS_SKILLS/zeta")" = "$TMP_ROOT/unrelated-skill"
test "$(readlink "$AGENTS_SKILLS/eta")" = "$TMP_ROOT/missing-foreign-target"

# Idempotency: our own links are refreshed, not skipped
out2="$( cd "$WORK" && HOME="$AGENTS_HOME_DIR" ./install.sh --agents --global 2>&1 )"
if grep -qE 'Skipping (gamma|using-bearpaws)' <<<"$out2"; then
  echo "FAIL: own links skipped on rerun"
  exit 1
fi
test -L "$AGENTS_SKILLS/gamma"
test -f "$AGENTS_SKILLS/gamma/SKILL.md"
test -f "$AGENTS_SKILLS/using-bearpaws/SKILL.md"
test -f "$AGENTS_SKILLS/beta/mine.txt"

grep -qF '"instructions": ["~/.agents/skills/using-bearpaws/SKILL.md"]' "$TMP_ROOT/bearpaws-install-agents.log"
grep -qF 'Before responding to any request, read `~/.agents/skills/using-bearpaws/SKILL.md` and follow it.' "$TMP_ROOT/bearpaws-install-agents.log"

echo "OK: Agents installer (global skills, preserves unrelated skills and name collisions, idempotent, OpenCode and Codex snippets)"

# ========== Grok Build Installer Tests ==========
GROK_HOME_DIR="$TMP_ROOT/grok-home"
GROK_RULE="$GROK_HOME_DIR/.grok/rules/bearpaws.md"
BOOTSTRAP_LINE='Before responding to any request, read `~/.agents/skills/using-bearpaws/SKILL.md` and follow it.'
mkdir -p "$GROK_HOME_DIR"

if ( cd "$WORK" && HOME="$GROK_HOME_DIR" ./install.sh --grok ) >/dev/null 2>&1; then
  echo "FAIL: install should require --global for grok"
  exit 1
fi
test ! -e "$GROK_RULE"

( cd "$WORK" && HOME="$GROK_HOME_DIR" ./install.sh --grok --global ) >"$TMP_ROOT/bearpaws-install-grok.log" 2>&1

# Skills come from ~/.agents/skills, which Grok scans at the user tier
test -L "$GROK_HOME_DIR/.agents/skills/gamma"
test -f "$GROK_HOME_DIR/.agents/skills/using-bearpaws/SKILL.md"
# Bootstrap is a real, Bearpaws-owned rule file Grok loads in every project
test -f "$GROK_RULE"
test ! -L "$GROK_RULE"
grep -qF "$BOOTSTRAP_LINE" "$GROK_RULE"
grep -qF 'Managed by Bearpaws' "$GROK_RULE"

# Idempotent: rerun refreshes our own rule without duplicating the line
( cd "$WORK" && HOME="$GROK_HOME_DIR" ./install.sh --grok --global ) >/dev/null 2>&1
test "$(grep -cF "$BOOTSTRAP_LINE" "$GROK_RULE")" -eq 1

# A user-authored bearpaws.md is never overwritten, and the install fails loudly
FOREIGN_HOME="$TMP_ROOT/grok-foreign-home"
mkdir -p "$FOREIGN_HOME/.grok/rules"
echo "my own rule" > "$FOREIGN_HOME/.grok/rules/bearpaws.md"
if ( cd "$WORK" && HOME="$FOREIGN_HOME" ./install.sh --grok --global ) >"$TMP_ROOT/bearpaws-install-grok-foreign.log" 2>&1; then
  echo "FAIL: grok install should fail rather than overwrite a foreign rule"
  exit 1
fi
grep -qx "my own rule" "$FOREIGN_HOME/.grok/rules/bearpaws.md"
grep -qF "not created by Bearpaws" "$TMP_ROOT/bearpaws-install-grok-foreign.log"

# GROK_HOME relocates Grok's config root
RELOC_HOME="$TMP_ROOT/grok-reloc-home"
mkdir -p "$RELOC_HOME"
( cd "$WORK" && HOME="$RELOC_HOME" GROK_HOME="$RELOC_HOME/custom-grok" ./install.sh --grok --global ) >/dev/null 2>&1
test -f "$RELOC_HOME/custom-grok/rules/bearpaws.md"
test ! -e "$RELOC_HOME/.grok"

echo "OK: Grok installer (requires --global, skills via ~/.agents/skills, owned rule, idempotent, never clobbers, GROK_HOME)"
