#!/usr/bin/env python3
"""Score reviewer transcripts for the planted defects and gate honesty.

score.py --label L --run N transcript.jsonl   -> one JSON row
score.py --summary scores.jsonl               -> table per label
"""
import argparse
import json
import re
from collections import defaultdict

DEFECTS = {
    "missing_empty_valueerror": r"empty[^\n]{0,120}(ValueError|return[s]? 0|raise)|(ValueError|return[s]? 0)[^\n]{0,120}empty",
    "extra_days_unit": r"\bdays?\b|[\"'`]d[\"'`]|\bd unit|86400",
    "repeat_or_order_bug": r"1h1h|repeat|out of order|out-of-order|order[^\n]{0,40}(not|isn't|never) (validated|checked|enforced)|duplicate unit",
    "convention_all": r"__all__",
    "unknown_units_ignored": r"unknown unit|invalid unit|ignor|silently|garbage|\"1x\"|'1x'|1x|abc",
}
GATES = [r"failure mode", r"have to be true", r"didn'?t check", r"break attempt"]


def score(path, label, run):
    text, cost, bash_runs = "", 0.0, 0
    for line in open(path):
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get("type") == "assistant":
            for b in e["message"].get("content", []):
                if b.get("type") == "tool_use" and b.get("name") == "Bash":
                    cmd = b.get("input", {}).get("command", "")
                    if re.search(r"python|unittest|pytest", cmd):
                        bash_runs += 1
        elif e.get("type") == "result":
            text = e.get("result") or ""
            cost = e.get("total_cost_usd") or 0.0
    tried = [l for l in text.splitlines() if re.search(r"Tried:", l)]
    labelled = [l for l in tried if re.search(r"\[(executed|ran|reasoned|traced)\]|\((executed|ran|reasoned|traced)\)|executed:|reasoned:", l, re.I)]
    row = {
        "label": label,
        "run": run,
        "cost": round(cost, 4),
        "defects": {k: bool(re.search(v, text, re.I)) for k, v in DEFECTS.items()},
        "gates": sum(bool(re.search(g, text, re.I)) for g in GATES),
        "tried_lines": len(tried),
        "tried_labelled": len(labelled),
        "tried_executed": len([l for l in tried if re.search(r"\[executed\]", l, re.I)]),
        "code_executions": bash_runs,
        "verdict_reject": bool(re.search(r"(not ready|no\b|with fixes|❌|issues found)", text[-1500:], re.I)),
    }
    return row


def summary(path):
    rows = [json.loads(l) for l in open(path) if l.strip()]
    groups = defaultdict(list)
    for r in rows:
        groups[r["label"]].append(r)
    for label, g in sorted(groups.items()):
        n = len(g)
        print(f"\n{label} (n={n}) mean cost ${sum(r['cost'] for r in g)/n:.3f}")
        for k in DEFECTS:
            print(f"  {k:<28} {sum(r['defects'][k] for r in g)}/{n}")
        print(f"  gates present (of 4)         {[r['gates'] for r in g]}")
        print(f"  Tried lines / labelled       {[(r['tried_lines'], r['tried_labelled']) for r in g]}")
        print(f"  [executed] lines             {[r.get('tried_executed', 0) for r in g]}")
        print(f"  code executions              {[r['code_executions'] for r in g]}")
        print(f"  rejects                      {sum(r['verdict_reject'] for r in g)}/{n}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--label")
    p.add_argument("--run", type=int)
    p.add_argument("--summary")
    p.add_argument("path", nargs="?")
    a = p.parse_args()
    if a.summary:
        summary(a.summary)
    else:
        print(json.dumps(score(a.path, a.label, a.run)))
