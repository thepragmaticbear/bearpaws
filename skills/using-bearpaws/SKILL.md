---
name: using-bearpaws
description: Use when starting any conversation, before responding or exploring the project
---

<skill>

  <subagent-stop>If you were dispatched as a subagent to execute a specific task, skip this skill.</subagent-stop>

  <warning level="hard">
    If a skill might apply, invoke it before responding, asking, or exploring. Follow applicable skills; user instructions take precedence.
  </warning>

  <process>
    <step>**Claude Code:** Invoke `Skill` and follow it; do not `Read` skill files.</step>
    <step>**In Antigravity:** Use native Agent Skills and the capability mapping.</step>
    <step>**Other Agent Skills agents:** Load `.agents/skills/` or `~/.agents/skills/` via the native tool (`skill` in OpenCode) or read `SKILL.md`. Users can type `$skill-name` (Codex) or `/skill-name` (Devin CLI).</step>
  </process>

  ## Red Flags

  These thoughts mean STOP — you're rationalizing:

  | Thought | Reality |
  |---------|---------|
  | "This is just a simple question" | Questions are tasks. Check for skills. |
  | "I need more context first" | Skill check comes BEFORE clarifying questions. |
  | "Let me explore the codebase first" | Skills tell you HOW to explore. Check first. |
  | "Let me gather information first" | Skills tell you HOW to gather information. |
  | "I can check git/files quickly" | Files lack conversation context. Check for skills. |
  | "I'll just do this one thing first" | Check BEFORE doing anything. |
  | "This doesn't count as a task" | Action = task. Check for skills. |
  | "The skill is overkill" | Simple things become complex. Use it. |
  | "I remember this skill" | Skills evolve. Read current version. |
  | "This feels productive" | Undisciplined action wastes time. Skills prevent this. |
  | "I know what that means" | Knowing the concept ≠ using the skill. Invoke it. |
  | "I know where this is going" | Early confidence is not permission to skip inspection, planning, or verification. |

  ## Pace Control

  Check knowns, assumptions, and existing work before acting. Re-evaluate when scope or risk changes. Verify each required gate.

  **Momentum does not waive gates.**

  ## Skill priority

  1. **`bp:onboarding-to-a-project`** first for projects; skip only for abstract design with no project involved.
  2. **`bp:brainstorming`** next for design, using project conventions.
  3. **Other process skills** for planning, TDD, debugging, review, and verification.

  ## Lazy-load contract

  `<see file="...">` and `<include ref="...">` are advisory. Read targets only when needed; do not load them automatically.

  ## Skill types

  Follow rigid process skills exactly; adapt flexible patterns to context.

  ## Brevity Policy

  - Answer directly and keep routine updates brief when no process skill sets the output format.
  - Follow a process skill's detail requirements when it applies.
  - Never compress safety warnings, migration risks, acceptance criteria, defect-preventing review findings, test failures and error output, or verification results.

</skill>
