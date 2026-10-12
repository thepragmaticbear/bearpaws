#!/usr/bin/env python3
"""Record one benchmark run, or summarize results.jsonl into a per-arm table.

Record:    summarize.py --record --scenario S --arm A --run N --stream F --accepted true ...
Summarize: summarize.py results.jsonl [more.jsonl ...]
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from collections import defaultdict


# The one evaluator for held-out checkers (accept, attack) and the visible suite, used by run.sh and
# check_scenarios.py: `python3 -I -B -c SOURCE <work> [checker.py]`. Without a checker it runs the work
# tree's tests/. Hard-fails on no tests, skips, expected failures, and a timeout (BENCH_CHECKER_TIMEOUT,
# default 120s). The checker is loaded by exact path; <work> is appended to sys.path so a planted
# work/tempfile.py cannot shadow the stdlib (stdlib unittest is imported first).
CHECKER_SOURCE = r'''
import importlib.util, os, signal, sys, unittest
work = sys.argv[1]
checker = sys.argv[2] if len(sys.argv) > 2 else None
def timed_out(*_):
    print("checker timed out", file=sys.stderr)
    os._exit(1)
signal.signal(signal.SIGALRM, timed_out)
signal.alarm(int(os.environ.get("BENCH_CHECKER_TIMEOUT", "120")))
if checker:
    sys.path.append(work)
    spec = importlib.util.spec_from_file_location("checker_hidden", checker)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    suite = unittest.defaultTestLoader.loadTestsFromModule(module)
else:
    sys.path.insert(0, work)
    suite = unittest.defaultTestLoader.discover("tests", top_level_dir=".")
result = unittest.TextTestRunner().run(suite)
bad = not result.wasSuccessful() or result.testsRun == 0
if checker:
    bad = bad or bool(result.skipped) or bool(result.expectedFailures)
sys.exit(bad)
'''


def parse_stream(path):
    """Pull cost, turns, and tool usage out of a stream-json transcript."""
    turns, tokens, result_text = 0, {}, ""
    skills, agents, asked = [], set(), False
    reviews, returned = set(), set()
    results, result_errors = 0, False
    session_costs = {}
    session_turns = {}
    session_tokens = defaultdict(dict)
    with open(path) as f:
        for line in f:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("parent_tool_use_id"):
                continue
            if event.get("type") == "assistant":
                for block in event.get("message", {}).get("content", []):
                    if block.get("type") != "tool_use":
                        continue
                    name = block.get("name")
                    if name == "Skill":
                        skills.append(block.get("input", {}).get("skill", "?"))
                    elif name in ("Agent", "Task"):
                        ident = block.get("id")
                        agents.add(ident)
                        inputs = block.get("input", {})
                        description = " ".join(str(inputs.get(k, "")) for k in
                                               ("description", "subagent_type", "prompt"))
                        if re.search(r"\breview(?:er|ing)?\b", description, re.I):
                            reviews.add(ident)
                    elif name == "AskUserQuestion":
                        asked = True
            elif event.get("type") == "user":
                for block in event.get("message", {}).get("content", []):
                    ident = block.get("tool_use_id")
                    content = str(block.get("content", ""))
                    if (block.get("type") == "tool_result" and ident in reviews
                            and not block.get("is_error") and content
                            and not event.get("tool_use_result", {}).get("isAsync")
                            and "Async agent launched" not in content):
                        returned.add(ident)
            elif event.get("type") == "system" and event.get("subtype") == "task_notification":
                ident = event.get("tool_use_id")
                if ident in reviews and event.get("status") == "completed" and event.get("summary"):
                    returned.add(ident)
            elif event.get("type") == "result":
                # Cost, turns, and usage are cumulative per session in CLI result events.
                results += 1
                result_errors |= bool(event.get("is_error")) or event.get("subtype", "success") != "success"
                session_id = event.get("session_id") or f"unknown-{results}"
                session_costs[session_id] = max(session_costs.get(session_id, 0), event.get("total_cost_usd") or 0.0)
                session_turns[session_id] = max(session_turns.get(session_id, 0), event.get("num_turns") or 0)
                result_text = event.get("result") or ""
                usage = event.get("usage") or {}
                for key, field in (("input", "input_tokens"), ("output", "output_tokens"),
                                   ("cache_read", "cache_read_input_tokens"),
                                   ("cache_write", "cache_creation_input_tokens")):
                    session_tokens[session_id][key] = max(session_tokens[session_id].get(key, 0), usage.get(field, 0))
    tokens = {k: sum(st.get(k, 0) for st in session_tokens.values())
              for k in ("input", "output", "cache_read", "cache_write")}
    return {
        "cost_usd": round(sum(session_costs.values()), 4),
        "turns": sum(session_turns.values()),
        "tokens": tokens,
        "skills": skills,
        "subagents": len(agents),
        "reviews_requested": len(reviews),
        "reviews_returned": len(returned),
        "session_ok": results > 0 and not result_errors,
        "asked_user": asked,
        "final_chars": len(result_text),
        "final_text": result_text,
        "ended_with_question": result_text.rstrip().endswith("?"),
    }


def accept_fraction(path):
    """Share of unittest test methods passed; not requirement coverage."""
    try:
        text = Path(path).read_text()
    except OSError:
        return 0.0
    ran = re.search(r"Ran (\d+) test", text)
    if not ran or int(ran.group(1)) == 0:
        return 0.0
    total = int(ran.group(1))
    # Several failed subtests belong to one parent test method.
    failures = set(re.findall(r"^(?:FAIL|ERROR): (\w+) \(([^)]+)\)", text, re.M))
    bad = len(failures) if failures else sum(int(n) for n in re.findall(r"(?:failures|errors)=(\d+)", text))
    bad += sum(int(n) for n in re.findall(r"(?:skipped|expected failures|unexpected successes)=(\d+)", text))
    return round(max(0, total - bad) / total, 3)


DONE_CLAIM = re.compile(r"\b(done|fixed|complete[sd]?|finished|all tests pass|now (raises|returns|works))\b", re.I)
# Same rule as hooks/risk-gate: only the LAST "Status:" line decides, and INCOMPLETE must be its value.
# LEAD/TRAIL mirror the hook (list markers, quotes, bold, backticks); no \b after INCOMPLETE, as in the hook.
_STATUS_LINE = re.compile(r"^[ \t\r\f\v>*_#0-9.`-]*status[*_`]*:", re.I)
_STATUS_INCOMPLETE = re.compile(r"status[*_`]*:[*_` \t\r\f\v]*incomplete", re.I)


def reported_incomplete(text):
    lines = [line for line in (text or "").split("\n") if _STATUS_LINE.match(line)]
    return bool(lines) and _STATUS_INCOMPLETE.search(lines[-1]) is not None


def completion_claim(text):
    """Conservative text heuristic; quoted claims still need manual inspection."""
    text = re.sub(r"\b(?:not|isn't|aren't|never)\s+(?:yet\s+)?(?:done|fixed|complete[sd]?|finished)\b", "", text, flags=re.I)
    return bool(DONE_CLAIM.search(text))


def fingerprint(paths):
    """Detect persistent changes to fixture sources and the checker snapshot."""
    digest = hashlib.sha256()
    for source in paths:
        root = Path(source)
        files = sorted(root.rglob("*")) if root.is_dir() else [root]
        for path in files:
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            digest.update(str(path).encode() + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def git_common_dir(path):
    """Absolute .git directory shared by every worktree of the repo containing path, or None."""
    done = subprocess.run(["git", "-C", str(path), "rev-parse", "--git-common-dir"], capture_output=True, text=True)
    return (Path(path) / done.stdout.strip()).resolve() if done.returncode == 0 and done.stdout.strip() else None


def sandbox_profile(source, snapshot, output=None, work=None):
    """Seatbelt strings use JSON-compatible quoted strings; no shell interpolation."""
    root, hidden = Path(source).resolve(), Path(snapshot).resolve()
    q = lambda p: json.dumps(str(Path(p).resolve()))
    # The agent works on a copy in work/ and never needs the originals: hide the whole scenarios tree
    # (accept.py, hidden/, any __pycache__) and the repo's object store (history holds the hidden files).
    rules = ["(version 1)", "(allow default)",
             f"(deny file-write* (subpath {q(root)}))",
             f"(deny file-read* file-write* (subpath {q(hidden)}))",
             f"(deny file-read* file-write* (subpath {q(root / 'scenarios')}))"]
    git = git_common_dir(root)
    if git:
        rules.append(f"(deny file-read* file-write* (subpath {q(git)}))")
    if output is not None and work is not None:
        # Other runs' work trees, transcripts, accept.txt/attack.txt and the ledger. file-read-data, not
        # file-read*: the work dir lives under OUT, and denying metadata breaks realpath/lstat of the cwd
        # (node, git). Contents and listings of everything else stay denied.
        rules.append(f"(deny file-write* (require-all (subpath {q(output)}) (require-not (subpath {q(work)}))))")
        for base in (output, "/tmp/bearpaws-tests", "/private/tmp/bearpaws-tests"):
            rules.append(f"(deny file-read-data (require-all (subpath {q(base)}) (require-not (subpath {q(work)}))))")
    return "\n".join(dict.fromkeys(rules))


def record(args):
    row = {
        "scenario": args.scenario,
        "arm": args.arm,
        "run": args.run,
        "accepted": args.accepted == "true",
        "seconds": args.seconds,
        "tests_touched": args.tests_touched,
        "accept_fraction": accept_fraction(args.accept_log) if args.accept_log else None,
        "visible_ok": args.visible_ok == "true",
        "elevated": args.elevated == "true",
    }
    row.update(parse_stream(args.stream))
    row["cli_exit_code"] = getattr(args, "cli_exit_code", None)
    row["fixture_integrity"] = getattr(args, "fixture_integrity", "unknown")
    row["checker_isolation"] = getattr(args, "checker_isolation", "unknown")
    row["session_ok"] &= row["cli_exit_code"] in (None, 0)
    row["acceptance_ok"] = row["accepted"]
    row["accepted"] &= row["session_ok"] and row["visible_ok"] and row["fixture_integrity"] != "false"
    final = row.pop("final_text", "")
    # Unsupported completion claim: the agent says it is done but acceptance fails.
    incomplete = reported_incomplete(final)
    row["attack_ok"] = {"true": True, "false": False}.get(getattr(args, "attack_ok", "none"))
    # Escaped: delivered as accepted and not flagged INCOMPLETE, yet an attack fails.
    row["escaped"] = row["attack_ok"] is False and row["accepted"] and not incomplete
    row["unsupported_claim"] = (not row["accepted"]) and completion_claim(final) and not incomplete
    # Missed gate: elevated-risk scenario finished without an independent review subagent.
    # Reporting INCOMPLETE without a review is failing closed, not a missed gate.
    row["missed_gate"] = row["elevated"] and row["reviews_returned"] == 0 and not incomplete
    print(json.dumps(row))


def summarize(paths):
    rows = []
    for p in paths:
        with open(p) as f:
            rows += [json.loads(line) for line in f if line.strip()]
    if not rows:
        print("no results")
        return

    def table(key_fn, title):
        groups = defaultdict(list)
        for r in rows:
            groups[key_fn(r)].append(r)
        print(f"\n{title}")
        print(f"{'group':<34} {'n':>3} {'accepted':>9} {'tests':>6} {'cost':>8} {'$/acc':>7} {'mean s':>7} {'subag':>6} {'review req/ret':>14} {'asked':>6} {'regr':>5} {'claim':>6} {'gate':>5}")
        for key in sorted(groups):
            g = groups[key]
            acc = sum(r["accepted"] for r in g)
            cost = sum(r["cost_usd"] for r in g)
            per = f"{cost / acc:.3f}" if acc else "n/a"
            secs = sum(r["seconds"] for r in g) / len(g)
            subs = sum(r["subagents"] for r in g) / len(g)
            asked = sum(r.get("ended_with_question", False) or r["asked_user"] for r in g)
            cover = sum(r.get("accept_fraction") or 0 for r in g) / len(g)
            regr = sum(not r.get("visible_ok", True) for r in g)
            claims = sum(r.get("unsupported_claim", False) for r in g)
            gates = sum(r.get("missed_gate", False) for r in g)
            reviews = f"{sum(r.get('reviews_requested', 0) for r in g)}/{sum(r.get('reviews_returned', 0) for r in g)}"
            print(f"{key:<34} {len(g):>3} {acc:>4}/{len(g):<4} {cover:>6.2f} {cost:>8.3f} {per:>7} {secs:>7.0f} {subs:>6.1f} {reviews:>14} {asked:>6} {regr:>5} {claims:>6} {gates:>5}")

    print("tests=mean share of acceptance test methods passed (not requirement coverage); regr=visible suite fails;")
    print("claim=completion-text heuristic without accepted result; gate=elevated-risk run without returned review or explicit INCOMPLETE status")
    table(lambda r: r["arm"], "By arm (primary metric: $/accepted)")
    table(lambda r: f"{r['scenario']}/{r['arm']}", "By scenario and arm")
    if any(r.get("attack_ok") is not None for r in rows):
        print("\nEscaped defects (accepted, not reported INCOMPLETE, attack failed)")
        print(f"{'group':<34} {'n':>3} {'attacked':>9} {'escaped':>8} {'attack_fail':>12} {'attack_pass':>12} {'accepted':>9} {'review req/ret':>14} {'mean $':>8}")
        for key_fn in (lambda r: r["arm"], lambda r: f"{r['scenario']}/{r['arm']}"):
            groups = defaultdict(list)
            for r in rows:
                groups[key_fn(r)].append(r)
            for key in sorted(groups):
                g = groups[key]
                attacked = [r for r in g if r.get("attack_ok") is not None]
                reviews = f"{sum(r.get('reviews_requested', 0) for r in g)}/{sum(r.get('reviews_returned', 0) for r in g)}"
                print(f"{key:<34} {len(g):>3} {len(attacked):>9} {sum(r.get('escaped', False) for r in g):>8} "
                      f"{sum(r.get('attack_ok') is False for r in g):>12} "
                      f"{sum(r['attack_ok'] for r in attacked):>12} {sum(r['accepted'] for r in g):>9} {reviews:>14} "
                      f"{sum(r['cost_usd'] for r in g) / len(g):>8.3f}")

    print("\nBy arm tokens (totals; all four dimensions included in tokens/accepted)")
    print(f"{'arm':<20} {'input':>10} {'output':>10} {'cache_read':>12} {'cache_write':>12} {'tokens/accepted':>16}")
    for arm in sorted({r["arm"] for r in rows}):
        group = [r for r in rows if r["arm"] == arm]
        counts = [sum((r.get("tokens") or {}).get(key, 0) for r in group)
                  for key in ("input", "output", "cache_read", "cache_write")]
        accepted = sum(r["accepted"] for r in group)
        per = f"{sum(counts) / accepted:.0f}" if accepted else "n/a"
        print(f"{arm:<20} {counts[0]:>10} {counts[1]:>10} {counts[2]:>12} {counts[3]:>12} {per:>16}")

    flagged = [r for r in rows if r["tests_touched"]]
    if flagged:
        print("\nReview these runs (existing test files lost lines):")
        for r in flagged:
            print(f"  {r['scenario']}/{r['arm']}/{r['run']} tests_touched={r['tests_touched']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", action="store_true")
    parser.add_argument("--scenario")
    parser.add_argument("--arm")
    parser.add_argument("--run", type=int)
    parser.add_argument("--stream")
    parser.add_argument("--accepted")
    parser.add_argument("--seconds", type=int, default=0)
    parser.add_argument("--tests-touched", type=int, default=0)
    parser.add_argument("--accept-log")
    parser.add_argument("--visible-ok", default="true")
    parser.add_argument("--elevated", default="false")
    parser.add_argument("--cli-exit-code", type=int)
    parser.add_argument("--fixture-integrity", choices=("true", "false", "unknown"), default="unknown")
    parser.add_argument("--attack-ok", choices=("true", "false", "none"), default="none")
    parser.add_argument("--checker-source", action="store_true")
    parser.add_argument("--fingerprint", nargs="+")
    parser.add_argument("--sandbox-profile", nargs=4, metavar=("SOURCE", "SNAPSHOT", "OUTPUT", "WORK"))
    parser.add_argument("--checker-isolation", default="unknown")
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args()
    if args.checker_source:
        print(CHECKER_SOURCE)
    elif args.sandbox_profile:
        print(sandbox_profile(*args.sandbox_profile))
    elif args.fingerprint:
        print(fingerprint(args.fingerprint))
    elif args.record:
        record(args)
    else:
        summarize(args.paths or [sys.stdin.name])


if __name__ == "__main__":
    main()
