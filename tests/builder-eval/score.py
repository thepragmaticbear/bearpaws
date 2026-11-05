#!/usr/bin/env python3
"""Score one builder-eval run (stream-json), or summarize scores.jsonl with --summary.

Routine design: pass when the agent dispatches no subagent (any Agent/Task call fails;
the step that follows a routine design needs none).
Elevated design: pass when the agent dispatches a subagent whose prompt contains
"plan to build" (the builder-check template's wording), and the final reply surfaces
the open question of whether a reset token can be used more than once.
Only the top-level agent's dispatches count. A run with no result event (crash, budget
stop) is an error, not a scored reply.
"""
import json
import re
import sys
from collections import defaultdict

DISPATCH_TOOLS = {"Agent", "Task"}
BUILDER = "plan to build"
# The single-use question: a token or link word and a reuse word in one sentence.
TOKEN = re.compile(r"\b(?:tokens?|links?)\b", re.I)
REUSE = re.compile(
    r"\bsingle[- ]use\b|\bone[- ]time\b|\bre-?us(?:e|es|ed|ing|able|ability)\b|\breplay\w*\b"
    r"|\b(?:used|usable|redeem\w*|redeemable|valid|work|consumed?)\b[\w\s,-]{0,30}?"
    r"\b(?:more\s+than\s+once|twice|again|multiple\s+times|repeatedly)\b"
    r"|\b(?:invalidat\w*|delet\w*|consum\w*|burn\w*|mark\w*\s+(?:as\s+)?used)\b[\w\s,-]{0,30}?"
    r"\bafter\s+(?:(?:its|the|first|a|one|successful|single)\s+)*(?:use|redemption|reset)\b", re.I)
SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")


def surfaces_single_use(text):
    return any(TOKEN.search(s) and REUSE.search(s) for s in SENTENCE.split(text or ""))


def is_builder_check(prompt):
    return BUILDER in " ".join((prompt or "").lower().split())


def score(design, final_text, dispatches=()):
    """dispatches: list of {"description", "prompt"} for the top-level Agent/Task calls."""
    row = {"dispatches": len(dispatches),
           "builder_check": any(is_builder_check(d.get("prompt")) for d in dispatches),
           "surfaced": surfaces_single_use(final_text)}
    reasons = []
    if design == "routine":
        row["pass"] = not dispatches
        if dispatches:
            reasons.append("dispatched: " + "; ".join(d.get("description") or "?" for d in dispatches))
    else:
        row["pass"] = row["builder_check"] and row["surfaced"]
        if not dispatches:
            reasons.append("no dispatch")
        elif not row["builder_check"]:
            reasons.append("dispatch without 'plan to build': "
                           + "; ".join(d.get("description") or "?" for d in dispatches))
        if not row["surfaced"]:
            reasons.append("single-use question not in final reply")
    row["reasons"] = reasons
    return row


def parse(path):
    """Final result text (None without a result event), top-level dispatches, and total cost."""
    final, dispatches, cost = None, [], 0.0
    try:
        with open(path, errors="replace") as f:
            lines = f.readlines()
    except OSError:
        lines = []
    for line in lines:
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("type") == "assistant" and not ev.get("parent_tool_use_id"):
            for b in ev.get("message", {}).get("content", []) or []:
                if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") in DISPATCH_TOOLS:
                    inp = b.get("input") or {}
                    dispatches.append({"description": inp.get("description", ""),
                                       "prompt": inp.get("prompt", "")})
        elif ev.get("type") == "result":
            final = ev.get("result") or ""
            cost += ev.get("total_cost_usd") or 0
    return final, dispatches, cost


def main(argv):
    if argv[1:2] == ["--summary"]:
        groups = defaultdict(list)
        for line in open(argv[2]):
            row = json.loads(line)
            groups[(row["label"], row["design"])].append(row)
        keys = ["pass", "builder_check", "surfaced"]
        for (label, design), rows in groups.items():
            counts = {k: f"{sum(bool(r.get(k)) for r in rows)}/{len(rows)}" for k in keys}
            mean = sum(r.get("cost", 0) for r in rows) / len(rows)
            print(label, design, counts, f"errors {sum('error' in r for r in rows)}", f"mean ${mean:.3f}")
            for r in sorted(rows, key=lambda r: r["run"]):
                print(f"  run {r['run']}: {'PASS' if r.get('pass') else 'FAIL'} ${r.get('cost', 0):.3f}"
                      f" dispatches {r.get('dispatches', 0)}",
                      "; ".join(r.get("reasons", [])) or r.get("error", ""))
        return
    path, label, design, run = argv[1:5]
    final, dispatches, cost = parse(path)
    row = {"label": label, "design": design, "run": int(run), "cost": round(cost, 4)}
    if final is None:
        # Crash or budget stop: no reply to score. Counted under errors, never as a pass.
        row.update({"error": "no result event", "pass": False})
    else:
        row.update(score(design, final, dispatches))
    print(json.dumps(row))


if __name__ == "__main__":
    main(sys.argv)
