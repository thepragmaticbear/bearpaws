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

  <see file="_shared/red-flags-skill-discipline.md"/>

  ## Skill priority

  When multiple skills apply: process skills first (brainstorming, debugging) then implementation skills.

  ## Skill types

  Rigid (TDD, debugging) — follow exactly. Flexible (patterns) — adapt to context. The skill itself tells you which.

  <warning level="soft">
    Instructions say WHAT, not HOW. "Add X" or "Fix Y" doesn't mean skip workflows.
  </warning>

</skill>
