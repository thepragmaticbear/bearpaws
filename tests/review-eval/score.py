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
    "missing_empty_valueerror": (
        r"(?:empty(?:\s+(?:string|input|value|text))?|\"\"|''|not\s+text|blank)"
        r"[^\n]{0,100}(?:(?:returns|returning|:\s*return)\s+0\b|instead\s+of\s+(?:raising\s+)?ValueError|"
        r"(?:does\s+not|doesn't|fails?\s+to|never|not)\s+raise\s+ValueError|"
        r"(?:should|must|needs?\s+to)\s+raise\s+ValueError|not\s+rejected|missing\s+ValueError)"
        r"|(?:(?:returns|returning|:\s*return)\s+0\b|missing\s+ValueError|(?:does\s+not|doesn't|fails?\s+to|never)\s+raise\s+ValueError|"
        r"(?:should|must|needs?\s+to)\s+raise\s+ValueError)"
        r"[^\n]{0,100}(?:empty(?:\s+(?:string|input|value|text))?|\"\"|''|not\s+text|blank)"
    ),
    "extra_days_unit": (
        r"(?:unrequested|unexpected|extra|unsupported|unasked|scope\s+creep|"
        r"not\s+(?:in\s+(?:the\s+)?(?:spec|requirements?|task)|requested|asked|specified)|"
        r"should\s+(?:not\s+(?:accept|support|allow)|be\s+removed|raise\s+ValueError)|"
        r"remove(?:d|s)?|reject(?:ed|s)?|violates?\s+(?:the\s+)?(?:spec|requirements?))"
        r"[^\n]{0,80}(?:\bdays?\b|[\"'`]d[\"'`]|\bd\s+(?:unit|branch)|86400)"
        r"|(?:\bdays?\b|[\"'`]d[\"'`]|\bd\s+(?:unit|branch)|86400)"
        r"[^\n]{0,80}(?:unrequested|unexpected|extra|unsupported|unasked|scope\s+creep|"
        r"not\s+(?:in\s+(?:the\s+)?(?:spec|requirements?|task)|requested|asked|specified)|"
        r"should\s+(?:not\s+(?:accept|support|allow)|be\s+removed|raise\s+ValueError)|"
        r"be\s+removed|violates?\s+(?:the\s+)?(?:spec|requirements?))"
    ),
    "repeat_or_order_bug": (
        r"(?:accepts?|allows?|permits?|double-?counts?|sums?|silently\s+sums?|"
        r"fails?\s+to\s+(?:reject|validate|check|raise)|"
        r"(?:does\s+not|doesn't|never|not)\s+(?:reject|validate|check|enforce|raise)|"
        r"missing\s+check|no\s+check|should\s+(?:raise\s+ValueError|reject))"
        r"[^\n]{0,90}(?:1h1h|30m1h|repeat(?:ed|ing|s)?(?:\s+units?)?|duplicate\s+units?|out[- ]of[- ]order(?:\s+units?)?|unit\s+order)"
        r"|(?:1h1h|30m1h|repeat(?:ed|ing|s)?(?:\s+units?)?|duplicate\s+units?|out[- ]of[- ]order(?:\s+units?)?|order(?:\s+of\s+units)?)"
        r"[^\n]{0,90}(?:accept(?:ed|s)?|allow(?:ed|s)?|double-?count(?:ed|s)?|summed|"
        r"not\s+(?:validated|checked|enforced|rejected)|isn't\s+(?:validated|checked|enforced)|"
        r"never\s+(?:validated|checked|enforced)|(?:does\s+not|doesn't|fails?\s+to)\s+raise|"
        r"should\s+(?:raise\s+ValueError|be\s+rejected))"
    ),
    "convention_all": (
        r"(?:missing|omits?|empty|not\s+(?:added|listed|included|exported|registered)|"
        r"doesn't\s+(?:include|export|list)|does\s+not\s+(?:include|export|list)|"
        r"fails?\s+to\s+(?:export|list|add)|must\s+(?:be\s+added|include|export)|"
        r"should\s+(?:be\s+added|include|export)|add\s+\w+\s+to)"
        r"[^\n]{0,80}__all__"
        r"|__all__[^\n]{0,80}(?:missing|omits?|empty|is\s+\[\]|does\s+not\s+(?:include|contain|export|list)|"
        r"doesn't\s+(?:include|contain|export|list)|lacks?|needs?\s+parse_duration|"
        r"must\s+(?:include|contain|list)|should\s+(?:include|contain|list))"
    ),
    "unknown_units_ignored": (
        r"(?:unknown\s+units?|invalid\s+units?|unrecognized\s+(?:units?|char(?:acter)?s?|tokens?|input)|"
        r"non-?matching\s+(?:char(?:acter)?s?|text)|garbage|[\"'`]1x[\"'`]|[\"'`]abc[\"'`])"
        r"[^\n]{0,90}(?:silently\s+)?(?:ignor(?:ed|es|ing)|skip(?:ped|s|ping)?|dropp?(?:ed|s|ing)|"
        r"accept(?:ed|s|ing)|allow(?:ed|s)|not\s+(?:rejected|flagged|caught)|"
        r"(?:does\s+not|doesn't|fails?\s+to)\s+raise|should\s+(?:raise\s+ValueError|be\s+rejected))"
        r"|(?:silently\s+(?:ignor(?:ed|es|ing)|skip(?:ped|s|ping)?|dropp?(?:ed|s|ing))|"
        r"(?:does\s+not|doesn't|fails?\s+to)\s+(?:raise\s+ValueError|reject))"
        r"[^\n]{0,90}(?:unknown\s+units?|invalid\s+units?|unrecognized|non-?matching|garbage|[\"'`]1x[\"'`]|[\"'`]abc[\"'`])"
    ),
    # refund-narrow: a negative amount is user input, so it must be a blocking finding.
    "negative_amount_blocking": (
        r"(?:negative|<=?\s*0\b|<\s*0\b|non-?positive)"
        r"[^\n]{0,90}(?:accept(?:ed|s)|allow(?:ed|s)|unchecked|not\s+(?:rejected|checked|validated)|"
        r"(?:does\s+not|doesn't|fails?\s+to)\s+(?:reject|check|validate|raise)|"
        r"missing\s+(?:sign\s+)?check|lacks?\s+(?:a\s+)?(?:sign\s+)?check|lowers?\s+refunded|"
        r"credits?\s+money|should\s+(?:raise\s+ValueError|be\s+rejected)|must\s+(?:raise\s+ValueError|be\s+rejected))"
        r"|(?:accept(?:ed|s)|no\s+sign\s+check|missing\s+(?:sign\s+)?check|lacks?\s+(?:a\s+)?(?:sign\s+)?check|"
        r"(?:does\s+not|doesn't|fails?\s+to)\s+(?:reject|check|validate|raise)|should\s+(?:raise\s+ValueError|reject))"
        r"[^\n]{0,90}(?:negative|<=?\s*0\b|<\s*0\b|non-?positive|\bsign\b)"
    ),
    # reimplemented: parse_duration duplicates src/clock.py hms_seconds, so the reuse finding must be blocking.
    "reimplements_helper_blocking": (
        r"(?:reimplement(?:s|ed|ing)|duplicat(?:es|ed|ing)|reinvent(?:s|ed|ing)|instead\s+of\s+(?:calling|using|reusing)|"
        r"(?:should|could)\s+(?:call|reuse|use)|already\s+(?:exists?\s+(?:in|as)|(?:provides?|implements?)\s+(?:this|the|duration|hms_seconds)))"
        r"[^\n]{0,90}(?:hms_seconds|src/clock\.py|clock\.py|existing\s+(?:helper|function|parser))"
        r"|(?:hms_seconds|src/clock\.py|clock\.py)"
        r"[^\n]{0,90}(?:is\s+reimplemented|is\s+duplicated|already\s+(?:exists?\s+(?:in|as)|(?:provides?|implements?)\s+(?:this|the|duration|parse_duration|hms_seconds))|"
        r"should\s+(?:be\s+called|be\s+reused)|instead\s+of\s+(?:reimplementing|duplicating|hand-?rolling))"
    ),
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

BLOCKING_HEADING = re.compile(
    r"\b(?:critical|important|must[- ]?fix|should[- ]?fix|blockers?|blocking|high(?:\s+(?:priority|severity))?|major(?:\s+issues?)?|required\s+(?:fixes|changes)|p[01])\b",
    re.I,
)
EXCLUDED_HEADING = re.compile(
    r"\[?gate|failure\s+mode|have\s+to\s+be\s+true|didn'?t\s+check|break\s+attempt|minor|nice\s+to\s+have|"
    r"suggestions?|out[- ]of[- ]scope|strengths|recommendations?|assessment|verdict",
    re.I,
)
CONTAINER_HEADING = re.compile(
    r"\b(?:issues?|findings?|problems?|defects?|review\s+findings?|code\s+review)\b",
    re.I,
)
NEGATED_FINDING = re.compile(
    r"\b(?:this\s+is\s+not|not\s+actually|isn't|is\s+not)\s+(?:an?\s+)?(?:\w+\s+){0,3}"
    r"(?:bug|issue|defect|problem|vulnerability|injection|reimplementation|duplicate|finding|blocker|error)\b"
    r"|\b(?:no|not\s+an?)\s+(?:sql\s+injection|bug|issue|defect|problem|vulnerability|reimplementation|duplicate|finding)\b"
    r"|\bfalse\s+positive\b"
    r"|\b(?:does\s+not|doesn't|do\s+not|don't)\s+(?:reimplement|duplicate|ignore|skip|accept|allow|return\s+0)\b"
    r"|\b(?:is|are)\s+not\s+(?:accepted|ignored|skipped|a\s+bug|an\s+issue|missing|reimplemented)\b"
    r"|\b(?:__all__\s+is\s+not\s+missing|not\s+an?\s+unrequested)\b"
    r"|\b(?:correctly|properly)\s+(?:raises?\s+ValueError|rejects?|validates?|checks?|handles?)\b",
    re.I,
)
FIX_CUE = re.compile(
    r"(?:how\s+to\s+fix|fix(?:\s+is)?|remediation|recommendation|suggest(?:ion)?)\s*[:—-]\s*(.+)"
    r"|fix\s+by\s+(.+)",
    re.I | re.S,
)
WRONG_FIX = {
    "missing_empty_valueerror": re.compile(
        r"\b(?:return(?:ing)?\s+(?:0|-1|None|False|0\.0)|keep\s+returning\s+0|do\s+not\s+raise|don't\s+raise)\b",
        re.I,
    ),
    "extra_days_unit": re.compile(
        r"\b(?:keep(?:ing)?\s+(?:the\s+)?['\"`]?d['\"`]?|document\s+(?:days|['\"`]?d['\"`]?)|support\s+['\"`]?d['\"`]?)\b",
        re.I,
    ),
    "repeat_or_order_bug": re.compile(
        r"\b(?:sort\s+(?:and\s+)?deduplicat|deduplicat\w*|sum\s+repeats|allow\s+repeats|take\s+(?:the\s+)?(?:first|last)\s+(?:match|unit))\b",
        re.I,
    ),
    "convention_all": re.compile(
        r"\b(?:remove|delete|ignore)\s+__all__\b",
        re.I,
    ),
    "unknown_units_ignored": re.compile(
        r"\b(?:log\s+(?:a\s+)?warning|warn\s+and\s+continue|continue\s+skipping|skip\w*|ignore\w*|return\s+(?:0|None))\b",
        re.I,
    ),
    "negative_amount_blocking": re.compile(
        r"\b(?:abs\(|clamp|max\(\s*0|return\s+(?:0|None|False)|treat\s+(?:as|negative\s+as)\s+0)\b",
        re.I,
    ),
    "reimplements_helper_blocking": re.compile(
        r"\b(?:keep\s+(?:the\s+)?(?:custom|hand-rolled)|add\s+(?:a\s+)?comment|copy\s+hms_seconds)\b",
        re.I,
    ),
}
LOCAL_NEG_BEFORE = re.compile(
    r"\b(?:no|not|never|nor|without|neither|isn't|aren't|wasn't|doesn't|don't|cannot|can't)\b",
    re.I,
)


def _extract_fix_clause(chunk):
    m = FIX_CUE.search(chunk)
    if not m:
        return ""
    return (m.group(1) or m.group(2) or "").strip()


def _has_wrong_fix(defect_key, chunk):
    wf = WRONG_FIX.get(defect_key)
    if not wf:
        return False
    fix_text = _extract_fix_clause(chunk)
    return bool(fix_text and wf.search(fix_text))


def _split_items(text):
    """Split text into bullet/numbered items (with indented sub-bullets) or paragraphs/lines."""
    items, cur = [], None
    for line in (text or "").splitlines():
        if re.match(r"^\s*(?:#{1,6}\s+|\*\*[^*]+\*\*:?\s*$)", line):
            cur = None
            continue
        m = re.match(r"^(\s*)(?:[-*]|\d+\.)\s+\S", line)
        if m and len(m.group(1).expandtabs()) < 2:
            cur = line
            items.append(cur)
        elif not line.strip():
            cur = None
        elif cur is not None:
            items[-1] += "\n" + line
        else:
            items.append(line)
    return [i for i in items if i.strip()]


def defect_found(key, text):
    """True when text contains a non-negated, non-wrong-fix diagnosis matching DEFECTS[key]."""
    pat = DEFECTS[key]
    for item in _split_items(text):
        if NEGATED_FINDING.search(item):
            continue
        if _has_wrong_fix(key, item):
            continue
        if re.search(pat, item, re.I):
            return True
    return False


def _is_negated_match(text, pattern):
    """True if every match of pattern in text is locally negated (e.g., 'this is not a SQL injection')."""
    matched_any = False
    for m in re.finditer(pattern, text, re.I):
        matched_any = True
        before = re.split(r"[.!?\n;—]", text[:m.start()])[-1]
        if not LOCAL_NEG_BEFORE.search(before[-40:]):
            return False
    return matched_any


def _has_positive_match(text, pattern):
    for item in _split_items(text):
        if NEGATED_FINDING.search(item):
            continue
        for m in re.finditer(pattern, item, re.I):
            before = re.split(r"[.!?\n;—]", item[:m.start()])[-1]
            if not LOCAL_NEG_BEFORE.search(before[-40:]):
                return True
    return False


def _parse_heading(line):
    m = re.match(r"^\s*#{1,6}\s+(.*)$", line)
    if m:
        return m.group(1).strip(" *:#")
    m = re.match(r"^\s*\*\*([^*]+)\*\*:?\s*$", line)
    if m:
        return m.group(1).strip(" *:#")
    m = re.match(
        r"^\s*(Critical|Important|Minor|Must[- ]?Fix|Should[- ]?Fix|Blockers?|Blocking|Suggestions?|Nice to Have|Issues|Findings|Review Findings)\s*:?\s*$",
        line,
        re.I,
    )
    if m:
        return m.group(1).strip(" *:#")
    return None


def blocking_issues(text):
    """Text of blocking sections (Critical/Important/Must Fix/Blockers) and inline-blocking items.

    Skips [GATE], Minor, Suggestions, Out-of-Scope, Strengths, Recommendations, Assessment, Verdict,
    and sections whose body opens with "None".
    """
    sections = []
    mode = None
    buf = []

    def flush():
        if mode in ("blocking", "container") and buf:
            body = "\n".join(buf)
            if not re.match(r"^\s*\**\s*None\b", body, re.I):
                if mode == "blocking":
                    sections.append(body)
                else:
                    # In a neutral container heading (e.g. "### Findings"), keep items tagged Critical/Important.
                    for item in _split_items(body):
                        first = re.sub(r"^\s*(?:[-*]|\d+\.)\s*", "", item).split("\n", 1)[0]
                        if (re.search(r"\bseverity\W*(?:critical|important)\b", item, re.I)
                                or re.match(r"[\W*]*(?:critical|important)\b", first, re.I)
                                or re.search(r"\[(?:critical|important)\]|\((?:critical|important)\)", first, re.I)):
                            sections.append(item)

    for line in (text or "").splitlines():
        title = _parse_heading(line)
        if title is not None:
            flush()
            buf = []
            if EXCLUDED_HEADING.search(title):
                mode = "excluded"
            elif BLOCKING_HEADING.search(title):
                mode = "blocking"
            elif CONTAINER_HEADING.search(title):
                mode = "container"
            else:
                mode = "excluded"
            continue
        if mode is not None:
            buf.append(line)
    flush()
    return "\n".join(sections)


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
# The zero item must name a zero amount: refund(..., 0), an amount of zero, or the `< 0` vs `<= 0` check on
# the amount. "Below zero" or "total - 600 - 600 < 0" is an F2 duplicate, not the zero bug.
REREVIEW_ZERO = (r"refund\([^)]*,\s*0\)|\bamount(?:_cents)?\s*(?:of|=|==|is)\s*(?:0|zero)\b|\bzero[- ](?:amount|refund|cents?)"
                 r"|(?:amount|refund)s? of (?:0|zero)\b|accepts? (?:a )?(?:0|zero)\b|\b(?:0|zero)(?: amounts?)? (?:is|are) (?:still )?accepted"
                 r"|amount_cents\s*<=?\s*0\b|`<=? ?0`|<= ?0\b[^\n]{0,40}\bamount|\b0-cent")
SEV = r"(critical|important|minor)"
REREVIEW_SQL = r"\bSQL\b|injection|concatenat"
SEVERITIES = ("minor", "important", "critical")


def rereview_items(text):
    """Split a reply into items, each tagged with its section and severity.

    A heading that names a known section opens it; any other heading or bold-only line opens an item
    (and sets the severity when it names one). Bullets and numbered lines open items too. A Verdict
    heading's own text ("### Verdict: Findings remain open") and an inline "**Verdict:** ..." line are
    kept as verdict items. An item's severity, in order of preference: an explicit "Severity: X"; a
    leading label ("- Important: ...", "- **Important** — ..."); a label after a file:line prefix
    ("- src/a.py:9 (Important): ...", "- **src/a.py:9** — Important: ..."); a closing severity word on
    the first line ("... Important."), unless preceded by "not"; else the enclosing severity heading's.
    A severity word elsewhere ("Not critical: ...") does not count.
    """
    items, section, heading_sev = [], "", None
    current = None
    for line in text.splitlines():
        h = re.match(r"\s*(?:#{1,6}\s+(.*)|\*\*([^*]+)\*\*:?\s*$)", line)
        title = h and (h.group(1) or h.group(2)).strip(" *:#")
        inline = not h and re.match(r"\s*\*\*\s*(verdict)\s*:?\s*\*\*:?\s*(.*)$", line, re.I)
        if inline and "finding verdict" not in section:
            section, heading_sev, current = "verdict", None, None
            if inline.group(2).strip():
                current = {"section": section, "text": inline.group(2), "heading_sev": None}
                items.append(current)
            continue
        if title and re.search(REREVIEW_SECTION, title, re.I):
            section, heading_sev, current = title.lower(), None, None
            rest = re.match(r"verdict\W*(.+)", title, re.I)
            if rest:
                current = {"section": section, "text": rest.group(1), "heading_sev": None}
                items.append(current)
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
        first = re.sub(r"^\s*(?:[-*]|\d+\.|#{1,6})\s*", "", item["text"]).split("\n", 1)[0]
        sev = (re.search(r"\bseverity\W*" + SEV + r"\b", item["text"], re.I)
               or re.match(r"\W*" + SEV + r"\b", first, re.I)
               or re.match(r"[*`\s]*[\w./-]+:\d+(?:-\d+)?[*`]*\s*(?:\(\W*" + SEV + r"\W*\)|[—–:-]+\s*[*_]*" + SEV + r"\b)",
                           first, re.I)
               or re.search(r"(?<!not )\b" + SEV + r"\W*$", first, re.I))
        item["severity"] = next(g for g in sev.groups() if g).lower() if sev else item["heading_sev"]
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
    zero = [i for i in items if re.search(REREVIEW_ZERO, i["text"], re.I) and "finding verdict" not in i["section"]
            and "break attempt" not in i["section"] and "didn" not in i["section"]]
    zero.sort(key=lambda i: ("new breakage" in i["section"], SEVERITIES.index(i["severity"]) if i["severity"] else -1),
              reverse=True)
    sql = [i for i in items if re.search(REREVIEW_SQL, i["text"], re.I) and not _is_negated_match(i["text"], REREVIEW_SQL)]
    sql_sections = {i["section"] for i in sql}
    scoped = {s for s in sql_sections if re.search(r"out[- ]of[- ]scope|break attempt|didn'?t check", s)}

    def blocking(pattern):
        """An item at Important or Critical, outside the sections that never block."""
        return any(re.search(pattern, i["text"], re.I) and not _is_negated_match(i["text"], pattern)
                   and i["severity"] in ("important", "critical")
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
        "findings_remain_open": bool(re.search(r"remains? open", verdict, re.I)),
        "break_attempts": sum("Tried:" in i["text"] for i in items if "break attempt" in i["section"]),
    }


def rereview_pass(r):
    return (r["f1"] == "ADDRESSED" and r["f2"] == "NOT ADDRESSED" and bool(r["zero_section"])
            and "new breakage" in r["zero_section"] and r["zero_severity"] in ("important", "critical")
            and r["sql_only_out_of_scope"] and not r["sql_blocking"]
            and r["findings_remain_open"] and r["break_attempts"] >= 1)


def _accuracy_and_compliance(text, blocking, defects_map, blocking_items, flags_overbuild, demands_overbuild,
                             gates, tried, labelled, rr=None, fixture=None):
    fixture = fixture or os.environ.get("FIXTURE", "planted")
    if fixture == "rereview" and rr is not None:
        defect_checks = [
            rr["f1"] == "ADDRESSED",
            rr["f2"] == "NOT ADDRESSED",
            bool(rr["zero_section"]),
            not rr["sql_blocking"],
        ]
        severity_checks = [
            rr["zero_severity"] in ("important", "critical"),
            not rr["sql_blocking"],
            rr["f2"] == "NOT ADDRESSED" or rr["f2_blocking"],
        ]
        items = rereview_items(text)
        has_verdict = any(re.match(r"verdict", i["section"]) for i in items)
        has_blindspots = bool(re.search(r"didn'?t\s+check|out[- ]of[- ]scope", text, re.I))
        format_checks = [
            rr["f1"] is not None and rr["f2"] is not None,
            bool(tried) and len(labelled) == len(tried),
            has_blindspots,
            has_verdict,
        ]
        return (
            round(sum(defect_checks) / len(defect_checks), 4),
            round(sum(severity_checks) / len(severity_checks), 4),
            round(sum(format_checks) / len(format_checks), 4),
        )

    if fixture in ("refund-narrow", "refund-scoped"):
        expected = ("negative_amount_blocking",)
        defect_accuracy = 1.0 if defect_found("negative_amount_blocking", text) else 0.0
        severity_accuracy = 1.0 if defect_found("negative_amount_blocking", blocking) else 0.0
    elif fixture == "reimplemented":
        expected = ("reimplements_helper_blocking",)
        defect_accuracy = 1.0 if defect_found("reimplements_helper_blocking", text) else 0.0
        severity_accuracy = 1.0 if defect_found("reimplements_helper_blocking", blocking) else 0.0
    elif fixture == "overbuilt":
        defect_accuracy = 1.0 if _has_positive_match(text, OVERBUILD_FLAGGED) else 0.0
        severity_accuracy = 1.0 if flags_overbuild else 0.0
    elif fixture in ("minimal", "traversal", "refund", "refund-offscope"):
        false_pos = any(defect_found(k, text) for k in DEFECTS) or demands_overbuild
        defect_accuracy = 0.0 if false_pos else 1.0
        severity_accuracy = 1.0 if (blocking_items == 0 and not verdict_reject(text)) else 0.0
    else:
        expected = ["missing_empty_valueerror", "extra_days_unit", "repeat_or_order_bug", "unknown_units_ignored"]
        if os.environ.get("CONVENTION") == "1":
            expected.append("convention_all")
        defect_hits = sum(1 for k in expected if defect_found(k, text))
        severity_hits = sum(1 for k in expected if defect_found(k, blocking))
        defect_accuracy = round(defect_hits / len(expected), 4)
        severity_accuracy = round(severity_hits / len(expected), 4)

    has_issues_structure = any(
        (_parse_heading(l) is not None and (BLOCKING_HEADING.search(_parse_heading(l))
                                            or CONTAINER_HEADING.search(_parse_heading(l))
                                            or re.search(r"\bminor\b", _parse_heading(l), re.I)))
        for l in text.splitlines()
    )
    has_verdict = bool(re.search(r"(?:ready to merge\?|###\s*verdict|\*\*verdict\*\*)", text, re.I))
    format_checks = [
        gates == 4,
        bool(tried) and len(labelled) == len(tried),
        has_issues_structure,
        has_verdict,
    ]
    format_compliance = round(sum(format_checks) / len(format_checks), 4)
    return defect_accuracy, severity_accuracy, format_compliance


def score(path, label, run):
    text, cost, bash_runs = "", 0.0, 0
    with open(path, errors="replace") as f:
        for line in f:
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
    defects_map = {k: defect_found(k, blocking if k.endswith("_blocking") else text) for k in DEFECTS}
    blocking_items = len(re.findall(r"^\s*(?:[-*]|\d+\.)\s+\S", blocking, re.M))
    flags_overbuild = _has_positive_match(blocking, OVERBUILD_FLAGGED)
    demands_overbuild = _has_positive_match(blocking, OVERBUILD_DEMANDED)
    gates = sum(bool(re.search(g, text, re.I)) for g in GATES)

    fixture = os.environ.get("FIXTURE")
    rr = rereview_score(text) if fixture == "rereview" else None
    if rr is not None:
        rr["pass"] = rereview_pass(rr)

    defect_accuracy, severity_accuracy, format_compliance = _accuracy_and_compliance(
        text, blocking, defects_map, blocking_items, flags_overbuild, demands_overbuild,
        gates, tried, labelled, rr=rr, fixture=fixture,
    )
    row = {
        "label": label,
        "run": run,
        "cost": round(cost, 4),
        "defects": defects_map,
        "defect_accuracy": defect_accuracy,
        "severity_accuracy": severity_accuracy,
        "format_compliance": format_compliance,
        "blocking_items": blocking_items,
        "flags_overbuild": flags_overbuild,
        "demands_overbuild": demands_overbuild,
        "gates": gates,
        "tried_lines": len(tried),
        "tried_labelled": len(labelled),
        "tried_executed": len([l for l in tried if re.search(r"\[executed\]", l, re.I)]),
        "code_executions": bash_runs,
        "verdict_reject": verdict_reject(text),
    }
    if rr is not None:
        row["rereview"] = rr
    return row


def summary(path):
    with open(path) as f:
        rows = [json.loads(l) for l in f if l.strip()]
    groups = defaultdict(list)
    for r in rows:
        groups[r["label"]].append(r)
    for label, g in sorted(groups.items()):
        n = len(g)
        print(f"\n{label} (n={n}) mean cost ${sum(r['cost'] for r in g)/n:.3f}")
        for k in DEFECTS:
            print(f"  {k:<28} {sum(r['defects'][k] for r in g)}/{n}")
        print(f"  defect accuracy (mean)       {sum(r.get('defect_accuracy', 0.0) for r in g)/n:.2f}")
        print(f"  severity accuracy (mean)     {sum(r.get('severity_accuracy', 0.0) for r in g)/n:.2f}")
        print(f"  format compliance (mean)     {sum(r.get('format_compliance', 0.0) for r in g)/n:.2f}")
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
