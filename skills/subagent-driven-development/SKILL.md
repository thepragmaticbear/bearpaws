---
name: subagent-driven-development
description: Use when executing implementation plans with independent tasks in the current session
---

<skill>

  <purpose>
    Execute plan by dispatching fresh subagent per task, with two-stage review after each: spec compliance first, then code quality. Fresh subagent per task + two-stage review = high quality, fast iteration.
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
    <step>**Setup** — Read plan, extract all tasks with full text, note context, create TodoWrite. Set up workspace with bp:using-git-worktrees.</step>
    <step>**Dispatch implementer** — Fresh subagent per task (use ./implementer-prompt.md). Provide full task text + context. Never make subagent read the plan file.</step>
    <step>**Handle status** — DONE: proceed to review. DONE_WITH_CONCERNS: assess before review. NEEDS_CONTEXT: provide and re-dispatch. BLOCKED: assess (context problem → re-dispatch; reasoning problem → more capable model; too large → break up; plan wrong → escalate to human).</step>
    <step>**Spec compliance review** — Dispatch spec reviewer subagent (./spec-reviewer-prompt.md). Must pass before code quality review. If issues found: implementer fixes → re-review → repeat until ✅.</step>
    <step>**Code quality review** — Dispatch code quality reviewer subagent (./code-quality-reviewer-prompt.md). If issues: implementer fixes → re-review → repeat until ✅.</step>
    <step>**Mark complete, next task** — Mark task in TodoWrite. Proceed to next task.</step>
    <step>**Final review + finish** — After all tasks: dispatch final reviewer for entire implementation, then invoke bp:finishing-a-development-branch.</step>
  </process>

  ## Model selection

  Use the least powerful model that handles each role:
  - **Mechanical tasks** (isolated functions, clear specs, 1-2 files): fast/cheap model
  - **Integration tasks** (multi-file, pattern matching): standard model
  - **Architecture/design/review**: most capable model

  <rules>
    <rule>Never start on main/master without explicit user consent.</rule>
    <rule>Never skip reviews (spec OR quality).</rule>
    <rule>Never dispatch multiple implementers in parallel (conflicts).</rule>
    <rule>Never let implementer self-review replace actual review.</rule>
    <rule>Spec compliance must pass BEFORE code quality review.</rule>
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
