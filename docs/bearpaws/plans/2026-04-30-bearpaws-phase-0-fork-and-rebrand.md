# Bearpaws Phase 0 — Fork & Rebrand Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hard-fork superpowers v5.0.7 into a new `bearpaws` plugin at `/Users/brandon/Downloads/bearpaws/`, drop Cursor and Codex platform support, rename plugin identity in all manifests / hooks / commands / skill paths, and ship `bearpaws@0.1.0` with all existing skill-triggering tests passing unchanged-except-for-slug. Zero changes to skill body content in this phase.

**Architecture:** Files copied from `/Users/brandon/Downloads/superpowers-main/` (the source) to `/Users/brandon/Downloads/bearpaws/` (the target) excluding `.git/` and `node_modules/`. Fresh `git init` in the target — no history preserved (hard fork per spec §Open Question 1). All platform-identity strings (`superpowers` → `bearpaws`) and version bumps (`5.0.7` → `0.1.0`) applied via targeted edits, not blind sed-replace, because some content references upstream URLs and attribution that should remain. Tests rerun against the renamed plugin to confirm zero regressions.

**Tech Stack:** bash/zsh; `jq` for JSON manipulation; `git`; Node.js (used by some tests); Claude Code CLI (used by integration tests); Gemini CLI (used by Phase 0 exit verification).

**Spec:** [docs/bearpaws/specs/2026-04-30-bearpaws-fork-design.md](docs/bearpaws/specs/2026-04-30-bearpaws-fork-design.md). Phase 0 scope is §1 (Identity & Repo Layout) and §5 Phase 0 (Fork & Rebrand).

**Roadmap for Phases 1–3** appears at the end of this document. Phases 1–3 each get their own dedicated implementation plan written *after* the prior phase ships (so that real measurements and discoveries from Phase 0/1 inform later planning).

---

## File Structure (Phase 0 deliverable)

After Phase 0 completes, `/Users/brandon/Downloads/bearpaws/` contains:

```
bearpaws/
├── .claude-plugin/
│   ├── plugin.json              [name="bearpaws", version="0.1.0", new homepage/repo]
│   └── marketplace.json         [marketplace name="bearpaws-dev", plugins[0].name="bearpaws"]
├── gemini-extension.json        [name="bearpaws", version="0.1.0"]
├── package.json                 [name="bearpaws", version="0.1.0", main path updated]
├── hooks/
│   ├── hooks.json               [unchanged structurally]
│   ├── run-hook.cmd             [unchanged]
│   └── session-start            [reads using-bearpaws/SKILL.md; legacy path uses ~/.config/bearpaws]
├── skills/
│   ├── using-bearpaws/          [renamed from using-superpowers; SKILL.md text updated]
│   │   ├── SKILL.md
│   │   └── references/
│   │       └── gemini-tools.md  [retained; copilot-tools.md and codex-tools.md DELETED]
│   ├── brainstorming/           [unchanged in Phase 0]
│   ├── test-driven-development/ [unchanged]
│   ├── ... [all other process skills, unchanged]
├── agents/
│   └── code-reviewer.md         [unchanged]
├── commands/
│   ├── brainstorm.md            [text updated to reference bearpaws:brainstorming]
│   ├── execute-plan.md          [text updated]
│   └── write-plan.md            [text updated]
├── scripts/
│   └── bump-version.sh          [unchanged structurally]
├── tests/
│   ├── claude-code/
│   │   ├── ... [test scripts with /tmp/superpowers-tests → /tmp/bearpaws-tests]
│   └── skill-triggering/
│       ├── run-all.sh           [SKILLS array unchanged]
│       └── run-test.sh          [/tmp paths and comments updated]
├── docs/
│   └── bearpaws/
│       ├── specs/2026-04-30-bearpaws-fork-design.md  [copied from source]
│       └── plans/2026-04-30-bearpaws-phase-0-fork-and-rebrand.md  [this file, copied]
├── CLAUDE.md                    [rewritten for Bearpaws identity]
├── README.md                    [rewritten with attribution to superpowers]
├── .version-bump.json           [drops .cursor-plugin and .codex-plugin entries]
├── .gitignore                   [copied from source if present, else generated]
└── LICENSE                      [copied from source — MIT — preserved per spec]
```

**Deleted from copy (not present in target):**
- `.cursor-plugin/` (entire directory)
- `.codex-plugin/` (entire directory)
- `.opencode/` (if present — opencode integration is dropped along with the codex.md README)
- `skills/using-superpowers/references/copilot-tools.md`
- `skills/using-superpowers/references/codex-tools.md`
- `docs/README.codex.md`, `docs/README.opencode.md` (if present — referenced platforms we're dropping)
- Any `.git/`, `node_modules/`, `.DS_Store` from the source

---

## Pre-flight

### Task 0: Verify environment

**Files:** none (environment check).

- [ ] **Step 0.1: Confirm source repo location and version**

Run:
```bash
ls /Users/brandon/Downloads/superpowers-main/.claude-plugin/plugin.json
jq -r '.name + " v" + .version' /Users/brandon/Downloads/superpowers-main/.claude-plugin/plugin.json
```

Expected output:
```
/Users/brandon/Downloads/superpowers-main/.claude-plugin/plugin.json
superpowers v5.0.7
```

If version differs from `5.0.7`, stop and surface to the user — the plan is written against `5.0.7` and content references may have shifted.

- [ ] **Step 0.2: Confirm `bearpaws/` does not already exist**

Run:
```bash
test ! -e /Users/brandon/Downloads/bearpaws && echo "OK — target free" || echo "ABORT — target exists"
```

Expected: `OK — target free`. If the target exists, stop and ask the user whether to overwrite or pick a different path.

- [ ] **Step 0.3: Confirm required tools present**

Run:
```bash
command -v jq && command -v git && command -v bash && command -v node && echo "OK"
```

Expected: each tool path printed, then `OK`. If any is missing, install it before proceeding (most likely missing: `jq` — install via `brew install jq` on macOS).

---

## Task 1: Create `bearpaws/` and copy the source tree

**Files:**
- Create: `/Users/brandon/Downloads/bearpaws/` (entire directory tree, copied from source)

- [ ] **Step 1.1: Create target directory**

Run:
```bash
mkdir -p /Users/brandon/Downloads/bearpaws
```

- [ ] **Step 1.2: Copy source tree, excluding git/build artifacts and dropped platform dirs**

Run:
```bash
cd /Users/brandon/Downloads/superpowers-main && \
rsync -a \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='.DS_Store' \
  --exclude='.cursor-plugin' \
  --exclude='.codex-plugin' \
  --exclude='.opencode' \
  ./ /Users/brandon/Downloads/bearpaws/
```

- [ ] **Step 1.3: Verify the copy**

Run:
```bash
ls /Users/brandon/Downloads/bearpaws/.claude-plugin/plugin.json && \
ls /Users/brandon/Downloads/bearpaws/gemini-extension.json && \
ls -d /Users/brandon/Downloads/bearpaws/.cursor-plugin 2>/dev/null && echo "FAIL: cursor still present" || echo "OK: cursor absent" && \
ls -d /Users/brandon/Downloads/bearpaws/.codex-plugin 2>/dev/null && echo "FAIL: codex still present" || echo "OK: codex absent"
```

Expected:
```
/Users/brandon/Downloads/bearpaws/.claude-plugin/plugin.json
/Users/brandon/Downloads/bearpaws/gemini-extension.json
OK: cursor absent
OK: codex absent
```

- [ ] **Step 1.4: Initialize fresh git history**

Run:
```bash
cd /Users/brandon/Downloads/bearpaws && \
git init -b main && \
git add -A && \
git commit -m "chore: initial import from superpowers v5.0.7"
```

Expected: `git status` reports a clean working tree on `main` after the commit.

---

## Task 2: Drop platform-specific reference docs from `using-superpowers`

**Files:**
- Delete: `/Users/brandon/Downloads/bearpaws/skills/using-superpowers/references/copilot-tools.md`
- Delete: `/Users/brandon/Downloads/bearpaws/skills/using-superpowers/references/codex-tools.md`
- Keep: `/Users/brandon/Downloads/bearpaws/skills/using-superpowers/references/gemini-tools.md`

(The directory is still named `using-superpowers/` at this point; we rename it in Task 8.)

- [ ] **Step 2.1: Verify the three reference files exist**

Run:
```bash
ls /Users/brandon/Downloads/bearpaws/skills/using-superpowers/references/
```

Expected: `codex-tools.md  copilot-tools.md  gemini-tools.md`

- [ ] **Step 2.2: Delete copilot-tools and codex-tools**

Run:
```bash
cd /Users/brandon/Downloads/bearpaws && \
git rm skills/using-superpowers/references/copilot-tools.md \
       skills/using-superpowers/references/codex-tools.md
```

Expected: two `rm` lines from git.

- [ ] **Step 2.3: Verify only Gemini reference remains**

Run:
```bash
ls /Users/brandon/Downloads/bearpaws/skills/using-superpowers/references/
```

Expected: `gemini-tools.md` (sole entry).

- [ ] **Step 2.4: Commit**

Run:
```bash
cd /Users/brandon/Downloads/bearpaws && \
git commit -m "chore: drop copilot/codex tool-mapping references (Claude+Gemini only)"
```

---

## Task 3: Drop unused docs/ READMEs

**Files:**
- Delete (if present): `docs/README.codex.md`, `docs/README.opencode.md`

- [ ] **Step 3.1: Identify which exist**

Run:
```bash
ls /Users/brandon/Downloads/bearpaws/docs/README.*.md 2>/dev/null
```

- [ ] **Step 3.2: Delete the codex and opencode READMEs if they exist**

Run:
```bash
cd /Users/brandon/Downloads/bearpaws && \
[ -f docs/README.codex.md ] && git rm docs/README.codex.md; \
[ -f docs/README.opencode.md ] && git rm docs/README.opencode.md; \
true
```

(The trailing `true` ensures the chained command exits 0 even if one of the files was already absent.)

- [ ] **Step 3.3: Commit**

Run:
```bash
cd /Users/brandon/Downloads/bearpaws && \
git diff --cached --quiet || git commit -m "chore: drop platform README stubs for codex/opencode"
```

(`git diff --cached --quiet` returns non-zero if anything is staged; the `||` only commits if there's something to commit.)

---

## Task 4: Update `.claude-plugin/plugin.json`

**Files:**
- Modify: `/Users/brandon/Downloads/bearpaws/.claude-plugin/plugin.json`

Target final content:

```json
{
  "name": "bearpaws",
  "description": "Bearpaws — a Claude Code skills library for Google Cloud, ADK, Vite, JS/TS, and Cloud Run development. Forked from superpowers v5.0.7.",
  "version": "0.1.0",
  "author": {
    "name": "Brandon Fitzgerald",
    "email": "47871143+brandonfla@users.noreply.github.com"
  },
  "homepage": "https://github.com/<TBD>/bearpaws",
  "repository": "https://github.com/<TBD>/bearpaws",
  "license": "MIT",
  "keywords": [
    "skills",
    "google-cloud",
    "cloud-run",
    "vite",
    "typescript",
    "adk"
  ]
}
```

> **Engineer note:** the `homepage` and `repository` URLs use `<TBD>` as a literal placeholder until you (or the user) decide on a GitHub org. After you create the GitHub repo, replace `<TBD>` with the actual org slug. This is the only place in Phase 0 a placeholder is acceptable — it's pinned to a real future action, not a missing-design issue.

- [ ] **Step 4.1: Replace the file content**

Run:
```bash
cat > /Users/brandon/Downloads/bearpaws/.claude-plugin/plugin.json <<'EOF'
{
  "name": "bearpaws",
  "description": "Bearpaws — a Claude Code skills library for Google Cloud, ADK, Vite, JS/TS, and Cloud Run development. Forked from superpowers v5.0.7.",
  "version": "0.1.0",
  "author": {
    "name": "Brandon Fitzgerald",
    "email": "47871143+brandonfla@users.noreply.github.com"
  },
  "homepage": "https://github.com/<TBD>/bearpaws",
  "repository": "https://github.com/<TBD>/bearpaws",
  "license": "MIT",
  "keywords": [
    "skills",
    "google-cloud",
    "cloud-run",
    "vite",
    "typescript",
    "adk"
  ]
}
EOF
```

- [ ] **Step 4.2: Verify JSON is valid**

Run:
```bash
jq . /Users/brandon/Downloads/bearpaws/.claude-plugin/plugin.json > /dev/null && echo OK
```

Expected: `OK`. If it errors, fix the syntax before continuing.

- [ ] **Step 4.3: Verify identity values**

Run:
```bash
jq -r '.name + " v" + .version' /Users/brandon/Downloads/bearpaws/.claude-plugin/plugin.json
```

Expected: `bearpaws v0.1.0`.

- [ ] **Step 4.4: Commit**

Run:
```bash
cd /Users/brandon/Downloads/bearpaws && \
git add .claude-plugin/plugin.json && \
git commit -m "chore: rebrand plugin.json as bearpaws@0.1.0"
```

---

## Task 5: Update `.claude-plugin/marketplace.json`

**Files:**
- Modify: `/Users/brandon/Downloads/bearpaws/.claude-plugin/marketplace.json`

Target final content:

```json
{
  "name": "bearpaws-dev",
  "description": "Development marketplace for the Bearpaws skills library",
  "owner": {
    "name": "Brandon Fitzgerald",
    "email": "47871143+brandonfla@users.noreply.github.com"
  },
  "plugins": [
    {
      "name": "bearpaws",
      "description": "Bearpaws — a Claude Code skills library for Google Cloud, ADK, Vite, JS/TS, and Cloud Run development. Forked from superpowers v5.0.7.",
      "version": "0.1.0",
      "source": "./",
      "author": {
        "name": "Brandon Fitzgerald",
        "email": "47871143+brandonfla@users.noreply.github.com"
      }
    }
  ]
}
```

- [ ] **Step 5.1: Replace the file content**

Run:
```bash
cat > /Users/brandon/Downloads/bearpaws/.claude-plugin/marketplace.json <<'EOF'
{
  "name": "bearpaws-dev",
  "description": "Development marketplace for the Bearpaws skills library",
  "owner": {
    "name": "Brandon Fitzgerald",
    "email": "47871143+brandonfla@users.noreply.github.com"
  },
  "plugins": [
    {
      "name": "bearpaws",
      "description": "Bearpaws — a Claude Code skills library for Google Cloud, ADK, Vite, JS/TS, and Cloud Run development. Forked from superpowers v5.0.7.",
      "version": "0.1.0",
      "source": "./",
      "author": {
        "name": "Brandon Fitzgerald",
        "email": "47871143+brandonfla@users.noreply.github.com"
      }
    }
  ]
}
EOF
```

- [ ] **Step 5.2: Verify and commit**

Run:
```bash
jq . /Users/brandon/Downloads/bearpaws/.claude-plugin/marketplace.json > /dev/null && \
jq -r '.name + " contains plugin: " + .plugins[0].name + " v" + .plugins[0].version' \
  /Users/brandon/Downloads/bearpaws/.claude-plugin/marketplace.json
```

Expected: `bearpaws-dev contains plugin: bearpaws v0.1.0`.

```bash
cd /Users/brandon/Downloads/bearpaws && \
git add .claude-plugin/marketplace.json && \
git commit -m "chore: rebrand marketplace.json as bearpaws-dev"
```

---

## Task 6: Update `gemini-extension.json`

**Files:**
- Modify: `/Users/brandon/Downloads/bearpaws/gemini-extension.json`

Target final content:

```json
{
  "name": "bearpaws",
  "description": "Bearpaws — a Gemini CLI extension for Google Cloud, ADK, Vite, JS/TS, and Cloud Run development. Forked from superpowers v5.0.7.",
  "version": "0.1.0",
  "contextFileName": "GEMINI.md"
}
```

- [ ] **Step 6.1: Replace and verify**

Run:
```bash
cat > /Users/brandon/Downloads/bearpaws/gemini-extension.json <<'EOF'
{
  "name": "bearpaws",
  "description": "Bearpaws — a Gemini CLI extension for Google Cloud, ADK, Vite, JS/TS, and Cloud Run development. Forked from superpowers v5.0.7.",
  "version": "0.1.0",
  "contextFileName": "GEMINI.md"
}
EOF
jq -r '.name + " v" + .version' /Users/brandon/Downloads/bearpaws/gemini-extension.json
```

Expected: `bearpaws v0.1.0`.

- [ ] **Step 6.2: Commit**

Run:
```bash
cd /Users/brandon/Downloads/bearpaws && \
git add gemini-extension.json && \
git commit -m "chore: rebrand gemini-extension.json as bearpaws@0.1.0"
```

---

## Task 7: Update `package.json` and `.version-bump.json`

**Files:**
- Modify: `/Users/brandon/Downloads/bearpaws/package.json`
- Modify: `/Users/brandon/Downloads/bearpaws/.version-bump.json`

The current `package.json` has a `"main"` pointing at an opencode plugin path which we don't ship. The new package.json drops `main` (no Node entry point) since the plugin is consumed by Claude Code via manifest, not as a Node library.

Target `package.json`:

```json
{
  "name": "bearpaws",
  "version": "0.1.0",
  "type": "module"
}
```

Target `.version-bump.json` (drops the `.cursor-plugin` and `.codex-plugin` entries):

```json
{
  "files": [
    { "path": "package.json", "field": "version" },
    { "path": ".claude-plugin/plugin.json", "field": "version" },
    { "path": ".claude-plugin/marketplace.json", "field": "plugins.0.version" },
    { "path": "gemini-extension.json", "field": "version" }
  ],
  "audit": {
    "exclude": [
      "CHANGELOG.md",
      "RELEASE-NOTES.md",
      "node_modules",
      ".git",
      ".version-bump.json",
      "scripts/bump-version.sh",
      "docs/bearpaws/specs",
      "docs/bearpaws/plans"
    ]
  }
}
```

(The `audit.exclude` adds `docs/bearpaws/specs` and `docs/bearpaws/plans` because spec/plan documents will mention prior versions like `superpowers v5.0.7` and shouldn't trigger drift alerts.)

- [ ] **Step 7.1: Replace package.json**

Run:
```bash
cat > /Users/brandon/Downloads/bearpaws/package.json <<'EOF'
{
  "name": "bearpaws",
  "version": "0.1.0",
  "type": "module"
}
EOF
```

- [ ] **Step 7.2: Replace .version-bump.json**

Run:
```bash
cat > /Users/brandon/Downloads/bearpaws/.version-bump.json <<'EOF'
{
  "files": [
    { "path": "package.json", "field": "version" },
    { "path": ".claude-plugin/plugin.json", "field": "version" },
    { "path": ".claude-plugin/marketplace.json", "field": "plugins.0.version" },
    { "path": "gemini-extension.json", "field": "version" }
  ],
  "audit": {
    "exclude": [
      "CHANGELOG.md",
      "RELEASE-NOTES.md",
      "node_modules",
      ".git",
      ".version-bump.json",
      "scripts/bump-version.sh",
      "docs/bearpaws/specs",
      "docs/bearpaws/plans"
    ]
  }
}
EOF
```

- [ ] **Step 7.3: Verify bump script reports clean state**

Run:
```bash
cd /Users/brandon/Downloads/bearpaws && bash scripts/bump-version.sh --check
```

Expected: every declared file reports version `0.1.0`. No drift warnings.

- [ ] **Step 7.4: Commit**

Run:
```bash
cd /Users/brandon/Downloads/bearpaws && \
git add package.json .version-bump.json && \
git commit -m "chore: rebrand package.json and trim .version-bump.json (drop cursor/codex)"
```

---

## Task 8: Rename `skills/using-superpowers/` → `skills/using-bearpaws/`

**Files:**
- Move: directory `skills/using-superpowers/` → `skills/using-bearpaws/`
- Modify: `skills/using-bearpaws/SKILL.md` (frontmatter `name:` and body references)

- [ ] **Step 8.1: Rename the directory via git**

Run:
```bash
cd /Users/brandon/Downloads/bearpaws && \
git mv skills/using-superpowers skills/using-bearpaws
```

Verify:
```bash
ls /Users/brandon/Downloads/bearpaws/skills/using-bearpaws/SKILL.md && \
[ ! -d /Users/brandon/Downloads/bearpaws/skills/using-superpowers ] && echo "OK"
```

Expected: SKILL.md path printed, then `OK`.

- [ ] **Step 8.2: Update the SKILL.md frontmatter `name:` field**

Inspect current frontmatter:
```bash
head -5 /Users/brandon/Downloads/bearpaws/skills/using-bearpaws/SKILL.md
```

Expected to show:
```
---
name: using-superpowers
description: ...
---
```

Replace `name: using-superpowers` with `name: using-bearpaws`:
```bash
cd /Users/brandon/Downloads/bearpaws && \
sed -i.bak '0,/^name: using-superpowers$/ s//name: using-bearpaws/' \
  skills/using-bearpaws/SKILL.md && \
rm skills/using-bearpaws/SKILL.md.bak
```

(The `0,/.../ s//.../` form replaces only the *first* occurrence — important because the body may legitimately reference the old name in attribution context.)

Verify:
```bash
grep -n "^name:" /Users/brandon/Downloads/bearpaws/skills/using-bearpaws/SKILL.md
```

Expected: `name: using-bearpaws` (single line).

- [ ] **Step 8.3: Update body references to `superpowers:` skill prefix**

The body of `SKILL.md` references `superpowers:using-superpowers` and similar fully-qualified skill names. Update to `bearpaws:` prefix.

Inspect:
```bash
grep -nE "superpowers:[a-z-]+" /Users/brandon/Downloads/bearpaws/skills/using-bearpaws/SKILL.md
```

Replace each `superpowers:` with `bearpaws:`:
```bash
cd /Users/brandon/Downloads/bearpaws && \
sed -i.bak -E 's/superpowers:([a-z-]+)/bearpaws:\1/g' skills/using-bearpaws/SKILL.md && \
rm skills/using-bearpaws/SKILL.md.bak
```

Verify zero remaining matches:
```bash
grep -E "superpowers:[a-z-]+" /Users/brandon/Downloads/bearpaws/skills/using-bearpaws/SKILL.md && \
  echo "FAIL: stale superpowers: prefixes remain" || echo "OK"
```

Expected: `OK`.

- [ ] **Step 8.4: Update body bare references to `using-superpowers` and "Superpowers"**

The body of using-bearpaws/SKILL.md may say things like *"your introduction to using skills"* and reference *"Superpowers"* as the product name. We update product-name references to "Bearpaws" but leave attribution (e.g., a comment crediting the upstream) intact when added by Task 17 (README rewrite).

Inspect current matches:
```bash
grep -nE "(using-superpowers|Superpowers|superpowers)" \
  /Users/brandon/Downloads/bearpaws/skills/using-bearpaws/SKILL.md
```

Replace **carefully**, line by line, using the Edit tool (not blind sed) because some references are deliberately abstract and shouldn't be renamed (e.g., a section title like *"Using Skills"* is fine; a phrase like *"your 'superpowers:using-superpowers' skill"* needs to become *"your 'bearpaws:using-bearpaws' skill"*).

For each match, decide:
- "Superpowers" the product name → "Bearpaws"
- `superpowers:using-superpowers` → `bearpaws:using-bearpaws`
- `using-superpowers` standalone → `using-bearpaws`
- generic word "superpowers" describing a feeling/capability → leave as-is *unless* the surrounding sentence is clearly about the plugin

Do these as individual `Edit` calls so each change is reviewable.

Verify after edits:
```bash
grep -nE "(using-superpowers|Superpowers)" \
  /Users/brandon/Downloads/bearpaws/skills/using-bearpaws/SKILL.md && \
  echo "Review remaining matches manually" || echo "OK: no plugin-name references left"
```

Expected ideally: `OK`. If matches remain, manually inspect each — they should be deliberate (e.g., attribution).

- [ ] **Step 8.5: Commit**

Run:
```bash
cd /Users/brandon/Downloads/bearpaws && \
git add skills/using-bearpaws/ && \
git commit -m "chore: rename using-superpowers skill to using-bearpaws"
```

---

## Task 9: Update `hooks/session-start` to point at `using-bearpaws/`

**Files:**
- Modify: `/Users/brandon/Downloads/bearpaws/hooks/session-start`

The current hook script reads `${PLUGIN_ROOT}/skills/using-superpowers/SKILL.md` (line 18) and references `superpowers` in its comment header (line 2), the legacy-warning logic (lines 12-14), and the wrapper text it injects (line 35). All of these need updating in Phase 0 *except* the wrapper-tag swap (`<EXTREMELY_IMPORTANT>` → `<warning level="hard">`) which is Phase 1's job.

- [ ] **Step 9.1: Update the comment header**

In `hooks/session-start`, line 2:

```
# SessionStart hook for superpowers plugin
```

→

```
# SessionStart hook for bearpaws plugin
```

Use the Edit tool:
- file_path: `/Users/brandon/Downloads/bearpaws/hooks/session-start`
- old_string: `# SessionStart hook for superpowers plugin`
- new_string: `# SessionStart hook for bearpaws plugin`

- [ ] **Step 9.2: Update the legacy-skills-warning path**

In `hooks/session-start`, line 12:

```
legacy_skills_dir="${HOME}/.config/superpowers/skills"
```

→

```
legacy_skills_dir="${HOME}/.config/bearpaws/skills"
```

Edit:
- old_string: `legacy_skills_dir="${HOME}/.config/superpowers/skills"`
- new_string: `legacy_skills_dir="${HOME}/.config/bearpaws/skills"`

- [ ] **Step 9.3: Update the legacy-warning text**

The warning_message string (line 14) mentions "Superpowers" and `~/.config/superpowers/skills` twice. Replace both.

Edit:
- old_string (the entire warning_message= line): the existing line containing `**WARNING:** Superpowers now uses Claude Code's skills system. Custom skills in ~/.config/superpowers/skills will not be read. Move custom skills to ~/.claude/skills instead. To make this message go away, remove ~/.config/superpowers/skills`
- new_string (same line, with three `superpowers` substring replacements): `**WARNING:** Bearpaws now uses Claude Code's skills system. Custom skills in ~/.config/bearpaws/skills will not be read. Move custom skills to ~/.claude/skills instead. To make this message go away, remove ~/.config/bearpaws/skills`

- [ ] **Step 9.4: Update the SKILL.md path**

In `hooks/session-start`, line 17 comment and line 18 path:

```
# Read using-superpowers content
using_superpowers_content=$(cat "${PLUGIN_ROOT}/skills/using-superpowers/SKILL.md" ...
```

→

```
# Read using-bearpaws content
using_bearpaws_content=$(cat "${PLUGIN_ROOT}/skills/using-bearpaws/SKILL.md" ...
```

The variable also gets renamed for clarity. Lines 33 and 35 use the variable:

```
using_superpowers_escaped=$(escape_for_json "$using_superpowers_content")
...
session_context="<EXTREMELY_IMPORTANT>\nYou have superpowers.\n\n**Below is the full content of your 'superpowers:using-superpowers' skill ... ${using_superpowers_escaped}\n\n${warning_escaped}\n</EXTREMELY_IMPORTANT>"
```

These three references (`using_superpowers_content`, `using_superpowers_escaped`, the `superpowers:using-superpowers` string in the wrapper) all become `using_bearpaws_*` and `bearpaws:using-bearpaws` respectively. The wrapper text "You have superpowers." becomes "You have bearpaws." (intentional pun preserved).

Make these edits one at a time using Edit tool. Use larger context strings to keep replacements unambiguous — for example replace the whole line containing the `cat` command rather than just the path fragment.

After all edits, verify:
```bash
grep -nE "(using_superpowers|using-superpowers|You have superpowers)" \
  /Users/brandon/Downloads/bearpaws/hooks/session-start && \
  echo "FAIL: stale superpowers references remain" || echo "OK"
```

Expected: `OK`.

- [ ] **Step 9.5: Smoke-test the hook script**

Run the hook directly with a stub plugin root to confirm it still produces valid JSON:

```bash
cd /Users/brandon/Downloads/bearpaws && \
CLAUDE_PLUGIN_ROOT="$(pwd)" bash hooks/session-start | jq . > /dev/null && echo OK
```

Expected: `OK`. (`jq .` with no output means the JSON parsed cleanly.)

If `jq` errors, the wrapper string likely has an unescaped quote — re-inspect the recent edits.

- [ ] **Step 9.6: Commit**

Run:
```bash
cd /Users/brandon/Downloads/bearpaws && \
git add hooks/session-start && \
git commit -m "chore: rename hook to read using-bearpaws and rebrand wrapper text"
```

---

## Task 10: Update slash command files

**Files:**
- Modify: `/Users/brandon/Downloads/bearpaws/commands/brainstorm.md`
- Modify: `/Users/brandon/Downloads/bearpaws/commands/execute-plan.md`
- Modify: `/Users/brandon/Downloads/bearpaws/commands/write-plan.md`

Each of these is a deprecation-shim file pointing users at the underlying skill (e.g., `superpowers:brainstorming`). Update the prefix to `bearpaws:`.

- [ ] **Step 10.1: Inspect current content of all three**

Run:
```bash
for f in brainstorm.md execute-plan.md write-plan.md; do
  echo "=== $f ==="
  cat /Users/brandon/Downloads/bearpaws/commands/$f
done
```

You'll see each file references one of: `superpowers brainstorming`, `superpowers:brainstorming`, `superpowers executing-plans`, `superpowers:executing-plans`, `superpowers writing-plans`, `superpowers:writing-plans`.

- [ ] **Step 10.2: Replace all `superpowers` occurrences in the three files**

Run:
```bash
cd /Users/brandon/Downloads/bearpaws && \
for f in commands/brainstorm.md commands/execute-plan.md commands/write-plan.md; do
  sed -i.bak -E 's/(superpowers)( |:)/bearpaws\2/g' "$f"
  rm "${f}.bak"
done
```

(The `\2` preserves whether the original used a space or a colon as the separator.)

- [ ] **Step 10.3: Verify zero stale references**

Run:
```bash
grep -nE "superpowers( |:)" /Users/brandon/Downloads/bearpaws/commands/*.md && \
  echo "FAIL" || echo "OK"
```

Expected: `OK`.

- [ ] **Step 10.4: Commit**

Run:
```bash
cd /Users/brandon/Downloads/bearpaws && \
git add commands/ && \
git commit -m "chore: rebrand slash commands to bearpaws: prefix"
```

---

## Task 11: Update test scripts (slug references and `/tmp` paths)

**Files:**
- Modify: `/Users/brandon/Downloads/bearpaws/tests/skill-triggering/run-test.sh`
- Modify (only if needed): files under `/Users/brandon/Downloads/bearpaws/tests/claude-code/`

The `run-test.sh` script has two superpowers-slug references (a comment and an output-dir path). The `claude-code/` test scripts may have similar.

- [ ] **Step 11.1: Find all stale references in tests/**

Run:
```bash
grep -rnE "(superpowers-tests|# Get the superpowers|superpowers plugin)" \
  /Users/brandon/Downloads/bearpaws/tests/ 2>/dev/null
```

Capture the output — these are the lines you need to edit.

- [ ] **Step 11.2: Apply replacements**

For `tests/skill-triggering/run-test.sh`:

Edit (using the Edit tool, not sed, to keep changes reviewable):
- `# Get the superpowers plugin root (two levels up from tests/skill-triggering)` → `# Get the bearpaws plugin root (two levels up from tests/skill-triggering)`
- `OUTPUT_DIR="/tmp/superpowers-tests/${TIMESTAMP}/skill-triggering/${SKILL_NAME}"` → `OUTPUT_DIR="/tmp/bearpaws-tests/${TIMESTAMP}/skill-triggering/${SKILL_NAME}"`

For each file in `tests/claude-code/` returned by Step 11.1, update similarly. Common patterns to expect:
- `/tmp/superpowers-tests/` → `/tmp/bearpaws-tests/`
- comment headers naming "superpowers" → "bearpaws"

Plugin-slug references in test prompts (text the model is asked to react to) should NOT be auto-replaced. If a prompt contains the literal string "superpowers", inspect whether it's testing a behavior tied to that name. If yes, decide case-by-case; most prompts under `tests/skill-triggering/prompts/` should be neutral.

Run a manual scan of test prompts:
```bash
grep -rln "superpowers" /Users/brandon/Downloads/bearpaws/tests/skill-triggering/prompts/ 2>/dev/null
```

If any matches return, open each and decide whether the reference is incidental (rename) or intentional (leave with comment).

- [ ] **Step 11.3: Verify no stale plugin-slug references remain in test infrastructure**

Run:
```bash
grep -rnE "superpowers-tests|# Get the superpowers|superpowers plugin" \
  /Users/brandon/Downloads/bearpaws/tests/ && echo "FAIL" || echo "OK"
```

Expected: `OK`.

- [ ] **Step 11.4: Commit**

Run:
```bash
cd /Users/brandon/Downloads/bearpaws && \
git add tests/ && \
git commit -m "chore: rebrand test scripts (paths + comments) for bearpaws"
```

---

## Task 12: Update `agents/code-reviewer.md` references

**Files:**
- Modify: `/Users/brandon/Downloads/bearpaws/agents/code-reviewer.md` (if it references superpowers)

- [ ] **Step 12.1: Inspect**

Run:
```bash
grep -nE "(superpowers|Superpowers)" /Users/brandon/Downloads/bearpaws/agents/code-reviewer.md
```

- [ ] **Step 12.2: Apply replacements case-by-case**

For each match, use the Edit tool — same rules as Step 8.4: product-name "Superpowers" → "Bearpaws"; `superpowers:<skill>` → `bearpaws:<skill>`. Don't blindly sed — some references may be intentional.

Verify:
```bash
grep -nE "(superpowers:|using-superpowers)" /Users/brandon/Downloads/bearpaws/agents/code-reviewer.md && \
  echo "FAIL" || echo "OK"
```

Expected: `OK`.

- [ ] **Step 12.3: Commit if anything changed**

Run:
```bash
cd /Users/brandon/Downloads/bearpaws && \
git diff --quiet agents/ || (git add agents/ && git commit -m "chore: rebrand agents/code-reviewer.md references")
```

---

## Task 13: Rewrite `CLAUDE.md`

**Files:**
- Modify: `/Users/brandon/Downloads/bearpaws/CLAUDE.md`

This is the project-instructions file. Current superpowers content describes superpowers' purpose, layout, bootstrap, version management, tests, and skill-editing conventions. Bearpaws keeps the structural sections but updates names, drops Cursor/Codex platform mentions, and adds a "Forked from superpowers" note. **The skill-editing TDD-on-prose discipline is preserved verbatim** — that section is one of the highest-value pieces of upstream content.

- [ ] **Step 13.1: Replace the file**

Run (using the Write tool, not bash heredoc, to keep formatting precise):

Write the new file with this exact content (the engineer should copy this verbatim into the Write tool):

```markdown
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Bearpaws is a Claude Code (and Gemini CLI) plugin that ships a library of behavior-shaping skills (TDD, debugging, planning, code review, parallel execution) plus domain-knowledge skills for Google Cloud, Google ADK, Vite, JS/TypeScript, and Cloud Run. It is a hard fork of [superpowers](https://github.com/obra/superpowers) v5.0.7 — credit to Jesse Vincent and contributors for the original. The plugin's job is to inject the `using-bearpaws` bootstrap at session start so the agent learns to discover and invoke the rest of the skills via the `Skill` tool.

## Repository layout

- [skills/](skills/) — one directory per skill, each with a `SKILL.md` and optional `references/`, `examples/`, `scripts/`. Flat namespace.
- [commands/](commands/) — slash commands. The current files are deprecation shims pointing users at the equivalent skills.
- [agents/](agents/) — subagent definitions (e.g. `code-reviewer`).
- [hooks/](hooks/) — `SessionStart` hook that injects the bootstrap.
- [.claude-plugin/](.claude-plugin/) — Claude Code plugin manifest and dev marketplace.
- [gemini-extension.json](gemini-extension.json) — Gemini CLI extension manifest.
- [scripts/](scripts/) — version-bump tooling.
- [tests/claude-code/](tests/claude-code/) — behavioral tests that shell out to the `claude` CLI.
- [tests/skill-triggering/](tests/skill-triggering/) — naive-prompt tests that verify skills auto-trigger.
- [docs/bearpaws/specs/](docs/bearpaws/specs/) — design specs.
- [docs/bearpaws/plans/](docs/bearpaws/plans/) — implementation plans.

## How the bootstrap works

The plugin manifest [.claude-plugin/plugin.json](.claude-plugin/plugin.json) registers the [hooks/hooks.json](hooks/hooks.json) `SessionStart` hook (matchers: `startup|clear|compact`). That hook calls [hooks/run-hook.cmd](hooks/run-hook.cmd) → [hooks/session-start](hooks/session-start), which:

1. Reads [skills/using-bearpaws/SKILL.md](skills/using-bearpaws/SKILL.md).
2. Wraps it in an `<EXTREMELY_IMPORTANT>` block (Phase 0; replaced with `<warning level="hard">` in Phase 1 per the XML-schema spec).
3. Emits JSON in the shape Claude Code expects: `{ "hookSpecificOutput": { "hookEventName": "SessionStart", "additionalContext": "..." } }`.

[hooks/run-hook.cmd](hooks/run-hook.cmd) is a bash/cmd polyglot so the same file works on macOS/Linux and Windows. Hook scripts under [hooks/](hooks/) are intentionally **extensionless** — Claude Code's Windows auto-detection prepends `bash` to anything ending in `.sh`, which would double-wrap the call.

If you change the bootstrap shape or the JSON output, run a fresh Claude Code session against this checkout (registered via `--plugin-dir` or the dev marketplace) and confirm the `using-bearpaws` content arrives in the first turn.

## Version management

The plugin version is duplicated across four manifest fields. They are kept in sync by [scripts/bump-version.sh](scripts/bump-version.sh), driven by [.version-bump.json](.version-bump.json):

```bash
scripts/bump-version.sh --check       # report current versions, detect drift
scripts/bump-version.sh --audit       # check + grep repo for stray version strings
scripts/bump-version.sh 0.2.0         # bump every declared file
```

Never hand-edit a version in one manifest — `--check` will flag the drift and `--audit` will surface any undeclared file that mentions the old version.

## Tests

Tests are behavioral, not unit — they invoke the `claude` CLI in headless mode and assert against transcripts. Requires the local plugin to be registered (e.g. `"bearpaws@bearpaws-dev": true` in `~/.claude/settings.json`, or pass `--plugin-dir` explicitly).

```bash
tests/claude-code/run-skill-tests.sh                                          # fast skill-content tests (~2 min)
tests/claude-code/run-skill-tests.sh --integration                            # full subagent-driven-dev run (10–30 min)
tests/claude-code/run-skill-tests.sh -t test-subagent-driven-development.sh   # single test
tests/claude-code/run-skill-tests.sh --verbose                                # stream Claude output
tests/skill-triggering/run-all.sh                                             # verify naive prompts trigger the right skill
```

[tests/skill-triggering/run-test.sh](tests/skill-triggering/run-test.sh) parses `stream-json` output for `"name":"Skill"` plus a matching `"skill":"..."` value — that's how it decides a skill triggered. Logs land under `/tmp/bearpaws-tests/<timestamp>/`.

## When editing skills

Skills are behavior-shaping code, not prose. Use the `bearpaws:writing-skills` skill — it applies TDD to skill content:

1. Run a baseline pressure scenario in a fresh subagent (RED).
2. Capture the exact rationalization the agent uses to skip the right behavior.
3. Write the minimum skill text that closes that loophole (GREEN).
4. Re-run the scenario in a fresh subagent and confirm compliance.
5. Probe for new rationalizations and repeat.

The Red Flags tables, rationalization lists, and the deliberate "your human partner" phrasing in existing skills are tuned content — change them only with eval evidence that the new wording works better, not because the prose reads cleaner.

## Skill structure

Each skill is a directory under [skills/](skills/) containing `SKILL.md` with YAML frontmatter:

```markdown
---
name: skill-name-with-hyphens
description: Use when [specific triggering conditions and symptoms]
---
```

Constraints worth knowing before editing frontmatter:

- `description` is third-person and describes **when** to use the skill, not what it does. The matcher uses it to decide whether to load.
- Frontmatter total ≤ 1024 chars; `name` is letters/numbers/hyphens only.
- Heavy reference material (>100 lines) and reusable scripts go in sibling files; keep `SKILL.md` focused on the rule.

See [skills/writing-skills/SKILL.md](skills/writing-skills/SKILL.md) and [skills/writing-skills/anthropic-best-practices.md](skills/writing-skills/anthropic-best-practices.md) for the full conventions. The XML-schema migration described in [docs/bearpaws/specs/2026-04-30-bearpaws-fork-design.md](docs/bearpaws/specs/2026-04-30-bearpaws-fork-design.md) §2 lands in Phase 1; until then, skill bodies remain in the legacy markdown-with-ad-hoc-tags form inherited from superpowers.
```

Use the Write tool to write that exact content to `/Users/brandon/Downloads/bearpaws/CLAUDE.md`.

- [ ] **Step 13.2: Verify no stale references**

Run:
```bash
grep -nE "superpowers-tests|using-superpowers|superpowers:[a-z]" \
  /Users/brandon/Downloads/bearpaws/CLAUDE.md && echo "FAIL" || echo "OK"
```

Expected: `OK`. The intentional `superpowers` mentions (the attribution paragraph and the GitHub link) should remain — they don't match the FAIL patterns above.

- [ ] **Step 13.3: Commit**

Run:
```bash
cd /Users/brandon/Downloads/bearpaws && \
git add CLAUDE.md && \
git commit -m "docs: rewrite CLAUDE.md for bearpaws identity (preserves attribution)"
```

---

## Task 14: Rewrite `README.md`

**Files:**
- Modify: `/Users/brandon/Downloads/bearpaws/README.md`

The Bearpaws README is shorter than CLAUDE.md and aimed at install/quickstart. It must include the superpowers attribution paragraph mandated by §1 of the spec.

- [ ] **Step 14.1: Write new README content**

Use the Write tool to replace `/Users/brandon/Downloads/bearpaws/README.md` with:

```markdown
# Bearpaws

A Claude Code (and Gemini CLI) plugin that ships a library of behavior-shaping skills — TDD, debugging, planning, code review — plus domain-knowledge skills for Google Cloud, Google ADK, Vite, JS/TypeScript, and Cloud Run.

> **Status:** v0.1.0. Phase 0 of a four-phase fork program (see [docs/bearpaws/specs/](docs/bearpaws/specs/)). Skill bodies are still in legacy markdown form; XML-schema migration arrives in Phase 1, domain skills in Phase 2.

## Install (Claude Code)

Register the plugin via the dev marketplace in `~/.claude/settings.json`:

```json
{
  "plugins": {
    "bearpaws@bearpaws-dev": true
  },
  "marketplaces": {
    "bearpaws-dev": "/path/to/bearpaws"
  }
}
```

Or pass it on the command line: `claude --plugin-dir /path/to/bearpaws`.

## Install (Gemini CLI)

Bearpaws ships a `gemini-extension.json` so it can also be loaded as a Gemini CLI extension. Refer to the Gemini CLI documentation for extension installation.

## Tests

```bash
tests/skill-triggering/run-all.sh           # ~2 min — verifies skills auto-trigger on naive prompts
tests/claude-code/run-skill-tests.sh        # ~2 min — fast skill-content tests
tests/claude-code/run-skill-tests.sh --integration   # 10–30 min — full integration suite
```

## Attribution

Bearpaws is a hard fork of **[superpowers](https://github.com/obra/superpowers)** at v5.0.7 by Jesse Vincent and contributors, released under the MIT license. The Bearpaws fork preserves the same license and credits the original authors. Subsequent changes (token-efficiency pass, XML schema migration, domain-knowledge skills, Cursor/Codex platform drop) are documented in [docs/bearpaws/specs/](docs/bearpaws/specs/).

## License

MIT — see [LICENSE](LICENSE).
```

- [ ] **Step 14.2: Verify and commit**

Run:
```bash
grep -E "^# Bearpaws$" /Users/brandon/Downloads/bearpaws/README.md && \
grep -E "hard fork.*superpowers" /Users/brandon/Downloads/bearpaws/README.md && \
echo "OK"
```

Expected: title line printed, attribution line printed, `OK`.

```bash
cd /Users/brandon/Downloads/bearpaws && \
git add README.md && \
git commit -m "docs: rewrite README.md for bearpaws (with superpowers attribution)"
```

---

## Task 15: Repo-wide audit for stale plugin-name references

**Files:** scan-only across `/Users/brandon/Downloads/bearpaws/`.

This task catches anything we missed. The expected output is **zero unexpected matches** — we've enumerated where `superpowers` legitimately remains (attribution in CLAUDE.md, README.md, the plugin description) and everything else should have been replaced.

- [ ] **Step 15.1: Run the bump-script audit**

Run:
```bash
cd /Users/brandon/Downloads/bearpaws && bash scripts/bump-version.sh --audit
```

Expected: clean output. The audit checks for stray version strings, not plugin-name strings, but it's a useful sanity check.

- [ ] **Step 15.2: Run a plugin-name grep**

Run:
```bash
cd /Users/brandon/Downloads/bearpaws && \
grep -rnE "(superpowers:[a-z-]|using-superpowers|/tmp/superpowers-tests|superpowers-dev)" \
  --include='*.md' --include='*.sh' --include='*.json' --include='*.cmd' \
  --include='session-start' \
  . 2>/dev/null | grep -v -E "(README\.md|CLAUDE\.md|docs/bearpaws/specs|docs/bearpaws/plans)"
```

Expected: zero output. (We exclude documents that legitimately discuss superpowers as the upstream — README/CLAUDE attribution and spec/plan docs.)

If any matches print, fix each one with Edit/sed, then re-run.

- [ ] **Step 15.3: Run a "Superpowers" (capitalized product name) grep**

Run:
```bash
cd /Users/brandon/Downloads/bearpaws && \
grep -rn "Superpowers" \
  --include='*.md' --include='*.sh' \
  . 2>/dev/null | grep -v -E "(README\.md|CLAUDE\.md|docs/bearpaws/specs|docs/bearpaws/plans|attribution)"
```

Expected: zero unintended matches. As before, the attribution-bearing files are excluded.

- [ ] **Step 15.4: Commit if any cleanup edits were applied during this task**

Run:
```bash
cd /Users/brandon/Downloads/bearpaws && \
git diff --quiet || (git add -A && git commit -m "chore: cleanup stale plugin-name references found during audit")
```

---

## Task 16: Run `tests/skill-triggering/` against the renamed plugin

**Files:** read-only execution (test results).

The skill-triggering suite is the primary Phase 0 exit criterion. Total runtime ~2 minutes.

- [ ] **Step 16.1: Register bearpaws as a plugin in Claude Code settings (if not already)**

Edit `~/.claude/settings.json` to include:

```json
{
  "plugins": {
    "bearpaws@bearpaws-dev": true
  },
  "marketplaces": {
    "bearpaws-dev": "/Users/brandon/Downloads/bearpaws"
  }
}
```

(Add to existing config — don't replace.)

Verify:
```bash
jq '.plugins["bearpaws@bearpaws-dev"], .marketplaces["bearpaws-dev"]' ~/.claude/settings.json
```

Expected: `true` and `"/Users/brandon/Downloads/bearpaws"`.

- [ ] **Step 16.2: Run the skill-triggering suite**

Run:
```bash
cd /Users/brandon/Downloads/bearpaws && bash tests/skill-triggering/run-all.sh
```

Expected: every skill in the `SKILLS` array (currently 6 skills: `systematic-debugging`, `test-driven-development`, `writing-plans`, `dispatching-parallel-agents`, `executing-plans`, `requesting-code-review`) reports a passing trigger test.

If the run fails: inspect logs under `/tmp/bearpaws-tests/<timestamp>/skill-triggering/`. Common failure modes for a renamed plugin:
- Skill not loaded → check that the plugin is registered and `claude` is reading the right config
- Skill triggered with wrong prefix → check that the test isn't asserting `superpowers:<skill>` — the harness greps for the skill *name* (not the prefix), so the rename should be transparent

- [ ] **Step 16.3: Commit a test-result note** (optional but recommended)

If you want to record the baseline, append to `docs/bearpaws/release-notes/0.1.0.md` (create the file):

```markdown
# Bearpaws v0.1.0 — Release Notes

**Phase:** 0 (Fork & Rebrand)
**Date:** YYYY-MM-DD
**Source:** superpowers v5.0.7

## Skill-triggering test baseline

All 6 skills in tests/skill-triggering/run-all.sh trigger correctly:
- systematic-debugging: PASS
- test-driven-development: PASS
- writing-plans: PASS
- dispatching-parallel-agents: PASS
- executing-plans: PASS
- requesting-code-review: PASS

## Changes from superpowers v5.0.7

- Plugin slug: superpowers → bearpaws
- Dropped platforms: Cursor, OpenAI Codex
- Dropped reference docs: copilot-tools.md, codex-tools.md
- Renamed skill: using-superpowers → using-bearpaws
- Hook namespace: superpowers → bearpaws
- Slash commands: superpowers:* → bearpaws:*
- Manifest count: 6 → 4

No skill body content changed.
```

Replace `YYYY-MM-DD` with today's date (`date +%Y-%m-%d`).

```bash
cd /Users/brandon/Downloads/bearpaws && \
mkdir -p docs/bearpaws/release-notes && \
git add docs/bearpaws/release-notes/0.1.0.md && \
git commit -m "docs: record v0.1.0 release notes (Phase 0 baseline)"
```

---

## Task 17: Run fast `tests/claude-code/` against the renamed plugin

**Files:** read-only execution.

The fast skill-content tests run in ~2 minutes. They're the second Phase 0 exit criterion.

- [ ] **Step 17.1: Run the fast suite**

Run:
```bash
cd /Users/brandon/Downloads/bearpaws && bash tests/claude-code/run-skill-tests.sh
```

Expected: all tests pass.

If failures: inspect logs (the harness prints log paths). Most common Phase 0 failure mode is a test asserting on `/tmp/superpowers-tests/<timestamp>/...` — re-run Task 11 grep to ensure no stale paths.

- [ ] **Step 17.2: Run the integration suite (one-time, optional but recommended)**

The integration suite takes 10–30 minutes. Run once at the end of Phase 0 to confirm the broader workflow tests pass.

```bash
cd /Users/brandon/Downloads/bearpaws && bash tests/claude-code/run-skill-tests.sh --integration
```

Expected: passes. If it fails, do not block Phase 0 ship on it — record the failure and triage in Phase 1 setup. (Phase 0's primary exit gate is skill-triggering; the integration suite is a defense-in-depth check.)

---

## Task 18: Verify plugin loads in Gemini CLI

**Files:** read-only execution; this is the second half of Phase 0's exit criteria (per spec §5 Phase 0).

- [ ] **Step 18.1: Confirm Gemini CLI is installed**

Run:
```bash
command -v gemini && gemini --version
```

Expected: a Gemini CLI version string. If Gemini CLI isn't installed, install it per Google's docs, then return.

- [ ] **Step 18.2: Register Bearpaws as a Gemini extension**

Refer to current Gemini CLI extension documentation for the exact registration mechanism (this varies by Gemini CLI version). At minimum, ensure Gemini CLI can locate `/Users/brandon/Downloads/bearpaws/gemini-extension.json` and the contextFileName `GEMINI.md` resolves.

- [ ] **Step 18.3: Smoke-test a single Gemini session**

Open Gemini CLI in `/Users/brandon/Downloads/bearpaws/`. The bootstrap should activate via the `SessionStart` hook (assuming Gemini CLI honors the same hook mechanism as Claude Code per the polyglot script in `hooks/run-hook.cmd`). Confirm the agent receives the `using-bearpaws` content.

If Gemini CLI's hook mechanism differs from Claude Code's: this is **R8** in the spec's risk register. The fallback is documented in spec §6 ("If Gemini can't parse our schema, we add a Gemini-specific transformation in `hooks/run-hook.cmd`"). For Phase 0, content hasn't changed, so the Gemini path should behave identically to its superpowers behavior.

- [ ] **Step 18.4: Record the Gemini smoke-test result**

Append to `docs/bearpaws/release-notes/0.1.0.md`:

```markdown
## Gemini CLI verification

Gemini CLI (version: <the version printed in 18.1>) loads bearpaws and the using-bearpaws bootstrap appears in the first session turn: PASS / FAIL <details if failure>
```

```bash
cd /Users/brandon/Downloads/bearpaws && \
git add docs/bearpaws/release-notes/0.1.0.md && \
git commit -m "docs: record Gemini CLI verification result for v0.1.0"
```

---

## Task 19: Tag and confirm Phase 0 exit

**Files:** none (git operations only).

- [ ] **Step 19.1: Confirm working tree is clean**

Run:
```bash
cd /Users/brandon/Downloads/bearpaws && git status
```

Expected: `nothing to commit, working tree clean`.

- [ ] **Step 19.2: Confirm version bump check is clean**

Run:
```bash
cd /Users/brandon/Downloads/bearpaws && bash scripts/bump-version.sh --check
```

Expected: every declared file at version `0.1.0`. No drift.

- [ ] **Step 19.3: Tag v0.1.0**

Run:
```bash
cd /Users/brandon/Downloads/bearpaws && git tag -a v0.1.0 -m "Bearpaws v0.1.0 — Phase 0 (Fork & Rebrand)"
```

Verify:
```bash
git tag --list -n
```

Expected: `v0.1.0  Bearpaws v0.1.0 — Phase 0 (Fork & Rebrand)`.

- [ ] **Step 19.4: Confirm Phase 0 exit criteria are met**

Spec §5 Phase 0 exit:
1. ☐ All existing skill-triggering tests pass against the renamed plugin (Task 16 result).
2. ☐ Plugin loads in Gemini CLI without error (Task 18 result).

Mark each box based on Tasks 16 and 18. **Both must be PASS to proceed to Phase 1.** If either is FAIL, do not tag — fix and rerun.

---

## Self-Review (run before handing this plan to an executor)

Per writing-plans skill discipline:

**1. Spec coverage.** Walk spec §5 Phase 0 deliverables and check each maps to a task above:

| Spec deliverable | Plan task |
|---|---|
| New repo `bearpaws/` per §1 layout | Task 1 |
| Manifests slimmed to Claude+Gemini | Tasks 4, 5, 6, 7 |
| `.version-bump.json` updated | Task 7 |
| Hook namespace renamed to `bearpaws-session-start` | Task 9 (path/text rename in script; the hook *event* name `SessionStart` is unchanged because that's a Claude Code-defined event, not a plugin namespace — the plugin identity is what changes) |
| `skills/using-superpowers/` → `skills/using-bearpaws/` | Task 8 |
| Per-platform reference docs trimmed | Task 2 |
| `commands/` renamed to `bearpaws:` slash commands | Task 10 |
| README + CLAUDE.md rewritten | Tasks 13, 14 |
| Tests pass against renamed plugin | Tasks 16, 17 |
| Plugin loads in Gemini CLI | Task 18 |

All deliverables covered.

**2. Placeholder scan.** The only intentional placeholder is `<TBD>` in `homepage`/`repository` URLs in plugin.json (Task 4). Documented as "pinned to a real future action" — engineer instructed to replace once GitHub repo is created. No other TBDs, TODOs, or "fill in later"s.

**3. Type/identifier consistency.** Plugin slug is consistently `bearpaws` (lowercase). Marketplace slug is `bearpaws-dev`. Skill directory is `using-bearpaws`. Slash command prefix is `bearpaws:`. Hook script reads `using-bearpaws/SKILL.md`. All match.

**4. One thing the engineer must not do.** Do not run `sed` blindly across the entire `bearpaws/` tree replacing `superpowers` with `bearpaws` — we deliberately preserve attribution and upstream-credit references in CLAUDE.md, README.md, and spec/plan docs. The audit task (15) excludes those files from the FAIL pattern for this reason.

---

## Roadmap — Phases 1–3 (preview only; each gets its own dedicated plan)

> **Why these are not detailed task-by-task here:** Phase 1's vertical-slice eval results will inform Phase 2 batching cadence; Phase 2's measurements may surface schema or `_shared/` extraction adjustments that change Phase 3's scope. Writing detailed Phase 2/3 tasks now would harden assumptions we have explicitly chosen to validate empirically. Detailed plans for each phase land in `docs/bearpaws/plans/` after the prior phase ships.

### Phase 1 — Vertical Slice (`bearpaws@0.2.0`)

Spec reference: §5 Phase 1.

**Goal:** Validate the XML schema, `skills/_shared/` library, lazy-load convention (`<include>` / `<see>`), and eval workflow on a controlled set of skills before scaling.

**Skills touched:**
- `skills/using-bearpaws/SKILL.md` — bootstrap rewritten to XML schema, target ~60 lines
- `skills/test-driven-development/SKILL.md` — migrated to XML, condensed to ~250 lines
- `skills/cloud-run/` (new) — domain reference skill
- `skills/deploying-to-cloud-run/` (new) — domain workflow skill

**Other deliverables:**
- `skills/_shared/` populated with the 5 extractions enumerated in spec §3a
- Hook script wraps injection in `<warning level="hard">` instead of `<EXTREMELY_IMPORTANT>`
- Schema-validator test (grep-based, fails on unknown tags)
- Token-measurement script
- Skill-triggering tests for the 4 new/migrated skills

**Exit gates** (spec §5 Phase 1):
1. Bootstrap eval ≥ baseline (writing-skills pressure scenarios in fresh subagents)
2. TDD eval ≥ baseline
3. Cloud Run pair triggers on naive prompts
4. Bootstrap shrink ≥ 40%

**Plan filename:** `docs/bearpaws/plans/<date>-bearpaws-phase-1-vertical-slice.md` (written after Phase 0 ships).

### Phase 2 — Parallel Tracks (`bearpaws@0.5.0`)

Spec reference: §5 Phase 2.

**Track A — XML migration of remaining 14 process skills**, in 4 batches:
- A.1: brainstorming, writing-plans, writing-skills (largest single token win)
- A.2: systematic-debugging, verification-before-completion, executing-plans
- A.3: requesting-code-review, receiving-code-review, finishing-a-development-branch
- A.4: subagent-driven-development, dispatching-parallel-agents, using-git-worktrees

**Track B — Build remaining 8 domain skills**, in 4 batches:
- B.1: vite + working-with-vite
- B.2: javascript-typescript + writing-typescript
- B.3: google-cloud + working-on-google-cloud
- B.4: google-adk + building-with-adk

**Coordination rule:** if Track A discovers a schema flaw, Track B pauses at next batch boundary; schema adjusts once, then both tracks resume.

**Exit gates** (spec §5 Phase 2):
- All 25 skills (15 process + 10 domain) in XML schema
- Schema validator passes for the whole `skills/` tree
- All skill-triggering tests pass
- Aggregate suite-wide content reduction ≥ 25%

**Plan filename:** `docs/bearpaws/plans/<date>-bearpaws-phase-2-parallel-tracks.md` (written after Phase 1 ships).

### Phase 3 — Integration & Release (`bearpaws@1.0.0`)

Spec reference: §5 Phase 3.

**Deliverables:**
- Heavy-reference demotions to `<see>` (spec §3b)
- Full integration suite run (`tests/claude-code/run-skill-tests.sh --integration`)
- Transcript audit: 5 normal sessions sampled; confirm `<see>`-demoted files unread by default
- Final token measurement documented in `docs/bearpaws/release-notes/1.0.0.md`
- README final pass
- Coordinated version bump to `1.0.0`

**Exit gates** (spec §5 Phase 3):
- All tests pass (skill-triggering + integration)
- `<see>`-demoted files confirmed unread by default
- Final token-reduction numbers within target bands or explicit ship-decision conversation

**Plan filename:** `docs/bearpaws/plans/<date>-bearpaws-phase-3-integration.md` (written after Phase 2 ships).
