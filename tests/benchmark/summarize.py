#!/usr/bin/env python3
"""Record one benchmark run, or summarize results.jsonl into a per-arm table.

Record:    summarize.py --record --scenario S --arm A --run N --stream F --accepted true ...
Summarize: summarize.py results.jsonl [more.jsonl ...]
"""

import argparse
import json
import sys
from collections import defaultdict


def parse_stream(path):
    """Pull cost, turns, and tool usage out of a stream-json transcript."""
    cost, turns, tokens, result_text = 0.0, 0, {}, ""
    skills, agents, asked = [], 0, False
    with open(path) as f:
        for line in f:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "assistant":
                for block in event.get("message", {}).get("content", []):
                    if block.get("type") != "tool_use":
                        continue
                    name = block.get("name")
                    if name == "Skill":
                        skills.append(block.get("input", {}).get("skill", "?"))
                    elif name in ("Agent", "Task"):
                        agents += 1
                    elif name == "AskUserQuestion":
                        asked = True
            elif event.get("type") == "result":
                cost = event.get("total_cost_usd") or 0.0
                turns = event.get("num_turns") or 0
                result_text = event.get("result") or ""
                usage = event.get("usage") or {}
                tokens = {
                    "input": usage.get("input_tokens", 0),
                    "output": usage.get("output_tokens", 0),
                    "cache_read": usage.get("cache_read_input_tokens", 0),
                    "cache_write": usage.get("cache_creation_input_tokens", 0),
                }
    return {
        "cost_usd": round(cost, 4),
        "turns": turns,
        "tokens": tokens,
        "skills": skills,
        "subagents": agents,
        "asked_user": asked,
        "final_chars": len(result_text),
        "ended_with_question": result_text.rstrip().endswith("?"),
    }


def record(args):
    row = {
        "scenario": args.scenario,
        "arm": args.arm,
        "run": args.run,
        "accepted": args.accepted == "true",
        "seconds": args.seconds,
        "tests_touched": args.tests_touched,
    }
    row.update(parse_stream(args.stream))
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
        print(f"{'group':<32} {'n':>3} {'accepted':>9} {'cost':>9} {'$/accepted':>11} {'mean s':>7} {'subagents':>9} {'asked':>6}")
        for key in sorted(groups):
            g = groups[key]
            acc = sum(r["accepted"] for r in g)
            cost = sum(r["cost_usd"] for r in g)
            per = f"{cost / acc:.3f}" if acc else "n/a"
            secs = sum(r["seconds"] for r in g) / len(g)
            subs = sum(r["subagents"] for r in g) / len(g)
            asked = sum(r.get("ended_with_question", False) or r["asked_user"] for r in g)
            print(f"{key:<32} {len(g):>3} {acc:>4}/{len(g):<4} {cost:>9.3f} {per:>11} {secs:>7.0f} {subs:>9.1f} {asked:>6}")

    table(lambda r: r["arm"], "By arm (primary metric: $/accepted)")
    table(lambda r: f"{r['scenario']}/{r['arm']}", "By scenario and arm")

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
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args()
    if args.record:
        record(args)
    else:
        summarize(args.paths or [sys.stdin.name])


if __name__ == "__main__":
    main()
