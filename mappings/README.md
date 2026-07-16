# Dataset Mapping Contracts

This directory stores versioned, evaluator-approved mappings from source
dataset labels to benchmark enums. Mapping contents are owned by the evaluation
workflow; converters consume them and reject unmapped labels.

Files ending in `.example.json` are templates only. They must not be used to
convert benchmark data until `status` is changed to `approved` and the mapping
has complete source-label coverage.
