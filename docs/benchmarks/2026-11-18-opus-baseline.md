# Opus baseline — 2026-11-18

This is the first full-session benchmark on Opus, the model users complain about. Every earlier benchmark was Sonnet. The first two sections measure v4.0.0 as released; the follow-ups measure two rule changes made the same day, a cut-down bootstrap, and a four-arm comparison with a fresh no-plugin control and a two-sentence note. The severity rule that v4.1.0 ships (a confirmed defect in changed code in the task's risk class is at least Important, even if the reviewer calls it Minor) was added after every live run here; no row measures it.

**On Opus, v4.0.0 was accepted more often than no plugin on the default suite (27/27 against 24/27) and less often on the risk suite (16/18 against 18/18). It let fewer defects escape the risk suite (3/18 runs against 9/18, but only 1 of 6 task types against 3 of 6). It cost 3.3 times as much per accepted task on the default suite and 6.3 times on the risk suite, and took about 5 times as long inside the session.** After the two rule changes below (the full arm of the ablation), the cost ratio is 1.9 times on the default suite (0.316 against 0.164) and 4.1 times on the risk suite (0.593 against 0.144). Review-specific spend was not measured, but the extra spend is concentrated in reviewed runs, which are the runs Bearpaws classified as elevated. On v4.0.0 those included two scenarios the benchmark treats as routine (a cart discount and a money formatter); the money-scope change made both routine. On the fully routine scenarios the overhead is 33 to 65 percent.

Two clocks appear below. **In-session** is the CLI's `duration_ms`, summed over the result events in each run's `stream.jsonl`. **Wall** is the row's `seconds` field, elapsed time around the CLI call, before acceptance checks; it also counts time outside the session: 11 runs in both arms, all the third run of their cell, spent 2.5 to 35 extra minutes outside it (for example a no-plugin `risk-upload-path` run: 1,565 s wall, 33 s in session). Ratios in this document use in-session time.

`$/accepted` counts a run as a win when it is accepted, even if it reported `Status: INCOMPLETE`. Tables give that count separately as "accepted, INCOMPLETE".

## Method

- Runner: `tests/benchmark/run.sh --model opus --jobs 3` at `9d84019`. Claude Code 2.1.325, model alias `opus` (claude-opus-5-5). Arms: no plugin (`baseline`) and Bearpaws. 3 runs per cell, the default non-interactive suffix.
- Data: [`2026-11-18-opus-routine.jsonl`](2026-11-18-opus-routine.jsonl) (54 rows) and [`2026-11-18-opus-risk.jsonl`](2026-11-18-opus-risk.jsonl) (36 rows). Total spend: $35.57. Transcripts: `/tmp/bearpaws-tests/benchmark/opus-*-20261118/runs/<scenario>/<arm>/<run>/`.
- The saved rows carry an `actions` field from a scorer experiment that was later removed; nothing here uses it.
- `--cost-sources` was not run: `PRICES` in `summarize.py` holds only Sonnet prices.
- n=3 per cell is a smoke-level sample. Read per-scenario differences under about 30% as noise. See Limits before relying on any comparison.

## Default suite (9 scenarios), v4.0.0

| Arm | Runs | Accepted | Accepted, INCOMPLETE | $/accepted | In-session s | Wall s | Reviews req/ret | Missed gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| No plugin | 27 | 24 | 0 | 0.164 | 21 | 42 | 0/0 | 6 |
| Bearpaws | 27 | **27** | 0 | 0.537 | 106 | 319 | 33/33 | 0 |

No plugin failed `resume-after-context-loss` in all 3 runs; Bearpaws passed it in all 3. That scenario rewards leaving seeded history alone (see Limits).

| Scenario | No plugin $/acc | Bearpaws $/acc | Ratio | Bearpaws risk call | Reviews |
|---|---:|---:|---:|---|---:|
| small-bug | 0.118 | 0.191 | 1.6× | routine | 0 |
| broken-test-config | 0.128 | 0.171 | 1.3× | routine | 0 |
| conventions | 0.120 | 0.197 | 1.6× | routine | 0 |
| resume-after-context-loss | n/a (0/3) | 0.231 | — | routine | 0 |
| new-subsystem | 0.190 | 0.552 | 2.9× | 2 routine, 1 elevated (concurrency) | 2 |
| simple-feature | 0.132 | **1.093** | **8.3×** | elevated (money) 3/3 | 11 |
| multi-file-refactor | 0.149 | 0.739 | 5.0× | elevated (money formatting) 3/3 | 6 |
| security-fix | 0.144 | 0.852 | 5.9× | elevated | 7 |
| security-fix-injected | 0.145 | 0.810 | 5.6× | elevated | 7 |

`simple-feature` adds discount codes to a cart, and `multi-file-refactor` consolidates price formatters. v4.0.0's "money" surface made both elevated, so each got pinning tests, a review and often a re-review.

## Risk suite (6 scenarios), v4.0.0

| Arm | Runs | Accepted | Accepted, INCOMPLETE | Escaped | Strict | $/accepted | $/strict | In-session s | Wall s | Reviews req/ret |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| No plugin | 18 | **18** | 0 | 9 | 9 | 0.144 | 0.288 | 28 | 123 | 0/0 |
| Bearpaws | 18 | 16 | 0 | **3** | 13 | 0.910 | 1.120 | 151 | 384 | 42/42 |

Strict: accepted, hidden attack passes, and not `Status: INCOMPLETE`.

Escapes by scenario (runs escaped of 3):

| Scenario | No plugin | Bearpaws |
|---|---:|---:|
| risk-refund | 3 | 0 |
| risk-tenant-authz | 3 | 0 |
| risk-reset-token | 3 | 3 |
| risk-backfill, risk-sql-sort, risk-upload-path | 0 each | 0 each |

Within each scenario, escapes are all-or-nothing in both arms in these morning rows (not in the later four-arm run; see the last follow-up), so the effective sample is 6 task types, not 36 independent runs. Unpaired, counting runs: 3/18 against 9/18, Fisher exact p = 0.075. Unpaired, counting task types: 1/6 against 3/6, p = 0.545. Paired by scenario, two scenarios are discordant (both in Bearpaws' favour) and none the other way: exact paired p = 0.50. Acceptance 16/18 against 18/18: p = 0.49.

- Bearpaws closed both escapes that no plugin had in `risk-refund` and `risk-tenant-authz`. Both arms escaped every run of `risk-reset-token`.
- **Both Bearpaws failures are a review-induced guard.** In `risk-backfill` runs 1 and 2 the reviewer suggested raising when the connection has an open transaction. The agent added the guard, and it rejects the caller the acceptance test models. Run 3 passed after five reviews, $3.22 and 575 s in session (44 minutes wall).

## Follow-up: money scope and review cap

Two rule changes, then Bearpaws-only re-runs on Opus (5 runs per scenario; the no-plugin and "before" columns are the 3-run cells above). Raw rows: `2026-11-18-opus-money-scope.jsonl` (both changes, cap still only in `requesting-code-review`) and `2026-11-18-opus-review-cap.jsonl` (cap in the bootstrap). No run in either set was accepted with `Status: INCOMPLETE`.

1. **Money means moving money.** Elevated when code charges, refunds, pays out, transfers, or writes balances; price display, formatting, and cart or discount arithmetic are routine. Changed in `using-bearpaws`, `subagent-driven-development`, the diagnosis prompt, and the hooks' path heuristic. Routing eval on Opus, `cart-discount`: 1/3 routine before, 3/3 after; refund and billing cases stay elevated.
2. **At most three reviews per change** (the review and two re-reviews), then no further edits. Placed first in `requesting-code-review`, where it had little effect: 1 of 30 runs loaded that skill (`risk-tenant-authz` run 5; agents usually dispatch `bp:code-reviewer` directly), and `risk-backfill` used 6, 9, 6, 2 and 3 reviews. The gate requires a fresh review after any edit; why the agents kept editing after review was not established. Moved into the bootstrap (subagent-driven development keeps its own five-round cap per task); `requesting-code-review` now carries the same stop rule.

| Scenario | No plugin $/acc | Bearpaws before | Money scope | + review cap in bootstrap |
|---|---:|---:|---:|---:|
| `simple-feature` | 0.132 | 1.093 (3.7 reviews) | **0.195** (0 reviews), 5/5 | — |
| `multi-file-refactor` | 0.149 | 0.739 | **0.228** (0 reviews), 5/5 | — |
| `risk-refund` | 0.156 (3/3 escaped) | 0.631 (0/3) | 0.600 (0/5; 3, 2, 1, 2, 2 reviews) | 0.355 (0/5, 1 review each) |
| `risk-backfill` | 0.150 | 4.723, 1/3 accepted | 2.624, 4/5 (6, 9, 6, 2, 3 reviews) | **1.118**, 4/5 (3, 1, 3, 2, 3 reviews) |
| `risk-tenant-authz` | 0.131 (3/3 escaped) | 0.944 (0/3) | 0.683 (**2/5** escaped) | — |
| `risk-reset-token` | 0.128 (3/3 escaped) | 0.445 (3/3) | 0.446 (5/5) | — |

- `risk-refund` became cheaper although the earlier cap never bound: no run before it used more than three reviews. The drop is within the session-to-session spread described under Limits.
- `risk-backfill` became cheaper alongside fewer reviews: three runs before it used 6 to 9, none after it more than 3. Review-specific spend was not measured, so this is an association.
- The one rejected `risk-backfill` run under the cap stopped at three reviews and reported `Status: INCOMPLETE` with two Important findings in `Open:`.
- `risk-reset-token` still escapes in every run of both arms.

## Follow-up: minimal-bootstrap ablation

Question: how much of the always-loaded bootstrap does anything on Opus? The `min` arm is a copy of the working tree (both rule changes above included) whose `skills/using-bearpaws/SKILL.md` keeps only the subagent-stop line, the Elevated risk section, the Risk receipt paragraph and one sentence saying other skills are optional: 2,769 bytes against 5,591. Hooks, agents and every other skill are identical. `min` and `bearpaws` (full) ran interleaved, 3 runs per cell; the no-plugin column is the morning's rows. Raw rows: [`2026-11-18-opus-ablation-routine.jsonl`](2026-11-18-opus-ablation-routine.jsonl) and [`2026-11-18-opus-ablation-risk.jsonl`](2026-11-18-opus-ablation-risk.jsonl). Spend: $35.67 with the smoke run. The minimal bootstrap is saved as [`2026-11-18-opus-ablation-minimal-bootstrap.md`](2026-11-18-opus-ablation-minimal-bootstrap.md). The full arm used the working tree's bootstrap at the time (5,591 bytes), which differs from the 5,586-byte bootstrap in the four-arm run below only in the review-cap sentence.

| | No plugin | Minimal | Full |
|---|---:|---:|---:|
| Default suite: accepted | 24/27 | 27/27 | 27/27 |
| Default suite: accepted, INCOMPLETE | 0 | 0 | 1 |
| Default suite: $/accepted | 0.164 | 0.254 | 0.316 |
| Default suite: in-session s | 21 | 38 | 49 |
| Default suite: reviews req/ret | 0/0 | 9/9 | 11/11 |
| Risk suite: accepted | 18/18 | 16/18 | 18/18 |
| Risk suite: accepted, INCOMPLETE | 0 | 1 | 4 |
| Risk suite: escaped | 9 | 3 | 3 |
| Risk suite: strict (accepted, attack passes, not INCOMPLETE) | 9/18 | 12/18 | 11/18 |
| Risk suite: $/accepted | 0.144 | 0.593 | 0.593 |
| Risk suite: $/strict | 0.288 | 0.790 | 0.970 |
| Risk suite: in-session s | 28 | 97 | 113 |
| Risk suite: reviews req/ret | 0/0 | 28/28 | 28/28 |

- **Minimal matched full on escapes and on risk classification** (every scenario classified the same way in all 3 runs of both arms). On acceptance it lost two `risk-backfill` runs to the open-transaction guard; on the strict score it is one run ahead, because four of full's accepted risk runs ended INCOMPLETE. At n=3 neither difference is evidence about the bootstrap text.
- Minimal invoked no skill in 45 runs. Full invoked `bp:onboarding-to-a-project` in 19 of 45 and `bp:executing-plans` in 2; nothing else. Full cost about 24% more per accepted task on the default suite. `security-fix-injected` accounts for 55% of that cost gap (full ran 6 reviews there against minimal's 4; one full run cost $1.32). Without the two security scenarios the gap is about 14%. Onboarding's own spend was not measured.
- `risk-reset-token` escaped 3/3 in all three arms.

## Agent behavior

The headless suffix grants approval, so this measures what agents did, not interruptions.

- No run of either arm called `AskUserQuestion`.
- **Commits.** Only `resume-after-context-loss` asks for commits (its plan says to commit after each task). Git history in each run's `work/` shows the agent added commits in 43 of 45 no-plugin sessions and 23 of 45 Bearpaws sessions across the default and risk suites.
- `bp:onboarding-to-a-project` ran in 21 of 45 Bearpaws runs, `bp:test-driven-development` in 5 and `bp:executing-plans` in 1. In `small-bug`, the run that loaded onboarding took 23 s in session against a no-plugin mean of 12 s; the Bearpaws mean of 59 s comes from a 141 s run that loaded `bp:test-driven-development`.
- `bp:brainstorming` and `bp:writing-plans` never fired. The concern about forced design approval did not show up here, though these prompts are fully specified.

## Transcript checks

- **`resume-after-context-loss` is not a demonstrated plugin win.** All 3 no-plugin runs did the task, then also changed an already-finished task; the acceptance test rejects the second commit to that file by design. Bearpaws left it alone, but 2 of its 3 runs loaded no skill, so nothing ties the difference to skill text.
- **`risk-backfill` is partly a scenario problem.** The reviewer offered the guard as one of two options ("raise an error when `conn.in_transaction` is true on entry, or document that the function owns the commit") and the root agent chose it. The prompt says nothing about transactions; acceptance rejects the guard only because its fixture inserts rows without committing.
- **`risk-reset-token` is a scoping failure, not a detection failure.** In all 8 Bearpaws runs examined the reviewer noticed that tokens are not single-use and rated it Minor or outside the requirement; each run ended `Open: none`, `Status: COMPLETE`. The prompt asks only for expiry.
- **`risk-tenant-authz` 2/5 escapes after the money change:** in both, the reviewer reproduced the cross-org owner case and rated it Minor. Severity does not separate escapes from passes: in passing run 2 the first reviewer also rated it Minor and the agent fixed it anyway; in run 1 it was Important; in run 5 the agent closed it before review. No sign the rule changes caused the escapes (0/3 against 2/5, Fisher p ≈ 0.46).
- **The money-scope change removes a behavior difference review produced.** The `simple-feature` prompt says only "rounded to 2 decimals". Before the change, the reviewers in all 3 runs chose half-up rounding (0.95 with SAVE10 gives 0.86, where Python's `round` gives 0.85), and the agents adopted it. After it, runs are routine and unreviewed and keep `round`, as no plugin does. Acceptance does not test this case. Reviews of `multi-file-refactor` never changed source.

## Limits

- **No plugin ran once, in the morning.** Every later comparison reuses those rows, except the last follow-up, which has its own control. Bearpaws' own cost on scenarios the rule changes did not touch moved by up to 2 times between sessions (`new-subsystem` 0.552 then 0.288, though one morning run classified it elevated and was reviewed; `risk-sql-sort` 0.544 then 0.361, `risk-upload-path` 0.714 then 0.501; no run of these used more than three reviews, so the cap cannot explain it). Cross-session ratios carry that noise.
- **Two risk scenarios test requirements the prompt does not state.** `risk-reset-token` asks only for a one-hour expiry; its hidden attack tests single use. `risk-backfill`'s acceptance fixture inserts rows and leaves the transaction open, so a guard against an open transaction fails acceptance though the prompt never mentions transactions.
- **`resume-after-context-loss` rewards leaving seeded history alone**, not resuming a plan well.
- Every prompt is fully specified, so brainstorming, planning and the Red Flags table were not exercised. Opus only. The scenario repos are too small to show what onboarding is worth on a real codebase.

## Follow-up: note arm, short bootstrap, review cap, vague requests

Four arms ran interleaved on Opus, 3 runs per cell, with a fresh no-plugin control: no plugin; **note** (no plugin, only a SessionStart hook injecting two sentences: dispatch a subagent to review the diff independently before reporting a change done if it touches auth, secrets, moving money, data deletion or migration, untrusted input, SQL or shell, or concurrency, and fix what it finds; otherwise just do the work); **full** (the bootstrap with the rule changes above, 5,586 bytes); **short** (a candidate replacement, 3,396 bytes, saved as [`2026-11-18-opus-short-bootstrap.md`](2026-11-18-opus-short-bootstrap.md): the same Elevated risk and Risk receipt text, the harness loading steps, and two sentences of routing in place of the skill mandate, Red Flags table, Pace Control, skill priority, skill types and brevity policy). Skills, hooks and agents were identical in full and short. Rows: [`2026-11-18-opus-4arm-routine.jsonl`](2026-11-18-opus-4arm-routine.jsonl), [`2026-11-18-opus-4arm-risk.jsonl`](2026-11-18-opus-4arm-risk.jsonl), [`2026-11-18-opus-vague.jsonl`](2026-11-18-opus-vague.jsonl), [`2026-11-18-opus-tenant-rerun.jsonl`](2026-11-18-opus-tenant-rerun.jsonl). Spend: $59.57 in the rows (plus a $0.12 smoke run) and $10.71 for the rerun.

In these follow-up files, the raw `arm` labels are `baseline` for No plugin, `note` for Note, `full` for Full, and `bearpaws` for Short. In the earlier files, `bearpaws` denotes the full bootstrap used in that run.

| Risk suite (18 runs each) | No plugin | Note | Full | Short |
|---|---:|---:|---:|---:|
| Accepted | 18 | 16 | 18 | 17 |
| Accepted, INCOMPLETE | 0 | 0 | 1 | 2 |
| Escaped | 8 | 3 | 3 | 6 |
| Strict (accepted, attack passes, not INCOMPLETE) | 10 | 13 | 14 | 9 |
| $/accepted | 0.133 | 0.331 | 0.559 | 0.553 |
| $/strict | 0.240 | 0.407 | 0.718 | 1.045 |
| Reviews requested | 0 | 18 | 29 | 25 |

| Default suite (27 runs each) | No plugin | Note | Full | Short |
|---|---:|---:|---:|---:|
| Accepted | 26 | 27 | 27 | 27 |
| $/accepted | 0.152 | 0.187 | 0.266 | 0.256 |
| Reviews requested | 0 | 6 | 7 | 9 |

- **The note matched full on escapes (3 each) at lower cost.** It dispatched one review in every run of the six risk scenarios and the two security-fix scenarios, and none elsewhere. Its two unaccepted runs are both `risk-backfill` (cause not opened; that scenario's fixture is known to be unfair). On this suite the note arm, which only asks for an independent review of risky changes, matched the plugin's measured defect benefit. The receipt, gate, pinning and cap did not show up as fewer escapes.
- **Short against full.** Level on the default suite. On the risk suite the escape gap is `risk-tenant-authz`: short escaped 3/3, full 0/3 (the strict gap also includes one unaccepted `risk-backfill` run and one more INCOMPLETE). A rerun of that scenario alone, 10 runs per arm, gave short 6/10 and full 3/10 (Fisher p = 0.37; pooled with the 3-run cells 9/13 against 3/13, p = 0.047, a comparison chosen after seeing the first result). The note arm escaped 0/3.
- **Why tenant-authz escapes.** In 25 of the 26 plugin runs (a text search of the first review found no mention in the other), the reviewer saw that a member who owns a resource in another organization is still allowed. Runs escaped when the first review rated it Minor or outside the bug report ("nothing in the repo shows a member can own a resource outside their org") and the root agent stopped after one review; runs passed when it was rated Important and fixed. The scenario repo has no caller of `can_access`, and the reviewer's rule defines reachable as "a caller in this repository or a user's input". No text present in full and absent in short could be tied to the difference.
- **`risk-reset-token` escaped 3/3 in all four arms.**

**Review cap in live sessions** (48 full and short runs on the risk suite and the security-fix scenarios): 32 runs had one review, 10 had two, 6 had three. No run exceeded three, edited source after the third, ended COMPLETE with an unfixed Critical or Important finding from its last review, or ended INCOMPLETE over Minor findings alone. Two runs fixed their last review's Important finding (committed `.pyc` files) with `git rm --cached` and an amend, without a re-review.

**Vague requests** (three one-sentence, under-specified prompts; `--interactive`, so no "don't ask" suffix; 5 runs per cell; scenarios kept outside the repo). Outcomes as stopped to ask / built and listed its choices / built silently:

| Scenario | No plugin | Full | Short |
|---|---|---|---|
| vague-export | 0 / 5 / 0 | 1 / 4 / 0 | 0 / 5 / 0 |
| vague-notify | 0 / 5 / 0 | 4 / 1 / 0 | 0 / 5 / 0 |
| vague-speed | 0 / 4 / 1 | 0 / 4 / 1 | 0 / 5 / 0 |

- Full loaded `bp:brainstorming` in 5 of 15 runs, exactly the five that stopped; short and no plugin loaded no skill and always built. Full loaded `bp:onboarding-to-a-project` in 15 of 15 with no visible difference in outcome.
- Stopping mattered on `vague-notify`, where the builds disagreed on who gets contacted and how (email with text fallback in one, both channels in others). On the other two, building with listed choices was as good.
- **The text-only routing eval predicted the opposite.** It scored short 27/27, with both vague cases routing to `bp:brainstorming` 3/3. Live, short did so 0/15. That eval records stated intent and is not evidence of behavior.

**Decision.** The short bootstrap was not adopted; the full bootstrap stays. Short saves about 550 tokens per session with no measurable cost difference on routine tasks (0.256 against 0.266, within noise), loses the ask-first behavior on vague requests, and is probably worse on authorization work. An independent second read of the transcripts recommended going smaller still (about the note's content); that was not adopted either, because it has not been run as a plugin arm and the gate still needs the receipt text.

## Next

1. Reviewer severity when the repository has no caller: a same-risk-class defect the reviewer reproduces through the changed function's own parameters is being rated Minor about half the time. v4.1.0 ships a rule, added after these runs, that counts such a confirmed defect as at least Important; [`tests/fixloop-eval/evidence.md`](../../tests/fixloop-eval/evidence.md) checks only how an agent handles a finding already labeled Minor, not whether reviewers assign the right severity in the first place. Test that live, test reviewer wording with `tests/review-eval` on a fixture like `risk-tenant-authz`, and check `risk-backfill` and diff size for the opposite failure (speculative guards).
2. Fix the two unfair scenarios: state the single-use requirement in `risk-reset-token` (or drop that attack), and make `risk-backfill`'s fixture commit before calling the function (or state the transaction contract in the prompt).
3. Trim the bootstrap one block at a time, each against full in live runs that include vague prompts and `risk-tenant-authz`; do not rely on the routing eval for it.
4. Run the note as a plugin arm with the hooks on (note text plus the receipt paragraph) to separate what the bootstrap's risk text buys from what the gate buys.
