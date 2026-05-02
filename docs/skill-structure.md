# Bearpaws Skill Structure

Bearpaws skills are plain files with a small, consistent shape. This document describes the current structure as it exists today. It is not a new schema, a migration requirement, or a promise that adapters may rewrite skill content.

Source skill content should stay behavior-preserving. If a future adapter needs a different shape, prefer copying, symlinking, or wrapping the source files rather than normalizing the skill body.

## Directory Layout

Skills live in a flat namespace:

```text
skills/
  skill-name/
    SKILL.md
    optional-sibling-files
```

Each directory name matches the skill name used in `SKILL.md` frontmatter. The repository currently has 15 skills:

- `brainstorming`
- `dispatching-parallel-agents`
- `executing-plans`
- `finishing-a-development-branch`
- `onboarding-to-a-project`
- `receiving-code-review`
- `requesting-code-review`
- `subagent-driven-development`
- `systematic-debugging`
- `test-driven-development`
- `using-bearpaws`
- `using-git-worktrees`
- `verification-before-completion`
- `writing-plans`
- `writing-skills`

## Required Skill File

Every skill has a `SKILL.md` file. That file is the primary contract for the skill.

The top of each `SKILL.md` uses YAML frontmatter:

```yaml
---
name: skill-name
description: Use when ...
---
```

Current conventions:

- `name` uses lowercase letters, numbers, and hyphens.
- `description` describes when to use the skill, not the full workflow.
- Descriptions should remain short enough for agent skill matchers.
- Skill names are stored without a namespace, but user-facing docs commonly refer to them as `bp:<skill-name>`.

## Body Shape

After frontmatter, every current skill body is wrapped in:

```xml
<skill>
  ...
</skill>
```

The body uses XML-like structural tags with Markdown inside the tags. Agents should treat this as instruction text. Adapters should not need to parse inner sections unless a later phase explicitly proves that is necessary.

Common tags currently used:

| Tag | Current purpose |
|---|---|
| `<skill>` | Root wrapper for the skill body. |
| `<purpose>` | Brief statement of what the skill is for. |
| `<triggers>` | Conditions where the skill should be used. |
| `<rules>` / `<rule>` | Behavioral requirements or trigger rules. |
| `<process>` / `<step>` | Ordered workflow steps. |
| `<warning level="hard">` | Critical behavioral warning. |
| `<warning level="soft">` | Lower-severity caution. |
| `<gate name="...">` | Named checkpoint that must pass before proceeding. |
| `<flow format="dot">` | Graphviz flowchart content. |
| `<example type="good">` | Positive example. |
| `<example type="bad">` | Negative example. |
| `<antipattern>` | Common failure mode to avoid. |
| `<see file="..."/>` | Advisory pointer to optional sibling content. |
| `<include ref="..."/>` | Advisory structural-dedup pointer; currently documented, not used in source skills. |
| `<placeholder name="...">` | Template variable marker. |
| `<subagent-stop>` | Bootstrap-only instruction to skip in subagent contexts. |

The existing validator in `tests/schema-validator/run-validator.sh` checks the tag whitelist only. It does not enforce element order, nesting, required sections, or semantic correctness.

## Sibling Files

Skills may include extra files beside `SKILL.md`. These are used for references, prompt templates, examples, helper scripts, or large supporting material.

Examples:

- `skills/brainstorming/visual-companion.md`
- `skills/brainstorming/scripts/`
- `skills/systematic-debugging/root-cause-tracing.md`
- `skills/subagent-driven-development/implementer-prompt.md`
- `skills/writing-skills/anthropic-best-practices.md`

The main `SKILL.md` should stay focused. Large or situational material belongs in sibling files when it should be loaded only for relevant tasks.

## Lazy-Load Convention

`<see file="..."/>` is advisory. It tells the agent that related material exists, but it does not mean the file should be loaded automatically.

The current bootstrap says:

- Read a `<see>` target only when the current task explicitly needs it.
- Do not auto-read every referenced file when loading a skill.
- Treat `<include>` the same way unless a later approved phase changes that behavior.

This convention is central to Bearpaws' token-efficiency goal.

## Bootstrap Skill

`skills/using-bearpaws/SKILL.md` is special.

It is injected at session start for supported agents and teaches the agent how to discover and invoke the other skills. It also defines skill priority, the lazy-load contract, and the fallback brevity policy for output not governed by process skills.

Because the bootstrap teaches the conventions, it should be preserved especially carefully. Avoid changing it unless there is explicit behavioral evidence and a fresh-session verification plan.

## Agent-Specific Language

Some skill text names current agent tools or capabilities:

- Claude Code: `Skill`, `Task`, `TodoWrite`, `Read`, `Write`, `Edit`, `Bash`
- Gemini CLI equivalents are documented in `skills/using-bearpaws/references/gemini-tools.md`
- Devin and Windsurf are described in the bootstrap as using a `skill` tool or slash command

This language is part of the current skill behavior. Do not rewrite source skills just to make an adapter cleaner. If an agent needs different tool names, use an agent-specific wrapper or reference note where possible.

## Adapter Boundary

The safest adapter boundary is:

1. Read `SKILL.md` frontmatter for `name` and `description`.
2. Preserve the rest of the `SKILL.md` body exactly.
3. Preserve sibling files exactly.
4. Add only minimal agent-specific placement or bootstrap wrapping.

The operational adapter policy lives in `docs/agent-support.md`. This document records only the source-preservation boundary for skill files.

If a future adapter cannot work without parsing and rewriting inner skill sections, that is evidence to stop and reconsider the architecture.

## Maintenance Notes

When changing skills:

- Use `bp:writing-skills`.
- Preserve intent over prose preference.
- Keep `SKILL.md` focused and move heavy supporting material to sibling files.
- Run `tests/schema-validator/run-validator.sh` after structural changes.
- For behavior-sensitive changes, run the appropriate Claude behavior tests or a fresh-session pressure scenario.

For documentation-only changes, this file may be updated without changing skill behavior.
