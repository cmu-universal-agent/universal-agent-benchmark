# H4 v3 Owner-Review Handoff

Updated: 2026-07-21

Status: `draft_pending_approval`. H4 is the only remaining WS2 semantic-review
gate. PR #1 and stacked CrewAI PR #2 must remain unmerged until this review and
the final validation suite are complete.

## What changed

The H4 v3 extractor implements the five issue classes identified by Chloe:

1. Secondary history titles such as `Medical` and `Surgical` are treated as
   headers rather than emitted as standalone history items.
2. Full-line history headers such as `PAST SURGICAL HISTORY:` are removed while
   their clinical content is retained.
3. Common honorifics (`Dr.`, `Mr.`, `Mrs.`, and `Ms.`) are protected during
   sentence splitting so sentences do not begin mid-clause.
4. Short same-line statements such as `Denies ...` are retained instead of
   being dropped after a preceding sentence.
5. HPI symptom supplementation now runs even when ROS already contains items,
   and covers frequent infection and lingering-cold descriptions.

Regression tests cover the reported H4 review cases 003, 004, 005, 006, and
007. The extractor version is `core-pilot-converter-v4`; the H4 rule version is
`h4-programmatic-extraction-v3`.

## Chloe's review artifact

Use the local evaluator-only workbook:

`../outputs/h4_review_20260721/H4_v3_Chloe_review_20260721.xlsx`

The workbook contains a review guide, an eight-case queue, a correction map,
and one detail sheet per regenerated case. Chloe should record `Approve`,
`Approve with edits`, or `Needs changes` for each case and add field-level notes
where needed.

The workbook, generated cases, source-note excerpts, and evaluator-only gold
must not be committed or uploaded. Only this status handoff, code, tests, and
specification metadata belong in the public pull request.

## Approval outcome

After review:

- if all eight cases are approved, record Chloe's name/date and change the H4
  specification from `draft_pending_approval` to the approved state;
- if edits are requested, update the deterministic rule and regression test,
  regenerate the same eight-case pack, and return only the affected cases for
  confirmation;
- in either case, rerun the complete WS2 offline validation suite before any
  merge decision.
