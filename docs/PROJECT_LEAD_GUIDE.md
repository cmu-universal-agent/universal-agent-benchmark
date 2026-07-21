# Universal Agent Benchmark — Project Lead Guide

Last verified: 2026-07-21 (Asia/Shanghai)

## Purpose

Use this file as the living project-lead entry point. It summarizes the current
phase, decision boundaries, ownership, gates, evidence, and recurring operating
workflow without relying on archived chat history.

This file is a navigation and coordination layer, not a replacement for source
code, approved schemas, dataset specifications, or GitHub review history.

## Canonical Locations

- Official repository: <https://github.com/cmu-universal-agent/universal-agent-benchmark>
- Canonical local checkout:
  `C:\Users\Jessica\Documents\Universal Agent\universal-agent-benchmark-git`
- Jessica's current branch: `jessica/infrastructure-schema-compat`
- Current WS2 Draft PR: <https://github.com/cmu-universal-agent/universal-agent-benchmark/pull/1>
- Stacked CrewAI PR: <https://github.com/cmu-universal-agent/universal-agent-benchmark/pull/2>
- Local working/reference directory, if still retained:
  `C:\Users\Jessica\Documents\Universal Agent\universal-agent-benchmark-working`

Do not resume work from Downloads copies or old repository clones. Confirm the
`official` remote before publishing.

## Information Precedence

When two sources conflict, use this order:

1. Current code, schemas, tests, and generated validation evidence in the
   canonical checkout.
2. Current official GitHub PR/branch state and explicit review comments.
3. Explicit owner decisions with a date and named decision-maker.
4. This guide's last-verified snapshot.
5. Workstream status documents and meeting notes.
6. Archived chats, downloaded attachments, and personal recollection.

Treat documents marked `draft`, `proposal`, `pending_approval`, or `preliminary`
as proposals or evidence, not decisions. Never silently convert a proposed
owner assignment or semantic mapping into an approved one.

## Proposal, Workplan, and Meeting-Note Index

The project does have an original proposal, a five-workstream workplan, dataset
and experiment-design notes, schema proposals, and newer workstream handoffs.
They were previously split between Codex attachments and repository documents.
Use this index instead of searching archived chats.

| Source | Type | What remains useful | Authority/status |
|---|---|---|---|
| Original “Project Direction” notes | Early proposal/meeting notes | Research question, Healthcare + E-commerce contrast, three selected frameworks, minimum H1/H2/H4/H5 and E1/E2/E3/E5 task set, shared stress-test ideas | Vertical/framework/minimum-task choices were adopted; early schema examples and framework hypotheses were superseded by implementation evidence. |
| Original five-workstream schedule | Baseline workplan | WS1 plan, WS2 agent setup, WS3 evaluation engine/data simulation, WS4 experiments, WS5 final deliverable; original team milestones | Useful roadmap baseline, not a current approval record. Dates and scope must be reconfirmed when later decisions differ. |
| “Proposed Team Structure” notes | Role proposal | Mickey as project lead; Jessica framework engineering; Chloe data evaluation; Xiaoxia visualization; Lanfang stress/failure analysis | Starting RACI only. Later explicit owner decisions and the ownership table in this guide take precedence. |
| Healthcare/e-commerce dataset mapping and experimental-design notes | Dataset/experiment proposal | Public dataset links, staged smoke/pilot/main design, preference for unique case coverage, three-repeat idea, fairness controls, contribution positioning | Dataset sources informed implementation. Case counts, repeats, scoring, and statistical claims are not final until approved. |
| `docs/schema_review_proposal.md` | Schema proposal | Field-level rationale and alternatives | Historical rationale; Chloe later confirmed no further pilot field adjustment was required. |
| `docs/dataset_gold_generation_plan.md` | Execution plan | Owner/engineering boundary, deterministic conversion sequence, audit rules | Active workflow, but some listed converter blockers are stale because PR #1 now contains all eight deterministic converters. |
| `docs/current_status_and_handoff.md` | WS2 handoff | Infrastructure history, coordination guidance, validation commands | Historical snapshot from 2026-07-16; use PR #1 and this guide for current completion status. |
| Local WS3 kickoff Word draft | Meeting agenda/proposal | WS2 closure decision, WS3 simulator scope, owner assignments, readiness/done gates | Local discussion draft, intentionally not published. This guide is the verified session-resume source until meeting decisions are recorded. |

Attachment provenance, retained only for traceability:

- Original workplan:
  `C:\Users\Jessica\.codex\attachments\1517643c-1d1c-4406-8308-13a00bef37b3\pasted-text.txt`
- Project direction notes:
  `C:\Users\Jessica\.codex\attachments\c76f76ff-611f-4c2c-ae1b-5ae4169f1459\pasted-text.txt`
- Proposed team structure:
  `C:\Users\Jessica\.codex\attachments\4906987f-ec4b-4030-a955-5042476670e9\pasted-text.txt`
- Dataset mapping plus experimental-design notes:
  `C:\Users\Jessica\.codex\attachments\b987404f-5c56-4f3c-aa5d-bec0f19d6dda\pasted-text.txt`
- Later concise dataset-link mapping:
  `C:\Users\Jessica\.codex\attachments\149e7584-b6ee-45dd-b052-b568dec3f763\pasted-text.txt`

### Original workplan reconciled with current status

| Original workstream | Original intent | Current interpretation |
|---|---|---|
| WS1 | Finalize project plan, industries, benchmarks, and task classification | Substantially complete: two verticals, three frameworks, and eight minimum task types selected. |
| WS2 | Infrastructure engine, framework setup, schemas, logging, stress/dashboard preparation | Jessica-owned engineering is complete and validated. H2, E3, and H5 owner review are closed. H4 v3 is implemented and awaits Chloe's regenerated eight-case review. Jessica explicitly placed PR #1 and stacked PR #2 on a no-merge hold until that review and final validation are complete. |
| WS3 | Evaluation engine development and validated simulation datasets | Proposed next focus is the shared tau-retail simulator/core, three thin wrappers, evaluator state, and initial stress coverage. Meeting approval and owners are still required. |
| WS4 | Experiment execution and framework integration | Formal experiment execution has not started. Preliminary smoke results are engineering checks only. |
| WS5 | Final report, dashboard, failure analysis, production-ready repository | Not started as a formal workstream; earlier documentation and report artifacts are inputs only. |

The original targets included a WS2 deliverable around 2026-07-21, a WS3
deliverable around 2026-07-28, experiment results around 2026-08-11, and final
delivery around 2026-08-18. Treat these as baseline planning targets until the
team reconfirms owners, scope, and dates.

## Current Executive Snapshot

### Repository and PR

As verified on 2026-07-21:

- The official repository is public and Jessica has push permission.
- Official `main` is at `15ebb8a`.
- Draft PR #1 is open and mergeable.
- PR #1 uses `jessica/infrastructure-schema-compat`; inspect the live PR for
  its current head rather than relying on a cached commit hash.
- PR #2 contains Mickey's CrewAI integration and is stacked on PR #1's branch.
  It remains separate and unmerged; do not retarget or integrate it before the
  agreed PR sequence.
- This guide and the WS2 owner-feedback batch are intended for that existing
  Draft PR, not a new pull request.
- Jessica's current instruction is **do not merge yet**. H4 v3 owner review and
  the final WS2 validation suite must finish first.

### Workstream 2

WS2 infrastructure and Jessica-owned implementation are complete and validated.
H2 and E3 were approved on 2026-07-20. Chloe approved all four H5 owner-authored
cases and rubrics on 2026-07-21. H4 v3 now incorporates Chloe's latest five
classes of feedback and awaits her review of the regenerated eight-case pack.
H4 is the only remaining WS2 semantic-review gate. WS3 planning may continue,
but PR #1 and stacked PR #2 remain unmerged.

The Draft PR contains:

- five compatible JSON Schemas and valid/invalid contract fixtures;
- shared legacy/v1 task loading and consistent `allowed_tools` enforcement;
- normalized adapter result metadata and tool traces;
- no-tool, tool-success, and tool-failure contract checks;
- deterministic converters for H1, H2, H4, H5, E1, E2, E3, and E5;
- Chloe's 2026-07-20 H2 owner decisions incorporated: review case 003 remains
  `urgent`, 004 remains `routine`, 005 changes to `routine`, and 008 changes to
  `self_care`; urgency-label review is complete and the converter uses a local,
  gitignored evaluator decision file. Chloe gave no recommendation to adjust
  the measured difficulty output (easy=90, medium=10, hard=353); Jessica chose
  to retain it provisionally and revisit it later, so it does not block H2;
- Chloe's H4 v2 corrections plus the 2026-07-21 v3 corrections incorporated:
  secondary history-header stripping, honorific-safe sentence splitting,
  retention of short same-line clinical statements, always-on HPI symptom
  supplementation, and infection/lingering-cold symptom coverage;
- Chloe's four H5 owner-authored cases incorporated locally: two `clarify` and
  two `escalate`; Chloe approved all four rubrics on 2026-07-21. Exact
  prompts/gold/rubrics remain gitignored and evaluator-only;
- Chloe's E3 decision recorded: every scenario containing
  `cancel_pending_order` is excluded from the E3 candidate pool and must not be
  mapped to `refund_allowed`;
- validated local preparation for 64 agent-visible review cases and 64
  evaluator-only gold records, with one-to-one linkage and no detected leakage;
- deterministic split manifests, coverage reporting, cache validation, and
  list-only runner discovery;
- strict task-specific output-schema validation and the
  `output_schema_invalid` failure mode;
- a preliminary before/after technical smoke report.

These are infrastructure and contract results, not benchmark scores.

### Preliminary Technical Smoke

The report at `results/preliminary_technical_smoke_20260717.md` records one
21-call baseline and one 21-call after-fix repeat across seven tasks and three
frameworks:

- runtime success: 21/21 to 21/21;
- valid JSON: 21/21 to 21/21;
- strict task output schema: 12/21 to 20/21;
- medical strict output schema: 3/12 to 12/12;
- the H1/H4/H5 string-boolean defect was not observed after the prompt fix;
- one E3 top-level field-placement drift remained and was correctly detected.

Interpret “one remaining failure” only as one strict output-schema failure, not
a runtime failure. Do not use single-run latency, token counts, or outputs to
rank frameworks.

### Workstream 3

WS3 is currently a proposed coordination phase, not an approved implementation
assignment. The proposed goal is a framework-neutral tau-retail simulator/core
contract with thin wrappers for CrewAI, LangGraph, and the OpenAI Agents SDK.

The local kickoff Word document is a discussion draft and is intentionally not
published. Its proposed ownership and scope require meeting confirmation. Use
the session-start checklist below rather than assuming its proposals were
accepted.

## Scope and Terminology

The minimum pilot contains eight task types:

- Healthcare: H1, H2, H4, H5
- E-commerce: E1, E2, E3, E5

“Eight tasks” means eight task types, not eight total records. The current local
review preparation uses eight cases per task type, for 64 cases total. The
older 20 legacy-compatible cases mainly cover H1 and E1 and remain compatibility
fixtures rather than full eight-task coverage.

## Decision Boundaries

### Jessica may proceed without another owner's semantic decision

- maintain schemas and validation without changing approved field meaning;
- fix adapter, runner, case-ID, metadata, and output-schema contract defects;
- implement deterministic converters from approved rules;
- apply Chloe's approved E3 `cancel_pending_order` candidate exclusion;
- generate review samples, coverage reports, split manifests, and leakage
  checks;
- run offline contract, cache, schema, and list-only checks;
- run clearly labelled technical smoke tests when costs and scope are already
  authorized;
- prepare status reports, meeting agendas, handoffs, and Draft PR updates;
- preserve evaluator-only gold and secrets outside agent prompts and Git.

### Jessica must not decide for another owner

- dataset/gold semantics, ambiguous label mappings, or scoring correctness;
- H2 lower-urgency interpretation;
- H4 clinical extraction meaning or audit acceptance;
- H5 clarify/escalate content and rubric;
- final E5 success/final-state semantics;
- stress taxonomy owned by Lanfang;
- framework-specific ownership or delivery commitments not accepted by the
  named owner;
- final benchmark rankings, publishable scores, or claims of framework
  superiority.

When blocked by one of these decisions, prepare the smallest review artifact
and ask the owner to approve the rule. Do not ask them to perform bulk
conversion or manual labeling when code can do it deterministically.

## Ownership and Open Decisions

| Area | Current/likely owner | Status and required action |
|---|---|---|
| Project coordination, converters, cross-framework validation | Jessica | Confirm WS3 scope before accepting additional implementation ownership. |
| Dataset/gold semantics | Chloe | H2 urgency labels and the E3 pending-order exclusion are confirmed. H5's four owner-authored cases/rubrics are approved. Review the regenerated H4 v3 eight-case pack; this is the only remaining WS2 semantic gate. E5 final-state semantics remain a separate WS3 readiness decision. |
| CrewAI wrapper | Mickey | CrewAI PR #2 is implemented as a stacked change with offline contract coverage. Live-model smoke, native Linux/CI confirmation, and E5 shared simulator integration remain external gates. CrewAI-specific ownership does not imply shared-core ownership. |
| Stress scenarios and failure taxonomy | Lanfang | Confirm initial scenarios, expected failures, and test requirements. |
| Dashboard/visual reporting | Xiaoxia | Confirm whether retained in WS3 or managed as a separate stream. |
| Shared tau-retail simulator/core contract | Unassigned | Assign one named owner and reviewer. Do not default this to Mickey. |
| LangGraph tau-retail wrapper | Unassigned | Assign one named owner after the shared contract is frozen. |
| OpenAI Agents SDK tau-retail wrapper | Unassigned | Assign one named owner after the shared contract is frozen. |
| Repository merge/review | Repository maintainers | Honor the current no-merge hold. Review PR #1 and stacked PR #2 only after H4 v3 approval and final WS2 validation. |

## Gates

### WS2 closure gate

The earlier carry-over path was superseded by Jessica's explicit 2026-07-21
instruction to **not merge yet**. PR #1 remains Draft and PR #2 remains a
separate stacked change until H4 v3 owner review and final validation complete.

Completed closure evidence:

- H2 urgency labels recorded as approved after review of 003/004/005/008; its
  difficulty rule is explicitly retained as provisional and deferred for later
  calibration, satisfying the current H2 gate;
- E3 pending-order exclusion reflected in the converter and coverage report;
- H5 four-case owner review recorded as approved on 2026-07-21;
- final offline validation passes for 64 cases and 64 evaluator-only gold
  records with zero detected leakage.

Named carry-overs:

- Chloe: review the regenerated H4 extraction v3 eight-case pack;
- repository maintainers: review PR #1 and ensure its description and
  limitations match the approved scope, then review stacked PR #2 in the agreed
  sequence. Do not merge either PR while the hold is active.

## Workstream 3 Session Start Checklist

On the first WS3 task:

1. Inspect official PR #1, stacked PR #2, and `main`; do not rely on the last
   snapshot here.
2. Do not add WS3 implementation commits to the WS2 feature branch. Confirm
   whether WS3 starts from merged `main` or from an explicitly accepted
   dependency branch.
3. Name one owner and one reviewer for the shared tau-retail simulator/core.
4. Name owners for the CrewAI, LangGraph, and OpenAI Agents SDK thin wrappers.
5. Approve the canonical tool/state/reset/error contract and minimum fixtures.
6. Resolve evaluator-visible E5 final-state semantics before scoring live runs.
7. Keep H4 v3 review separate from WS3 engineering; H5 is closed. H4 blocks WS2
   merge and semantic freeze, not contract-design discussion.

### WS3 definition of ready

- shared simulator/core owner and reviewer named;
- CrewAI, LangGraph, and OpenAI wrapper owners named;
- canonical tool/state contract approved;
- E5 gold and evaluator-visible final-state semantics identified;
- minimum fixtures and controlled-run matrix approved;
- branch/PR integration sequence agreed.

### WS3 definition of done

- deterministic simulator reset, mutation, error, and leakage tests pass;
- all three wrappers pass identical no-tool, success, failure, invalid-argument,
  and state-transition contracts;
- normalized traces and final state validate against the agreed schemas;
- one controlled E5 technical smoke passes through each framework;
- limitations are documented and results remain technical validation until the
  approved benchmark protocol is run.

## Standard Operating Workflow

### Start of every project session

1. Use the canonical checkout, not a downloaded copy.
2. Inspect `git status` before editing and preserve unrelated user changes.
3. Read this guide and the documents relevant to the current workstream.
4. Fetch or inspect official GitHub state when PR, ownership, or integration
   status matters.
5. Separate confirmed decisions from proposals and stale documents.
6. State what can proceed autonomously and what requires an owner's decision.

### Before implementation

1. Identify the owner of any semantic or shared-contract decision.
2. Confirm the task is infrastructure, approved conversion, or owner review.
3. Define the smallest deterministic validation that proves the change.
4. Avoid changing shared schemas, adapters, or runners in parallel without
   coordination.

### Before publishing

1. Run checks proportional to the change.
2. Review the exact diff and stage named files only.
3. Never commit `.env`, virtual environments, dataset caches, raw HealthBench
   records/canaries, evaluator-only generated gold, raw outputs, traces, or
   generated metrics.
4. Push to the official repository, not the old personal repository.
5. Keep preliminary smoke results explicitly labelled “not benchmark scores.”

### End of every project session

Update this guide only when the verified snapshot, owner, decision, gate, or
canonical location changes. Add the verification date and evidence link or
commit. Do not copy full meeting transcripts into this file.

Use this handoff structure:

```text
Outcome:
Evidence/commit/PR:
Confirmed decisions:
Completed work:
Open owner decisions:
Unassigned work:
Safe next actions for Jessica:
Tests run and results:
Files intentionally kept local:
```

## Validation Commands

From the canonical repository root:

```powershell
& ".\.venv-openai\Scripts\python.exe" ".\scripts\validate_contract_fixtures.py"
& ".\.venv-openai\Scripts\python.exe" ".\scripts\validate_adapter_contracts.py"
& ".\.venv-openai\Scripts\python.exe" ".\scripts\validate_shared_tool_contracts.py"
& ".\.venv-openai\Scripts\python.exe" ".\scripts\validate_core_dataset_caches.py"
& ".\.venv-openai\Scripts\python.exe" ".\scripts\validate_core_pilot.py" --expected-per-task 8
& ".\.venv-openai\Scripts\python.exe" ".\scripts\run_benchmark.py" --task ".\data\generated\core_pilot\cases" --list-only
```

Do not run live model calls merely to refresh status. Run them only for a
defined technical question with a stable experiment ID and an explicit
non-scoring label.

## Detailed References

- WS2 historical handoff: `docs/current_status_and_handoff.md`
- WS2 scope summary: `docs/workstream_2_summary.md`
- Dataset preparation: `docs/core_pilot_data_preparation.md`
- Dataset/gold workflow: `docs/dataset_gold_generation_plan.md`
- Schema field history: `docs/schema_field_review.md`
- Schema proposal: `docs/schema_review_proposal.md`
- Framework rationale: `docs/framework_comparison_rationale.md`
- Preliminary smoke report:
  `results/preliminary_technical_smoke_20260717.md`
- Local WS3 kickoff Word draft (updated locally on 2026-07-21; intentionally
  not published or committed):
  `docs/workstream_3_kickoff_meeting_20260721.docx`

Some historical documents were last updated before the eight converters and
strict output-schema validation were completed. Use them for rationale and
history, not as the current executive snapshot.
