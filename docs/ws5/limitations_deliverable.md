# Limitations and Claim Boundary — Lanfang Deliverable (WS5)

Status: **Ready for Mickey to paste into `experiment_report_skeleton.md`**
Owner: Lanfang Hai
Prepared: 2026-08-18
Protocol anchor: `docs/formal_benchmark_protocol_v2.0.md` (`pilot-60-v2.0` prospective
formal controlled pilot)

Paste target: report section **Limitations and claim boundary** (delta only; do not
overwrite the live scaffold's frozen-configuration table).

**Mickey — tense rule:** Formal v2.0 controlled-pilot execution and scoring are
complete (228/228 logical runs; H5 annotations 30/30), and Chloe approved C1–C6.
Use past tense and the public protocol label and formal execution commit recorded
in the scaffold; keep the private experiment ID local. Align numeric values with
the scaffold **Frozen configuration** table (for example requested maximum output
tokens `4096`, temperature `0`, requested seed `42`). Public release remains a
separate final authorization.

---

## Claim boundary (summary paragraph)

This report describes a **controlled 60-case pilot** executed under a frozen
protocol, evaluator semantics, and single-model configuration. It supports
narrow, task-specific observations about agent-framework behavior on approved
fixtures. It does **not** establish general deployment readiness, clinical
validity, market forecasting accuracy, or an overall best agent framework.
No composite score or framework championship is reported.

Results are **scored under one pinned formal experiment ID**, and C1–C6 are
owner-approved. Publication remains subject to explicit public-release
authorization. All v1.x and preliminary engineering-smoke attempts remain
**`technical_smoke_only`** and are excluded from v2.0 denominators, repeats,
claims, and failure-analysis numerators.

---

## Protocol limitations

**Scope and sample size.** The controlled pilot contains 60 frozen cases: eight
each for H1, H2, H4, H5, E1, E2, and E3, plus four owner-approved E5 cases.
Execution produces 228 controlled-pilot logical runs (180 main-pilot plus 48
additional targeted repeats on eight representative cases), separate from 24
readiness preflights. This is not a 400-case benchmark, a longitudinal study, or
a representative sample of real-world task traffic.

**Representative repeats.** Each of the eight frozen representative cases (`*-REVIEW-001`
and formal `E5-001`) is observed three times per framework (main-pilot plus two
targeted repeats). These repeats measure **run-to-run stability under a fixed
protocol**, not confidence intervals over a large case pool. Stable repeats are
informative; they do not prove robustness to new cases or providers.

**Execution identity.** A logical run is identified by experiment ID, case ID,
framework, and repeat number. Attempt 2 within a logical run is permitted only
for one documented infrastructure failure after human eligibility review. Retries
motivated by low scores, unsafe answers, or poor tool choice are excluded from
aggregate analysis and must not be used to support comparative claims.

**Post-freeze changes.** Any change to cases, evaluator-only gold, prompts,
runner code, dependencies, or model configuration after freeze requires a new
protocol version, owner approval, repeated affected preflights, and an entry in
the rerun ledger. Unaffected aggregates remain tied to the prior frozen record.

**Stress testing.** Deliberate stress variants (tool failure injection, long
context, adversarial policy traps, repeated-run stress suites) were **out of
scope** for formal delivery. Incidental failures during the controlled pilot may
be documented as isolated case studies but must not be merged into standard
accuracy tables.

---

## Evaluator limitations

**Task-specific metrics.** H1, H2, H4, H5, E1, E2, and E3 use owner-approved,
task-specific deterministic or rubric-backed semantics. Metrics are reported
separately by task; they are not combined into a single composite score.

**H4 extraction.** Gold fields are produced by approved programmatic extraction
rules and scored by exact normalized-set overlap. Model outputs were not generally
empty even though the frozen component scores were zero, so the report must not
describe this result as an absence of extracted content or assign a single causal
root without further semantic review.

**H5 hybrid scoring.** H5 combines owner-approved human criterion annotation with
deterministic `h5-scoring-rule-v1` aggregation. Failure analysis must not treat
one criterion mismatch as a full model failure without evaluator review. Criterion
text and safer-alternative guidance remain private audit material.

**E5 dual gate.** E5 pass requires both (a) response-contract satisfaction on
user-facing assistant content and (b) identical agent-DB and user-DB hashes after
independent final-state replay under semantics v0.3. Partial user-visible success
without state match is a failure. Harness or runtime errors (`error`) are distinct
from agent-caused failures (`fail`). A framework sweep with more than five percent
final-attempt errors is invalidated for that framework under the frozen E5 policy.

**Symptom vs attribution.** The report/metrics layer derives a primary
`failure_mode` via `adapter/evaluator.py` when building scored outputs; it is not
stored as a field in the result JSONL. E5 rows use v0.3 failure classes instead.
Case-study root-cause categories (model, framework adapter, evaluator,
infrastructure, protocol) are applied separately for narrative analysis.
Suspected gold or rubric issues are escalated to the evaluation owner rather than
resolved by relabeling in WS5.

**Aggregate tables.** Aggregate symptom or root-cause counts in the report use
definitions approved by the evaluation owner. WS5 case studies do not substitute
for those tables.

---

## Provider and model limitations

**Single model snapshot.** All formal pilot agent runs use one frozen agent model
configuration (`gpt-4o-mini` through the frozen OpenAI-compatible provider) with
temperature `0`, requested maximum output tokens `4096`, and requested seed `42`
(record null/unsupported where the provider does not honor seed). E5 user-simulator
turns use the same model family under pinned simulator controls with the same
generation caps. Observed framework differences
therefore confound orchestration/runtime behavior with a **single model and
provider snapshot**; they do not prove superiority of any framework across models,
providers, or time.

**Seed and caps.** Requested seeds and maximum output tokens are recorded; null or
unsupported provider behavior is documented rather than simulated. Token usage and
latency depend on provider reporting and adapter verbosity.

**Timeouts.** The per-attempt cap is 300 seconds. Timeout may reflect model
verbosity, deep tool loops, simulator contention, or infrastructure limits;
case-level attribution is required before describing a timeout as a model weakness.

---

## External-validity limitations

**Healthcare tasks.** H1, H2, H4, and H5 cases use synthetic or public-derived
review scenarios. They evaluate structured agent behavior on fixed fixtures; they
are not validations of clinical decision support in real care settings.

**E-commerce and retail tasks.** E1 and E2 use historical Amazon review aggregates;
E3 and E5 use pinned tau-retail simulator snapshots. These fixtures do not represent
live market conditions, real customer operations, or adversarial user behavior.

**Tool use in fixtures.** Many cases embed required evidence in the prompt; zero tool
calls can be expected on those cases. Framework tool orchestration on E5 and other
tool-heavy paths is evaluated only where the frozen case design requires tools.

**Offline wrapper evidence.** Three-framework retail wrapper parity and offline
contract evidence validate integration plumbing. They do not by themselves prove
live multi-turn robustness under production load or distribution shift.

**Environment heterogeneity.** If any framework sweep executed on a non-canonical
host (for example platform-specific dependency constraints), environment differences
may interact with framework behavior; such context belongs in limitations rather
than silent cross-host comparisons.

---

## What this report may and may not claim

| Permitted | Not permitted |
|---|---|
| Task-specific pass/fail patterns on frozen cases | Overall best framework |
| Documented failure modes with case IDs and frameworks | Full robustness or stress coverage |
| Repeat stability on representative anchors | Clinical or financial deployment advice |
| Infrastructure vs model attribution when evidenced | Use of v1.x smoke as benchmark scores |
| Explicit evaluator or protocol boundary cases | Composite or championship rankings |
