# Related Work Notes — nemo-plan-repair-coverage (v2: PDDL world-model self-repair)

8 comparative sentences for the Related Work section.
Apparatus (v2): agent holds a corrupted PDDL domain model, plans against a ground-truth
simulator, observes execution failures, and recursively repairs its own world model.
Verifier coverage c (fraction of ground-truth conditions the verifier can check) x repair
rounds k is the factorial design variable.

---

## 1. huang2023llmcantcorrect — Large Language Models Cannot Self-Correct Reasoning Yet

**What they did:** Huang et al. demonstrate empirically that LLMs in self-critique loops
do not improve, and may deteriorate, on reasoning benchmarks when no external ground-truth
oracle is provided; they attribute failure to the absence of reliable external feedback.

**What we do differently:** We extend this critique to the symbolic planning domain and add
a finer-grained dimension: even when a PDDL execution verifier *is* present, its coverage
fraction c determines whether recursive model repair converges or diverges — a mechanism
not visible in binary oracle-presence designs.

---

## 2. madaan2023selfrefine / shinn2023reflexion — Self-Refine and Reflexion

**What they did:** Self-Refine (Madaan et al.) iterates LLM output refinement via
self-generated natural-language critique; Reflexion (Shinn et al.) accumulates verbal
execution feedback in episodic memory across trials, improving agent task success without
weight updates.

**What we do differently:** Both frameworks repair *free-form LLM outputs* using full or
assumed-complete environment feedback; we repair a *structured, symbolic artifact* — a PDDL
action-schema file with explicit preconditions and effects — and we manipulate verifier
coverage as an independent variable rather than treating it as all-or-nothing.

---

## 3. yang2007arms / aineto2019fama / cresswell2013locm — Action Model Learning (ARMS, FAMA, LOCM)

**What they did:** ARMS (Yang et al.), FAMA (Aineto et al.), and LOCM (Cresswell et al.)
learn PDDL action models from plan traces or observation sequences, framing model acquisition
as an offline batch-learning problem with full or partial observability of action effects.

**What we do differently:** We study *online iterative repair* of an already-initialised
(but deliberately corrupted) model using execution failure signals, not offline batch
learning; coverage fraction c operationalises partial observability at *repair time*, and we
measure the interaction between c and repair rounds k rather than final model accuracy alone.

---

## 4. chakraborti2017reconciliation / sreedharan2018uncertainty / sreedharan2022reconciliation — Model Reconciliation

**What they did:** Chakraborti, Sreedharan, and Kambhampati frame explanation as model
reconciliation: the agent generates communications that move the human's model toward the
agent's; Sreedharan et al. extend this to handle model uncertainty and multiplicity over
possible user models.

**What we do differently:** We flip the direction — the agent reconciles its *own* corrupted
model toward the ground-truth execution evidence rather than reconciling a human's model
toward the agent's plan; our contribution is measuring how reconciliation quality degrades
when the verifier can only inspect a fraction c of the true model's conditions.

---

## 5. nguyen2017robust / weber2011incomplete — Planning with Incomplete Domain Models

**What they did:** Nguyen, Sreedharan & Kambhampati and Weber & Bryce design planners and
heuristics that remain effective when the domain model contains gaps or incorrect action
schemas, treating model incompleteness as a fixed property of the planning problem.

**What we do differently:** We do not improve the planner under a fixed incomplete model;
we study the repair loop that *updates* the domain model after each execution failure, and
we systematically vary how much of the true model the verifier can see, asking whether more
repair rounds help or hurt as c decreases.

---

## 6. konidaris2018skills / chitnis2022nsrts — Neuro-Symbolic Operator Learning

**What they did:** Konidaris et al. show that symbolic operators can be induced from
sensorimotor skill primitives; Chitnis et al. learn Neuro-Symbolic Relational Transition
Models (NSRTs) grounding PDDL-style operators in continuous observations for bilevel planning.

**What we do differently:** Our symbolic operators are given but intentionally corrupted;
the question is not how to learn them from scratch but how to repair them from execution
failures, and specifically whether verifier coverage c controls whether iterative repair
converges toward or diverges from the true model.

---

## 7. helmert2006fastdownward / fox2003pddl21 / howey2004val — PDDL Tooling

**What they did:** Fast Downward (Helmert), PDDL2.1 (Fox & Long), and VAL (Howey et al.)
establish the planning infrastructure used in IPC benchmarks: an expressive domain language,
a search-based planner, and a formal plan validator.

**What we do differently:** We use this infrastructure as the experimental substrate; our
contribution is not a planning or validation algorithm but a controlled factorial study of
world-model self-repair, using pyperplan as the lightweight planner and the IPC classical
domains (blocksworld, gripper, logistics) as the benchmark environment.

---

## 8. lightman2023verify / uesato2022process — Verifier / Process Reward Model Quality

**What they did:** Lightman et al. and Uesato et al. study process reward models (PRMs)
for mathematical reasoning, showing that step-level verifier quality affects final answer
selection and that process-based feedback outperforms outcome-based feedback in some regimes.

**What we do differently:** We study an analogous question in symbolic planning: how the
coverage fraction of a PDDL verifier — the share of the true model's conditions it can check
— modulates whether iterative model repair converges; this is the planning-domain analogue of
asking how verifier completeness governs self-improvement loop stability.

---

## Coverage Notes for Section Writing

- The coverage x k interaction claim has **no direct prior art** in the literature surveyed
  (see `NOVELTY_CHECK.md`).
- Nearest rivals are Huang et al. 2023 (oracle presence/absence) and Lightman et al. 2023
  (verifier quality) — both address verifier-completeness themes but not the specific
  factorial coverage-fraction x repair-rounds design over PDDL model repair.
- The action-model learning literature (ARMS/FAMA/LOCM) provides the closest technical
  background but studies offline batch acquisition rather than online iterative repair.
- The seed-paired bootstrap design follows Dror et al. 2018 (ACL), extended here to the
  embodied-planning evaluation setting.
