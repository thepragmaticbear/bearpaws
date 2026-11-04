#!/usr/bin/env python3
"""Score one drift-eval run, or summarize scores.jsonl with --summary.

The skill asks for a `Drift:` line followed by one bullet per divergence, or
"No drift." when there are none. Only bullets in that block are scored, so
verification prose elsewhere in the reply cannot count as a finding.
"""
import json
import re
import sys
from collections import defaultdict

CHECKS = {
    # Task 2 never landed: disallowed characters are kept.
    "missing_strip": r"task 2|punctuation|strip|disallowed|drop",
    # Task 3 hardcodes 50 instead of adding the max_len argument.
    "missing_max_len": r"max_len|hardcod",
    # src/cache.py is in no task.
    "unplanned_cache": r"cache",
}
HEADER = re.compile(r"^[\W_]*drift[\W_]*:")
BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")


def drift_block(text):
    """Bullets under the Drift: header, plus any finding on the header line.

    The block ends at the first non-blank line that is not a bullet. Returns
    None without a header and [] for "Drift: none".
    """
    lines = text.lower().splitlines()
    for i, line in enumerate(lines):
        m = HEADER.match(line)
        if m:
            rest = line[m.end():].strip(" *_.")
            block = [rest] if rest and rest not in ("none", "none found", "n/a") else []
            for nxt in lines[i + 1:]:
                if BULLET.match(nxt):
                    block.append(nxt)
                elif nxt.strip():
                    break
            return block
    return None


def score(text):
    block = drift_block(text)
    row = {k: bool(block) and any(re.search(p, l) for l in block) for k, p in CHECKS.items()}
    row["said_no_drift"] = not block and (block == [] or "no drift" in text.lower())
    return row


def main(argv):
    keys = [*CHECKS, "said_no_drift"]
    if argv[1:2] == ["--summary"]:
        groups = defaultdict(list)
        for line in open(argv[2]):
            row = json.loads(line)
            groups[row["label"]].append(row)
        for label, rows in groups.items():
            counts = {k: f"{sum(r.get(k, False) for r in rows)}/{len(rows)}" for k in keys}
            errors = sum("error" in r for r in rows)
            mean = sum(r.get("cost", 0) for r in rows) / len(rows)
            print(label, counts, f"errors {errors}", f"mean ${mean:.3f}")
        return
    path, label, run = argv[1:4]
    try:
        d = json.load(open(path))
    except Exception:
        d = {}
    row = {"label": label, "run": int(run), "cost": round(d.get("total_cost_usd") or 0, 4)}
    row.update(score(d.get("result") or ""))
    print(json.dumps(row))


if __name__ == "__main__":
    main(sys.argv)
