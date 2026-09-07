# Claim–Evidence–Risk Registry — nemo-plan-repair-coverage

**Paper:** NEmo @ NeurIPS 2026, short track (4-page body).
**Framing:** implementation-led. The paper's contribution is a **working
recursive world-model self-repair loop** plus **two design rules** (R1 engineer
coverage not round count; R2 monitor for stalling not corruption); the
pre-registered factorial evaluation is what makes those rules trustworthy.
**Verdict:** MIXED. The coverage × repair-round **interaction is confirmed**;
the pre-registered **mechanism is refuted** and the pre-declared **falsifier
FIRED**. Both halves are in the abstract, and the boundary is stated explicitly
in the "What we claim, and what we do not" paragraph in §1.
**Evidence root:** `evidence/` — three per-arm ledgers plus the merged
`evidence/nemo_plan_repair_coverage_stamp_manifest.json` (192 rows, all
`verdict=SUPPORTED`, all cited by a `\StampedCell` in `main.tex`).
**Arm namespaces:** primary grid = unprefixed, supplementary single-error arm =
`n1::`, secondary LLM-proposer arm = `llm::`. Arms are never pooled.

## Registry

| # | Claim text (verbatim or close) | Type | Evidence (ledger rows / files) | Statistical treatment | Reviewer-objection risk | Limitation sentence location |
|---|-------------------------------|------|-------------------------------|-----------------------|------------------------|------------------------------|
| 1 | Verifier coverage × repair-round interaction on held-out plan-execution success is +0.530 | positive | `evidence/nemo_plan_repair_coverage_primary_ledger.jsonl` claim `primary::interaction_coverage_x_k` | seed-clustered bootstrap, 10,000 resamples, unit = seed; 95% CI [+0.447, +0.615] excludes zero | (1) "deterministic proposer, not an agent" — stated in Setup and Limitations; (2) "only 3 classical domains" — conceded in Limitations; (3) "interaction could be a corruption confound" — refuted by the k=0 control | Limitations, sentence 1 |
| 2 | Held-out success at k=4 rises from 0.1733 (c=0.2) to 0.9000 (c=1.0) | positive | same ledger, `success::c0.2_k4`, `success::c1.0_k4` | per-cell mean over 60 seed-paired runs; seed-clustered bootstrap CIs in the appendix ledger table | "low absolute success at low coverage" — conceded verbatim in Limitations | Limitations, last sentence |
| 3 | The interaction replicates in each domain computed alone (+0.56 / +0.60 / +0.43) | positive | `robustness::interaction_blocks`, `robustness::interaction_gripper`, `robustness::interaction_logistics` | per-domain seed-clustered bootstrap; all three CIs exclude zero | "driven by one easy domain" — pre-empted by the per-domain split | Limitations, sentence 1 |
| 4 | The k=0 coverage main effect is exactly 0.0000 (negative control) | diagnostic | `maineffect::coverage_at_k0`, `success::k0_baseline_pooled` | exact by design: at k=0 all five coverage arms hold the identical corrupted model; bootstrap CI [0.0000, 0.0000] | "was there leakage between arms?" — this row is the leak test | Results, "Rival mechanisms" paragraph |
| 5 | Divergence-event rates do not differ between coverage bands: 2/360 vs 3/360, gap +0.0028 | negative (falsifier fired) | `falsifier::divergence_events_low`, `falsifier::divergence_transitions_low`, `falsifier::divergence_events_high`, `falsifier::divergence_transitions_high`, `falsifier::divergence_rate_low`, `falsifier::divergence_rate_high`, `falsifier::divergence_gap_high_minus_low` | seed-clustered bootstrap; CI [−0.0056, +0.0111] **includes zero** and the point estimate has the wrong sign | "5 events is too few to conclude anything" — conceded verbatim in Limitations; we claim a bound, not a null | Limitations, sentence 3 |
| 6 | Model-edit distance moves toward ground truth in both bands (4.000 to 1.1833 high, 4.000 to 3.0167 low) | positive/diagnostic | `editdist::high_k0`, `editdist::high_k4`, `editdist::low_k0`, `editdist::low_k4` | means over 60 seed-paired runs; seed-clustered bootstrap CIs; the start value 4.000 is exact by construction | "edit distance is not task performance" — success is reported alongside it | Limitations, sentence 1 |
| 7 | The primary proposer is deterministic and search-based, not an LLM | diagnostic | `design::proposer`, `integrity::llm_calls`, `integrity::llm_errors`, `integrity::parse_failures` | none (design fact plus integrity counters, all zero for LLM activity) | "the paper implies an LLM drove the result" — explicitly denied in the abstract, Setup and Limitations | Limitations, sentence 2 |
| 8 | The LLM arm is underpowered and directional only (interaction +0.0625, lower bound touches zero) | negative/underpowered | `llm::primary::interaction_coverage_x_k`, `llm::design::n_seeds`, `llm::design::n_runs`, `llm::success::c0.8_k4`, `llm::editdist::high_k4`, `llm::editdist::low_k4` | seed-clustered bootstrap over 8 seeds; 95% CI [0.0000, +0.1875] **touches zero**, so the arm cannot resolve the interaction | "why report it at all?" — it tests whether the effect is a deterministic-proposer artifact, and its weakness is stated, not hidden | Limitations, sentence 2 |
| 9 | The supplementary single-error arm has an interaction of exactly 0.0000 by construction | diagnostic | `n1::primary::interaction_coverage_x_k`, `n1::design::n_runs`, `n1::maineffect::coverage_at_k1` | exact: with one seeded error the loop converges in round 1, so k=1, 2 and 4 are identical in all 100 runs | "post-hoc arm selection" — amendment A8 was made **before** the primary grid ran and is recorded in the design notes | Appendix, "The superseded single-error arm" |
| 10 | Budget exhaustion and no-plan counters are reported, not filtered | diagnostic | `integrity::budget_exhausted_train`, `integrity::budget_exhausted_eval`, `integrity::plan_calls`, `integrity::no_plan_train`, `integrity::no_plan_eval` | none (raw counters over 300 runs) | "divergence is really timeouts" — this is a pre-declared rival mechanism, measured | Results, "Rival mechanisms" paragraph |

## Abstract claims

**Required.** One row per material claim in the paper's abstract, mapped to the
stamp-manifest key(s) that support it. Gate 14 parses this section.

| # | Claim text (verbatim from abstract) | claim_id | Evidence locator |
|---|-------------------------------------|----------|-------------------|
| 1 | over 20 seeds and 3 IPC domains (60 seed-paired runs per cell, held-out instances) | `design::n_seeds`, `design::n_domains`, `design::runs_per_ck_cell` | `evidence/nemo_plan_repair_coverage_primary_ledger.jsonl` |
| 2 | the pre-registered interaction holds: +0.530 (95% seed-clustered bootstrap CI [+0.447, +0.615]) | `primary::interaction_coverage_x_k` | `evidence/nemo_plan_repair_coverage_primary_ledger.jsonl` |
| 3 | success at k=4 rises from 0.1733 at c=0.2 to 0.900 at c=1.0 | `success::c0.2_k4`, `success::c1.0_k4` | `evidence/nemo_plan_repair_coverage_primary_ledger.jsonl` |
| 4 | it replicates in blocks (+0.56), gripper (+0.60) and logistics (+0.43) | `robustness::interaction_blocks`, `robustness::interaction_gripper`, `robustness::interaction_logistics` | `evidence/nemo_plan_repair_coverage_primary_ledger.jsonl` |
| 5 | the k=0 negative control — the coverage main effect before any repair, not a success rate — is exactly 0.0000, raw success being identically 0.0133 at every coverage level | `maineffect::coverage_at_k0`, `success::k0_baseline_pooled` | `evidence/nemo_plan_repair_coverage_primary_ledger.jsonl` |
| 6 | Our declared falsifier fired: divergence events were 2 of 360 transitions at c below 0.4 against 3 of 360 at c above 0.8 | `falsifier::divergence_events_low`, `falsifier::divergence_transitions_low`, `falsifier::divergence_events_high`, `falsifier::divergence_transitions_high` | `evidence/nemo_plan_repair_coverage_primary_ledger.jsonl` |
| 7 | gap +0.0028 [-0.0056, +0.0111], covering zero and pointing the wrong way | `falsifier::divergence_gap_high_minus_low` | `evidence/nemo_plan_repair_coverage_primary_ledger.jsonl` |
| 8 | while edit distance to truth falls in both bands (4.00 to 1.1833 at high coverage, 4.00 to 3.0167 at low) | `editdist::high_k0`, `editdist::high_k4`, `editdist::low_k0`, `editdist::low_k4` | `evidence/nemo_plan_repair_coverage_primary_ledger.jsonl` |
| 9 | The proposer is deterministic and search-based, not a language model | `design::proposer` | `evidence/nemo_plan_repair_coverage_primary_ledger.jsonl` |
| 10 | a local LLM proposer failed the pre-declared throughput pilot and appears only as an underpowered 8-seed arm | `llm::design::n_seeds` | `evidence/nemo_plan_repair_coverage_llm_secondary_ledger.jsonl` |
| 11 | at c ≤ 0.4, 0.6062 of repair rounds propose an edit and accept none, against 0.1437 at c ≥ 0.8 | `stall::no_accept_rate_low`, `stall::no_accept_rate_high` | `evidence/nemo_plan_repair_coverage_primary_ledger.jsonl` |

The two design rules stated in §Results are restatements of rows 2--5 (R1,
backed additionally by `maineffect::coverage_at_k4` and `success::c0.4_k4`) and
rows 6--8 (R2, backed additionally by `integrity::no_accept_rounds`); both
resolve to the same manifest and introduce no new claim.

Every claim_id above is a key in
`evidence/nemo_plan_repair_coverage_stamp_manifest.json`, and every abstract
sentence carrying a number has a row. The two abstract sentences without
numbers — the opening framing sentence, and "Weak verification does not make
recursive repair amplify error; it makes the loop stop improving --- the
failure mode is stagnation, not self-poisoning" — are interpretations of rows
6, 7 and 8 and carry no independent numeric claim.

## Rival mechanisms / alternative explanations

The pre-declaration (`A2_PREDECLARATION_2026-09-07.md`) named three rival
mechanisms and one discriminator falsifier. All four are addressed in
`main.tex`, Results, in the paragraph "Rival mechanisms and alternative
explanations".

- **Corruption-severity confound** (low-coverage cells might carry harder
  corruptions) — eliminated by design and measured: the same seeded corruption
  is reused across every coverage level within a seed, and the k=0 column of
  Table 1 reads identically across all five arms, with the coverage main effect
  `maineffect::coverage_at_k0` exactly zero.
- **Repair-budget exhaustion** (apparent divergence is timeouts, not bad edits)
  — measured and reported, never dropped: `integrity::budget_exhausted_train`
  and `integrity::budget_exhausted_eval` against `integrity::plan_calls`, with
  `integrity::parse_failures` and `integrity::llm_errors` both zero under the
  deterministic proposer.
- **Planner stochasticity** (success drift unrelated to model quality) —
  bounded: one fixed planner configuration throughout, and the k=1 arm is a
  within-seed control whose coverage main effect `maineffect::coverage_at_k1`
  still covers zero.
- **Discriminator falsifier** — pre-declared as: *"if divergence events occur
  at the same rate in high-coverage (c >= 0.8) and low-coverage (c <= 0.4)
  cells, the coverage mechanism is falsified regardless of the interaction CI,
  and the paper says so."* **THE FALSIFIER FIRED.**
  `falsifier::divergence_rate_low` against `falsifier::divergence_rate_high`
  gives `falsifier::divergence_gap_high_minus_low` with a 95% CI of
  [−0.0056, +0.0111] that covers zero **and** a point estimate pointing the
  opposite way to the hypothesis. The paper says so in the abstract, in the
  Results section and in the conclusion: the pre-registered amplification
  mechanism did not occur, and the failure mode of under-verified recursive
  repair on these domains is **stagnation, not divergence**. The corroborating
  measurement is `editdist::low_k0` falling to `editdist::low_k4` — the
  low-coverage model moves *toward* truth, slowly and then not at all —
  against `editdist::high_k0` falling to `editdist::high_k4`.

## Amendments disclosed in the paper

| amendment | what changed | where disclosed |
|---|---|---|
| A1 | apparatus replaced (the first pre-declaration's executor does not exist on disk); re-declared before any data collection, zero rows carried forward | Setup, "Pre-registration and amendments"; Appendix A |
| A6 | proposer switched to the pre-declared deterministic fallback after the LLM failed the throughput pilot | Setup, "The proposer is not a language model"; abstract |
| A8 | corruption magnitude fixed at 4 by a hypothesis-blind rule after the earlier rule was found to force the interaction to zero by construction; caught before the primary grid ran; the executed runs kept as a labelled supplementary arm | Setup, "Pre-registration and amendments"; Appendix A |
| A9 | 337 apparent LLM parse failures were bugs in our own parser; all rows produced under it deleted and the arm re-run | Setup, "Pre-registration and amendments"; Appendix A |
| A10 | LLM arm discarded and re-run a second time under an exclusive writer lock after contamination by a stray pre-fix process | Appendix A |

## Per-citation aptness (load-bearing citations only)

- `huang2023llmcantcorrect` — supports "the closest rival in spirit:
  self-correction fails without an external oracle, attributed to oracle
  absence, a binary" because Huang et al. 2023 show LLMs cannot reliably
  self-correct reasoning without external feedback and frame the determinant as
  the presence or absence of an oracle rather than a graded quantity; our
  coverage fraction is the graded version of that variable.
- `aineto2019fama` / `aineto2022comprehensive` — support "FAMA ... acquires
  action models from observation sequences under full, partial or null
  observability as an offline batch constraint problem, reporting final model
  accuracy" because the FAMA framework compiles action-model learning into a
  constraint/planning task parameterised by the observability of the input
  traces and evaluates learned models by accuracy against the reference model;
  it has no notion of repair rounds, so no interaction with repair depth can
  exist there.
- `lightman2023verify` / `uesato2022process` — support "grade verifier quality
  as a property of a trained model class, where ours is a measured fraction of
  a condition space" because both compare process-supervised against
  outcome-supervised reward models and report that the choice of verifier model
  changes final solution selection; verifier completeness is not a measured
  continuous covariate in either.
- `brown2024monkeys` — supports "show sampling converts into accuracy only
  where a checker can select" because the paper's coverage-versus-accuracy
  analysis shows repeated-sampling coverage translates into solve rate in
  domains with an automatic verifier and degrades where sample selection must
  be heuristic.
- `helmert2006fastdownward` — supports "a Python planner in the lineage of Fast
  Downward ... over PDDL" because Fast Downward defines the translation and
  search architecture, and the FF-style heuristic family, that the pyperplan
  greedy best-first h^FF configuration reimplements in Python.
- `fox2003pddl21` — supports "over PDDL" because PDDL2.1 is the reference
  definition of the action-schema syntax and semantics (preconditions,
  add/delete effects) that our corruption operator and repair edits act on.
- `howey2004val` — supports "execution is adjudicated against M* in-process
  under the STRIPS semantics VAL validates" because VAL defines the standard
  plan-validation semantics for PDDL plans; we reimplement that adjudication
  in-process rather than shelling out, and say so.
- `dror2018hitchhiker` — supports the analysis sentence on seed-clustered
  bootstrap and the unit of independence because Dror et al. 2018 set out how
  to choose the resampling unit and report significance for paired comparisons;
  we follow it by resampling seeds and carrying every (c, k) cell of a
  resampled seed together.
- `chakraborti2017reconciliation` — supports "moves one agent's model toward
  another's ... agent-to-human, explanatory" because model reconciliation is
  defined there as producing minimal model updates that bring the human's model
  into agreement with the agent's plan; our direction is the reverse.
- `nguyen2017robust` — supports "hardens the planner against a fixed flawed
  model" because the paper's contribution is robust plan generation under a
  fixed incomplete domain model, not modification of that model.
- `valmeekam2023planning` / `valmeekam2023planbench` — support "LLMs plan
  poorly unaided" because both report low autonomous plan-generation validity
  for LLMs on IPC-style benchmark domains, which is why our primary proposer is
  symbolic.
- `stechly2024chain` — supports "which chain-of-thought does not repair"
  because the paper measures chain-of-thought prompting on planning tasks and
  finds the gains do not carry over, in contrast to the arithmetic and
  commonsense results of `wei2022chain`.

## Checklist

- [x] Every claim_id above resolves in the merged stamp manifest and its
      backing ledger row has verdict SUPPORTED
- [x] No bare prose percentage or ratio in the PDF lacks a stamped cell (guard
      gate 3, strict mode, passes with 0 violations). Bootstrap CI bounds are
      `\SafeNum` literals quoted from the `ci_low` and `ci_high` fields of the
      same ledger rows, because `analysis/build_manifest.py` does not export CI
      bounds as separate manifest keys and that file is not owned by the
      the manuscript.
- [x] CI includes-zero status noted for every CI (rows 5 and 8 above)
- [x] Reviewer-objection risk column filled for every registry row
- [x] Limitation sentence location cited for every registry row
- [x] Per-citation aptness filled for the load-bearing citations
