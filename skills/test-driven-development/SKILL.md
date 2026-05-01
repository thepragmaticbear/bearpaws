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
    <rule>Use when refactoring or changing behavior in existing code.</rule>
  </triggers>

  <warning level="hard">
    NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST. Violating the letter of the rules is violating the spirit. Write code before the test? Delete it. Start over. No exceptions without your human partner's permission.
  </warning>

  <rules>
    <rule>Test-first is non-negotiable. RED before GREEN.</rule>
    <rule>Wrote code before the test? Delete it. Don't keep it as "reference", don't "adapt" it, don't look at it. Delete means delete. Implement fresh from tests.</rule>
    <rule>Exceptions (ask your human partner first): throwaway prototypes, generated code, configuration files.</rule>
  </rules>

  <process>
    <step>**RED** — Write one minimal failing test showing what should happen. One behavior, clear name, real code (no mocks unless unavoidable).</step>
    <step>**Verify RED** — Run `npm test path/to/test.test.ts`. Confirm: test *fails* (not errors), failure message is expected, fails because feature is missing (not typos). Test passes immediately? You're testing existing behavior — fix the test.</step>
    <step>**GREEN** — Write the simplest code to pass the test. Don't add features, refactor other code, or "improve" beyond the test.</step>
    <step>**Verify GREEN** — Run tests. Confirm: test passes, *all other* tests still pass, output is pristine (no errors, warnings). Test fails? Fix code, not test. Other tests fail? Fix now.</step>
    <step>**REFACTOR** — After green only: remove duplication, improve names, extract helpers. Keep tests green. Don't add behavior.</step>
    <step>**Repeat** — Next failing test for next behavior.</step>
  </process>

  <flow format="dot">
    ```dot
    digraph tdd_cycle {
      rankdir=LR;
      red [label="RED\nFailing test", shape=box, style=filled, fillcolor="#ffcccc"];
      green [label="GREEN\nMinimal code", shape=box, style=filled, fillcolor="#ccffcc"];
      refactor [label="REFACTOR\nClean up", shape=box, style=filled, fillcolor="#ccccff"];
      red -> green -> refactor -> red;
    }
    ```
  </flow>

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

    **REFACTOR** — Extract validation for multiple fields if needed.
  </example>

  <example type="bad">
    Writing production code first, then writing tests that pass immediately. Passing immediately proves nothing — you never saw the test catch the bug.
  </example>

  <antipattern>
    "I'll write tests after to verify it works" — Tests-after answer "What does this do?" Tests-first answer "What *should* this do?" Tests-after are biased by your implementation. You test what you built, not what's required.
  </antipattern>

  <antipattern>
    "Keep as reference, write tests first" — You'll adapt it. That's testing after. Delete means delete.
  </antipattern>

  ## Common Rationalizations

  | Excuse | Reality |
  |--------|---------|
  | "Too simple to test" | Simple code breaks. Test takes 30 seconds. |
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

  - [ ] Every new function/method has a test
  - [ ] Watched each test fail before implementing
  - [ ] Each test failed for expected reason (feature missing, not typo)
  - [ ] Wrote minimal code to pass each test
  - [ ] All tests pass with pristine output
  - [ ] Tests use real code (mocks only if unavoidable)
  - [ ] Edge cases and errors covered

  Can't check all boxes? You skipped TDD. Start over.

  <see file="testing-anti-patterns.md"/>

</skill>
