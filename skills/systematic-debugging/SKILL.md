---
name: systematic-debugging
description: Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes
---

<skill>

  <purpose>
    Random fixes waste time and create new bugs. ALWAYS find root cause before attempting fixes. Symptom fixes are failure. Violating the letter of this process is violating the spirit of debugging.
  </purpose>

  <triggers>
    <rule>Use for ANY technical issue: test failures, bugs, unexpected behavior, performance problems, build failures.</rule>
    <rule>Use ESPECIALLY under time pressure, when "just one quick fix" seems obvious, or after multiple failed fixes.</rule>
  </triggers>

  <warning level="hard">
    NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST. If you haven't completed Phase 1, you cannot propose fixes.
  </warning>

  <process>
    <step>**Phase 1: Root Cause Investigation** — (a) Read error messages completely (stack traces, line numbers, error codes). (b) Reproduce consistently (exact steps, every time?). (c) Check recent changes (git diff, new deps, config, env). (d) In multi-component systems: add diagnostic instrumentation at each component boundary BEFORE proposing fixes — log what enters/exits each layer, run once, analyze where it breaks. (e) Trace data flow backward to source (see root-cause-tracing.md).</step>
    <step>**Phase 2: Pattern Analysis** — Find working examples of similar code. Compare against references (read completely, don't skim). List every difference between working and broken. Understand all dependencies and assumptions.</step>
    <step>**Phase 3: Hypothesis and Testing** — Form ONE specific hypothesis ("X is root cause because Y"). Make the SMALLEST change to test it. One variable at a time. Didn't work? New hypothesis — don't pile fixes.</step>
    <step>**Phase 4: Implementation** — Create failing test (use bp:test-driven-development). Implement single fix addressing root cause. Verify: test passes, no regressions. If fix doesn't work: return to Phase 1 with new info.</step>
  </process>

  <gate name="three-fix-limit">
    If 3+ fixes have failed: STOP. This is an architectural problem, not a bug. Signals: each fix reveals new coupling, fixes require "massive refactoring", each fix creates new symptoms elsewhere. Discuss fundamentals with your human partner before attempting more fixes.
  </gate>

  ## Red Flags — STOP and return to Phase 1

  - "Quick fix for now, investigate later"
  - "Just try changing X and see if it works"
  - "Skip the test, I'll manually verify"
  - "It's probably X, let me fix that"
  - "I don't fully understand but this might work"
  - "Here are the main problems:" (listing fixes without investigation)
  - Proposing solutions before tracing data flow
  - "One more fix attempt" (when already tried 2+)

  ## Common rationalizations

  | Excuse | Reality |
  |---|---|
  | "Issue is simple, don't need process" | Simple issues have root causes. Process is fast for simple bugs. |
  | "Emergency, no time for process" | Systematic is FASTER than guess-and-check thrashing. |
  | "Just try this first, then investigate" | First fix sets the pattern. Do it right. |
  | "I see the problem, let me fix it" | Seeing symptoms ≠ understanding root cause. |
  | "One more fix attempt" (after 2+) | 3+ failures = architectural problem. Question the pattern. |

  ## Quick reference

  | Phase | Key Activities | Gate |
  |---|---|---|
  | 1. Root Cause | Read errors, reproduce, check changes, instrument | Understand WHAT and WHY |
  | 2. Pattern | Find working examples, compare, list differences | Identified differences |
  | 3. Hypothesis | Single theory, minimal test, one variable | Confirmed or new hypothesis |
  | 4. Implementation | Failing test, single fix, verify | Bug resolved, tests pass |

  <see file="root-cause-tracing.md"/>
  <see file="defense-in-depth.md"/>
  <see file="condition-based-waiting.md"/>

</skill>
