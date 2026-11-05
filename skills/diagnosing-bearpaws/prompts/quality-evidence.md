# Dimension: quality evidence

Judge whether the session's evidence supports the quality of what it built, from the transcript alone.

Look for:
- Tests written for the change: were they run, did they fail first (TDD), and do they cover what the
  request asked (edge cases the request or a review named)?
- Test runs whose output shows failures, errors, skips or zero tests collected, and what the session
  did next (fixed, re-ran, or moved on).
- Weakened checks: a test edited to pass (assertion loosened, test deleted, `skip` added) after it failed.
- Claims in assistant text ("all tests pass", "verified", "works") with no run behind them.
- Review findings about correctness, and whether a later edit addresses each.

You may not claim: that code is correct or buggy beyond what a test output, review or edit in the
transcript shows; that a test would pass or fail if run. You cannot run the session's project; say what
the transcript shows.
