# Universal Agent Benchmark Experiment Report

## Claim status

- Experiment ID:
- Formal experiment commit:
- Protocol version:
- Gate status: `experiment_ready | technical_smoke_only`
- Freeze timestamp and approver:

No result may be described as a formal benchmark unless the frozen-manifest,
evaluator, environment, and 24-run preflight gates all passed before execution.

## Frozen configuration

| Item | Frozen value | Evidence |
|---|---|---|
| Model/provider/version | | |
| Temperature/max output/seed | | |
| Run and token budgets | | |
| Case manifest and SHA-256 | | |
| Evaluator versions and SHA-256 | | |
| Framework/package versions | | |
| Timeout | | |
| Output root | | |
| Rerun policy | | |

## Architecture and implementation

- Unified runner:
- Shared E5 routing:
- E5 response-contract evaluator:
- E5 final-state replay:
- Deterministic H1/H2/H4/H5/E1/E2/E3 metrics:

## Reproducibility

- Environment build and validation commands:
- Python and package versions:
- Manifest/gold isolation:
- Randomness controls:
- Artifact inventory:

## Calibration / preflight

| Task | OpenAI Agents SDK | LangGraph | CrewAI | Gate |
|---|---|---|---|---|
| H1 | | | | |
| H2 | | | | |
| H4 | | | | |
| H5 | | | | |
| E1 | | | | |
| E2 | | | | |
| E3 | | | | |
| E5 | | | | |

Expected attempts: 8 tasks × 3 frameworks = 24, excluding documented,
policy-permitted infrastructure reruns.

## Main experiment results

- Planned runs:
- Completed logical runs:
- Errors and permitted reruns:
- Exclusions:
- Aggregate metrics:
- Framework comparison:

## Targeted repeats

- Selection rule and case IDs:
- Planned/completed runs:
- Repeat outcomes:

## Deviations and rerun ledger

Every post-freeze change receives a new version, reason, affected scope, owner
approval, and repeated preflight evidence. Original attempts remain immutable.

| Timestamp | Logical run | Attempt | Reason | Disposition | Artifact |
|---|---|---:|---|---|---|
| | | | | | |

## Limitations and claim boundary

- Protocol limitations:
- Evaluator limitations:
- Provider/model limitations:
- External-validity limitations:

## Technical-method appendix

### Case selection and gold

### Runner and framework parity

### Evaluator definitions

### E5 simulator and state validation

### Environment lock and commands

### Artifact checksums

### Failure taxonomy and adjudication
