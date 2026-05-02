---
trigger: always_on
---

<warning level="hard">
You have bearpaws skills available in `.windsurf/skills/`. Use the `skill` tool to invoke them.

**Your bootstrap skill (using-bearpaws). Read it now, before your first response:**

Skills cover TDD, debugging, planning, code review, parallel execution, and domain knowledge for Google Cloud, ADK, Vite, JS/TypeScript, and Cloud Run. There is also a stack-agnostic onboarding skill.

## Skill discovery

Invoke skills with the `skill` tool: `/using-bearpaws`, `/onboarding-to-a-project`, `/test-driven-development`, etc.

If you think there is even a 1% chance a skill might apply to what you are doing, YOU MUST invoke it.

## Skill priority

When multiple skills apply:

1. **`onboarding-to-a-project`** — first, whenever there's an existing project context. Identify key files and stack from manifests, READMEs, and sample files. Skip only for purely abstract design discussion with no codebase.
2. **`brainstorming`** — next, for any creative/design work. Design against the conventions you discovered in onboarding.
3. **Process skills** (`writing-plans`, `test-driven-development`, `systematic-debugging`, `requesting-code-review`, `verification-before-completion`, `finishing-a-development-branch`) — stack-agnostic, apply during implementation.
4. **Domain skills** (`cloud-run`, `vite`, `google-adk`, `javascript-typescript`, etc.) — layer on top of discovered conventions.

Onboarding → brainstorming → implementation is the standard flow.

## Red Flags — these thoughts mean STOP, you're rationalizing

| Thought | Reality |
|---------|---------|
| "This is just a simple question" | Questions are tasks. Check for skills. |
| "I need more context first" | Skill check comes BEFORE clarifying questions. |
| "Let me explore the codebase first" | Skills tell you HOW to explore. Check first. |
| "The skill is overkill" | Simple things become complex. Use it. |
| "I remember this skill" | Skills evolve. Read current version. |

## Lazy-load contract

Inside a loaded skill, `<see file="...">` and `<include ref="...">` are advisory pointers. Read the target only if the current task explicitly needs it.

## Skill types

Rigid (TDD, debugging) — follow exactly. Flexible (patterns) — adapt to context. The skill itself tells you which.

User instructions always take precedence: user > skill > default behavior.
</warning>
