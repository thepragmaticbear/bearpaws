# Bearpaws Migration Audit

This is a historical, point-in-time Phase 0 audit. It records the repository state observed during the migration review and is not expected to be updated for every later code or skill change. Do not use it as current support policy. For current support posture, see `docs/agent-support.md`; for the current descriptive skill contract, see `docs/skill-structure.md`.

## Summary

- Total skills: 15
- Current structure consistency: Mostly consistent. Every skill is a directory under `skills/` with `SKILL.md`, YAML frontmatter, and an XML-like `<skill>` body.
- Phase 0 agent support baseline: Claude Code is working; Gemini CLI is mostly working but not behavior-tested; Devin and Windsurf are partial symlink/bootstrap integrations; Codex is unsupported except for incidental guidance in skill text.
- Recommended path: Lean Path
- Key risks: Some skills name Claude-style tools or subagent patterns, Gemini lacks automated trigger tests, Devin/Windsurf support is unproven beyond repo-local wiring, README/CLAUDE positioning currently implies broader parity than the tests prove.

## Recommendation

### Lean Path Recommended

Use the current skill structure as the descriptive contract. It is regular enough for lightweight file placement or whole-file wrapping, and the repo already has simple guardrails for tag drift, token measurement, version drift, and Claude behavior tests.

Reasons:
- Existing structure is sufficient as the descriptive contract
- No formal schema required yet
- No validator required beyond the existing lightweight XML tag whitelist yet
- No generated build pipeline required yet
- Claude/Gemini support can be improved with minimal changes

## Repository Areas Inspected

- `.claude-plugin/`: `plugin.json`, `marketplace.json`
- `.devin/`: `hooks.v1.json`, symlinked `.devin/skills/`
- `.windsurf/`: `rules/bearpaws.md`, symlinked `.windsurf/skills/`
- `agents/`: `code-reviewer.md`
- `commands/`: deprecated shims for brainstorming, planning, and executing plans
- `docs/`: testing docs, Windows hook notes, release notes
- `hooks/`: `hooks.json`, `run-hook.cmd`, `session-start`
- `scripts/`: `bump-version.sh`
- `skills/`: all 15 skill directories, sibling references, prompts, scripts, and examples
- `tests/`: Claude behavior tests, triggering tests, explicit skill request tests, schema validator, token measurement, install tests
- `CLAUDE.md`
- `GEMINI.md`
- `gemini-extension.json`
- `install.sh`
- `README.md`
- Also inspected: `package.json`, `.version-bump.json`, top-level file inventory

## Skill Structure Findings

Skills are organized as a flat namespace under `skills/<skill-name>/`. Every skill has a `SKILL.md` file with YAML frontmatter:

```yaml
---
name: skill-name
description: Use when ...
---
```

Every skill body starts with `<skill>` and ends with `</skill>`. The bodies use a compact XML-like vocabulary: `<purpose>`, `<triggers>`, `<rules>`, `<rule>`, `<process>`, `<step>`, `<warning>`, `<gate>`, `<flow>`, `<example>`, `<antipattern>`, `<see>`, and the special `<subagent-stop>` tag in the bootstrap.

The sections are predictable enough for light adapters to consume by treating frontmatter as metadata and the body as opaque instruction text. Parsing the full XML-like structure is not necessary for Claude or Gemini. The existing `tests/schema-validator/run-validator.sh` checks only tag whitelist drift, not full grammar correctness.

Implicit conventions worth documenting:
- `SKILL.md` is the primary contract.
- Heavy or situational content lives in sibling files and is referenced through `<see file="..."/>`.
- `<see>` and `<include>` are advisory, not auto-load directives.
- `skills/using-bearpaws/SKILL.md` is the bootstrap and is injected at session start.
- Skill names are unprefixed in frontmatter but documented to users as `bp:<skill-name>`.
- Some skills assume agent capabilities such as skill activation, subagents, todo tracking, git commands, and shell access.

Materially different skills:
- `using-bearpaws`: bootstrap skill; includes agent-specific activation instructions.
- `writing-skills`: meta-skill; longer than others and contains the local schema documentation.
- `brainstorming`: includes visual companion server instructions and agent-specific runtime notes.
- `subagent-driven-development`, `dispatching-parallel-agents`, and `requesting-code-review`: depend heavily on subagent/task semantics.

Documenting the existing structure should be enough for near-term maintenance.

## Skill Audit

```json
{
  "skill": "brainstorming",
  "structure": "mostly consistent",
  "issues": ["References visual-companion.md and companion scripts; visual companion includes agent-specific runtime notes."],
  "intent_risk": "medium",
  "notes": "Intent is clear. Whole-file placement is safe; transforming visual companion behavior would be risky."
}
```

```json
{
  "skill": "dispatching-parallel-agents",
  "structure": "consistent",
  "issues": ["Assumes an agent can dispatch multiple independent subagents or tasks."],
  "intent_risk": "medium",
  "notes": "Intent is clear, but agents without parallel task primitives need a graceful fallback."
}
```

```json
{
  "skill": "executing-plans",
  "structure": "consistent",
  "issues": ["Mentions TodoWrite-style task tracking indirectly through workflow expectations."],
  "intent_risk": "low",
  "notes": "Good candidate for as-is consumption."
}
```

```json
{
  "skill": "finishing-a-development-branch",
  "structure": "consistent",
  "issues": ["Assumes git CLI availability and branch/PR workflow."],
  "intent_risk": "low",
  "notes": "Intent is clear and agent-agnostic enough."
}
```

```json
{
  "skill": "onboarding-to-a-project",
  "structure": "consistent",
  "issues": ["Names Claude-oriented project guidance files such as CLAUDE.md/AGENTS.md, but also includes GEMINI.md and generic files."],
  "intent_risk": "low",
  "notes": "Portable as-is; this is one of the strongest cross-agent skills."
}
```

```json
{
  "skill": "receiving-code-review",
  "structure": "consistent",
  "issues": [],
  "intent_risk": "low",
  "notes": "Agent-agnostic process skill with clear intent."
}
```

```json
{
  "skill": "requesting-code-review",
  "structure": "consistent",
  "issues": ["Depends on a bp:code-reviewer subagent and Task-tool style dispatch."],
  "intent_risk": "medium",
  "notes": "Intent is clear, but adapter claims should not imply this works in agents without compatible subagent support."
}
```

```json
{
  "skill": "subagent-driven-development",
  "structure": "consistent",
  "issues": ["Depends on subagents, TodoWrite, worktrees, and specific reviewer prompt files."],
  "intent_risk": "medium",
  "notes": "Structurally clean; behavior depends on agent execution primitives."
}
```

```json
{
  "skill": "systematic-debugging",
  "structure": "consistent",
  "issues": ["References optional sibling debugging materials."],
  "intent_risk": "low",
  "notes": "Portable as-is."
}
```

```json
{
  "skill": "test-driven-development",
  "structure": "consistent",
  "issues": ["References optional testing anti-patterns file."],
  "intent_risk": "low",
  "notes": "Portable as-is."
}
```

```json
{
  "skill": "using-bearpaws",
  "structure": "mostly consistent",
  "issues": ["Bootstrap skill includes Claude Code, Devin, Windsurf, and Gemini activation instructions; no Codex activation support beyond other incidental docs."],
  "intent_risk": "medium",
  "notes": "Do not rewrite casually. Wrapping is already used by SessionStart; preserve exact source content when possible."
}
```

```json
{
  "skill": "using-git-worktrees",
  "structure": "consistent",
  "issues": ["Mentions CLAUDE.md preferences and ~/.config/bearpaws worktree location."],
  "intent_risk": "low",
  "notes": "Mostly portable, assuming git CLI access."
}
```

```json
{
  "skill": "verification-before-completion",
  "structure": "consistent",
  "issues": [],
  "intent_risk": "low",
  "notes": "Agent-agnostic and portable."
}
```

```json
{
  "skill": "writing-plans",
  "structure": "consistent",
  "issues": ["Writes plans to docs/bearpaws/plans by default; references reviewer prompt file."],
  "intent_risk": "low",
  "notes": "Portable as-is."
}
```

```json
{
  "skill": "writing-skills",
  "structure": "mostly consistent",
  "issues": ["Meta-skill contains schema docs, Claude-oriented best-practice references, and a Codex personal skills path mention."],
  "intent_risk": "medium",
  "notes": "Useful as documentation and behavior guidance; avoid turning its schema section into a new hard contract during Lean Path."
}
```

## Agent Compatibility

| Agent | Current Status | Existing Files | Needed Work | Risk |
|---|---|---|---|---|
| Claude Code | Working | `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `hooks/hooks.json`, `hooks/run-hook.cmd`, `hooks/session-start`, `agents/code-reviewer.md`, `commands/`, `tests/claude-code/`, `tests/skill-triggering/` | Keep current plugin/hook shape; update positioning language; retain behavioral tests. | Low |
| Gemini CLI | Mostly working | `gemini-extension.json`, `GEMINI.md`, `skills/using-bearpaws/references/gemini-tools.md` | Add minimal documentation and lightweight validation for expected activation shape; avoid claiming Claude-level behavioral coverage until tested. | Medium |
| Codex | Unsupported | Incidental mentions in `skills/brainstorming/visual-companion.md` and `skills/writing-skills/SKILL.md`; no manifest, install target, or tests. | Treat as experimental/unsupported unless an explicit adapter or docs are added later. | Medium |
| Devin | Partial | `.devin/hooks.v1.json`, `.devin/skills/` symlinks, `install.sh`, `hooks/session-start` SDK-standard output path | Verify real Devin skill activation before stronger claims; preserve symlink install if kept. | Medium |
| Windsurf | Partial | `.windsurf/rules/bearpaws.md`, `.windsurf/skills/` symlinks, `install.sh` | Verify include/rule behavior in Windsurf before stronger claims; document as experimental. | Medium |

## Adapter Feasibility

Claude Code can use the current structure as-is. The plugin manifest and SessionStart hook already inject the bootstrap, and skills are native `SKILL.md` directories.

Gemini CLI appears able to consume the current structure with light context wiring. `gemini-extension.json` points to `GEMINI.md`, and `GEMINI.md` includes the bootstrap plus Gemini tool reference. A simple file placement or context-file adapter should be enough; parsing the XML-like body is not required.

Codex has no current adapter. A future Lean Path Codex target would likely need documentation and file placement under the relevant Codex skills directory, but this audit found no existing Codex install flow to preserve.

Devin and Windsurf currently use symlinks into `skills/`, plus bootstrap hook/rule files. That is compatible with the Lean Path if they truly understand the skill directory shape. If their native skill semantics differ, support should remain experimental rather than introducing a broad adapter layer now.

Adapter logic would become brittle only if it tried to parse and normalize inner XML-like sections. The safe adapter boundary is frontmatter plus opaque body text.

## Install Flow Findings

Installation is currently split by agent:

- Claude Code: documented use of `claude plugin marketplace add /path/to/bearpaws` and `claude plugin install bp@bearpaws`, or `claude --plugin-dir /path/to/bearpaws`.
- Gemini CLI: documented `gemini extensions install /path/to/bearpaws` or `gemini extensions link /path/to/bearpaws`.
- Devin and Windsurf: `install.sh` creates symlinks from `skills/*/` into `.devin/skills/` and `.windsurf/skills/`; Devin can also install symlinks globally under `~/.config/devin/skills`.

`.claude-plugin/`, `.devin/`, `.windsurf/`, and Gemini files are hand-maintained. There is no generated adapter output today.

The current install flow can remain mostly intact. Adding thin adapters later should not break it if adapters only copy/symlink/wrap source content. A build step would not materially improve the current install experience and would add maintenance/user friction unless generated artifacts become necessary.

## Token Reporting Findings

Token reporting exists in `tests/token-measurement/measure.sh` and `tests/token-measurement/README.md`.

It measures deterministic byte counts:
- `bootstrap_additional_context_bytes`
- `skills_skill_md_total_bytes`
- `skills_full_payload_bytes`
- `per_skill_skill_md_bytes`

Current measured snapshot:
- Bootstrap additional context: 4,286 bytes
- All `SKILL.md` files: 61,916 bytes
- Full `skills/` payload: 198,418 bytes

README also includes a static comparison against superpowers v5.0.7 using approximate token estimates. The measurement script itself does not compare against upstream and does not count generated artifacts.

Adapters would affect reporting only if generated outputs became user-visible or session-loaded artifacts. Under the Lean Path, token reporting can remain simple: bootstrap footprint, per-skill `SKILL.md` bytes, full skills payload, and clear caveats that bytes are deterministic while tokens are approximate.

## Triggering Test Findings

Triggering tests exist and are Claude-based:
- `tests/skill-triggering/run-all.sh` tests 9 naive-prompt skill triggers by invoking `claude -p` with `--plugin-dir` and scanning stream JSON for the `Skill` tool.
- `tests/explicit-skill-requests/` tests explicit skill-name requests and checks for premature tool use.
- `tests/claude-code/` includes fast and integration tests, focused especially on `subagent-driven-development`.
- `tests/schema-validator/run-validator.sh` checks XML tag whitelist drift and code-review gate alignment.
- `tests/install/run-install-tests.sh` checks symlink reconciliation for Devin/Windsurf in a temp copy.

The tests rely on actual Claude execution, not simulation. They are not per-agent and do not validate Gemini, Devin, Windsurf, or Codex behavior.

The Lean Path does not require a formal per-agent trigger matrix. Minimum useful future checks would be:
- Claude: keep current trigger and explicit-request tests.
- Gemini: add a lightweight extension/context smoke test or documented manual activation test.
- Experimental agents: install/symlink checks are enough until support is promoted.

A full per-agent trigger matrix would create more maintenance cost than value at the current maturity level.

## README Positioning Findings

README clearly preserves attribution and states that Bearpaws is a hard fork of superpowers v5.0.7. It also clearly describes the low-token goal.

Phase 0 positioning issues to adjust in a later phase:
- README said Bearpaws preserves the behavioral performance of upstream superpowers, which read like a parity claim.
- README called the project "A Claude Code (and Gemini CLI) skills plugin" but also included Devin/Windsurf install instructions that implied readiness.
- README said the repository was "ready out of the box" for Devin/Windsurf and that both platforms would invoke the bootstrap autonomously; the audit found wiring, but not behavioral evidence.
- README did not yet clearly say Bearpaws evolves independently rather than tracking upstream.

Recommended future language:
- Bearpaws is independent and began as a hard fork of superpowers v5.0.7.
- Claude Code and Gemini CLI are primary supported targets.
- Devin, Windsurf, and Codex should be experimental unless tested and documented.
- Avoid feature parity, behavioral parity, ongoing upstream tracking, and universal compatibility claims.

## Maintenance Burden Assessment

Lean Path for one year:
- Keep `SKILL.md` structure documented.
- Maintain current manifests and symlink install flow.
- Keep version fields synchronized through `scripts/bump-version.sh`.
- Keep Claude behavior tests and schema/tag guardrail passing.
- Add only small smoke checks for Gemini if support is claimed as primary.
- Update README/support docs to separate primary from experimental agents.

Heavy Path for one year:
- Design and maintain a formal schema.
- Build and maintain parsers, validators, adapters, generated artifacts, and CI gates.
- Decide compatibility behavior for every XML-like section and every sibling file reference.
- Add per-agent test expectations and keep them current as agent CLIs drift.
- Debug generated artifacts separately from source skills.

Ongoing maintenance obligations are highest for agent behavior claims, subagent features, bootstrap/hook APIs, and any generated adapter pipeline. One-time migrations are mostly README/support wording and descriptive skill-structure docs.

Claude and Gemini are the most justifiable primary targets. Devin and Windsurf are likely to drift because their support depends on symlinked skill semantics and repo-specific bootstrap files. Codex would create a new support surface because no current install path exists.

## Risks / Stop Conditions

- Stop before modifying any source skill body; skill text is behavior-shaping and should only change with eval evidence.
- Stop before adding metadata fields to skills; matcher behavior could change.
- Stop before introducing a formal schema or validator-as-gatekeeper; current structure does not justify it.
- Stop before replacing symlink install with generated artifacts; no audit finding requires that complexity.
- Stop before promoting Codex, Devin, or Windsurf to primary support; current evidence is insufficient.
- Stop if a future adapter needs to parse and rewrite inner skill sections instead of preserving the body as opaque text.
- Stop if bootstrap output shape changes; it must be verified in a fresh agent session.

## Final Recommendation

Lean Path is recommended. The current repository already has a coherent skill structure, simple bootstrap/install mechanisms, lightweight token reporting, and Claude-centered behavioral tests. The safest transition is to document the existing structure, narrow support claims, keep Claude and Gemini primary, keep Codex/Devin/Windsurf experimental, and avoid schema/build/adaptor machinery until evidence proves it is necessary.
