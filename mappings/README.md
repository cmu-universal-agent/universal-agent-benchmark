# Dataset Mapping Contracts

This directory stores versioned, evaluator-approved mappings from source
dataset labels to benchmark enums. Mapping contents are owned by the evaluation
workflow; converters consume them and reject unmapped labels.

Files ending in `.example.json` are templates only. They must not be used to
convert benchmark data until `status` is changed to `approved` and the mapping
has complete source-label coverage.

Files with `status: draft_pending_approval` are owner-provided specifications
preserved for review. Converters may be prototyped against them, but bulk gold
generation remains blocked until `approved_by` and `approved_at` are set.
