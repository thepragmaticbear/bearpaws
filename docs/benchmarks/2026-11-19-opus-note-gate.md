# Opus: what the risk gate adds over a review note (2026-11-19)

Question: on Opus, does Bearpaws' risk gate (receipt plus Stop-hook enforcement) or the rest of the plugin catch defects that a two-sentence review note does not?

## Method

Four arms, interleaved, 3 runs per scenario, Opus, `tests/benchmark/run.sh` defaults otherwise (session timeout 1800 s).

- **No plugin.**
- **Note:** a SessionStart hook injecting two sentences: dispatch a subagent to review the diff independently before reporting a change done if it touches auth, secrets, moving money, data deletion or migration, untrusted input reaching paths, SQL or shell, or concurrency, and fix what it finds; otherwise just do the work. Same arm as [2026-11-18](2026-11-18-opus-baseline.md).
- **Note + gate:** the note plus the bootstrap's Risk receipt paragraph, with Bearpaws' `risk-gate` hooks (PreToolUse, PostToolUse, PostToolUseFailure, Stop) from v4.1.0. No skills, no reviewer agent, and not the bootstrap's three-review cap sentence. Files: [`2026-11-19-notegate-arm/`](2026-11-19-notegate-arm/). A smoke run confirmed the gate wrote its session log.
- **Full:** Bearpaws v4.1.0 (`main` at `fde2450`).

Two risk scenarios were fixed first, because they were unfair to every arm:

- `risk-reset-token`: the hidden attack required single-use tokens, which the prompt never asked for. The prompt now states it.
- `risk-backfill`: the acceptance and attack fixtures now commit their inserts before calling the function, so a guard against an open transaction no longer rejects the test's own setup.

`check_scenarios.py` still passes for all six (naive overlay fails an attack, reference passes). After the fixes, neither scenario separated any arm: 0 escapes and 0 rejections everywhere, no plugin included.

Rows: [`2026-11-19-opus-notegate-risk.jsonl`](2026-11-19-opus-notegate-risk.jsonl), [`2026-11-19-opus-notegate-routine.jsonl`](2026-11-19-opus-notegate-routine.jsonl). Raw `arm` labels: `baseline`, `note`, `notegate`, `bearpaws` (full). Spend: $58.68, plus $0.94 for the smoke run.

## Results

| Risk suite (6 scenarios, 18 runs each) | No plugin | Note | Note + gate | Full |
|---|---:|---:|---:|---:|
| Accepted | 18 | 18 | 18 | 18 |
| Escaped | 6 | **0** | **0** | **0** |
| Reported INCOMPLETE | 0 | 0 | 3 | 0 |
| $/accepted | 0.146 | **0.298** | 0.812 | 0.539 |
| Reviews requested (max per run) | 0 | 18 (1) | 52 (5) | 26 (2) |
| Mean in-session s | 19 | 54 | 166 | 103 |

| Default suite (9 scenarios, 27 runs each) | No plugin | Note | Note + gate | Full |
|---|---:|---:|---:|---:|
| Accepted | 27 | 27 | 26 | 27 |
| $/accepted | 0.155 | **0.190** | 0.349 | 0.295 |
| Reviews requested | 0 | 6 | 17 | 8 |
| Mean in-session s | 20 | 28 | 66 | 42 |

- **Escapes:** all six no-plugin escapes are `risk-refund` and `risk-tenant-authz` (3/3 each). Every arm that asked for a review closed both. Note, note + gate and full did not differ.
- **The gate added cost and no catches.** Without the bootstrap's cap sentence, note + gate re-reviewed after every follow-up edit (up to 5 reviews per run) and ran 2.7× the note's cost on the risk suite. This arm does not show what the gate costs with the cap in place; full has both and cost 1.8× the note.
- **Full against note:** same escapes and acceptance. Full cost 1.8× on the risk suite and 1.6× on the default suite. On the default suite the gap is spread across every scenario (onboarding ran in 15 of 27 runs), plus the two security-fix scenarios where full ran 4 reviews to the note's 3.
- Note + gate's one rejection is `resume-after-context-loss` run 1.
- Brainstorming did not fire in any arm; these prompts are fully specified. The earlier [vague-request runs](2026-11-18-opus-baseline.md#follow-up-note-arm-short-bootstrap-review-cap-vague-requests) are the only measured behavior full has that the note lacks (stopping to ask on an ambiguous request in 4 of 5 runs of one scenario).

## Limits

3 runs per cell, six risk task types, Python stdlib scenarios, one model. Escapes are all-or-nothing per scenario here, so the risk comparison rests on two scenarios. After the fixes, `risk-reset-token` no longer has a hidden defect any arm misses, so the suite has lost its hardest case. Nothing here measures what the receipt and gate do for honest status reporting, which they are designed for, rather than for catching defects.

## Conclusion

On this suite and model, the defect benefit comes from asking for an independent review of risky changes. The gate, the receipt, onboarding and the other skills did not catch more, and cost 1.6–2.7× the note. Candidates for a smaller default: the risk list and the review request (the note), the review cap, and a brainstorming trigger for vague requests, with the gate opt-in. That needs a new arm run before shipping, plus a harder replacement for `risk-reset-token`.
