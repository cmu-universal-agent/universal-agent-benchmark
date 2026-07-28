# Locked Split Manifests

Each dataset conversion writes a deterministic manifest containing source
record IDs and their benchmark split. Original dataset splits remain in
`metadata.source_split`; manifests control `metadata.split` and leakage checks.

No real manifest is committed until dataset selection and split policy are
approved.
