---
name: using-bearpaws
description: Use when starting any conversation - establishes how to find and use skills, requiring Skill tool invocation before ANY response including clarifying questions
---

<skill>

  <subagent-stop>If you were dispatched as a subagent to execute a specific task, skip this skill.</subagent-stop>

  <warning level="hard">
    If you think there is even a 1% chance a skill might apply to what you are doing, you ABSOLUTELY MUST invoke the skill. IF A SKILL APPLIES TO YOUR TASK, YOU DO NOT HAVE A CHOICE. YOU MUST USE IT.
  </warning>

  <purpose>
    Skill discovery and invocation. Bearpaws skills override default system behavior where they conflict, but **user instructions always take precedence**: user > skill > default system prompt.
  </purpose>

  <triggers>
    <rule>Use at the start of every conversation, before any response.</rule>
    <rule>Use before clarifying questions — skill check comes first.</rule>
    <rule>Use before exploring the codebase — skills tell you HOW to explore.</rule>
  </triggers>

  <process>
    <step>**In Claude Code:** Use the `Skill` tool. When you invoke a skill, its content loads — follow it directly. Never `Read` skill files.</step>
    <step>**In Devin for Terminal / Windsurf Cascade:** Use the `skill` tool (slash command `/skill-name`). Skills live in `.devin/skills/` or `.windsurf/skills/`.</step>
    <step>**In Gemini CLI:** Skills activate via `activate_skill`. Gemini loads metadata at session start, full content on demand.</step>
    <step>Even a 1% chance a skill might apply means invoke the skill to check.</step>
    <step>If an invoked skill turns out to be wrong for the situation, you don't need to use it.</step>
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

  ## Lazy-load contract

  Inside a loaded skill, `<see file="...">` and `<include ref="...">` are **advisory pointers, not directives**. Read the target only if the current task explicitly needs it. Never auto-Read them at skill load time.

  ## Skill priority

  When multiple skills apply, the order is:

  1. **`bp:onboarding-to-a-project`** — first, whenever there's an existing project context. Identify the key files and stack from manifests, READMEs, and a sample of similar files. Skip only for purely abstract design discussion with no codebase ("how would I architect a system that does X?" with no project named).
  2. **`bp:brainstorming`** — next, for any creative/design work. Brainstorming designs *against the conventions you discovered in onboarding*, not against your training-data prior.
  3. **Other process skills** (writing-plans, TDD, debugging, code review, verification) — stack-agnostic, apply during implementation.

  Onboarding tells you the *project's specific* conventions; brainstorming reconciles them with the work to be done before code is written. Onboarding → brainstorming → implementation is the standard flow.

  ## Skill types

  Rigid (TDD, debugging) — follow exactly. Flexible (patterns) — adapt to context. The skill itself tells you which.

  <warning level="soft">
    Instructions say WHAT, not HOW. "Add X" or "Fix Y" doesn't mean skip workflows.
  </warning>

</skill>
