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

echo "OK: install reconciles existing skill directories"
