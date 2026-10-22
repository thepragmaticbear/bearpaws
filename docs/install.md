# Installing Bearpaws

Claude Code and Google Antigravity IDE are the primary supported targets. Every other agent on this page is experimental: the wiring exists and some of it is checked in CI, but behavior is not proven enough for strong claims. See [agent-support.md](agent-support.md) for the evidence behind each status.

## Claude Code

From GitHub:

```bash
claude plugin marketplace add thepragmaticbear/bearpaws
claude plugin install bp@bearpaws
```

From a local checkout:

```bash
claude plugin marketplace add /path/to/bearpaws
claude plugin install bp@bearpaws
```

Or pass it on the command line without installing: `claude --plugin-dir /path/to/bearpaws`.

The risk gate (the `Stop` hook that enforces the risk receipt and the elevated-risk review) needs `jq`. Without it, the gate prints a note and does nothing. Set `BEARPAWS_ENFORCE=0` to turn it off.

## Git gate (any agent)

From a Bearpaws checkout, run the installer inside the repository you want to gate:

```bash
cd /path/to/your/repo
/path/to/bearpaws/install.sh --git
```

It writes a `commit-msg` hook (in `.git/hooks/`, or `core.hooksPath` if set) that runs the checkout's `hooks/git-commit-msg`, so updating the checkout updates the gate. Commits with staged changes then need the risk receipt in the message. It refuses to replace a `commit-msg` hook it did not write and prints the line to chain it instead. Bypass with `git commit --no-verify` or `BEARPAWS_ENFORCE=0`; remove it by deleting the hook. It needs only bash and git 2.31 or later. A clean cherry-pick or revert does not run `commit-msg`, so the gate does not see it; one that stops on a conflict carries the original message, so for a pre-gate commit finish it with `git commit --no-verify` (or `BEARPAWS_ENFORCE=0`).

### Recommended Claude Code setup

For non-trivial work, Bearpaws pairs well with Claude Code's built-in `/model opusplan` setting: Claude Code uses Opus in native Plan Mode and Sonnet for execution, in the same session. Bearpaws governs how planning and implementation are done; Claude Code chooses the model for each phase. `opusplan` is recommended, not required, and Bearpaws never switches models itself.

```text
Plan Mode: bp:writing-plans (read-only) -> you approve -> plan saved to docs/bearpaws/plans/ -> subagent-driven-development or executing-plans -> review + verification
```

Plan approval counts as the go-ahead; Bearpaws does not ask a second time. See [`skills/using-bearpaws/references/claude-code.md`](../skills/using-bearpaws/references/claude-code.md).

## Google Antigravity IDE

Clone Bearpaws:

```bash
git clone https://github.com/thepragmaticbear/bearpaws.git
cd bearpaws
```

Install globally:

```bash
./install.sh --antigravity --global
```

Bearpaws installs as a native Antigravity plugin to:
`~/.gemini/config/plugins/bearpaws/`

Restart Antigravity.

### Verify

Type:
```
/brain
```
Confirm `brainstorming` appears in the skill list.

### Update

```bash
git pull
./install.sh --antigravity --global
```

### Uninstall

```bash
rm -rf ~/.gemini/config/plugins/bearpaws
```

Bearpaws uses native Antigravity plugin packaging, rules, skills, and subagents — not Gemini CLI compatibility mode.

## Experimental: OpenCode, Codex, Grok Build, Devin, Cursor, Copilot, …

Codex, Devin, OpenCode, and other Agent Skills agents read `~/.agents/skills/`. One command links every Bearpaws skill there without touching unrelated skills:

```bash
./install.sh --agents --global
```

Restart your agent and invoke `using-bearpaws` (`skill` tool in OpenCode, `$using-bearpaws` in Codex, `/using-bearpaws` in Devin CLI) to confirm discovery. This repo also ships `.agents/skills/` (per-skill links into `skills/`) for sessions inside the checkout. Repo-local discovery through `.agents/skills` needs git symlinks enabled (`core.symlinks=true`; Developer Mode on Windows).

**OpenCode bootstrap:** merge into `~/.config/opencode/opencode.json` so the bootstrap loads every session:

```json
"instructions": ["~/.agents/skills/using-bearpaws/SKILL.md"]
```

**Codex bootstrap:** add this line to `~/.codex/AGENTS.md` so Codex loads the bootstrap every session:

```text
Before responding to any request, read `~/.agents/skills/using-bearpaws/SKILL.md` and follow it.
```

The installer prints both snippets and never edits your agent config.

**Grok Build:** one command links the skills and adds a bootstrap rule that Grok loads in every project:

```bash
./install.sh --grok --global      # writes ~/.grok/rules/bearpaws.md ($GROK_HOME/rules/ if set)
grok inspect                      # confirm the rule and skills are listed
```

The installer only writes a `bearpaws.md` it owns, and it refuses to overwrite one you wrote.

**Copilot CLI:** installs from the same plugin marketplace as Claude Code, with skills plus a SessionStart hook:

```bash
copilot plugin marketplace add /path/to/bearpaws
copilot plugin install bp@bearpaws
```

**Cursor:** the repo ships `.cursor-plugin/plugin.json` (skills plus a `sessionStart` hook). It has not been verified in Cursor.

**Devin CLI:** reads `~/.agents/skills`. Put the Codex bootstrap line in your project's `AGENTS.md`. Sessions inside this repo also get the bootstrap from `.devin/hooks.v1.json`.

Other agents load `using-bearpaws` when it is invoked or matched by its description. On every agent except Claude Code, the risk receipt and the elevated-risk review are instructions only; no hook enforces them.

### Updating and uninstalling the linked skills

Links point into your clone: `git pull` updates skills; moving or deleting the clone breaks them (re-run `./install.sh --agents --global` from the new location; it reclaims links it recorded in `~/.agents/skills/.bearpaws-roots`). Uninstall:

```bash
roots=~/.agents/skills/.bearpaws-roots
for link in ~/.agents/skills/*; do
  target="$(readlink "$link" 2>/dev/null)" || continue
  target="${target%/}"
  grep -qxF -- "${target%/*}" "$roots" 2>/dev/null && rm "$link"
done
rm -f "$roots"
```

Then remove the `instructions` entry from your OpenCode config, the bootstrap line from `~/.codex/AGENTS.md`, and `~/.grok/rules/bearpaws.md`.
