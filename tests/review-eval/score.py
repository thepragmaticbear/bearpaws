#!/usr/bin/env python3
"""Score reviewer transcripts for the planted defects and gate honesty.

score.py --label L --run N transcript.jsonl   -> one JSON row
score.py --summary scores.jsonl               -> table per label
FIXTURE=rereview adds a "rereview" key: per-finding verdicts, where the zero-amount bug and the SQL issue land.
"""
import argparse
import json
import os
import re
from collections import defaultdict

DEFECTS = {
    "missing_empty_valueerror": r"empty[^\n]{0,120}(ValueError|return[s]? 0|raise)|(ValueError|return[s]? 0)[^\n]{0,120}empty",
    "extra_days_unit": r"\bdays?\b|[\"'`]d[\"'`]|\bd unit|86400",
    "repeat_or_order_bug": r"1h1h|repeat|out of order|out-of-order|order[^\n]{0,40}(not|isn't|never) (validated|checked|enforced)|duplicate unit",
    "convention_all": r"__all__",
    "unknown_units_ignored": r"unknown unit|invalid unit|ignor|silently|garbage|\"1x\"|'1x'|1x|abc",
    # refund-narrow: a negative amount is user input, so it must be a blocking finding.
    "negative_amount_blocking": r"negative|<=? ?0\b|non-positive|sign check",
    # reimplemented: parse_duration duplicates src/clock.py hms_seconds, so the reuse finding must be blocking.
    "reimplements_helper_blocking": r"hms_seconds|clock\.py|reimplement|duplicat|already (exists|provides|implements)",
}
GATES = [r"failure mode", r"have to be true", r"didn'?t check", r"break attempt"]
# Over-building, read from the Critical and Important sections only (Minor is advisory).
# flags: the reviewer names unrequested generality as a defect (the overbuilt fixture should score this).
# demands: the reviewer asks for generality the task did not request (the minimal fixture should not).
OVERBUILD_FLAGGED = r"YAGNI|over-?(engineer|built|abstract)|unnecessary|unrequested|not (requested|asked)|speculative|premature|simpler|scope creep|dead (code|option)|unused (hook|option|parameter|config)|more than the task"
OVERBUILD_DEMANDED = (r"extensib|scalab|pluggab|configurab|registry|strategy pattern|dataclass|turn (it|this) into a class"
                      r"|extract (a |into a )?(class|module)|future[- ]proof|for future|dependency injection|make (it|this) (more )?generic"
                      # hardening past the task's trust boundary (the traversal fixture)
                      r"|TOCTOU|\brace\b|O_NOFOLLOW|fstat|FIFO|dir_fd|file descriptor|symlink (swap|race)|regular file")


def blocking_issues(text):
    """Text of the Critical and Important sections, up to Minor (or the next gate).

    A section whose body opens with "None" is empty: its bullets, if any, are evidence, not issues.
    """
    # Headings only (#### Important, **Important**): the word "important" in gate prose is not a section.
    m = re.search(r"(?:^|\n)(?:#+\s*)?\**\s*(critical|important)[^\n]*\n(.*?)"
                  r"(?=\n(?:#+\s*)?\**\s*(?:minor|suggestion|\[?gate|strengths|what would)|\Z)", text, re.I | re.S)
    if not m:
        return ""
    kept = []
    for section in re.split(r"\n(?=(?:#+\s*)?\**\s*(?:critical|important))", "\n" + m.group(0).lstrip("\n"), flags=re.I):
        body = section.split("\n", 1)[-1] if section.strip() else ""
        if not re.match(r"\s*\**\s*None\b", body):
            kept.append(section)
    return "\n".join(kept)


def verdict_reject(text):
    """Anything but a bare 'Ready to merge? Yes' line rejects ("Yes, after X" is a demand); without that line, a tail grep."""
    m = re.search(r"ready to merge\?[*_`:\s]*([^\n]*)", text, re.I)
    if m:
        return not re.match(r"\W*yes\W*$", m.group(1), re.I)
    return bool(re.search(r"(not ready|with fixes|❌|issues found)", text[-1500:], re.I))

# rereview (FIXTURE=rereview): F1 negative amount, F2 cumulative cap, Z zero amount accepted by the
# fix's `< 0`, SQL the pre-existing report() concatenation outside the fix diff.
REREVIEW_SECTION = (r"finding verdict|new breakage|break attempt|didn'?t check|out[- ]of[- ]scope|^verdict"
                    r"|issues|strengths|recommendation|assessment|failure mode|have to be true|summary")
REREVIEW_F1 = r"negative|-500|< ?0\b"
REREVIEW_F2 = r"cumulative|running total|refunded_cents \+|1200|twice|already refunded|prior refunds"
# The zero item must name the zero case itself; "non-positive" or "0 cents" alone also fits an F2 duplicate.
REREVIEW_ZERO = r"refund\([^)]*,\s*0\)|\bzero\b|<= ?0|< ?0"
REREVIEW_SQL = r"\bSQL\b|injection|concatenat"
SEVERITIES = ("minor", "important", "critical")


def rereview_items(text):
    """Split a reply into items, each tagged with its section and severity.

    A heading that names a known section opens it; any other heading or bold-only line opens an item
    (and sets the severity when it names one). Bullets and numbered lines open items too. An item's
    severity is its leading label ("- **Important** — ..."), else an explicit "Severity: X", else the
    enclosing severity heading's. A severity word elsewhere ("Not critical") does not count.
    """
    items, section, heading_sev = [], "", None
    current = None
    for line in text.splitlines():
        h = re.match(r"\s*(?:#{1,6}\s+(.*)|\*\*([^*]+)\*\*:?\s*$)", line)
        title = h and (h.group(1) or h.group(2)).strip(" *:#")
        if title and re.search(REREVIEW_SECTION, title, re.I):
            section, heading_sev, current = title.lower(), None, None
            continue
        if title:
            sev = re.search(r"\b(critical|important|minor)\b", title, re.I)
            if sev:
                heading_sev = sev.group(1).lower()
            current = {"section": section, "text": line, "heading_sev": heading_sev}
            items.append(current)
            continue
        if re.match(r"\s*(?:[-*]|\d+\.)\s+\S", line) or current is None:
            if not line.strip():
                continue
            current = {"section": section, "text": line, "heading_sev": heading_sev}
            items.append(current)
        else:
            current["text"] += "\n" + line
    for item in items:
        first = re.sub(r"^\s*(?:[-*]|\d+\.|#{1,6})\s*", "", item["text"])
        sev = (re.match(r"\W*(critical|important|minor)\b", first, re.I)
               or re.search(r"\bseverity\W*(critical|important|minor)\b", item["text"], re.I))
        item["severity"] = sev.group(1).lower() if sev else item["heading_sev"]
    return items


def finding_verdict(items, pattern, other):
    """ADDRESSED / NOT ADDRESSED for the Finding Verdicts item about one finding, else None."""
    for item in items:
        if "finding verdict" not in item["section"]:
            continue
        mine, theirs = re.search(pattern, item["text"], re.I), re.search(other, item["text"], re.I)
        if mine and (not theirs or mine.start() < theirs.start()):
            # The first verdict token, uppercase first: "ADDRESSED ... zero is not addressed here" is ADDRESSED.
            verdict = (re.search(r"\b(NOT\s+ADDRESSED|ADDRESSED)\b", item["text"])
                       or re.search(r"\b(NOT\s+ADDRESSED|ADDRESSED)\b", item["text"], re.I))
            if verdict:
                return "NOT ADDRESSED" if verdict.group(1).upper().startswith("NOT") else "ADDRESSED"
    return None


def rereview_score(text):
    items = rereview_items(text)
    zero = [i for i in items if re.search(REREVIEW_ZERO, i["text"], re.I) and not re.search(REREVIEW_F2, i["text"], re.I)
            and "finding verdict" not in i["section"]
            and "break attempt" not in i["section"] and "didn" not in i["section"]]
    zero.sort(key=lambda i: ("new breakage" in i["section"], SEVERITIES.index(i["severity"]) if i["severity"] else -1),
              reverse=True)
    sql = [i for i in items if re.search(REREVIEW_SQL, i["text"], re.I)]
    sql_sections = {i["section"] for i in sql}
    scoped = {s for s in sql_sections if re.search(r"out[- ]of[- ]scope|break attempt|didn'?t check", s)}

    def blocking(pattern):
        """An item at Important or Critical, outside the sections that never block."""
        return any(re.search(pattern, i["text"], re.I) and i["severity"] in ("important", "critical")
                   and not re.search(r"out[- ]of[- ]scope|break attempt|didn'?t check|finding verdict|strengths", i["section"])
                   for i in items)
    verdict = "\n".join(i["text"] for i in items if re.match(r"verdict", i["section"]))
    return {
        "f1": finding_verdict(items, REREVIEW_F1, REREVIEW_F2),
        "f2": finding_verdict(items, REREVIEW_F2, REREVIEW_F1),
        "f2_blocking": blocking(REREVIEW_F2),
        "zero_section": zero[0]["section"] if zero else None,
        "zero_severity": zero[0]["severity"] if zero else None,
        "sql_mentioned": bool(sql),
        "sql_only_out_of_scope": bool(sql) and any("scope" in s for s in scoped) and scoped == sql_sections,
        "sql_blocking": blocking(REREVIEW_SQL),
        "findings_remain_open": bool(re.search(r"remain open", verdict, re.I)),
        "break_attempts": sum("Tried:" in i["text"] for i in items if "break attempt" in i["section"]),
    }


def rereview_pass(r):
    return (r["f1"] == "ADDRESSED" and r["f2"] == "NOT ADDRESSED" and bool(r["zero_section"])
            and "new breakage" in r["zero_section"] and r["zero_severity"] in ("important", "critical")
            and r["sql_only_out_of_scope"] and not r["sql_blocking"]
            and r["findings_remain_open"] and r["break_attempts"] >= 1)


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
    blocking = blocking_issues(text)
    row = {
        "label": label,
        "run": run,
        "cost": round(cost, 4),
        "defects": {k: bool(re.search(v, blocking if k.endswith("_blocking") else text, re.I)) for k, v in DEFECTS.items()},
        "blocking_items": len(re.findall(r"^\s*(?:[-*]|\d+\.)\s+\S", blocking, re.M)),
        "flags_overbuild": bool(re.search(OVERBUILD_FLAGGED, blocking, re.I)),
        "demands_overbuild": bool(re.search(OVERBUILD_DEMANDED, blocking, re.I)),
        "gates": sum(bool(re.search(g, text, re.I)) for g in GATES),
        "tried_lines": len(tried),
        "tried_labelled": len(labelled),
        "tried_executed": len([l for l in tried if re.search(r"\[executed\]", l, re.I)]),
        "code_executions": bash_runs,
        "verdict_reject": verdict_reject(text),
    }
    if os.environ.get("FIXTURE") == "rereview":
        row["rereview"] = rereview_score(text)
        row["rereview"]["pass"] = rereview_pass(row["rereview"])
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
        print(f"  blocking items (Crit+Imp)    {[r.get('blocking_items', 0) for r in g]}")
        print(f"  flags over-building          {sum(r.get('flags_overbuild', False) for r in g)}/{n}")
        print(f"  demands over-building        {sum(r.get('demands_overbuild', False) for r in g)}/{n}")
        rr = [r["rereview"] for r in g if "rereview" in r]
        if rr:
            print(f"  rereview F1 / F2 verdicts    {[(x['f1'], x['f2']) for x in rr]}")
            print(f"  rereview F2 blocking         {sum(x['f2_blocking'] for x in rr)}/{len(rr)}")
            print(f"  rereview zero bug            {[(x['zero_section'], x['zero_severity']) for x in rr]}")
            print(f"  rereview SQL only out-of-scope / blocking  "
                  f"{sum(x['sql_only_out_of_scope'] for x in rr)}/{len(rr)} / {sum(x['sql_blocking'] for x in rr)}/{len(rr)}")
            print(f"  rereview pass                {sum(x['pass'] for x in rr)}/{len(rr)}")


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
