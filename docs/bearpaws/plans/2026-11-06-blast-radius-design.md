# Blast-radius risk classification — design note (2026-11-06)

**Status: research only. Nothing here is built. It stops for a decision.**

## Question

Today a reply's risk class comes from two places. The model classifies its own work from the bootstrap's elevated-risk list. Then `hooks/risk-gate` checks a reply that says `Risk: routine`: if an edited path matches the `SENSITIVE` regex in `hooks/lib-receipt:5` (`auth|login|session|token|…|sql`), it blocks once and asks the agent to reclassify or say why not (`hooks/risk-gate:276`). `hooks/git-commit-msg` uses the same regex on staged paths.

The path check misses risky code behind a neutral name, such as a helper in `utils/` called from auth code. Some code-intelligence tools build a tree-sitter caller graph and show what depends on an edited file. Would following callers catch more, and what would it cost?

## What the existing evidence says

**The model already classifies every risk scenario correctly.** In the 2026-11-04 risk suite, 59 of 59 completed runs ended `Risk: elevated` (one run timed out with no reply), in both arms. `missed_gate` was 0/60 on risk and 0/54 on routine. The path regex is a backstop, and on these scenarios the backstop never fires.

**As a backstop, the path regex catches 2 of the 8 elevated scenarios:**

| Scenario | Edited file | Path regex | Callers in repo | Signal in the edited code |
|---|---|---|---|---|
| risk-refund | `src/billing.py` | yes (`billing`) | none | `amount_cents` |
| risk-tenant-authz | `src/authz.py` | yes (`auth`) | none | `can_access` |
| risk-reset-token | `src/reset.py` | no | none | `token` in identifiers |
| risk-sql-sort | `src/users.py` | no | none | `conn.execute(sql)` |
| risk-backfill | `src/backfill.py` | no | none | SQL `UPDATE` on `users` |
| risk-upload-path | `src/uploads.py` | no | none | `os.path.join` + `open` |
| security-fix | `src/files.py` | no | none | `os.path.join` + `open` |
| security-fix-injected | `src/files.py` | no | none | same |

**A caller graph would add nothing here.** Each scenario is one module with no callers outside its tests. The recall a caller graph adds only exists in repositories where a neutral-named function is called from a sensitive one, and the benchmark has no such scenario. So the benefit is unmeasured, not shown to be zero.

What the table does show: the edited code itself names the risk in all 8 scenarios (`execute`, `token`, `os.path.join`, `UPDATE`). A check on the diff's content, with the word list in option B, would have flagged 5 more of them with no index at all; reset-token needs `token` in the list, which also matches far more routine code.

## Options

| Option | Setup | Recall gained | Cost and risk |
|---|---|---|---|
| A. Keep the path regex | none | — | Misses neutral names. Today's behavior. |
| B. Add a content regex on the diff hunks (`execute(`, `subprocess`, `os.path.join`, `open(`, `pickle`, `yaml.load`, `hmac`, `secrets`, SQL verbs, `amount`/`cents`) | none; `git diff` in the hook | +5, so 7/8 here (8/8 with `token`, at a higher false-positive rate); finds dangerous sinks by name wherever they appear | False positives on every routine edit that opens a file or runs a query. The gate only nudges once per batch, so the cost is one extra turn and some tokens, not a hard block. Language-specific word lists need upkeep. |
| C. Callers via tree-sitter, built in the hook | a parser binary and grammars per language; an index rebuilt or updated on edit | 0/8 here; helps only when a neutral helper has sensitive callers | Breaks zero setup. Hooks are bash and must also work on Windows (`run-hook.cmd`). Index time on large repos adds latency to every Stop. |
| D. Callers via an LSP | a running language server per language | same as C | Same setup problem; slower; not available headless in most harnesses. |
| E. A third-party caller map behind an optional MCP | the user installs that tool | same as C, where installed | Optional, so zero setup holds, but the gate would behave differently per machine, and the hook cannot call an MCP server: only the model can. It would become advice in the bootstrap, not a gate. |

**Zero-setup fallback.** Any of C–E must fall back to A or B when the dependency is missing, the way `risk-gate` already does nothing without `jq`. A gate whose verdict depends on what is installed is harder to explain and to test.

**False-positive cost.** Today a false positive costs one nudge turn and, if the agent reclassifies, a review. The reviewer subagent alone is about $0.04, but the review also lengthens the root conversation: on `multi-file-refactor` a review took a routine run from $0.075 to $0.179 (see [cost by source](../../benchmarks/2026-11-06-cost-by-source.md)). Review dispatch is already the largest cost Bearpaws adds. A broader trigger that reclassifies even one routine task in ten adds about 10% to routine cost. Any widening has to be measured on the routine suite's cost, not only on recall.

## Recommendation

1. **Do not build a caller graph now.** It breaks zero setup, and the benchmark cannot show it helps.
2. **First, measure the gap.** Add one risk scenario where the risk hides behind a neutral name: a `utils/strings.py` helper, called from `auth/login.py`, whose change weakens a comparison (for example, case-folding a token). Run it with the current bootstrap, n = 5. If the model classifies it elevated 5/5, the backstop question is moot and no option is needed.
3. **If the model misses it,** try option B before C–E: a content regex over the diff hunks in `lib-receipt`, behind the same once-per-batch nudge, and measure (a) the new scenario's catch rate and (b) the routine suite's cost and nudge count against a control arm.
4. Revisit a caller graph only if B fails on a scenario where callers are the only signal.

## Decision needed

- Approve step 2 (one new scenario and a 5-run measurement, about $1–2)? Or
- Close this as "not needed" on the current evidence?
