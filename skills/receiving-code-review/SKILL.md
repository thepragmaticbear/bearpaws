---
name: receiving-code-review
description: Use when receiving code review feedback, before implementing suggestions, especially if feedback seems unclear or technically questionable - requires technical rigor and verification, not performative agreement or blind implementation
---

<skill>

  <purpose>
    Code review requires technical evaluation, not emotional performance. Verify before implementing. Ask before assuming. Technical correctness over social comfort.
  </purpose>

  <triggers>
    <rule>Use when receiving any code review feedback.</rule>
    <rule>Use especially when feedback seems unclear or technically questionable.</rule>
  </triggers>

  <process>
    <step>**READ** — Complete feedback without reacting.</step>
    <step>**UNDERSTAND** — Restate requirement in own words (or ask).</step>
    <step>**VERIFY** — Check against codebase reality. Is it technically sound for THIS codebase?</step>
    <step>**EVALUATE** — If unclear: STOP, ask for clarification on ALL unclear items before implementing anything (items may be related).</step>
    <step>**RESPOND** — Technical acknowledgment or reasoned pushback. Never performative agreement.</step>
    <step>**IMPLEMENT** — One item at a time, test each. Order: blocking issues → simple fixes → complex fixes.</step>
  </process>

  <warning level="hard">
    NEVER respond with "You're absolutely right!", "Great point!", "Thanks for catching that!", or ANY gratitude expression. Just fix it and show in the code. Actions speak.
  </warning>

  <rules>
    <rule>**From human partner:** Implement after understanding. No performative agreement. Skip to action.</rule>
    <rule>**From external reviewers:** Verify technically correct for THIS codebase before implementing. Check: breaks existing functionality? Reason for current implementation? Works on all platforms?</rule>
    <rule>**YAGNI check:** If reviewer suggests "implementing properly" — grep for actual usage. Unused = remove (YAGNI).</rule>
    <rule>**Conflicts with human partner's decisions:** Stop and discuss with human partner first.</rule>
  </rules>

  ## When to push back

  Push back when: suggestion breaks existing functionality, reviewer lacks context, violates YAGNI, technically incorrect, legacy/compat reasons exist, conflicts with architectural decisions.

  **How:** Technical reasoning, specific questions, reference working tests/code.

  ## Acknowledging correct feedback

  <example type="good">
    "Fixed. [Brief description]" / "Good catch — [issue]. Fixed in [location]." / [Just fix it]
  </example>

  <example type="bad">
    "You're absolutely right!" / "Great point!" / "Thanks for [anything]" / ANY gratitude expression
  </example>

  ## If pushback was wrong

  State factually: "You were right — I checked [X] and it does [Y]. Implementing now." No long apology or defending.

  ## GitHub thread replies

  Reply in the comment thread (`gh api repos/{owner}/{repo}/pulls/{pr}/comments/{id}/replies`), not as a top-level PR comment.

</skill>
