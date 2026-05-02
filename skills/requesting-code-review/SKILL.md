---
name: requesting-code-review
description: Use when completing tasks, implementing major features, or before merging to verify work meets requirements
---

<skill>

  <purpose>
    Dispatch bp:code-reviewer subagent to catch issues before they cascade. The reviewer gets crafted context for evaluation — never your session's history.
  </purpose>

  <triggers>
    <rule>Use after each task in subagent-driven development.</rule>
    <rule>Use after completing a major feature or before merge to main.</rule>
    <rule>Use when stuck (fresh perspective) or after fixing complex bugs.</rule>
  </triggers>

  <process>
    <step>**Get git SHAs** — `BASE_SHA=$(git rev-parse HEAD~1)` (or `origin/main`), `HEAD_SHA=$(git rev-parse HEAD)`.</step>
    <step>**Dispatch bp:code-reviewer subagent** — Use Task tool with code-reviewer type. Fill placeholders: `{WHAT_WAS_IMPLEMENTED}`, `{PLAN_OR_REQUIREMENTS}`, `{BASE_SHA}`, `{HEAD_SHA}`, `{DESCRIPTION}`.</step>
    <step>**Validate adversarial structure** — Review MUST contain all four named gates: (1) **Failure Mode Enumeration** with ≥3 concrete scenarios, (2) **What would have to be true for this to be wrong** steel-manning, (3) **What I didn't check and why** mapping blind spots, (4) **Break Attempts** documented as "Tried: X — Y". Vague is rejection-worthy: a "Tried" line without a `—` separator and outcome, or a failure mode without a specific code reference. If any gate is missing or vague, send back: "Review incomplete — missing [gate]. Redo."</step>
    <step>**Act on feedback** — Fix Critical immediately. Fix Important before proceeding. Note Minor for later. Push back if reviewer is wrong (with technical reasoning).</step>
  </process>

  <rules>
    <rule>Never skip review because "it's simple".</rule>
    <rule>Never proceed with unfixed Critical or Important issues.</rule>
    <rule>Never accept a review missing adversarial gates — a review without break attempts is not a review.</rule>
    <rule>If reviewer is wrong: push back with code/tests that prove it.</rule>
  </rules>

  ## Integration

  - **Subagent-Driven Development** — review after EACH task
  - **Executing Plans** — review after each batch (3 tasks)
  - **Ad-hoc** — review before merge or when stuck

  <see file="code-reviewer.md"/>

</skill>
