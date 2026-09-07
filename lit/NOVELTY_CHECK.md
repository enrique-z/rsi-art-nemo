# Novelty Check — nemo-plan-repair-coverage (v2: PDDL world-model self-repair)

**Claim being checked (v2, supersedes v1):**
"On classical IPC planning domains (blocksworld, gripper, logistics), an agent that
recursively repairs its own corrupted PDDL domain model from execution failures improves
plan-execution success monotonically only when the verifier it repairs against checks a
sufficient fraction of the true model's conditions. Formally: the verifier coverage (c) x
repair-round (k) interaction has a non-zero effect on plan-execution success; at low
coverage, additional repair rounds degrade success (the loop amplifies model error), while
at high coverage they improve it."

**Sweep conducted:** arXiv API, Crossref, paper-researcher, Semantic Scholar (2026-09-07).
Queries: "coverage plan repair interaction PDDL", "verifier coverage model repair PDDL",
"domain model repair incomplete verifier", "action model repair execution failure coverage",
"recursive domain repair convergence partial observability", "coverage fraction symbolic
repair rounds".

---

## 5 Closest Prior Works

### 1. Huang et al. 2023 — Large Language Models Cannot Self-Correct Reasoning Yet
**arXiv:** 2310.01798

**What they claim:** LLMs in self-correction loops degrade on reasoning tasks absent an
external ground-truth oracle; the failure is attributed to oracle absence (binary: present
vs. absent).

**Overlap with our claim:** Both papers show that recursive self-correction can fail and
even worsen; the failure mechanism involves verifier completeness.

**Gap vs. our claim:** Huang et al. treat the verifier as absent vs. present (binary). They
do not vary fractional coverage of the verifier, do not study the interaction between
coverage level and repair depth k, do not study PDDL domain model repair, and do not use a
symbolic planning substrate. Our claim is strictly more specific: we vary coverage fraction c
continuously as a factorial treatment, crossing it with repair rounds k, and study convergence
of a structured symbolic artifact (a PDDL domain file), not of LLM text output.

**Verdict: Closest single-paper rival; partially overlapping in conclusion, but our claim
is novel at the coverage-fraction x repair-rounds interaction level in PDDL model repair.**

---

### 2. Nguyen, Sreedharan & Kambhampati 2017 — Robust planning with incomplete domain models
**DOI:** 10.1016/j.artint.2016.12.003

**What they claim:** Planning with incomplete domain models remains tractable when the
planner exploits model uncertainty; they design heuristics that perform well despite action-
model gaps.

**Overlap with our claim:** Both papers study classical planning with incomplete or incorrect
domain models; the Kambhampati group is the primary research thread on this topic.

**Gap vs. our claim:** Nguyen et al. hold the incomplete model fixed and improve the
*planner* under it; they do not study *repair* of the model itself, do not use an LLM repair
proposer, and do not treat verifier coverage as an independent variable. Their incomplete
model is a fixed given; ours is a dynamically repaired artifact with coverage-controlled
feedback.

**Verdict: Related setting; orthogonal technical contribution (planner robustness vs.
model self-repair with coverage manipulation).**

---

### 3. Aineto, Jiménez & Onaindia 2022 — A Comprehensive Framework for Learning Declarative Action Models (FAMA)
**DOI:** 10.1613/jair.1.13073

**What they claim:** Action models can be learned from observation sequences with varying
degrees of observability (full, partial, or null), using a constraint-satisfaction framework;
observability level affects the quality and completeness of learned models.

**Overlap with our claim:** Both papers vary the observability of the domain model at
learning/repair time; the relationship between observability level and model quality is a
shared theme.

**Gap vs. our claim:** FAMA frames model learning as offline batch acquisition from traces
under fixed observability; we study online iterative repair from execution failures with
coverage varying across runs as a factorial factor. FAMA measures final model accuracy; we
measure the interaction between coverage fraction and repair round on plan-execution success
trajectory. The coverage x k interaction effect — specifically whether more rounds help or
hurt — has no analogue in FAMA.

**Verdict: Closest technical ancestor; our paper is the online-repair, interaction-effect
analogue of FAMA's offline-learning, accuracy-level analysis.**

---

### 4. Chakraborti, Sreedharan, Zhang & Kambhampati 2017 — Plan Explanations as Model Reconciliation
**DOI:** 10.24963/ijcai.2017/23

**What they claim:** Explanation in human-robot interaction is model reconciliation: the
agent generates communications that bring the human's world model into alignment with the
agent's, using the minimal edit to the human model.

**Overlap with our claim:** Both papers study the problem of a world model diverging from
ground truth and the process of reconciling it; the Kambhampati group's reconciliation
framework is the closest prior formalisation of "repairing a divergent model."

**Gap vs. our claim:** Chakraborti et al. reconcile a *human's* model toward the *agent's*
plan (explanation for communication); we reconcile the *agent's own* corrupted model toward
the ground-truth execution evidence (self-repair for planning). Their reconciliation is
one-shot and deterministic; ours is iterative with k rounds and a coverage-controlled
verifier. No factorial design on coverage fraction.

**Verdict: Closest formal framework; complementary direction (agent-to-human vs.
agent-self); no claim overlap on coverage x repair-rounds interaction.**

---

### 5. Lightman et al. 2023 — Let's Verify Step by Step
**arXiv:** 2305.20050

**What they claim:** Process reward models that verify intermediate steps outperform outcome
reward models for LLM reasoning; higher-quality PRM leads to better outcomes.

**Overlap with our claim:** Both papers study the relationship between verifier quality and
iterative improvement; the PRM quality analogy maps conceptually to PDDL verifier coverage.

**Gap vs. our claim:** Lightman et al. compare trained PRM quality as a discrete property
of fixed model classes, not a continuous coverage fraction within a single verifier. They
study mathematical reasoning, not PDDL domain model repair. No interaction with repair round
depth k; no factorial design. Coverage in our sense (fraction of ground-truth conditions the
verifier can check) has no direct analogue in their setup.

**Verdict: Thematically close; the coverage-PRM quality analogy is useful for framing but
there is no direct claim overlap.**

---

## Novelty Assessment

**Honest verdict: The specific claim — that PDDL verifier coverage fraction c moderates
the sign and magnitude of the repair-round (k) interaction in a recursive domain-model
self-repair loop — has no direct prior art.**

No paper found that:
- Treats verifier coverage fraction as a continuous treatment variable in PDDL model repair
  (as opposed to oracle present vs. absent, or observability level in offline batch learning)
- Uses a factorial design crossing coverage bins x repair-round depth k in a symbolic
  domain-repair setting
- Studies whether the improvement curve inverts (success decreasing with k) as a function
  of coverage, rather than assuming monotone improvement at full coverage

The claim is novel at the stated specificity. The action-model learning literature (ARMS,
FAMA, LOCM) provides the offline-learning background; the Kambhampati group's reconciliation
work provides the model-divergence background; neither addresses the coverage x k interaction
on an online repair loop.

**Primary novelty threat:** Nguyen et al. 2017 (incomplete domain models, Kambhampati group)
is the closest setting; but their contribution is planner robustness under a fixed incomplete
model, not model self-repair. No paper by this group was found studying iterative repair
with coverage-controlled verifier feedback.

**Secondary novelty threat:** FAMA (Aineto et al. 2022) studies partial observability in
action-model learning; if a follow-on paper extends FAMA to online repair with coverage
manipulation, it could overlap. No such paper was found in the Crossref/arXiv sweep.

**Third threat:** An unpublished or unindexed workshop paper from ICAPS 2025 or IJCAI 2025
could exist. The IJCAI 2025 model-repair candidate could not be verified (no DOI/arXiv
found). Authors should manually check ICAPS 2025 and IJCAI 2025 proceedings before final
submission.

---

## How to Address in Paper

1. Cite Huang et al. 2023 as the closest rival in spirit; state explicitly that their
   binary oracle-presence finding motivates our *continuous coverage fraction* treatment —
   a different and finer-grained variable.
2. Cite Nguyen et al. 2017 and the Kambhampati reconciliation line (Chakraborti 2017,
   Sreedharan 2018) as the classical planning background for model-divergence problems;
   frame our contribution as the *self-repair + coverage manipulation* extension.
3. Cite FAMA (Aineto et al. 2022) as the offline-learning analogue; frame our paper as the
   online-repair, interaction-effect complement — same model-quality-vs-observability
   question, different experimental regime.
4. Cite Lightman et al. 2023 to establish that verifier quality matters in iterative
   improvement; distinguish our real-time PDDL repair setting from offline PRM training.
5. Note that if the 95% CI on the coverage x k interaction includes zero (honest-negative
   outcome per pre-declaration), the paper still reports a methodologically clean null; the
   novelty of the factorial design over PDDL model repair stands regardless.
