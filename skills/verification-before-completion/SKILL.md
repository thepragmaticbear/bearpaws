---
name: verification-before-completion
description: Use when about to claim work is complete, fixed, or passing, before committing or creating PRs - requires running verification commands and confirming output before making any success claims; evidence before assertions always
---

<skill>

  <purpose>
    Claiming work is complete without verification is dishonesty, not efficiency. Evidence before claims, always. Violating the letter of this rule is violating the spirit.
  </purpose>

  <triggers>
    <rule>Use before ANY success/completion claim, expression of satisfaction, or positive statement about work state.</rule>
    <rule>Use before committing, PR creation, task completion, moving to next task.</rule>
  </triggers>

  <warning level="hard">
    NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE. If you haven't run the verification command in this message, you cannot claim it passes.
  </warning>

  <process>
    <step>**IDENTIFY** — What command proves this claim?</step>
    <step>**RUN** — Execute the FULL command (fresh, complete).</step>
    <step>**READ** — Full output, check exit code, count failures.</step>
    <step>**VERIFY** — Does output confirm the claim? If NO: state actual status with evidence. If YES: state claim WITH evidence.</step>
    <step>**ONLY THEN** — Make the claim.</step>
  </process>

  ## What requires verification

  | Claim | Requires | Not sufficient |
  |---|---|---|
  | Tests pass | Test output: 0 failures | Previous run, "should pass" |
  | Linter clean | Linter output: 0 errors | Partial check, extrapolation |
  | Build succeeds | Build command: exit 0 | Linter passing, logs look good |
  | Bug fixed | Original symptom test passes | Code changed, assumed fixed |
  | Agent completed | VCS diff shows changes | Agent reports "success" |
  | Requirements met | Line-by-line checklist | Tests passing alone |

  ## Red Flags — STOP

  - Using "should", "probably", "seems to"
  - Expressing satisfaction before verification ("Great!", "Perfect!", "Done!")
  - About to commit/push/PR without verification
  - Trusting agent success reports without independent check
  - ANY wording implying success without having run verification

  ## Rationalizations

  | Excuse | Reality |
  |---|---|
  | "Should work now" | RUN the verification |
  | "I'm confident" | Confidence ≠ evidence |
  | "Linter passed" | Linter ≠ compiler |
  | "Agent said success" | Verify independently |
  | "Partial check is enough" | Partial proves nothing |

  <example type="good">
    `[Run test command]` → See: 34/34 pass → "All tests pass"
  </example>

  <example type="bad">
    "Should pass now" / "Looks correct" / "I've written a regression test" (without red-green verification)
  </example>

</skill>
