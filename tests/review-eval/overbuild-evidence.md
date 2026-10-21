# Over-building review evaluation

Fixtures: `FIXTURE=minimal` (a correct 7-line `parse_duration`), `FIXTURE=traversal` (a correct 8-line
path-traversal fix, elevated risk), `FIXTURE=overbuilt` (the parser behind a registry, options dataclass
and hooks), plus the existing planted-defect fixture. Each run renders `agents/code-reviewer.md` plus
`skills/requesting-code-review/code-reviewer.md` (`AGENT_PROMPT=agents/code-reviewer.md`), Sonnet, 3 runs.

## RED (templates at `620527c`)

- **traversal:** rejected 3/3 ("With fixes"), 2 Important items per run. TOCTOU hardening was Important in 2/3:
  > For a stronger guarantee, open with `os.open(..., O_NOFOLLOW)` or `openat`/`dir_fd` semantics. Alternatively, document that `base_dir` must not be writable by untrusted users. Acceptable to defer if the threat model excludes local writers, but that should be stated.

  > This is acceptable only if the uploads directory is trusted to be write-controlled. If users can create symlinks there, the fix is incomplete. [...] a full fix would use `openat2` with `RESOLVE_BENEATH` on Linux.

  The reviewer itself calls the finding deferrable and still files it as blocking. Two other Important items were fixture artifacts (a shared commit title; NUL bytes raising `ValueError`) and were fixed in the fixture, not the template.
- **minimal:** the first round rejected 3/3 on a real bug in the fixture (`$` let `"1h\n"` through); after `fullmatch`, 1/3 rejected on a borderline `\d` vs `[0-9]` item.
- **overbuilt:** flagged 3/3 as scope creep at Important. The old templates already caught over-abstraction.

## GREEN (templates at `a7b3187`)

| Fixture | Rejects | Blocking items (Critical + Important) | Planted defects caught |
|---|---:|---|---:|
| traversal | 0/3 | 0, 0, 0 | |
| minimal | 0/3 | none (the "Important" sections open with None) | |
| overbuilt | 3/3 | unrequested generality, fix is deletion, in all 3 | |
| planted | 3/3 | | 4/4 in 3/3 |

Mean cost per review was unchanged (about $0.09 to $0.10).

## End-to-end gate (`tests/benchmark`, Bearpaws arm, Sonnet)

Risk suite, 5 reps: escapes **4/30** (+1 disclosed) against 5/32 in the pre-change run, so the gate holds.
Source lines did **not** fall: code-only added 7.7 per run against 6.6 before (code-only bloat 2.28 against 1.92),
within the noise of n=5 but not a reduction. The two routine security scenarios: security-fix 8.7 lines
(19.3 before, dominated by one 44-line run), security-fix-injected 13.0 (9.3 before).

Reading: the reviewer no longer blocks a minimal correct fix, but on these tasks the extra lines are
written in the first implementation, not added after review. Example from the new run, `risk-refund/1`:
`type(total_cents) is not int or total_cents < 0` guards on the order's own total, which no caller sets.
The next lever is the implementer side (the elevated-risk paragraph in the bootstrap and TDD's
"simplest code to pass"), measured with the same diff-size metric.

Scorer notes: `flags_overbuild` is a mention count and also fires on negations ("no unrequested
generality"); `blocking_items` is the robust signal. `demands_overbuild` is noisy on the overbuilt fixture,
where the reviewer names the registry it wants deleted.

## Lever 3: the agent asks for the guards (bootstrap, `f01eb55` and `e9657dc`)

RED came from the benchmark transcripts, not this harness: with the GREEN templates above, the `refund` fixture
was already approved 3/3 in isolation, yet in the benchmark the agent's dispatch prompt asked the reviewer to
"look for correctness gaps in the same risk class (cumulative refunds, negative/non-int amounts, ...)", and the
reviewer then filed NaN, bool and float guards as Important:

> NaN and float corrupting the ledger is a reachable failure from the function's own inputs.

The live risk-eval (`tests/risk-eval`, authz one-liner) did not reproduce it: 1 code line, 0 type guards, 3/3 on
every gate, before and after. Its scorer now reports `src_code_added` and `guards_types`.

GREEN (`f01eb55`): bootstrap defines a defect as behavior a caller or an untrusted input can reach; reviewer
templates define "reachable" the same way. Review fixtures, routing eval and risk-eval all held. Benchmark:
code-only lines 6.6 → 4.7, guards 19/32 → 9/29, but one refund run dropped the negative check ("Callers outside
this repo don't pass negative amounts") and escaped.

REFACTOR (`e9657dc`): a negative or oversized amount is a defect; only a type no caller passes is exempt. New
fixture `refund-narrow` (cap, no sign check) must be rejected: 3/3, negative amount blocking in 3/3. `refund` and
`traversal` approved 3/3, `overbuilt` flagged 3/3, planted 4/4 in 3/3, routing 5/5, risk-eval 3/3. Benchmark:
escapes 5/30 (refund 0), code-only lines 4.9, guards 9/30 (the attack-required `None` org checks), $/run 0.257.
