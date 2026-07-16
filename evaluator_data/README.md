# Evaluator-Only Data

Nothing in this directory may be passed to a framework adapter or included in
an agent-visible benchmark case. Ground truth and rubrics are joined by the
evaluator after execution.

- `gold_answers/{task_id}.jsonl`: one evaluator-only record per `case_id`.
- `rubrics/{task_id}.json`: one versioned scoring rubric per task type.

Gold-generation methods confirmed by the evaluation owner:

- source-derived: H1, H2, E1, E2, E3, E5;
- programmatic extraction from source records: H4;
- manual case/rubric design: H5 `clarify` and `escalate`.

Only README files are committed until the evaluation owner approves real data.
