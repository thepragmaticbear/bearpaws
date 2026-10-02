#!/usr/bin/env bash
# Model-free wiring checks: install Bearpaws the documented way into a throwaway
# HOME, then ask each harness CLI what it loaded. No API keys, no model calls.
# Proves discovery and bootstrap wiring only; behavior needs live conformance.
#
# Usage: tests/harness-wiring/run.sh
#   HARNESSES="codex opencode copilot grok"  which to check (default: all)
#   REQUIRE="codex opencode"                 missing CLIs here are blocked, not skipped
#   CODEX_BIN / OPENCODE_BIN / COPILOT_BIN / GROK_BIN  override CLI paths
# Exit: 0 all checked pass; 1 a check failed; 2 a required CLI is missing.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT
BOOTSTRAP_HOME='Before responding to any request, read `~/.agents/skills/using-bearpaws/SKILL.md` and follow it.'
BOOTSTRAP_REPO='Before responding to any request, read `.agents/skills/using-bearpaws/SKILL.md` and follow it.'
EXPECTED="$(cd "$ROOT/skills" && ls -d */ | tr -d / | sort | tr '\n' ' ')"
failed=0; blocked=0; checked=0

pass() { echo "OK: $1"; }
fail() { echo "FAIL: $1"; failed=$((failed + 1)); }

# expect_skills <label> <json-file> <python expr yielding (name, path) pairs> <path substring>
expect_skills() {
  if python3 - "$2" "$4" "$EXPECTED" "$3" <<'PY'
import json, sys
src, where, expected, expr = sys.argv[1:]
data = json.load(open(src))
pairs = eval(expr, {"data": data})
found = {n.removeprefix("bp:") for n, p in pairs if where in p}
missing = sorted(set(expected.split()) - found)
assert not missing, f"missing from {where}: {missing}"
PY
  then pass "$1: all Bearpaws skills discovered"; else fail "$1: skill discovery"; fi
}

fresh_home() { local h="$TMP_ROOT/$1"; mkdir -p "$h"; printf '%s' "$h"; }

repo_with_links() { # dir [bootstrap-file]
  mkdir -p "$1/.agents/skills"
  for s in "$ROOT"/skills/*/; do ln -s "${s%/}" "$1/.agents/skills/$(basename "$s")"; done
  [ -z "${2:-}" ] || printf '%s\n' "$BOOTSTRAP_REPO" > "$1/$2"
  git -C "$1" init -q
}

global_install() { # home flag
  HOME="$1" "$ROOT/install.sh" "$2" --global > "$1/install.log" 2>&1 || { cat "$1/install.log"; return 1; }
}

check_codex() {
  local bin="$1" h r
  # Codex prompt-input lists skills as "- name: description (file: rN/name/SKILL.md)"
  # and wraps AGENTS.md in an instructions block.
  local skills_expr='[(l[2:].split(": ")[0], l) for l in "".join(c["text"] for m in data for c in m["content"]).splitlines() if l.startswith("- ") and "(file: " in l]'
  local agents_check='import json,sys; t="".join(c["text"] for m in json.load(open(sys.argv[1])) for c in m["content"]); assert sys.argv[2] in t'

  h="$(fresh_home codex-repo)"; r="$h/repo"; repo_with_links "$r" AGENTS.md; mkdir -p "$h/.codex"
  if (cd "$r" && HOME="$h" CODEX_HOME="$h/.codex" "$bin" debug prompt-input hi > "$h/prompt.json" 2>"$h/err"); then
    expect_skills "codex repo-level" "$h/prompt.json" "$skills_expr" "(file: r"
    python3 -c "$agents_check" "$h/prompt.json" "$BOOTSTRAP_REPO" && pass "codex repo-level: AGENTS.md bootstrap in prompt" || fail "codex repo-level: bootstrap missing"
  else fail "codex repo-level: prompt-input failed ($(head -c 300 "$h/err"))"; fi

  h="$(fresh_home codex-global)"; r="$h/proj"; mkdir -p "$r" && git -C "$r" init -q
  global_install "$h" --agents || { fail "codex global: install"; return; }
  mkdir -p "$h/.codex" && printf '%s\n' "$BOOTSTRAP_HOME" > "$h/.codex/AGENTS.md"
  if (cd "$r" && HOME="$h" CODEX_HOME="$h/.codex" "$bin" debug prompt-input hi > "$h/prompt.json" 2>"$h/err"); then
    python3 - "$h/prompt.json" "$h/.agents/skills" <<'PY' || { fail "codex global: skills root is not ~/.agents/skills"; }
import json, sys
t = "".join(c["text"] for m in json.load(open(sys.argv[1])) for c in m["content"])
assert f"= `{sys.argv[2]}`" in t, "missing skills root"
PY
    expect_skills "codex global" "$h/prompt.json" "$skills_expr" "(file: r"
    python3 -c "$agents_check" "$h/prompt.json" "$BOOTSTRAP_HOME" && pass "codex global: ~/.codex/AGENTS.md bootstrap in prompt" || fail "codex global: bootstrap missing"
  else fail "codex global: prompt-input failed ($(head -c 300 "$h/err"))"; fi
}

check_opencode() {
  local bin="$1" h r
  oc() { # home cwd out args...
    local home="$1" cwd="$2" out="$3"; shift 3
    # Write to a file: piped output is truncated at 64 KiB on exit.
    (cd "$cwd" && HOME="$home" XDG_CONFIG_HOME="$home/.config" XDG_DATA_HOME="$home/.local/share" \
      XDG_CACHE_HOME="$home/.cache" XDG_STATE_HOME="$home/.local/state" "$bin" "$@" > "$out" 2>"$out.err")
  }
  local skills_expr='[(s["name"], s["location"]) for s in data]'

  h="$(fresh_home opencode-repo)"; r="$h/repo"; repo_with_links "$r"
  oc "$h" "$r" "$h/skill.json" debug skill && expect_skills "opencode repo-level" "$h/skill.json" "$skills_expr" "/repo/.agents/skills/" \
    || fail "opencode repo-level: debug skill failed"

  h="$(fresh_home opencode-global)"; r="$h/proj"; mkdir -p "$r" "$h/.config/opencode" && git -C "$r" init -q
  global_install "$h" --agents || { fail "opencode global: install"; return; }
  printf '{"instructions": ["~/.agents/skills/using-bearpaws/SKILL.md"]}\n' > "$h/.config/opencode/opencode.json"
  oc "$h" "$r" "$h/skill.json" debug skill && expect_skills "opencode global" "$h/skill.json" "$skills_expr" "/.agents/skills/" \
    || fail "opencode global: debug skill failed"
  if oc "$h" "$r" "$h/config.json" debug config && python3 - "$h/config.json" <<'PY'
import json, sys
assert "~/.agents/skills/using-bearpaws/SKILL.md" in json.load(open(sys.argv[1])).get("instructions", [])
PY
  then pass "opencode global: bootstrap in resolved instructions"; else fail "opencode global: bootstrap not in resolved config"; fi
}

check_copilot() {
  local bin="$1" h; h="$(fresh_home copilot)"
  local want; want="$(echo "$EXPECTED" | wc -w | tr -d ' ')"
  if HOME="$h" COPILOT_HOME="$h/.copilot" "$bin" plugin marketplace add "$ROOT" > "$h/add.log" 2>&1 \
     && HOME="$h" COPILOT_HOME="$h/.copilot" "$bin" plugin install bp@bearpaws > "$h/install.log" 2>&1; then
    grep -qE "Installed $want skills" "$h/install.log" && pass "copilot: plugin installs from .claude-plugin marketplace with $want skills" \
      || fail "copilot: expected $want skills ($(cat "$h/install.log"))"
  else fail "copilot: marketplace add/install failed ($(cat "$h/add.log" "$h/install.log" 2>/dev/null | head -c 300))"; fi
}

check_grok() {
  local bin="$1" h r; h="$(fresh_home grok)"; r="$h/proj"; mkdir -p "$r" && git -C "$r" init -q
  global_install "$h" --grok || { fail "grok: install"; return; }
  if (cd "$r" && HOME="$h" GROK_HOME="$h/.grok" "$bin" inspect --json > "$h/inspect.json" 2>"$h/err"); then
    python3 - "$h/inspect.json" "$h/.grok/rules/bearpaws.md" <<'PY' && pass "grok: bootstrap rule loaded" || fail "grok: bootstrap rule not loaded"
import json, sys
rules = json.load(open(sys.argv[1]))["projectInstructions"]
assert any(r["path"] == sys.argv[2] and r["scope"] == "global" for r in rules), rules
PY
    expect_skills "grok global" "$h/inspect.json" \
      '[(s["name"], s["source"].get("path", "")) for s in data["skills"]]' "/.agents/skills/"
  else fail "grok: inspect failed ($(head -c 300 "$h/err"))"; fi
}

for harness in ${HARNESSES:-codex opencode copilot grok}; do
  var="$(echo "$harness" | tr '[:lower:]' '[:upper:]')_BIN"
  bin="${!var:-$(command -v "$harness" 2>/dev/null || true)}"
  if [ -z "$bin" ] || [ ! -x "$bin" ]; then
    if [[ " ${REQUIRE:-} " == *" $harness "* ]]; then echo "BLOCKED: $harness CLI not found"; blocked=$((blocked + 1))
    else echo "SKIP: $harness CLI not found"; fi
    continue
  fi
  echo "--- $harness ($("$bin" --version 2>/dev/null | head -1))"
  checked=$((checked + 1))
  "check_$harness" "$bin"
done

echo "checked=$checked failed=$failed blocked=$blocked"
[ "$failed" -eq 0 ] || exit 1
[ "$blocked" -eq 0 ] || exit 2
exit 0
