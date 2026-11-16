---
name: test-driven-development
description: Use when implementing any feature or bugfix, before writing implementation code
---

<skill>

  <purpose>
    Write the test first. Watch it fail. Write minimal code to pass. If you didn't watch the test fail, you don't know if it tests the right thing.
  </purpose>

  <triggers>
    <rule>Use when implementing any new feature, before writing implementation code.</rule>
    <rule>Use when fixing any bug — write a failing test that reproduces it first.</rule>
    <rule>Use when changing behavior in existing code, including during a refactor.</rule>
  </triggers>

  <warning level="hard">
    NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST. Violating the letter of the rules is violating the spirit. Write code before the test? Delete it. Start over. No exceptions without your human partner's permission.
  </warning>

  <rules>
    <rule>Test-first is non-negotiable. RED before GREEN.</rule>
    <rule>Wrote code before the test? Delete it. Don't keep it as "reference", don't "adapt" it, don't look at it. Delete means delete. Implement fresh from tests.</rule>
    <rule>Exceptions (ask your human partner first): throwaway prototypes, generated code.</rule>
    <rule>**Exempt, no new test or permission needed:** docs and comments that shape no agent's or tool's behavior; behavior-preserving typo, format, rename and refactor changes; config no caller or user can observe (lint, formatter). Overrides the warning, tables, Red Flags and checklist for these only. Code/config: run existing tests and check uncovered behavior directly (run it, compare output), before and after; if you can't, end `Status: INCOMPLETE` naming it. Docs: name what you checked. Never exempt: elevated-risk work, even a pure rename, from the pins, review and receipt (`bp:using-bearpaws`), though it needs a failing test only if behavior changes; a changed runtime default, limit, flag or timeout, in any file; prompts or Markdown that shape agent or model behavior (test them with an eval or the project's prompt-content test).</rule>
  </rules>

  <process>
    <step>**RED** — Write one minimal failing test showing what should happen. One behavior, clear name, real code (no mocks unless unavoidable).</step>
    <step>**Verify RED** — Run the test alone, before any code edit, never in the same command. Confirm: test *fails* (not errors), failure message is expected, fails because feature is missing (not typos). Test passes immediately? You're testing existing behavior — fix the test.</step>
    <step>**GREEN** — Write the simplest code to pass the test. Don't add features, refactor other code, or "improve" beyond the test.</step>
    <step>**Verify GREEN** — Run tests. Confirm: test passes, *all other* tests still pass, output is pristine (no errors, warnings). Test fails? Fix code, not test. Other tests fail? Fix now.</step>
    <step>**REFACTOR** — After green only: remove duplication, improve names, extract helpers. Keep tests green. Don't add behavior.</step>
    <step>**Repeat** — Next failing test for next behavior.</step>
  </process>

  <example type="good">
    **RED** — Bug: empty email accepted
    ```typescript
    test('rejects empty email', async () => {
      const result = await submitForm({ email: '' });
      expect(result.error).toBe('Email required');
    });
    ```
    **Verify RED** — `FAIL: expected 'Email required', got undefined`

    **GREEN**
    ```typescript
    function submitForm(data: FormData) {
      if (!data.email?.trim()) return { error: 'Email required' };
      // ...
    }
    ```
    **Verify GREEN** — `PASS`
  </example>

  ## Common Rationalizations

  | Excuse | Reality |
  |--------|---------|
  | "Too simple to test" (changed behavior) | Simple code breaks. Test takes 30 seconds. |
  | "I'll test after" | Tests passing immediately prove nothing. |
  | "Already manually tested" | Ad-hoc != systematic. No record, can't re-run. |
  | "Deleting X hours is wasteful" | Sunk cost fallacy. Keeping unverified code is tech debt. |
  | "Need to explore first" | Fine. Throw away exploration, start with TDD. |
  | "Test hard = design unclear" | Listen to the test. Hard to test = hard to use. |
  | "TDD will slow me down" | TDD is faster than debugging. |
  | "This is different because..." | No. Start over with TDD. |

  ## Red Flags — STOP and Start Over

  - Code before test
  - Test passes immediately
  - Can't explain why test failed
  - Tests added "later"
  - Rationalizing "just this once"
  - "It's about spirit not ritual"

  **All of these mean: Delete code. Start over with TDD.**

  ## When Stuck

  | Problem | Solution |
  |---------|----------|
  | Don't know how to test | Write wished-for API. Write assertion first. Ask your human partner. |
  | Test too complicated | Design too complicated. Simplify interface. |
  | Must mock everything | Code too coupled. Use dependency injection. |

  ## Verification Checklist

  Before marking work complete:

  - [ ] Each changed behavior has a test; extend an existing test file or reuse a reproducing test first
  - [ ] Each test pins a user-visible behavior and fails if it breaks slightly, not that a framework works or an argument exists (a prompt-content test may assert required text)
  - [ ] Before review: broke the code each test you added or rewrote covers, then restored it; a test that still passed is fixed or deleted
  - [ ] Watched each test fail for the expected reason before implementing
  - [ ] Removed a pre-existing assertion only when your human partner's requirement made it untrue, never to get green; each named in the receipt

  Can't check all boxes? You skipped TDD. Start over.

  <see file="testing-anti-patterns.md"/>

</skill>
