# Design: One `.agents/skills` Target, OpenCode Support, Spec Check

Date: 2026-09-28
Status: Approved (brainstorming)
Target release: 2.3.0 (unreleased branch `feat/llm-state-alignment-649e48`)

## Goal

Replace per-agent skill wiring with the cross-agent `.agents/skills/` convention, add experimental OpenCode support, retire Windsurf, and guard portability with an Agent Skills spec check. The change should remove code overall, in line with the mantra: low-token, portable, simple.

## Evidence

- `.agents/skills/` and `~/.agents/skills/` are scanned by Codex, Devin (Cascade), OpenCode, Cursor, VS Code Copilot, Gemini CLI, and others.
- Devin/Cascade docs (`docs.devin.ai/desktop/cascade/skills`) list `.agents/skills/` and `~/.agents/skills/` as cross-agent locations. `docs.windsurf.com` now redirects to Devin. Windsurf is retired.
- OpenCode (`opencode.ai/docs/skills`) scans `.agents/skills/` and `~/.agents/skills/` and invokes skills with a native `skill` tool. It enforces `name` matching `^[a-z0-9]+(-[a-z0-9]+)*$` (1–64 characters, equal to the folder name) and a `description` of 1–1024 characters.
- OpenCode (`opencode.ai/docs/config`) loads always-on context from the `instructions` array in `~/.config/opencode/opencode.json`. Paths may be absolute or start with `~`.
- Codex follows symlinked skill folders.

## Design

### 1. Install surface (`install.sh`)

- Rename `--codex` to `--agents`. It requires `--global` and links each `skills/<name>/` into `~/.agents/skills/`, removing only broken links.
- Delete `--devin`, `--windsurf`, `--all`, `install_devin`, and `install_windsurf`.
- With no platform flag, print usage and exit 1.
- Remaining flags: `--antigravity`, `--agents`, `--global`, and `--help`.
- After `--agents`, print the OpenCode bootstrap snippet. Do **not** edit the user's OpenCode config: it is user-owned, and merging JSON adds complexity.

### 2. Repo files

- Delete `.windsurf/` (the rule file and 15 skill links).
- Delete the `.devin/skills/*` links (15). Keep `.devin/hooks.v1.json`, because the SessionStart hook is still Devin for Terminal's only automatic bootstrap.
- Keep the committed `.agents/skills -> ../skills` link.

### 3. OpenCode (experimental)

- Skills: covered by `install.sh --agents --global`, or by `.agents/skills` when working inside this repo.
- Bootstrap: the user adds one line to `~/.config/opencode/opencode.json`:
  ```json
  { "instructions": ["~/.agents/skills/using-bearpaws/SKILL.md"] }
  ```
- No OpenCode plugin (JS), because it isn't needed while `instructions` works.

### 4. Bootstrap (`skills/using-bearpaws/SKILL.md`)

Replace the Devin/Windsurf line and the Codex line with one line:

> **In other Agent Skills agents (Codex, Devin, OpenCode, Cursor, Copilot, …):** Skills live in `.agents/skills/` or `~/.agents/skills/`. Load one with your native skill tool (`skill` in OpenCode) or by reading its `SKILL.md`; users can also type `$skill-name` (Codex) or `/skill-name` (Devin CLI).

Net: one line shorter.

### 5. Support tiers (README, CLAUDE.md, `docs/agent-support.md`)

| Agent | Status | Evidence |
|---|---|---|
| Claude Code | Primary | Working |
| Google Antigravity IDE | Primary | Native plugin, skills, subagents, capability adapter |
| OpenCode | Experimental | Native `.agents/skills` discovery + `instructions` bootstrap |
| Other Agent Skills agents (Codex, Devin, Cursor, Copilot, …) | Experimental | Native `.agents/skills` discovery; `install.sh --agents --global` |

The Windsurf row is removed. The Devin SessionStart hook is noted under "Other Agent Skills agents".

### 6. Spec check (`tests/schema-validator/run-validator.sh`)

For each `skills/*/SKILL.md`, fail if:
- the `name` frontmatter is missing, does not match `^[a-z0-9]+(-[a-z0-9]+)*$`, is longer than 64 characters, or differs from the folder name;
- `description` is missing, empty, or longer than 1024 characters.

It already runs in CI and adds no new dependencies (bash + awk/grep).

### 7. Tests

- `tests/install/run-install-tests.sh`:
  - Drop the Devin/Windsurf block and rename the Codex block to `--agents`.
  - Assert that no flags exits non-zero.
  - Assert that `--agents` output contains the OpenCode `instructions` snippet.
- Validator: a negative test proving a bad `name` fails (temporary fixture, not committed).
- Manual smoke tests (installed locally): `opencode run` and `codex exec` in a temp repo with `.agents/skills` confirm that `using-bearpaws` is discovered. Record the results in `docs/agent-support.md`.

### 8. Docs

- Remove Windsurf and Devin-symlink wording from README, CLAUDE.md, `docs/agent-support.md`, `docs/skill-structure.md`, and `tests/brainstorm-server/windows-lifecycle.test.sh` if its mention is Windsurf-specific.
- Fold everything into `docs/bearpaws/release-notes/2.3.0.md`, following the 2.2.0 precedent for retiring Gemini CLI in a minor release.

## Out of scope

- Cursor and Copilot branches in `hooks/session-start` (unchanged).
- An OpenCode JS plugin, and per-agent tool-mapping references for Codex, OpenCode, or Devin.
- Automatic edits to user agent configs.

## Error handling

- `--agents` or `--antigravity` without `--global`: error with a usage hint, exit 1.
- Broken links in `~/.agents/skills/`: removed; valid foreign links are preserved (existing test).
- The validator prints the file and the rule broken, and exits 1.

## Success criteria

- All static suites pass: validator, installer, Antigravity adapter, token measurement, version check.
- The fast Claude skill test passes.
- The OpenCode and Codex smoke tests discover `using-bearpaws` from `.agents/skills`.
- The net line count goes down.
