#!/usr/bin/env python3
"""Record one benchmark run, or summarize results.jsonl into a per-arm table.

Record:    summarize.py --record --scenario S --arm A --run N --stream F --accepted true ...
Summarize: summarize.py results.jsonl [more.jsonl ...]
Rescore:   summarize.py --rescore results.jsonl --runs-dir OUT/runs   (adds diff-size fields from preserved work trees)
Supervise: summarize.py --supervise SECONDS -- argv...   (exit 124 on timeout; kills the process tree)
"""

import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
from collections import Counter, defaultdict


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


# Diff size: source lines the agent changed against the pristine scenario repo, so over-building shows
# up next to acceptance. Tests, docs, caches and VCS metadata are excluded. Where a scenario ships
# hidden/reference/ (a careful fix), its added lines are the denominator for the bloat ratio.
SRC_SKIP_DIRS = {"tests", "test", "__tests__", "docs", "__pycache__", ".git", ".pytest_cache", ".claude", "node_modules"}
SRC_SKIP_SUFFIXES = (".md", ".pyc", ".jsonl", ".txt")


def source_files(root):
    """{relative path: Path} of the source files under root."""
    root = Path(root)
    files = {}
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if path.is_file() and not set(rel.parts[:-1]) & SRC_SKIP_DIRS and rel.suffix not in SRC_SKIP_SUFFIXES:
            files[str(rel)] = path
    return files


def _lines(path):
    try:
        return path.read_text().splitlines()
    except (OSError, UnicodeDecodeError):
        return None  # binary: not counted


def tree_diff(base, other, overlay=False):
    """Source lines added and removed, and source files added, going from base to other.

    overlay=True treats other as a partial overlay: files it lacks are unchanged, not deleted.
    """
    base_files, other_files = source_files(base), source_files(other)
    added = removed = files_added = 0
    for rel in sorted(set(base_files) | set(other_files)):
        if overlay and rel not in other_files:
            continue
        a = _lines(base_files[rel]) if rel in base_files else []
        b = _lines(other_files[rel]) if rel in other_files else []
        if a is None or b is None:
            continue
        files_added += rel not in base_files
        for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
            if op != "equal":
                removed += i2 - i1
                added += j2 - j1
    return {"src_added": added, "src_removed": removed, "src_files_added": files_added}


def reference_size(scenario_dir):
    """Source lines the scenario's reference fix adds, or None without hidden/reference/."""
    ref = Path(scenario_dir) / "hidden" / "reference"
    return tree_diff(Path(scenario_dir) / "repo", ref, overlay=True)["src_added"] if ref.is_dir() else None


def diff_fields(work, scenario_dir):
    fields = dict.fromkeys(("src_added", "src_removed", "src_files_added", "ref_src_added"))
    # A work tree with no source files was cleaned after the run (the 2026-10-12 run dirs): unmeasured, not "deleted everything".
    if work and scenario_dir and (Path(scenario_dir) / "repo").is_dir() and Path(work).is_dir() and source_files(work):
        fields.update(tree_diff(Path(scenario_dir) / "repo", work))
        fields["ref_src_added"] = reference_size(scenario_dir)
    return fields


def rescore(results, runs_dir, scenarios_dir=None):
    """Re-emit results.jsonl rows with diff fields read from <runs_dir>/<scenario>/<arm>/<run>/work."""
    scenarios_dir = Path(scenarios_dir or Path(__file__).parent / "scenarios")
    with open(results) as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            work = Path(runs_dir) / row["scenario"] / row["arm"] / str(row["run"]) / "work"
            row.update(diff_fields(work, scenarios_dir / row["scenario"]))
            print(json.dumps(row))


def process_table():
    """{pid: (ppid, lstart)} from `ps -A -o pid=,ppid=,lstart=` (BSD and GNU, LC_ALL=C). Empty if ps fails."""
    try:
        out = subprocess.run(["ps", "-A", "-o", "pid=,ppid=,lstart="], capture_output=True, text=True,
                             env=dict(os.environ, LC_ALL="C")).stdout
    except OSError:
        return {}
    table = {}
    for line in out.splitlines():
        parts = line.split(None, 2)
        if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
            table[int(parts[0])] = (int(parts[1]), " ".join(parts[2].split()))
    return table


def track_descendants(tracked, table):
    """Add every descendant of a still-verified tracked pid to tracked {pid: lstart}; True if any are new."""
    kids = defaultdict(list)
    for pid, (ppid, _) in table.items():
        kids[ppid].append(pid)
    todo = [pid for pid, lstart in tracked.items() if pid in table and table[pid][1] == lstart]
    new = False
    while todo:
        for pid in kids.get(todo.pop(), []):
            if tracked.get(pid) != table[pid][1]:
                tracked[pid] = table[pid][1]
                new = True
            todo.append(pid)
    return new


def signal_verified(tracked, sig, fallback=()):
    """Send sig to tracked pids whose current lstart still matches (a mismatch is pid reuse: skipped).

    If ps fails (empty table), signal `fallback` pids instead: ones verified earlier in this kill.
    Returns the pids signalled.
    """
    table = process_table()
    if table:
        pids = [pid for pid, lstart in tracked.items() if pid in table and table[pid][1] == lstart]
    else:
        pids = list(fallback)
    for pid in pids:
        try:
            os.kill(pid, sig)
        except (ProcessLookupError, PermissionError):
            pass
    return pids


def kill_verified(tracked):
    """SIGSTOP the tracked tree (up to 3 rounds), then SIGKILL it.

    If ps fails on the final read, kill the pids already stopped. A process that detaches
    between two 0.5 s polls is never tracked and escapes.
    """
    stopped = set()
    for _ in range(3):
        grew = track_descendants(tracked, process_table())
        stopped.update(signal_verified(tracked, signal.SIGSTOP))
        if not grew:
            break
    signal_verified(tracked, signal.SIGKILL, fallback=stopped)


POLL = 0.5


def supervise(seconds, argv):
    """Run argv in its own process group with a wall-clock limit; exit 124 on timeout.

    stdout/stderr are inherited, so run.sh's pipes into stream.jsonl/stderr.txt are unchanged. The
    tree is killed on every exit path (timeout, normal exit, SIGINT/SIGTERM/SIGHUP), so
    agent-spawned background loops cannot outlive the session or hold the pipes open. Descendants
    (including setsid ones) are recorded with their start time while the child runs, so they can
    still be found and verified after the child exits and they are reparented to init.
    """
    try:
        child = subprocess.Popen(argv, start_new_session=True)
    except OSError as e:
        print(f"supervise: cannot run {argv[0]}: {e}", file=sys.stderr)
        return 127
    tracked = {}
    entry = process_table().get(child.pid)
    if entry:
        tracked[child.pid] = entry[1]

    def on_signal(signum, _frame):
        raise SystemExit(128 + signum)
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, on_signal)
    try:
        deadline = time.monotonic() + seconds
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                code = child.wait(timeout=min(POLL, remaining))
                return code if code >= 0 else 128 - code
            except subprocess.TimeoutExpired:
                track_descendants(tracked, process_table())
        # TERM goes to the group only: TERMing a tracked setsid spawner would orphan children it forks
        # before dying, untracked. Those processes are frozen and killed in the finally instead.
        try:
            os.killpg(child.pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):  # macOS: EPERM when the group holds a zombie
            pass
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        return 124
    finally:
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            signal.signal(sig, signal.SIG_IGN)
        kill_verified(tracked)
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        child.poll()


SUPERVISE_USAGE = "usage: summarize.py --supervise SECONDS -- COMMAND [ARG...]   (SECONDS > 0)"


def supervise_main(args):
    try:
        seconds = float(args[0])
        if not (0 < seconds < float("inf")) or args[1] != "--" or len(args) < 3:
            raise ValueError
    except (ValueError, IndexError):
        print(SUPERVISE_USAGE, file=sys.stderr)
        return 2
    return supervise(seconds, args[2:])


def parse_stream(path):
    """Pull cost, turns, and tool usage out of a stream-json transcript."""
    turns, tokens, result_text, result_texts = 0, {}, "", []
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
                result_texts.append(result_text)
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
        "all_text": "\n".join(result_texts),
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
# Same rule as hooks/risk-gate: only the last "Status:" line decides, and INCOMPLETE must be its value.
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
    # Hide the scenarios tree and the git object store; the agent only needs its copy in work/.
    rules = ["(version 1)", "(allow default)",
             f"(deny file-write* (subpath {q(root)}))",
             f"(deny file-read* file-write* (subpath {q(hidden)}))",
             f"(deny file-read* file-write* (subpath {q(root / 'scenarios')}))"]
    git = git_common_dir(root)
    if git:
        rules.append(f"(deny file-read* file-write* (subpath {q(git)}))")
    if output is not None and work is not None:
        # Hide other runs. file-read-data, not file-read*: denying metadata breaks realpath of the work dir.
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
    row.update(diff_fields(getattr(args, "work", None), getattr(args, "scenario_dir", None)))
    row["fixture_integrity"] = getattr(args, "fixture_integrity", "unknown")
    row["checker_isolation"] = getattr(args, "checker_isolation", "unknown")
    row["timed_out"] = getattr(args, "timed_out", "false") == "true"
    row["session_ok"] &= row["cli_exit_code"] in (None, 0) and not row["timed_out"]
    row["acceptance_ok"] = row["accepted"]
    row["accepted"] &= row["session_ok"] and row["visible_ok"] and row["fixture_integrity"] != "false"
    final = row.pop("final_text", "")
    # The last Status: line across every reply decides (a later reply may carry no Status line).
    incomplete = row["reported_incomplete"] = reported_incomplete(row.pop("all_text", final))
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
        print(f"{'group':<34} {'n':>3} {'accepted':>9} {'tests':>6} {'cost':>8} {'$/acc':>7} {'mean s':>7} {'subag':>6} {'review req/ret':>14} {'asked':>6} {'regr':>5} {'claim':>6} {'gate':>5} {'timeouts':>8}")
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
            timeouts = sum(r.get("timed_out", False) for r in g)
            reviews = f"{sum(r.get('reviews_requested', 0) for r in g)}/{sum(r.get('reviews_returned', 0) for r in g)}"
            print(f"{key:<34} {len(g):>3} {acc:>4}/{len(g):<4} {cover:>6.2f} {cost:>8.3f} {per:>7} {secs:>7.0f} {subs:>6.1f} {reviews:>14} {asked:>6} {regr:>5} {claims:>6} {gates:>5} {timeouts:>8}")

    print("tests=mean share of acceptance test methods passed (not requirement coverage); regr=visible suite fails;")
    print("claim=completion-text heuristic without accepted result; gate=elevated-risk run without returned review or explicit INCOMPLETE status")
    table(lambda r: r["arm"], "By arm (primary metric: $/accepted)")
    table(lambda r: f"{r['scenario']}/{r['arm']}", "By scenario and arm")
    if any(r.get("attack_ok") is not None for r in rows):
        print("\nEscaped defects (accepted, not reported INCOMPLETE, attack failed)")
        print("disclosed=accepted, attack failed, reported INCOMPLETE; incomplete=all runs reporting INCOMPLETE")
        print(f"{'group':<34} {'n':>3} {'attacked':>9} {'escaped':>8} {'disclosed':>10} {'incomplete':>11} {'attack_fail':>12} {'attack_pass':>12} {'accepted':>9} {'review req/ret':>14} {'mean $':>8}")
        for key_fn in (lambda r: r["arm"], lambda r: f"{r['scenario']}/{r['arm']}"):
            groups = defaultdict(list)
            for r in rows:
                groups[key_fn(r)].append(r)
            for key in sorted(groups):
                g = groups[key]
                attacked = [r for r in g if r.get("attack_ok") is not None]
                reviews = f"{sum(r.get('reviews_requested', 0) for r in g)}/{sum(r.get('reviews_returned', 0) for r in g)}"
                print(f"{key:<34} {len(g):>3} {len(attacked):>9} {sum(r.get('escaped', False) for r in g):>8} "
                      f"{sum(r['accepted'] and r.get('attack_ok') is False and r.get('reported_incomplete', False) for r in g):>10} "
                      f"{sum(r.get('reported_incomplete', False) for r in g):>11} "
                      f"{sum(r.get('attack_ok') is False for r in g):>12} "
                      f"{sum(r['attack_ok'] for r in attacked):>12} {sum(r['accepted'] for r in g):>9} {reviews:>14} "
                      f"{sum(r['cost_usd'] for r in g) / len(g):>8.3f}")

    measured = [r for r in rows if r.get("src_added") is not None]
    if measured:
        print("\nDiff size (source lines changed vs the scenario repo; tests, docs and caches excluded)")
        print("bloat=mean over runs of added / the reference fix's added lines; only scenarios with hidden/reference")
        print(f"{'group':<34} {'n':>3} {'added':>7} {'removed':>8} {'new files':>10} {'bloat':>6}")
        for key_fn in (lambda r: r["arm"], lambda r: f"{r['scenario']}/{r['arm']}"):
            groups = defaultdict(list)
            for r in measured:
                groups[key_fn(r)].append(r)
            for key in sorted(groups):
                g = groups[key]
                ratios = [r["src_added"] / r["ref_src_added"] for r in g if r.get("ref_src_added")]
                bloat = f"{sum(ratios) / len(ratios):.2f}" if ratios else "n/a"
                print(f"{key:<34} {len(g):>3} {sum(r['src_added'] for r in g) / len(g):>7.1f} "
                      f"{sum(r['src_removed'] for r in g) / len(g):>8.1f} "
                      f"{sum(r['src_files_added'] for r in g) / len(g):>10.1f} {bloat:>6}")

    print("\nBy arm tokens (totals; all four dimensions included in tokens/accepted)")
    print(f"{'arm':<20} {'input':>10} {'output':>10} {'cache_read':>12} {'cache_write':>12} {'tokens/accepted':>16}")
    for arm in sorted({r["arm"] for r in rows}):
        group = [r for r in rows if r["arm"] == arm]
        counts = [sum((r.get("tokens") or {}).get(key, 0) for r in group)
                  for key in ("input", "output", "cache_read", "cache_write")]
        accepted = sum(r["accepted"] for r in group)
        per = f"{sum(counts) / accepted:.0f}" if accepted else "n/a"
        print(f"{arm:<20} {counts[0]:>10} {counts[1]:>10} {counts[2]:>12} {counts[3]:>12} {per:>16}")

    if any(r.get("skills") for r in rows):
        print("\nSkills by arm (runs that invoked each skill / n)")
        for arm in sorted({r["arm"] for r in rows}):
            group = [r for r in rows if r["arm"] == arm]
            used = Counter(s for r in group for s in set(r.get("skills") or []))
            print(f"  {arm}: " + ", ".join(f"{s} {used[s]}/{len(group)}" for s in sorted(used)))

    flagged = [r for r in rows if r["tests_touched"]]
    if flagged:
        print("\nReview these runs (existing test files lost lines):")
        for r in flagged:
            print(f"  {r['scenario']}/{r['arm']}/{r['run']} tests_touched={r['tests_touched']}")


def main():
    if sys.argv[1:2] == ["--supervise"]:  # --supervise SECONDS -- argv...
        sys.exit(supervise_main(sys.argv[2:]))
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
    parser.add_argument("--timed-out", choices=("true", "false"), default="false")
    parser.add_argument("--checker-source", action="store_true")
    parser.add_argument("--fingerprint", nargs="+")
    parser.add_argument("--sandbox-profile", nargs=4, metavar=("SOURCE", "SNAPSHOT", "OUTPUT", "WORK"))
    parser.add_argument("--checker-isolation", default="unknown")
    parser.add_argument("--work", help="the run's work tree, for diff size")
    parser.add_argument("--scenario-dir", help="scenarios/<name>, for diff size and the reference fix")
    parser.add_argument("--rescore", metavar="RESULTS", help="re-emit rows with diff fields from --runs-dir")
    parser.add_argument("--runs-dir")
    parser.add_argument("--scenarios-dir")
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
    elif args.rescore:
        rescore(args.rescore, args.runs_dir, args.scenarios_dir)
    else:
        summarize(args.paths or [sys.stdin.name])


if __name__ == "__main__":
    main()
