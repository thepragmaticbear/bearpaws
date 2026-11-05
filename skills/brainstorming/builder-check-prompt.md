# Builder Check Prompt Template

Use this template when a design covers elevated-risk work (see bp:using-bearpaws) and is written,
before the user reviews it. Routine designs skip it.

**Purpose:** Find the open questions where the builder's wrong guess would change the plan.

```
Agent tool (general-purpose):
  description: "Builder check of design"
  prompt: |
    You are a talented [DOMAIN] builder. You have to plan to build the design at
    [DOCUMENT_PATH], and you cannot talk to its author: whatever the document leaves open,
    you will have to guess.

    Read the document, and the code it names if that helps. Then list only the questions
    where a wrong guess would change the plan: a different data model, flow, interface,
    security property, or test. Rank them, most consequential first.

    Skip:
    - anything the document deliberately leaves to the builder;
    - anything you can decide from the code, the document, or common practice;
    - wording, formatting, and style nitpicks.

    ## Output

    For each question, one entry:
    1. [The question] — [why a wrong guess changes the plan]

    If no such question is left, reply exactly: nothing important left
```

**The author then** answers each question or amends the design, before the user review.
