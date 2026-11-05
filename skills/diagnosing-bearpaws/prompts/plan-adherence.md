# Dimension: plan adherence

Compare what the session was asked or planned to do with what it did.

Look for:
- The request (your partner's first prompt and later instructions) and any plan file the session read
  or wrote (`docs/**/plans/*.md`, checkbox lists). List each asked-for item.
- For each item: the edit or run that did it, or its absence. Plan checkboxes ticked with no matching
  edit or run.
- Skills the situation called for and whether they were invoked (`Skill` tool_use lines) — e.g.
  a bug with no `systematic-debugging`, a completion claim with no verification run, elevated work
  with no review.
- Work beyond the request: files or features nobody asked for.

You may not claim: that a skill "should have fired" without naming the request text or event that
called for it; intent the transcript does not state.
