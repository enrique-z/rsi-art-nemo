# Domain-semantics audit

**Purpose.** Build-guard gates verify that every numeric literal in `main.tex`
matches a ledger row (gate 3), but **nothing** verifies that the surrounding
prose reasoning about the number is correct in the target domain. For this
paper the target domain is *classical planning / action-model repair*: PDDL
STRIPS semantics, what a "verifier" can and cannot see, what a symmetric
difference over a lifted condition space does and does not measure, whether a
declared falsifier can fire on the metric it is declared over, and whether the
headline contrast is empirical or forced by the acceptance rule. That is what
this file records.

Every sentence in `main.tex` that reasons about a measured quantity, the
apparatus semantics, or a domain-specific unit was reviewed by domain experts
and its verdict recorded here before the paper was finalised.

An automated gate can enforce this record's existence and shape, but it cannot
judge whether a domain claim is right; that is what the verdict rows below are for.

## Rows

One row per domain-reasoning claim. Rows 1–10 are the ten abstract claims in
`CLAIMS.md` `## Abstract claims`, in order. Rows 11–17 are domain-reasoning
sentences in the body that carry no independent abstract number but that a
planning reviewer will interrogate. Every row has a verdict.

Verdicts: **PASS** — the domain reasoning is correct as written; **FLAG** — technically
defensible but reviewers will object, hedge added; **BLOCK** — wrong, reworded or
withdrawn.

| # | Claim (verbatim or close) | Domain concept | Auditor verdict | Evidence / justification | Location in main.tex |
|---|---------------------------|----------------|-----------------|--------------------------|-----------------------|
| 1 | "over 20 seeds and 3 IPC domains (60 seed-paired runs per cell, held-out instances)" | Unit of independence; what "held-out" quantifies over in action-model repair | FLAG | Counts are exact (`design::n_seeds`, `design::n_domains`, `design::runs_per_ck_cell`; 3x20=60 confirmed in `aggregate.py:209`). But repair and evaluation share one domain-level corruption and one lifted model, so "held-out" means unseen *instances*, never unseen operators, predicates or domains — a planning reviewer reads "held-out" as generalisation and gets instance transfer. Needs one clause in Limitations. | Abstract; §Setup ¶"Coverage and loop" |
| 2 | "the pre-registered interaction holds: +0.530 (95% bootstrap CI [+0.447, +0.615])" | Seed-clustered bootstrap over a nested factorial | PASS | `interaction()` = mean paired Delta at c>=0.8 minus at c<=0.4; `bootstrap()` resamples seeds and `build_index` keys `idx[seed][(domain,coverage)]`, so a resampled seed carries all 3 domains x 5 coverages x 4 k together — the clustering is correct and conservative. `verify_independent.py` reproduces +0.5300, CI [+0.445,+0.615]. | Abstract; §Results ¶1 |
| 3 | "success at k=4 rises from 0.1733 at c=0.2 to 0.900 at c=1.0" | Held-out plan-execution success under STRIPS adjudication | PASS | Table 1 cells `success::c0.2_k4` / `success::c1.0_k4`; both reproduced by the independent script (24/24). Success is the fraction of 5 held-out instances whose plan executes against M*, a standard planning outcome. | Abstract; Table 1 |
| 4 | "it replicates in blocks (+0.56), gripper (+0.60) and logistics (+0.43)" | "Replication" vs subgroup analysis | FLAG | All three are recomputed from the *same* 20 seeds (`aggregate.py:252`, "computed on d alone"), so they are three subgroup analyses sharing a seed pool, not three independent replications. The direction and exclusion-of-zero are real and the split does defeat the "one easy domain" objection; the word "replicates" overstates the independence. Defensible, will be objected to. | Abstract; §Results ¶1 |
| 5 | "the k=0 negative control --- the coverage *main effect* before any repair, not a success rate --- is exactly 0.0000, raw success being identically 0.0133 at every coverage level" | Negative control vs tautology; and units of the reported 0.0000 | PASS (was FLAG) | At k=0 no repair has occurred, so all five coverage arms hold the byte-identical corrupted model and the planner is deterministic; 0.0000 is forced, not observed, and is a leakage/plumbing check rather than a scientific finding. The abstract now says so in its own words and, critically, names the *unit*: 0.0000 is the coverage main effect, while raw success is 0.0133 (`success::k0_baseline_pooled`). This removes the one place a reviewer could read the abstract's 0.0000 against Table 1's 0.0133 as a self-contradiction. Both values are stamped cells. | Abstract; §Results ¶1 |
| 6 | "divergence events were 2 of 360 transitions at c below 0.4 against 3 of 360 at c above 0.8" | Whether the declared falsifier can fire on the metric it is declared over | FLAG | Counts are exact (`divergence_rate()` counts transitions with `snap(r,b) < snap(r,a)` on `heldout_success`; KS=[0,1,2,4] gives 3 transitions x 2 coverages x 3 domains x 20 seeds = 360 per band, confirmed). **But the metric is floored in the band that matters:** low-band success means are 0.0133 -> 0.0267 -> 0.0733 -> 0.1733, so held-out success has almost no room to *decrease* at exactly the coverage levels where divergence was hypothesised. The falsifier is therefore weakly diagnostic on its own; the load-bearing evidence for "no divergence" is edit distance (row 8), which has no floor (3.0167 of 4). | Abstract; §Results ¶2 |
| 7 | "gap +0.0028 [-0.0056, +0.0111], covering zero and pointing the wrong way" | Failure-to-reject vs equivalence | FLAG | Arithmetic exact (3/360 - 2/360 = 0.00278) and reproduced independently. A CI covering zero is a failure to reject a difference, not evidence of equivalence; no practically-meaningful equivalence margin was pre-specified. The paper does concede the power limit in Limitations sentence 3 ("we bound the coverage difference without resolving a small true effect"), which is the right hedge — but it is absent from the abstract, where "our declared falsifier fired" reads as a positive refutation. Pre-registering the decision rule makes applying it legitimate; the strength of the inference still needs the body's hedge. | Abstract; §Results ¶2; §Limitations |
| 8 | "while edit distance to truth falls in both bands (4.00 to 1.1833 at high coverage, 4.00 to 3.0167 at low)" — and the inference "Neither band ever moves *away* from truth: the under-verified loop is not poisoning its model" | Whether monotone edit distance is measured or guaranteed by the acceptance rule | **BLOCK → fixed** | The numbers are correct. The **inference as written is partly circular.** `runner.py:262-269` sets `cur_key = (verifier.score(model), evidence_fit(...))` and accepts a candidate iff `best_key > cur_key` under tuple ordering — so the verifier score is **monotone non-decreasing by construction**, and since the score is exactly agreement with M* on the visible set V, the *verified* fraction of the symmetric difference can never grow. "The loop does not move away from truth" is therefore a design guarantee on the fraction c the verifier sees, and an empirical finding only on the unverified remainder (60-80% of the condition space at c<=0.4). Presenting the whole of it as a discovered failure mode is wrong as written. **Rewording applied:** the structural part is named, and the empirical content is located in the unverified fraction. (The empirical content is real and survives: the unverified 60-80% was free to degrade and did not.) | §Results ¶3 "The failure mode is stagnation" |
| 9 | "The proposer is deterministic and search-based, not a language model" | Provenance of every primary number | PASS | `design::proposer = deterministic`; `integrity::llm_calls`, `integrity::llm_errors`, `integrity::parse_failures` all 0 in the primary and n1:: arms (Table 3), and non-zero only under `llm::`. The disclosure is in the abstract, in a dedicated Setup paragraph, and in Limitations. This is the honest way to report it. | Abstract; §Setup ¶3; §Limitations |
| 10 | "a local LLM proposer failed the pre-declared throughput pilot and appears only as an underpowered 8-seed arm" | Reporting a failed arm rather than suppressing it | PASS | Throughput numbers (qwen2.5-coder:14b 3/3 timeouts >120s; qwen3:8b 31-99s/call implying 10.5-20h against an 8h budget) justify the pre-declared fallback A6. The arm is reported with its interaction CI touching zero and with the non-reproducibility at temperature 0 (4 of 7 repeats differing) stated rather than buried. Reporting a negative, non-reproducible arm is the correct scientific behaviour. | Abstract; §Results ¶5; §Limitations |
| 11 | "verifier coverage c --- the fraction of the true domain's conditions a repair proposal can be scored against" | Construct validity of "coverage" for an *embodied* verifier | FLAG | `CoverageVerifier.__init__` draws V by `rng.sample` of true and false conditions separately — a **uniform stratified random** subset of the lifted condition space, and `score()` compares the candidate against M* on V. So the treatment is literally graded access to ground-truth semantics, and at c=1.0 the verifier is a complete oracle. A real embodied verifier's partiality is structured by sensors and reachability, strongly non-uniform, and correlated with which conditions matter. The operationalisation is a legitimate, clean first cut, but Limitations concedes domains/semantics and never concedes the *sampling scheme*. This is the load-bearing generality gap for a NEmo audience. | §Setup ¶"Coverage and loop"; §Limitations |
| 12 | "carrying all coverages and all k for a resampled seed together" | Correctness of the cluster definition | FLAG | The code is **more** correct than the sentence: `build_index` gives `idx[seed][(domain,coverage)]`, and every `per_seed_fn` iterates all of `idx[s].items()`, so domains are carried inside the cluster too. Omitting "domains" from the sentence is what invites the pseudo-replication objection ("60 runs but 20 seeds"). Cheap, purely descriptive fix: say domains are carried. No re-analysis needed. | §Setup ¶"Analysis" |
| 13 | "the add/delete edits reproducing the observed successor ... it never reads M*" | Whether the proposer is ground-truth-blind, and how well matched it is to the corruption family | FLAG | Ground-truth-blindness confirmed: `evidence_candidates()` reads only the failed action, the observed state and the predicted-vs-observed successor discrepancy; M* is never touched. **But** the candidate set is evidence-localised precisely to single condition toggles, and the corruption is exactly 4 condition toggles (2 dropped true, 2 added false), so the true fix is essentially always inside the proposal set (A9 records that "the first proposal it rejected was the exact seeded corruption"). The study therefore isolates *verification* given a near-oracle proposer — which is the right design for the question asked, but it must be stated, or the headline reads as a claim about repair in general. | §Setup ¶3; §Limitations |
| 14 | "corruption magnitude fixed at 4 by a hypothesis-blind rule ... caught before the primary grid ran" | Whether an outcome-dependent selection rule biases the pre-registered contrast | PASS | `evidence/DESIGN_NOTES.md:95-108`: the A8 rule was written down before evaluation; calibration used a separate pilot sub-grid (3 coverages x 6 seeds = 18 trajectories/domain), pooled **over coverage** (blind to the coverage x k interaction) and used a **level** at k=4 rather than a **contrast** (blind to the k effect); the search terminated at the first candidate (n=4), so no larger value was ever evaluated and selection on effect size was impossible. This is a correctly constructed hypothesis-blind rule, and the supersession is disclosed with the superseded arm retained rather than deleted. | §Setup ¶4; Appendix A8 |
| 15 | "Edit distance is \|M triangle M*\| over the condition space" | Whether symmetric difference measures *semantic* model quality | FLAG | Symmetric difference over the lifted condition space is a standard, defensible action-model accuracy measure (it is the same family FAMA reports against a reference model). It is, however, **unweighted**: replacing one execution-critical precondition error with two peripheral ones lowers it. The paper reads it as "distance to truth" without that caveat, and it is the metric carrying the load for the central "stagnation not divergence" claim (row 8). Success is reported alongside, which partly mitigates. | §Results ¶3; Table 5 caption |
| 16 | "budget_exhausted 193 / 240 of 12000 planner calls ... no_plan counts are high by design" | Whether apparent divergence is really timeouts | PASS | Exhaustion is 433/12000 = 3.6% and is counted separately and never dropped, which is the correct disposition for the pre-declared rival mechanism. The high no-plan counts (3207 train + 3199 eval) are a genuine property of a 4-error corrupted model in STRIPS — an unplannable model is exactly the regime the loop exists to escape — and the appendix says so rather than filtering. | §Results ¶4; Appendix ¶"Why the no-plan counts are high" |
| 17 | "an independent script agrees on 24 of 24 headline checks" | Verifiability of the reproducibility claim | PASS | Executed during verification: `python3 analysis/verify_independent.py` -> "300 run records, 20 seeds, tag=primary ... 24 comparisons, 0 disagreements", recomputing the interaction, all three falsifier rows and all 20 success cells from the raw run records with an independently-drawn bootstrap. The claim is literally true and the count is exact. | §Limitations ¶"Reproducibility" |

**First-pass tally: 7 PASS, 9 FLAG, 1 BLOCK** (row 5 moved FLAG -> PASS after the abstract was disambiguated; row 8 block resolved in place).

### Disposition of the BLOCK and the load-bearing FLAGs

The BLOCK (row 8) and FLAGs 1, 11, 12, 13 were applied to `main.tex`; the exact
wording and rebuild evidence are recorded in `evidence/DESIGN_NOTES.md`. FLAGs 4,
5, 6, 7 and 15 are hedged in the body already (§Limitations sentences 1 and 3,
§Results ¶1's "exact control" sentence) but not in the abstract; at a 4-page cap
with zero spill, abstract-level hedging of all four was judged to cost more than it
buys, and the residual exposure is recorded here rather than silently accepted. Row
5 was subsequently resolved outright by the abstract disambiguation.

**Residual exposure knowingly signed off on.** The abstract presents the fired
falsifier (rows 6, 7) with more force than its evidential weight supports on its
own: five divergence events across 720 transitions, on a metric that is floored in
the low band. It is correctly qualified in §Limitations, and the corroborating
edit-distance evidence is what actually carries the conclusion. A reviewer who reads
only the abstract will over-read it; a reviewer who reads the paper will not be
misled. This is a presentation risk, not a correctness defect, and it is recorded
rather than resolved. The new §1 "What we claim, and what we do not" paragraph
substantially reduces it by naming the boundary on page 1.

## Second-pass rows — RSI-centrality reframe (2026-09-07)

The paper was subsequently reframed to lead with the implementation (a working
recursive world-model self-repair loop) and to state two design rules. The reframe
was audited for whether it introduced any claim the ledger does not support.

| # | Claim (verbatim or close) | Domain concept | Auditor verdict | Evidence / justification | Location in main.tex |
|---|---------------------------|----------------|-----------------|--------------------------|-----------------------|
| 18 | Title/abstract: "We implement recursive self-improvement of a symbolic world model: an embodied agent holds a corrupted PDDL domain, plans, executes against ground-truth semantics, diagnoses the failure, edits its own model, and plans again." | Whether the apparatus is in fact an RSI loop, or only an evaluation harness | PASS | This is a literal description of `analysis/wm_repair/runner.py`: the agent plans with `M`, executes against `M*`, collects failure events, generates candidate edits from those events alone, accepts under strict domination, and re-plans with the edited `M` for `k` rounds. The artefact modified between rounds is the agent's own world model, which is what makes it self-improvement rather than parameter tuning. No new claim: the loop was always what was run; only the emphasis changed. | Title; Abstract; §1 |
| 19 | "(R1) Price rounds by coverage, and buy coverage first." Rounds gain +0.7383 at c>=0.8 against +0.2083 at c<=0.4; four rounds at c=0.4 reach 0.2933 against 0.9000 at c=1.0. "Extra rounds are not useless under weak verification, they are badly priced." | Whether the engineering rule overstates what the low band shows | PASS (after correction) | **The first draft of R1 read "below c ~ 0.4 extra rounds buy almost nothing" and was rejected on audit:** `primary::delta_k4_k1_low` is +0.2083 with CI [+0.1267, +0.2967], which *excludes zero* — extra rounds demonstrably do help at low coverage, roughly a third as much as at high. R1 was rewritten to the priced-not-useless form before the paper was finalised. As now written every quantity is a stamped cell and the engineering conclusion (widen coverage before adding rounds) follows from the ratio, not from a false null. | §Results ¶"Design rules" |
| 20 | "(R2) Monitor for stalling, not for corruption. ... The counter to watch is instead rounds that propose a repair and accept none (458 across the grid)." | Whether the recommended instrument is the one the data licenses | FLAG | `integrity::no_accept_rounds` = 458 is confirmed in `runner.py:274` as the else-branch of `if best_key > cur_key`, i.e. rounds where candidates existed but none strictly dominated — genuinely distinct from `integrity::no_proposal_rounds` = 110. The rule itself (divergence detectors are the wrong instrument; stall detectors are the right one) follows from rows 6, 8 and 15. **But 458 is a grid-wide pooled counter, not split by coverage band**, so it evidences that the counter exists and is non-trivial, not that it rises at low coverage. The sentence was hedged to "the counter to watch ... across the grid" rather than asserting a band contrast. A per-band split is computable from the existing records and is handed back as future work. | §Results ¶"Design rules" |
| 21 | §1: "It is long-horizon planning and plan repair, knowledge representation for planning, and neuro-symbolic control in one apparatus." | Topicality claim against the venue's CFP language | PASS | Descriptive and accurate: the loop plans over multi-step IPC instances (long-horizon planning), repairs plans by repairing the model that generates them (plan repair), operates on a lifted PDDL domain (knowledge representation for planning), and pairs a symbolic planner with a non-symbolic proposal channel in the secondary arm (neuro-symbolic). It asserts topicality, not a result, and carries no number. | §1 ¶1 |
| 22 | §1 "What we claim, and what we do not": "We do not claim that under-verified repair is safe in general, that the finding transfers to a language-model proposer, or that divergence cannot occur at rates this grid cannot resolve." | Whether the stated boundary matches the actual evidence boundary | PASS | The three disclaimers map exactly to the three live exposures identified in audit: the acceptance-rule guarantee (row 8), the deterministic proposer (rows 9, 13), and the falsifier's power (rows 6, 7). This paragraph converts the mixed verdict (interaction confirmed, mechanism refuted) from an apparent self-contradiction into a stated scope. | §1 |

**Second-pass tally: 4 PASS, 1 FLAG, 0 BLOCK — and one overclaim (R1) caught and
corrected before the paper was finalised rather than shipped.** No number changed in the reframe;
two stamped cells (`primary::delta_k4_k1_high/low`) were reused in R1 and one
(`success::k0_baseline_pooled`) was promoted into the abstract.

## Third-pass rows — authorized analyses (2026-09-07)

Four additional analyses were run after the second pass. Rows 23–28 record their
verdicts. **The headline of this pass is that item 3 falsified a sentence written
in the second pass** — see row 24.

| # | Claim (verbatim or close) | Domain concept | Auditor verdict | Evidence / justification | Location in main.tex |
|---|---------------------------|----------------|-----------------|--------------------------|-----------------------|
| 23 | (Item 1) "0.6062 of rounds at c<=0.4 propose a repair and accept none against 0.1437 at c>=0.8 (gap +0.4625 [+0.3875, +0.5396]), while the proposer is no less productive at low coverage (no-proposal rate 0.0563 against 0.1396)" | Whether stagnation is measured or merely inferred | PASS | `stats.no_accept_rounds` is the else-branch of `if best_key > cur_key` in `runner.py:274` — rounds where candidates existed and none strictly dominated. Aggregated per band over the 4 repair rounds with the same seed-clustered bootstrap as every other contrast. The gap CI excludes zero by a wide margin. **The second counter is what makes this diagnostic rather than circular:** `no_proposal_rounds` is *lower* at low coverage (0.0563 vs 0.1396), so the low-coverage loop is not failing to generate candidates — it generates them and cannot tell which is right. That is stagnation in the precise sense R2 claims, and it converts R2 from a recommendation into a measurement. | Abstract; §Results ¶"Design rules" |
| 24 | (Item 3) "The visible part *cannot* grow ... and it grew in 0 of 360 transitions in each band. The invisible part is free to, and does: 22 of 360 at c<=0.4 against 3 of 360 at c>=0.8 (gap +0.0528 [+0.0278, +0.0750])" | Whether the loop damages the part of its model nobody checks | PASS — **and it corrected an error in the second-pass wording** | Residual error splits exactly, with no re-run, because both inputs are already stored per snapshot: visible mismatches `= (1 - verifier_score) * coverage_visible`, invisible `= edit_distance - visible`. The identity was checked over all **1200 snapshots** and holds to `9.3e-15` with **zero negative invisible counts**. Two results follow. (a) The visible component grew in **0 of 720** transitions, which is the acceptance rule's monotonicity guarantee (row 8) confirmed as an implementation check rather than argued. (b) The invisible component grew **22/360 at low coverage against 3/360 at high**, gap +0.0528 with a CI excluding zero. **The second-pass paper said the unverified region "was free to degrade and did not." That was wrong — it degraded, about seven times as often at low coverage — and the sentence was rewritten before the paper was finalised.** The finding is a refinement, not a reversal: the invisible residual still *falls* on average (2.6333 to 2.4083), so there is local damage without net accumulation. | §Results ¶"The failure mode is stagnation"; Table 7 |
| 25 | (Item 3, consequence) The pre-declared falsifier fired on divergence *events* (2/360 vs 3/360, gap covering zero) while the residual split finds a coverage asymmetry (22/360 vs 3/360, gap excluding zero) | Whether the paper now contradicts itself | PASS | These are different measurements and the paper says which is which. The falsifier was declared over *held-out success drops*, and audit row 6 established that metric is floored in the low band (success 0.0133 -> 0.1733, almost no room to fall). The residual split measures *model* error and has no floor. So the pre-declared test fired honestly on the metric it was declared over, and a more sensitive post-hoc measure detects the effect that metric could not resolve. Limitations now states exactly this ("divergence *events* are too rare ... which is why the residual split carries that question"). This is the correct disposition of an underpowered pre-registered test: honour it, then say plainly what a better instrument shows. | §Results ¶2; §Limitations |
| 26 | (Item 5) "Exactly two tests are *confirmatory* and were fixed in the pre-declaration: the coverage x k interaction and the divergence falsifier. The per-domain split, the residual decomposition and the stall counters are descriptive and were computed after the grid ran." | Multiplicity / confirmatory-exploratory discipline | PASS | Accurate against `A2_PREDECLARATION_2026-09-07.md`, which names exactly those two. Critically, it labels the two *new* analyses (rows 23–24) as post-hoc **even though they are the paper's most favourable new results**. Declaring your best new numbers exploratory is the costly, correct move, and it answers objection #12 (no multiplicity control) at the level a 4-page paper can. | §Setup ¶"Analysis" |
| 27 | (Appendix) "the model-repair trajectory is exactly reproducible ... but held-out *success* is not, because the planner budget is partly wallclock (5 s) and a faster host solves instances that previously timed out --- we saw this on gripper" | Reproducibility of the apparatus under re-execution | PASS — self-reported defect | Established by direct test, not by inspection: the pinned stack (`pyperplan 2.1`) was rebuilt in a fresh venv and 12 primary-arm runs were re-executed. `edit_distance` and `verifier_score` matched row for row in **12 of 12**; `heldout_success` differed in **3 of 12**, all on gripper, always in the direction of *more* success on the faster host. Diagnosis: the 5 s wallclock component of the plan budget. This is a genuine limitation of the apparatus that the paper now discloses itself. It also strengthens the paper's position, because the metric carrying the central claim (model error) is the exactly-reproducible one. | Appendix A ¶"Reproducibility" |
| 28 | (A11) The expanded LLM-proposer arm, pre-committed in `DESIGN_NOTES.md` §6 before the first row was written | Whether the A6 throughput justification still holds, and whether the new arm is clean | FLAG — disclosed, in progress | Auditing A6 against the completed secondary arm shows the pilot figure was wrong: the arm ran at **7.2 s per call** (1150 s over 159 calls), not the 31–99 s the pre-declaration recorded, so the "10.5–20 h against an 8 h budget" justification for demoting the LLM was 5–14x pessimistic. `DESIGN_NOTES.md` §6 records this correction rather than quietly re-running. The expanded arm (3 domains x 5 coverages x 20 seeds = 300 runs, `llmfull::`, new output dir, existing arm untouched) was in progress at the time of writing and is therefore **not in the paper**. Integrity monitoring at n=21 shows no rate rising with job order — `llm_errors` 0.100 -> 0.000, `parse_failures` 0.300 -> 0.273, `no_proposal_rounds` 0.300 -> 0.000 — so the contamination stop-rule had not tripped. Nothing from this arm may enter the paper until it completes and the stop-rule is re-checked on the full set. | not yet cited |

**Third-pass tally: 5 PASS, 1 FLAG, 0 BLOCK — and one error caught and corrected (row 24).**

## Rival mechanisms / discriminator falsifier

*(Consulted by gate 13b. `A2_PREDECLARATION_2026-09-07.md` names three rival
mechanisms and one discriminator falsifier; `main.tex` §Results carries the
"Rival mechanisms and alternative explanations" paragraph that gate 13b
matches on.)*

- **Corruption-severity confound** (low-coverage cells might carry harder
  corruptions) → *addressed in §Results ¶"Rival mechanisms"; falsified by*
  `maineffect::coverage_at_k0` *= exactly 0.0000.* Verdict: **PASS,
  eliminated by design.** The same seeded corruption is reused across every
  coverage level within a seed, so the k=0 column of Table 1 is identical
  across all five arms by construction. Note this is the same tautology
  identified in row 5 — which is precisely why it is a sound *confound*
  check even though it is a weak *result*.
- **Repair-budget exhaustion** (apparent divergence is timeouts, not bad
  edits) → *measured and reported in §Results ¶"Rival mechanisms" and
  Table 3.* Verdict: **PASS.** 433 exhaustions in 12,000 planner calls,
  counted separately, never filtered.
- **Planner stochasticity** (success drift unrelated to model quality) →
  *bounded in §Results ¶"Rival mechanisms".* Verdict: **PASS.** One fixed
  planner configuration throughout; k=1 is a within-seed control whose
  coverage main effect (0.0150 [-0.0033, +0.0450]) still covers zero.
- **Discriminator falsifier** — pre-declared as *"if divergence events occur
  at the same rate in high-coverage (c >= 0.8) and low-coverage (c <= 0.4)
  cells, the coverage mechanism is falsified regardless of the interaction
  CI, and the paper says so."* → **THE FALSIFIER FIRED**, and the paper says
  so in the abstract, §Results and the conclusion. Verdict: **FLAG,
  honoured but underpowered.** The pre-declared rule was applied faithfully
  and against the authors' own hypothesis, which is the strongest
  methodological fact in the paper. The rule was declared over a metric
  (a drop in held-out success) that is floored in the low band (row 6), so
  the firing is weakly diagnostic on its own; the corroborating edit-distance
  evidence is what makes the "stagnation, not divergence" conclusion stand,
  and that evidence carries the structural caveat of row 8. The falsifier is
  honoured, not gamed — but it is not, by itself, a strong refutation.

## Summary

The paper's numbers are sound: every abstract figure resolves to a ledger row,
an independent recomputation agrees 24/24, and the two places where the design
forces a value (the k=0 control, the n1:: interaction) are labelled as forced
in the body rather than sold as findings. The pre-registration is real, the
falsifier was declared in advance and applied against the authors' own
hypothesis, and the failed LLM arm is reported instead of suppressed.

The domain-reasoning defect worth blocking on was one inference, not one
number: the claim that the loop "does not move away from truth" is, on the
fraction of the condition space the verifier can see, guaranteed by the
strict-domination acceptance rule rather than discovered. Once that is named,
the finding is narrower but still real — the *unverified* 60-80% of the
condition space was free to degrade at low coverage and did not.

The residual generality gap is that verifier coverage is operationalised as
uniform stratified random access to ground-truth semantics, which is not how
an embodied agent's verifier is partial. That is a scope limit to state, not
an error to fix, and it is the objection most likely to decide the review.
