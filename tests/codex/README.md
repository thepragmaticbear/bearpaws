# Codex conformance

Run offline assertion regressions first:

```sh
python3 tests/codex/test_conformance.py
```

Run seven fresh CLI turns with repo-level discovery and a bootstrap in throwaway repositories:

```sh
tests/codex/run-conformance.sh /tmp/bearpaws-tests/codex/new-run
```

The output directory must be fresh. The runner does not install skills or change global configuration. `GLOBAL=1` uses an existing global install instead. `NO_BOOTSTRAP=1` omits the repo bootstrap. `CODEX_MODEL` is an optional command-local model override; when unset, the configured model is used. The CLI version and chosen mode are recorded. Default timeout is 600 seconds per turn and 2400 seconds for the security fix; override with `CODEX_TIMEOUT` and `CODEX_C4_TIMEOUT`.

| Roadmap surface | Assertion | Required evidence |
| --- | --- | --- |
| Bootstrap | C0 | Successful completed read of using-bearpaws on ordinary debugging work |
| Skills activate | C1–C3 | Exact discovered names; actual explicit skill read and exact answer; automatic debugging skill read |
| Onboarding | C5 | Successful completed reads of the onboarding skill and CONTRIBUTING.md |
| Tool mapping | C9 | Actual source read, completed native source file change, and a successful nonempty test run |
| Subagents | C6 | Independent reviewer spawn correlated with a completed wait result containing the review |
| Review gate | C4 | Review skill loaded, independent review of the final edited revision, independent security acceptance checks pass |
| Verification gate | C7 | Verification skill loaded, integration command fails for missing PAYMENTS_DB_URL, exact INCOMPLETE final line |
| Completion behavior | C8 | Verification skill loaded, nonempty tests pass after the final edit, independent bug acceptance checks pass, exact COMPLETE final line |

`summary.json` keeps **passed**, **failed**, and **blocked** separate. Exit 0 means every assertion passed; exit 1 means completed turns failed a behavioral assertion; exit 2 means at least one turn was blocked (timeout, nonzero CLI exit, failed or missing terminal turn, malformed/missing evidence). A mixed run retains its failures even when exit 2 takes precedence. JSONL transcripts, stderr, status sidecars, and independent acceptance logs remain beside the summary.

These assertions inspect `item.completed` events rather than quoted tool names or prose. Native reads are recognized for `cat` and `rtk read`; unfamiliar tool event representations need their own regression fixtures before being accepted. Review evidence requires `collab_tool_call` spawn and correlated agent state. The old g3/g4 streams exposed empty wait events without reviewer identities or results; those events do not demonstrate a completed independent review. Missing evidence on an otherwise completed turn fails the assertion, and does not establish that a review never happened outside the captured stream. Transport limitations cannot justify support promotion.

No support-tier promotion follows from offline fixture tests. Live results are still required, and incomplete/blocked turns cannot pass from partial transcripts. The fresh run uses the existing security-fix, conventions, setup-unverifiable, and small-bug fixtures rather than adding another scenario catalog.
