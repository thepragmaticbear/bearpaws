---
name: subagent-driven-development
description: Use when executing implementation plans with independent tasks in the current session
---

<skill>

  <purpose>
    Execute plan by dispatching fresh subagent per task, with independent review after each. Routine tasks get one combined review (spec compliance and code quality); elevated-risk tasks get two stages: spec compliance first, then code quality.
  </purpose>

  <triggers>
    <rule>Use when you have an implementation plan and the user chose subagent-driven execution.</rule>
    <rule>Use when tasks are mostly independent and you're staying in this session.</rule>
  </triggers>

  <flow format="dot">
    ```dot
    digraph when_to_use {
      "Have plan?" [shape=diamond];
      "Tasks independent?" [shape=diamond];
      "Stay in session?" [shape=diamond];
      "subagent-driven-dev" [shape=box];
      "executing-plans" [shape=box];
      "brainstorm first" [shape=box];

      "Have plan?" -> "Tasks independent?" [label="yes"];
      "Have plan?" -> "brainstorm first" [label="no"];
      "Tasks independent?" -> "Stay in session?" [label="yes"];
      "Tasks independent?" -> "brainstorm first" [label="tightly coupled"];
      "Stay in session?" -> "subagent-driven-dev" [label="yes"];
      "Stay in session?" -> "executing-plans" [label="parallel session"];
    }
    ```
  </flow>

  <process>
    <step>**Setup** — Read the plan once, extract all tasks with full text, note context, track progress with the plan's checkboxes (and a task-tracking tool if one is available). Set up workspace with bp:using-git-worktrees.</step>
    <step>**Dispatch implementer** — Fresh subagent per task (use ./implementer-prompt.md). Provide full task text + context. Never make subagent read the plan file.</step>
    <step>**Handle status** — DONE: proceed to review. DONE_WITH_CONCERNS: assess before review. NEEDS_CONTEXT: provide and re-dispatch. BLOCKED: assess (context problem → re-dispatch; reasoning problem → more capable model; too large → break up; plan wrong → escalate to human).</step>
    <step>**Classify risk** — A task is elevated-risk if it touches authentication or authorization, secrets or cryptography, money, data deletion or migration, untrusted input reaching paths, SQL, shell, or deserialization, concurrency, or a public API or schema, or if the plan marks it high-risk. Otherwise it is routine. When unsure, it is elevated-risk. Size does not lower risk: a one-line auth change is elevated-risk.</step>
    <step>**Routine: combined review** — Dispatch one code reviewer subagent (./code-quality-reviewer-prompt.md) with the full task text as requirements; it checks spec compliance and code quality together. If issues: implementer fixes → re-review → repeat until ✅.</step>
    <step>**Elevated-risk: two-stage review** — Dispatch spec reviewer subagent (./spec-reviewer-prompt.md); it must pass before the code quality review (./code-quality-reviewer-prompt.md). If either finds issues: implementer fixes → re-review → repeat until ✅.</step>
    <step>**Mark complete, next task** — Check the task off in the plan. Proceed to next task.</step>
    <step>**Final review + finish** — After all tasks: dispatch final reviewer for entire implementation, then invoke bp:finishing-a-development-branch.</step>
  </process>

  ## Model selection

  Use the least powerful model that handles each role:
  - **Mechanical tasks** (isolated functions, clear specs, 1-2 files): fast/cheap model
  - **Integration tasks** (multi-file, pattern matching): standard model
  - **Architecture/design/review**: most capable model

  <rules>
    <rule>Never start on main/master without explicit user consent.</rule>
    <rule>Never skip reviews. Routine tasks still get spec compliance checked, inside the combined review.</rule>
    <rule>Never dispatch multiple implementers in parallel (conflicts).</rule>
    <rule>Never let implementer self-review replace actual review.</rule>
    <rule>For elevated-risk tasks, spec compliance must pass BEFORE code quality review.</rule>
    <rule>Never downgrade a task to routine to save a review. If the classification is arguable, it is elevated-risk.</rule>
    <rule>If reviewer finds issues: implementer fixes → reviewer re-reviews → repeat.</rule>
    <rule>If subagent asks questions: answer clearly before letting them proceed.</rule>
    <rule>If subagent fails: dispatch fix subagent — don't fix manually (context pollution).</rule>
  </rules>

  ## Integration

  - **bp:using-git-worktrees** — set up workspace before starting
  - **bp:writing-plans** — creates the plan this skill executes
  - **bp:requesting-code-review** — template for reviewer subagents
  - **bp:finishing-a-development-branch** — complete after all tasks
  - **bp:test-driven-development** — subagents follow TDD

  <see file="implementer-prompt.md"/>
  <see file="spec-reviewer-prompt.md"/>
  <see file="code-quality-reviewer-prompt.md"/>

</skill>
