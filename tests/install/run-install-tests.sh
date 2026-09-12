#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT

WORK="$TMP_ROOT/bearpaws"
mkdir -p "$WORK"

cp "$REPO_ROOT/install.sh" "$WORK/install.sh"
mkdir -p "$WORK/skills/alpha" "$WORK/skills/beta" "$WORK/skills/using-bearpaws" "$WORK/.windsurf/rules" "$WORK/.devin/skills" "$WORK/.windsurf/skills"
touch "$WORK/skills/alpha/SKILL.md" "$WORK/skills/beta/SKILL.md" "$WORK/skills/using-bearpaws/SKILL.md" "$WORK/.windsurf/rules/bearpaws.md"
ln -sfn "$WORK/skills/alpha" "$WORK/.devin/skills/alpha"
ln -sfn "$WORK/skills/alpha" "$WORK/.windsurf/skills/alpha"

( cd "$WORK" && ./install.sh --all ) >/tmp/bearpaws-install-test.log 2>&1

test -L "$WORK/.devin/skills/alpha"
test -L "$WORK/.devin/skills/beta"
test -L "$WORK/.windsurf/skills/alpha"
test -L "$WORK/.windsurf/skills/beta"

echo "OK: Devin/Windsurf install reconciles existing skill directories"

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
