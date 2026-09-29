# Agents Skills Target + OpenCode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use bp:subagent-driven-development (recommended) or bp:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Replace per-agent skill wiring with a single `~/.agents/skills` install. Add experimental OpenCode support, retire Windsurf, and enforce the Agent Skills frontmatter spec in CI.

**Architecture:** `install.sh --agents --global` symlinks each skill into `~/.agents/skills/`, which Codex, Devin, OpenCode, Cursor, Copilot and others scan natively. OpenCode gets its bootstrap from one user-added `instructions` entry. The validator gains a frontmatter check matching the agentskills.io/OpenCode rules. Spec: `docs/bearpaws/plans/2026-09-28-agents-skills-design.md`.

**Tech Stack:** bash (installer, tests, validator), markdown (skills/docs). No new dependencies.

---

## File map

| File | Change |
|---|---|
| `tests/schema-validator/run-validator.sh` | Add the Agent Skills spec check |
| `install.sh` | `--codex` → `--agents`; drop `--devin`/`--windsurf`/`--all`; no flags exits 1; print the OpenCode snippet |
| `tests/install/run-install-tests.sh` | Drop the Devin/Windsurf block; test `--agents`, no-flag failure, and the snippet |
| `.windsurf/` | Delete |
| `.devin/skills/` | Delete (keep `.devin/hooks.v1.json`) |
| `tests/brainstorm-server/windows-lifecycle.test.sh:26-33` | Drop the `.devin`/`.windsurf` fallbacks |
| `skills/using-bearpaws/SKILL.md:26-27` | Two platform lines → one |
| `README.md`, `CLAUDE.md`, `docs/agent-support.md`, `docs/skill-structure.md` | Tiers, install docs, layout |
| `docs/bearpaws/release-notes/2.3.0.md` | Append section |

---

### Task 1: Agent Skills spec check in the validator

**Files:**
- Modify: `tests/schema-validator/run-validator.sh` (insert after the `echo "OK: no schema violations in skills/"` line)

- [x] **Step 1: Write the failing check (a temporary fixture that should fail)**

```bash
T=$(mktemp -d); mkdir -p "$T/tests/schema-validator" "$T/skills/good-skill" "$T/skills/Bad_Skill"
cp tests/schema-validator/run-validator.sh "$T/tests/schema-validator/"
printf -- '---\nname: good-skill\ndescription: Use when testing\n---\nbody\n' > "$T/skills/good-skill/SKILL.md"
printf -- '---\nname: Bad_Skill\ndescription: Use when testing\n---\nbody\n' > "$T/skills/Bad_Skill/SKILL.md"
bash "$T/tests/schema-validator/run-validator.sh"; echo "exit=$?"
```

- [x] **Step 2: Run it and verify FAIL (no spec check yet)**

Expected: the output does NOT contain `SPEC VIOLATION: skills/Bad_Skill/SKILL.md`. It fails later on the missing gate files instead.

- [x] **Step 3: Implement the check**

Insert after `echo "OK: no schema violations in skills/"`:

```bash
# Agent Skills spec check (agentskills.io; same rules OpenCode enforces at load time).
spec_violations=0
for f in skills/*/SKILL.md; do
  dir=$(basename "$(dirname "$f")")
  fm=$(awk 'NR==1 && /^---$/ {inside=1; next} inside && /^---$/ {exit} inside' "$f")
  name=$(printf '%s\n' "$fm" | sed -n 's/^name:[[:space:]]*//p' | head -1)
  desc=$(printf '%s\n' "$fm" | sed -n 's/^description:[[:space:]]*//p' | head -1)
  desc=${desc#\"}; desc=${desc%\"}
  if ! [[ "$name" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]] || (( ${#name} > 64 )) || [[ "$name" != "$dir" ]]; then
    echo "SPEC VIOLATION: ${f}: name '${name}' must equal folder '${dir}', match ^[a-z0-9]+(-[a-z0-9]+)*\$, and be <=64 chars"
    spec_violations=$((spec_violations + 1))
  fi
  if [[ -z "$desc" ]] || (( ${#desc} > 1024 )); then
    echo "SPEC VIOLATION: ${f}: description must be 1-1024 chars (got ${#desc})"
    spec_violations=$((spec_violations + 1))
  fi
done

if [[ $spec_violations -gt 0 ]]; then
  echo ""
  echo "FAIL: ${spec_violations} Agent Skills spec violation(s)"
  exit 1
fi

echo "OK: skills match the Agent Skills frontmatter spec"
```

- [x] **Step 4: Verify PASS on the fixture and the real repo**

Re-run the Step 1 fixture (after `cp` of the updated validator). Expected: `SPEC VIOLATION: skills/Bad_Skill/SKILL.md: name 'Bad_Skill' ...` and exit 1. Then run `rm -rf "$T"`.
Run: `tests/schema-validator/run-validator.sh`. Expected: three `OK:` lines, exit 0.

- [x] **Step 5: Commit** — `feat(validator): enforce Agent Skills frontmatter spec`

---

### Task 2: Installer tests for the new surface (RED)

**Files:**
- Modify: `tests/install/run-install-tests.sh`

- [x] **Step 1: Replace the Devin/Windsurf block**

Delete from `cp "$REPO_ROOT/install.sh"` through `echo "OK: Devin/Windsurf install reconciles existing skill directories"` and replace it with:

```bash
cp "$REPO_ROOT/install.sh" "$WORK/install.sh"
mkdir -p "$WORK/skills/alpha" "$WORK/skills/beta" "$WORK/skills/using-bearpaws"
touch "$WORK/skills/alpha/SKILL.md" "$WORK/skills/beta/SKILL.md" "$WORK/skills/using-bearpaws/SKILL.md"

if ( cd "$WORK" && ./install.sh ) >/dev/null 2>&1; then
  echo "FAIL: install with no platform flag should exit non-zero"
  exit 1
fi
for retired in --devin --windsurf --all; do
  if ( cd "$WORK" && ./install.sh "$retired" ) >/dev/null 2>&1; then
    echo "FAIL: retired flag $retired should be rejected"
    exit 1
  fi
done

echo "OK: no-flag and retired flags are rejected"
```

- [x] **Step 2: Rename the Codex block to `--agents` and assert the snippet**

In the `# ========== Codex Installer Tests ==========` block:
- `--codex` → `--agents` (both invocations)
- the header → `# ========== Agents Installer Tests ==========`
- the variables `CODEX_HOME_DIR`/`CODEX_SKILLS` → `AGENTS_HOME_DIR`/`AGENTS_SKILLS`
- the log → `$TMP_ROOT/bearpaws-install-agents.log`
- the final echo → `echo "OK: Agents installer (global skills, preserves unrelated skills, OpenCode snippet)"`

Before that echo, add:

```bash
grep -qF '"instructions": ["~/.agents/skills/using-bearpaws/SKILL.md"]' "$TMP_ROOT/bearpaws-install-agents.log"
```

- [x] **Step 3: Run and verify FAIL**

Run: `tests/install/run-install-tests.sh`
Expected: `FAIL: install with no platform flag should exit non-zero`, because no flags still defaults to Devin + Windsurf.

---

### Task 3: Installer implementation (GREEN)

**Files:**
- Modify: `install.sh`

- [x] **Step 1: Delete `install_devin()` and `install_windsurf()`** (the whole functions, including their `# Install for ...` comments).

- [x] **Step 2: Replace `install_codex()` with:**

```bash
# Install for Agent Skills agents (Codex, Devin, OpenCode, Cursor, Copilot, ...) via ~/.agents/skills
install_agents() {
    log_info "Setting up experimental Agent Skills wiring..."
    if [[ "${INSTALL_GLOBAL:-}" != "true" ]]; then
        log_error "Agents installation currently requires --global"
        log_info "Use: ./install.sh --agents --global"
        return 1
    fi
    create_symlinks "$BEARPAWS_ROOT/skills" "$HOME/.agents/skills"
}
```

- [x] **Step 3: Replace the argument parser cases.** Remove the `--codex`, `--devin`, `--windsurf`, and `--all` cases, and add:

```bash
            --agents)
                platforms+=("agents")
                shift
                ;;
```

- [x] **Step 4: Replace the help text body with:**

```bash
                echo "Bearpaws installation script"
                echo ""
                echo "Usage: $0 --antigravity --global | --agents --global"
                echo ""
                echo "Options:"
                echo "  --antigravity Install BearPaws plugin for Google Antigravity"
                echo "  --agents      Link skills into ~/.agents/skills (Codex, Devin, OpenCode, Cursor, Copilot, ...)"
                echo "  --global      Required for both targets"
                echo "  --help        Show this help message"
```

- [x] **Step 5: Make no flags an error.** Replace the `# Default to all platforms if none specified` block with:

```bash
    if [[ ${#platforms[@]} -eq 0 ]]; then
        log_error "No platform given"
        echo "Use --help for usage information"
        exit 1
    fi
```

- [x] **Step 6: Update the dispatch and next steps.** In the `case $platform` loop, replace the `codex)`, `devin)`, and `windsurf)` arms with:

```bash
            agents)
                if ! install_agents; then
                    ((++failed))
                fi
                ;;
```

Replace the Codex, Devin, and Windsurf "Next steps" blocks with:

```bash
        if [[ " ${platforms[*]} " =~ " agents " ]]; then
            echo "  • Agent Skills (experimental): Skills are now available in ~/.agents/skills/"
            echo "  • Restart your agent; invoke using-bearpaws or let descriptions trigger skills"
            echo "  • OpenCode bootstrap: add to ~/.config/opencode/opencode.json:"
            echo '      "instructions": ["~/.agents/skills/using-bearpaws/SKILL.md"]'
        fi
```

Update the header comment to `# Installs Bearpaws for Antigravity, and experimental ~/.agents/skills wiring for other Agent Skills agents`.

- [x] **Step 7: Verify PASS**

Run: `bash -n install.sh && tests/install/run-install-tests.sh`
Expected: `OK: no-flag and retired flags are rejected`, the Antigravity OK line, and the Agents OK line; exit 0.
Run: `git grep -n "codex\|devin\|windsurf" install.sh`. Expected: only the `install_agents` comment line.

- [x] **Step 8: Commit** — `feat(install): single --agents target; retire devin/windsurf wiring`

---

### Task 4: Remove the retired repo wiring

**Files:**
- Delete: `.windsurf/`, `.devin/skills/`
- Modify: `tests/brainstorm-server/windows-lifecycle.test.sh:26-33`

- [x] **Step 1: Delete**

```bash
git rm -rq .windsurf .devin/skills
```

- [x] **Step 2: Drop the fallbacks.** In `windows-lifecycle.test.sh`, delete the two `elif` branches for `.devin/skills/...` and `.windsurf/skills/...` (lines 26–33), leaving the `if` and the `else` error.

- [x] **Step 3: Verify**

Run: `ls .devin` → `hooks.v1.json` only. Run `bash -n tests/brainstorm-server/windows-lifecycle.test.sh`, then `git grep -n "\.windsurf\|\.devin/skills" -- ':!docs/bearpaws'`. Expected: no hits in code or tests (docs are fixed in Task 6).

- [x] **Step 4: Commit** — `chore: remove Windsurf and Devin per-skill symlinks`

---

### Task 5: Bootstrap line

**Files:**
- Modify: `skills/using-bearpaws/SKILL.md:26-27`

- [x] **Step 1: Replace both lines** (`**In Devin for Terminal / Windsurf Cascade:** …` and `**In Codex:** …`) with:

```markdown
    <step>**In other Agent Skills agents (Codex, Devin, OpenCode, Cursor, Copilot, …):** Skills live in `.agents/skills/` or `~/.agents/skills/`. Load one with your native skill tool (`skill` in OpenCode) or by reading its `SKILL.md`; users can also type `$skill-name` (Codex) or `/skill-name` (Devin CLI).</step>
```

- [x] **Step 2: Verify**

Run: `tests/schema-validator/run-validator.sh && tests/antigravity/run-adapter-tests.sh | tail -1 && CLAUDE_PLUGIN_ROOT=$PWD hooks/session-start | grep -c "Agent Skills agents"`
Expected: validator OK lines, `ALL ANTIGRAVITY ADAPTER TESTS PASSED`, and `1`.

- [x] **Step 3: Commit** — `feat(bootstrap): one line for all .agents/skills agents`

---

### Task 6: Docs

**Files:**
- Modify: `README.md`, `CLAUDE.md`, `docs/agent-support.md`, `docs/skill-structure.md`, `docs/bearpaws/release-notes/2.3.0.md`

- [x] **Step 1: Support table** (replace the Codex, Devin and Windsurf rows in README, CLAUDE.md, and `docs/agent-support.md`):

```markdown
| OpenCode | Experimental | Native `.agents/skills` discovery + `instructions` bootstrap |
| Other Agent Skills agents (Codex, Devin, Cursor, Copilot, …) | Experimental | Native `.agents/skills` discovery; `install.sh --agents --global` |
```

Intro sentence (README:5 and CLAUDE.md:9): `Claude Code and Google Antigravity IDE are the primary supported targets. OpenCode and other Agent Skills agents (Codex, Devin, Cursor, Copilot, …) are experimental unless a specific workflow has been validated.` Keep CLAUDE.md's trailing "Avoid adding language…" sentence.

- [x] **Step 2: README install sections.** Replace `## Experimental Install (Codex)` and `## Experimental Install (Devin for Terminal & Windsurf Cascade)`, through the paragraph ending "…verified in the target tool.", with:

````markdown
## Experimental Install (OpenCode, Codex, Devin, Cursor, Copilot, …)

Most coding agents now read the shared Agent Skills folder `~/.agents/skills/`. One command links every Bearpaws skill there without touching unrelated skills:

```bash
./install.sh --agents --global
```

Restart your agent and invoke `using-bearpaws` (`skill` tool in OpenCode, `$using-bearpaws` in Codex, `/using-bearpaws` in Devin CLI) to confirm discovery. This repo also ships `.agents/skills -> skills` for sessions inside the checkout.

**OpenCode bootstrap:** add to `~/.config/opencode/opencode.json` so the bootstrap loads every session:

```json
{ "instructions": ["~/.agents/skills/using-bearpaws/SKILL.md"] }
```

Other agents load `using-bearpaws` when it is invoked or matched by its description. Devin for Terminal sessions in this repo also get it from `.devin/hooks.v1.json`.
````

- [x] **Step 3: CLAUDE.md layout.**
  - Replace the `.devin/` bullet with: `- [.devin/](.devin/) — Devin for Terminal \`hooks.v1.json\` (SessionStart hook). Skills come from \`.agents/skills\`.`
  - Delete the `.windsurf/` bullet.
  - Change the `.agents/skills` bullet to end with: `\`install.sh --agents --global\` links skills into \`~/.agents/skills/\` for Codex, Devin, OpenCode, Cursor, Copilot, and others.`
  - `tests/install/` bullet: `installer tests for Antigravity and Agent Skills (\`--agents\`).`
  - The test command comment: `# verify Antigravity and --agents installer`.

- [x] **Step 4: `docs/agent-support.md`.** Replace the `## Codex`, `## Devin for Terminal`, and `## Windsurf Cascade` sections with:

```markdown
## OpenCode

Status: Experimental.

- Skills: OpenCode scans `.agents/skills/` and `~/.agents/skills/` and invokes them with its native `skill` tool. It enforces the Agent Skills frontmatter rules (name `^[a-z0-9]+(-[a-z0-9]+)*$`, ≤64 chars, equals folder; description 1–1024 chars), which `tests/schema-validator/run-validator.sh` checks in CI.
- Bootstrap: `"instructions": ["~/.agents/skills/using-bearpaws/SKILL.md"]` in `~/.config/opencode/opencode.json`. The installer prints this line and never edits user config.
- Evidence: <smoke test result from Task 7>.
- Known limitations: no OpenCode tool-name mapping reference; Claude Code tool names (`Agent`, `Skill`) in skills are interpreted by the model.

## Other Agent Skills agents (Codex, Devin, Cursor, Copilot, …)

Status: Experimental.

- Install: `./install.sh --agents --global` links each skill into `~/.agents/skills/`, removing only broken links. The repo ships `.agents/skills -> skills`.
- Invocation: `$skill-name` or `/skills` (Codex), `/skill-name` (Devin CLI), or implicitly when a description matches.
- Devin for Terminal: `.devin/hooks.v1.json` runs `hooks/session-start`, which emits top-level `additionalContext` when `DEVIN_PROJECT_DIR` is set.
- Evidence: installer test (global linking, the `--global` requirement, preserved unrelated skills); <Codex smoke test result from Task 7>.
- Known limitations: no automatic bootstrap outside hook-capable agents; no per-agent behavior tests.

Windsurf Cascade is retired: its docs now redirect to Devin, which reads `.agents/skills/`.
```

Update the Testing Policy table: replace the Codex, Devin, and Windsurf rows with `| OpenCode | Spec validator + manual discovery smoke test. |` and `| Other Agent Skills agents | \`--agents\` installer test + manual activation proof before promotion. |`. Also update the tier table at the top (per Step 1).

- [x] **Step 5: `docs/skill-structure.md:131`** → `- Other Agent Skills agents (Codex, Devin, OpenCode, …) are described in the bootstrap by their native skill mechanism`

- [x] **Step 6: Release notes.** Append to `docs/bearpaws/release-notes/2.3.0.md`:

```markdown

### One `.agents/skills` target, OpenCode, Windsurf retired
- `install.sh --codex` renamed `--agents` (unreleased); it links skills into `~/.agents/skills/`, which Codex, Devin, OpenCode, Cursor, Copilot, and others scan.
- Added experimental OpenCode support: native `.agents/skills` discovery plus a one-line `instructions` bootstrap that the installer prints.
- Removed `--devin`, `--windsurf`, `--all`, `.windsurf/`, and `.devin/skills/`. `.devin/hooks.v1.json` stays. Windsurf is retired (its docs now redirect to Devin).
- `install.sh` with no flags now prints an error instead of installing Devin + Windsurf.
- The validator enforces the Agent Skills frontmatter spec (name format and folder match, description length).
```

Also edit the existing Codex section in the same file: change `./install.sh --codex --global` to `./install.sh --agents --global`, and change `Added a Codex line to the using-bearpaws bootstrap` to `Codex is covered by the shared Agent Skills bootstrap line`.

- [x] **Step 7: Verify**

Run: `git grep -n -i "windsurf\|--codex\|--devin\|install.sh --all" -- ':!docs/bearpaws/release-notes' ':!docs/bearpaws/plans'`
Expected: only the "Windsurf Cascade is retired" line in `docs/agent-support.md`.

- [x] **Step 8: Commit** — `docs: agents target, OpenCode, retire Windsurf`

---

### Task 7: Real-agent smoke tests (manual, results recorded)

- [x] **Step 1: Temp project**

```bash
S=$(mktemp -d) && cd "$S" && git init -q && mkdir -p .agents && ln -s /Users/brandon/repos/bearpaws/.claude/worktrees/llm-state-alignment-649e48/skills .agents/skills
```

- [x] **Step 2: OpenCode discovery**

Run: `opencode run "List the names of every skill available to you via the skill tool. Output names only."`
Expected: the output includes `using-bearpaws` and `brainstorming`.

- [x] **Step 3: OpenCode bootstrap via project `instructions`**

```bash
printf '{ "instructions": [".agents/skills/using-bearpaws/SKILL.md"] }\n' > opencode.json
opencode run "Quote the first bold line under '## Pace Control' in your instructions, verbatim."
```

Expected: the output contains `Momentum does not waive gates`.

- [x] **Step 4: Codex discovery**

Run: `codex exec "List the names of every skill available to you. Output names only."`
Expected: the output includes `using-bearpaws`.

- [x] **Step 5: Record.** Fill in the `<smoke test result from Task 7>` placeholders in `docs/agent-support.md` with the date, agent version (`opencode --version`, `codex --version`), and pass/fail per step. Then run `rm -rf "$S"`.

- [x] **Step 6: Commit** — `docs: record OpenCode and Codex smoke tests`

---

### Task 8: Full verification

- [ ] Run:

```bash
tests/schema-validator/run-validator.sh && tests/install/run-install-tests.sh && tests/antigravity/run-adapter-tests.sh | tail -1 && tests/token-measurement/measure.sh >/dev/null && scripts/bump-version.sh --check | tail -1 && tests/claude-code/run-skill-tests.sh && git diff main --shortstat
```

Expected: every suite OK/PASSED, versions in sync at 2.3.0, and the net diff shows deletions > insertions.
