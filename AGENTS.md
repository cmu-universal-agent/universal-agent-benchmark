# Repository working rules

Keep changes easy for another teammate to review.

## Scope

- Start each task with one concrete outcome and the smallest acceptance test.
- Change only files required for that outcome.
- Do not add optional frameworks, reports, abstractions, compatibility layers,
  or follow-up tooling unless the task explicitly requires them.
- If the change starts solving a second problem, stop and record it as a
  follow-up instead of implementing it.

## Readability

- Prefer direct code and existing helpers over new infrastructure.
- Keep entry points orchestration-only; put each distinct operation in a
  plainly named function.
- Use domain terms from the benchmark (`case`, `task`, `framework`, `run`,
  `evaluation`) and avoid generic layers with unclear ownership.
- Add comments only for non-obvious constraints or approved semantic rules.
- Do not change owner-approved dataset or gold semantics during refactoring.

## Review gate

Before handing off any change:

1. Inspect `git diff --stat` and the exact diff.
2. Explain why every changed file is necessary.
3. Remove dead code, debugging output, speculative options, and duplicate
   documentation.
4. Run the smallest relevant offline tests; do not make live model calls just
   to validate a refactor.
5. Call out any remaining file over 500 lines or function over 60 lines that
   the change made longer.
