#!/usr/bin/env bash
# Tests for scripts/bump-version.sh against a throwaway copy of the declared files.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT
trap 'echo "FAIL: line $LINENO: $BASH_COMMAND"' ERR

WORK="$TMP_ROOT/repo"
mkdir -p "$WORK/scripts"
cp "$REPO_ROOT/scripts/bump-version.sh" "$WORK/scripts/"
cp "$REPO_ROOT/.version-bump.json" "$WORK/"
while IFS= read -r path; do
  mkdir -p "$WORK/$(dirname "$path")"
  cp "$REPO_ROOT/$path" "$WORK/$path"
done < <(jq -r '.files[].path' "$REPO_ROOT/.version-bump.json")
BUMP="$WORK/scripts/bump-version.sh"

snapshot() { jq -S . "$WORK/package.json" "$WORK/.claude-plugin/plugin.json"; }

# Versions that are not exactly X.Y.Z[-pre][+build] are rejected, files untouched
before="$(snapshot)"
for bad in '9.9.9" | .name = "pwned' '9.9.9garbage' '9.9' 'v9.9.9' '9.9.9 '; do
  if "$BUMP" "$bad" >/dev/null 2>&1; then
    echo "FAIL: bump accepted malformed version: $bad"
    exit 1
  fi
done
test "$(snapshot)" = "$before"

echo "OK: malformed versions are rejected without touching any file"

# A valid version, including a pre-release, lands verbatim in every declared field
"$BUMP" 9.9.9-rc.1+build.5 >/dev/null
while IFS=$'\t' read -r path field; do
  jq_path=".$(sed -E 's/\.([0-9]+)/[\1]/g' <<<"$field")"
  test "$(jq -r "$jq_path" "$WORK/$path")" = "9.9.9-rc.1+build.5"
done < <(jq -r '.files[] | "\(.path)\t\(.field)"' "$WORK/.version-bump.json")
test "$(jq -r .name "$WORK/package.json")" = "$(jq -r .name "$REPO_ROOT/package.json")"
"$BUMP" --check >/dev/null

echo "OK: valid versions are written to every declared field and nothing else"

# Audit: path excludes (with a slash) skip only that path; undeclared files are reported
jq '.audit.exclude += ["only/this/dir"]' "$WORK/.version-bump.json" > "$WORK/vb.tmp" && mv "$WORK/vb.tmp" "$WORK/.version-bump.json"
mkdir -p "$WORK/only/this/dir" "$WORK/other/this/dir"
echo "9.9.9-rc.1+build.5" > "$WORK/only/this/dir/note.txt"
echo "9.9.9-rc.1+build.5" > "$WORK/other/this/dir/note.txt"
echo "9.9.9-rc.1+build.5" > "$WORK/stray.txt"
audit_out="$("$BUMP" --audit)"
grep -qF "stray.txt" <<<"$audit_out"
grep -qF "other/this/dir/note.txt" <<<"$audit_out"
if grep -qF "only/this/dir/note.txt" <<<"$audit_out"; then
  echo "FAIL: audit reported a file under an excluded path"
  exit 1
fi

echo "OK: audit honors path excludes and reports undeclared files"
