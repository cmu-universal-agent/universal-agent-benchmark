# Gold Answers

Place approved evaluator-only JSONL files here. The runner and adapters must
not read this directory while constructing agent input.

The `.example.json` files define local templates only. They are not gold data
and must not be consumed by evaluators as approved records.

Owner-provided extraction specifications may be stored here with
`status: draft_pending_approval` or `status: approved`. Draft rules must not be
used for bulk generation until formally approved. Approved specifications still
define generation semantics rather than publishable gold records.
