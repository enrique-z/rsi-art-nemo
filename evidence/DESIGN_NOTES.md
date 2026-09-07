# DESIGN_NOTES — nemo-plan-repair-coverage (v2 apparatus)

**Written 2026-09-07 UTC, BEFORE the full run.** Configuration, provenance, operational
definitions and every deviation-as-amendment. The v1 escalation history is preserved in
the final section (full v1 text kept at `evidence/DESIGN_NOTES.v1.bak`).

---

## 1. Apparatus

A **world-model self-repair loop**: RSI over an agent's own symbolic domain model.

The agent holds a *corrupted* copy of a ground-truth PDDL domain. Each repair round it
(i) plans with its corrupted model, (ii) executes the plan against a ground-truth
simulator, (iii) observes failures, (iv) proposes model repairs, (v) adjudicates the
candidates with a **verifier that can see only a fraction `c` of the domain's condition
space**. Held-out plan-execution success is measured at repair rounds k ∈ {0,1,2,4}.

### Planner + versions (verified on this host)

| item | value |
|---|---|
| planner | **pyperplan 2.1** (pure-Python, GPL-3), `pip install pyperplan` into `<REPO_ROOT>/.venv-nemo` |
| search | greedy best-first over **hFF** (`pyperplan.heuristics.relaxation.hFFHeuristic`), duplicate-eliminating, expansion- and time-capped — `analysis/wm_repair/core.py:plan()` |
| grounding | `pyperplan.grounding._ground_actions` / `_create_type_map` / `_get_statics`, driven from our lifted model |
| Python | 3.14.7 |
| platform | macOS (Darwin 24.6.0), arm64 |
| plan budget | 1200 expansions **or** 5.0 s per plan call, whichever first; exhaustion logged as `budget_exhausted_*`, never silently dropped |

The pip wheel does **not** ship the IPC benchmark PDDL. They were taken from the upstream
repository and are vendored, with checksums, at `external/pyperplan-benchmarks/`.

### Domains and their provenance

| domain | source | instances used | \|C\| (condition space) | \|C*\| (true conditions) |
|---|---|---|---|---|
| blocks (4-op BLOCKS) | `github.com/aibasel/pyperplan` `benchmarks/blocks` | task01–task10 | 96 | 27 |
| gripper (gripper-strips) | `…/benchmarks/gripper` | task01–task10 | 180 | 14 |
| logistics (typed) | `…/benchmarks/logistics` | task01–task10 | 48 | 22 |

* upstream git SHA: `586b99f060bfe457f359aa8b4bae1a299fa4e8c7` (`external/pyperplan-benchmarks/PROVENANCE.txt`)
* per-file SHA-256: `external/pyperplan-benchmarks/SHA256SUMS.txt` (39 files)
* **train instances:** task01, 03, 05, 07, 09 — used during repair
* **held-out instances:** task02, 04, 06, 08, 10 — **never** used during repair; the primary
  outcome is measured only on these. The odd/even interleave balances instance difficulty
  across the two splits (IPC tasks are ordered by size).
* Ground-truth sanity check: with the *uncorrupted* model the planner finds and successfully
  executes a plan on **30/30** instances (10 per domain).

### Condition space `C` (what corruption, repair and coverage all act on)

For each action `a` and each **non-static** predicate `P`, enumerate every type-consistent
binding of `P`'s arguments to `a`'s own parameters. Each such *slot* contributes three
binary decisions — is it in `pre(a)`, in `add(a)`, in `del(a)`. `C` is the set of those
`(action, kind, slot)` triples; `C*` ⊆ `C` is the subset true in the ground-truth domain.
A model is exactly an assignment of booleans to `C`; `edit distance = |M △ M*|` over `C`.

**Assumption (amendment A3):** *static* predicates — those appearing in no ground-truth
action effect (`room`/`ball`/`gripper` in gripper, `in-city` in logistics; none in blocks) —
encode sort structure and are held **fixed**. They are never corrupted, never repaired and
never sampled by the verifier. This keeps the true model and every candidate model grounding
into the same fact space and the same operator-name set, so "the model changed" can never be
confounded with "the state space changed".

### Corruption operator (seeded, fixed before any run)

`core.corrupt()` applies **n_corrupt = 4** condition toggles to the ground-truth model, drawn
from a seed-derived RNG: `n_drop = n//2 = 2` DROPS of true conditions and `n_add = 2`
ADDITIONS of false ones — a fixed, seeded perturbation of preconditions and effects, exactly
as pre-declared. The corrupted model is **identical across all five coverage levels for a
given (domain, seed)** — the pre-declared mitigation of the corruption-severity confound
(rival mechanism 1).

**How `n_corrupt = 4` was chosen (see amendment A4/A8; both rules fixed in writing before
being evaluated).**

*First rule (A4, superseded):* the smallest `n_corrupt` whose mean pre-repair (k=0) held-out
success is strictly in (0,1) in every domain. Calibration over 12 seeds/domain:

| n_corrupt | blocks k=0 succ | gripper k=0 succ | logistics k=0 succ |
|---|---|---|---|
| 1 | 0.27 | 0.50 | 0.53 |
| 2 | 0.10 | 0.00 | 0.12 |
| 3 | 0.00 | 0.00 | 0.07 |
| 4 | 0.00 | 0.00 | 0.03 |

That rule selected `n_corrupt = 1` — and **`n_corrupt = 1` makes `k` degenerate.** A single
seeded error is repaired (or not) in round 1; the loop then observes no training failure,
proposes nothing, and halts. In the 100-run `n_corrupt = 1` blocks sub-grid actually executed
under it, held-out success at k=1, k=2 and k=4 are *identical in every single run*, so the
pre-registered k=1-vs-k=4 contrast — and therefore the coverage×k interaction — is exactly
0.0000 **by construction, not by evidence**. The pre-declaration's k ∈ {1,2,4} nested design
presupposes multi-round repair; rule A4 silently violated that presupposition.

*Replacement rule (A8), stated in writing before evaluation:* **`n_corrupt` must be ≥ max(k)
= 4, so that every repair round has work available; among such values take the smallest whose
mean held-out success at k=4, POOLED OVER ALL COVERAGE LEVELS, is strictly in (0,1) in every
domain.** Pooling over coverage makes the criterion blind to the coverage×k interaction (the
quantity of interest); using a *level* at k=4 rather than a *contrast* makes it blind to the
k effect. The rule therefore evaluates `n_corrupt = 4` first. Measured (3 coverages × 6 seeds
= 18 trajectories per domain):

| n_corrupt | blocks pooled k=4 succ | gripper pooled k=4 succ | logistics pooled k=4 succ |
|---|---|---|---|
| **4** | **0.556** | **0.411** | **0.500** |

All three lie strictly in (0,1); the search terminates at the first candidate. **n_corrupt =
4.** No larger value was evaluated, so no selection on effect size was possible.

The `n_corrupt = 1` blocks sub-grid (5 coverages × 20 seeds = 100 runs) is **retained, not
discarded**, at `evidence/runs_n1/` as a labelled supplementary *single-error* arm. It is
reported separately and never pooled with the primary grid.

### Verifier coverage `c` — the operational definition

`c ∈ {0.2, 0.4, 0.6, 0.8, 1.0}`. For each seed a visible set `V ⊆ C` is drawn once and held
fixed for the whole run. `V` is **stratified**: it contains `round(c·|C*|)` of the domain's
true conditions and `round(c·|C \ C*|)` of its false ones, so `V` simultaneously

* contains a fraction `c` of the ground-truth domain's conditions, and
* is a fraction `c` of the whole condition space the verifier could see.

`verifier.score(M) = |{t ∈ V : M(t) = M*(t)}| / |V|` — the fraction of *visible* conditions
on which a candidate agrees with truth. Everything outside `V` is invisible: the verifier can
detect neither a missing true condition nor a spurious false one there. The verifier is a
**checker on candidates only** — the loop can never enumerate `C` through it.

### Repair loop and acceptance rule

Per round: roll out the current model on the 5 training instances (plan → execute against
ground truth) → collect failure evidence → the proposer emits candidate edit-sets → each
candidate is scored by `(verifier_score, evidence_fit)` → the best candidate is **accepted
only if that pair strictly dominates the current model's pair**; ties are broken by a seeded
RNG draw (never by sort order). Rounds that propose nothing (`no_proposal_rounds`) or accept
nothing (`no_accept_rounds`) are logged.

`evidence_fit(M)` counts recorded failure events that `M` would no longer produce, recomputed
directly on the recorded `(state, action, observed-successor)` tuples. It reads **no ground
truth**. The blind fallback proposer (`unsolvable_candidates`) fires **only** when the model
produced no plan at all; if every training instance already succeeds the loop proposes
nothing and has converged.

**k is nested:** the k=4 trajectory *is* the k=2 trajectory extended, which is the k=1
trajectory extended. Snapshots at k ∈ {0,1,2,4} come from one trajectory, so the (c,k) grid
is seed-paired by construction and every within-seed contrast is exact.

### Proposer — **DETERMINISTIC SEARCH-BASED** (pre-declared fallback invoked)

The pre-declaration named a local-Ollama LLM proposer with an explicit fallback: *"if LLM
throughput or parse reliability fails the pilot, a deterministic search-based repair proposer
is used instead and stated explicitly in the paper (never hidden)."*

**The LLM proposer failed the pilot on throughput.** Measured on this host, blocks domain,
Ollama at `http://localhost:11434`:

| model | latency / proposal call | outcome |
|---|---|---|
| `qwen2.5-coder:14b` | > 120 s | **3/3 calls timed out** |
| `qwen3:8b` (thinking disabled via `think:false`, verified — raw response contained no reasoning tokens) | 31.6 s first probe; 54.8–99 s on real prompts after trimming | usable but slow |

Full grid = 3 domains × 5 coverages × 20 seeds × 4 rounds = **1200 proposal calls**. At the
observed `qwen3:8b` latency that is 10.5–20 h of LLM time alone, against an ≤8 h wallclock
bound. **Throughput failure ⇒ pre-declared fallback ⇒ the primary grid uses the deterministic
proposer.** This is stated in the paper as well as here.

*Parse reliability was NOT the failing criterion.* With thinking disabled `qwen3:8b`
returns well-formed JSON and repeatedly recovers the exact seeded corruption (probes
recovered `unstack / add / (handempty)` and `put-down / pre / (holding ?x)`).

**Correction (amendment A9).** The parse-failure counts first observed (4 across 3 calls in
the pilot, 16 per trajectory in the first LLM sub-grid attempt) were caused by **two defects
in our own parser**, not by the model:

1. `slot = (pred, tuple(t.lstrip("?") ...))` stripped the leading `?` from parameter names,
   while the skeleton's slots carry it (`('holding', ('?x',))`). **No proposal could ever
   match a legal slot.**
2. The model answered `"list": "precondition"`; the parser accepted only the literal token
   `"pre"` and rejected an unambiguous synonym.

Both are fixed (`_KIND_SYN` synonym table; `"?" + t.lstrip("?")` normalisation). After the
fix the same prompt yields **0 parse failures** and a candidate set containing the exact
corrupted condition. **Every LLM run produced under the buggy parser was discarded and the
arm was re-run from scratch** — reporting those rows would have attributed a harness defect
to the model. The throughput failure is independent of this bug and stands: it is measured
in wallclock per call, not in parse yield.

**Deterministic proposer** (`core.evidence_candidates`) is ground-truth-blind. From a
*precondition violation* it proposes adding, as a precondition, any lifted slot whose
grounding is **false in the observed state** (the world refused an action the model thought
applicable, so the true precondition contains something false there). From an *effect
discrepancy* it proposes, for each fact the world produced but the model did not predict,
adding it to `add` or removing it from `del`, and symmetrically for spuriously predicted
facts. It never reads `M*`.

### LLM secondary arm (explicitly smaller N)

Because the LLM arm answers a real question — *is the effect an artifact of the deterministic
proposer?* — a reduced LLM sub-grid is run **concurrently** on the cheapest domain:
`qwen3:8b`, **blocks only, 5 coverages × 8 seeds**. It is reported as a secondary arm with
its own smaller N, never pooled with the primary grid.

---

## 2. Configuration chosen before the full run

```
domains         blocks, gripper, logistics            (3)
instances       task01..task10 per domain             (10 each)
  train         01,03,05,07,09                        (5)
  held-out      02,04,06,08,10                        (5, never seen during repair)
coverages       0.2, 0.4, 0.6, 0.8, 1.0               (5)
repair rounds   k = 1..4, snapshots at k = 0,1,2,4    (nested)
seeds           0..19                                 (20 per (domain, coverage) cell)
n_corrupt       4   (2 drops of true conditions + 2 additions of false ones)
plan budget     1200 expansions / 5.0 s
proposer        deterministic (primary) | qwen3:8b (secondary, blocks x 8 seeds)
```

Supplementary arm: n_corrupt = 1, blocks only, 5 coverages x 20 seeds (evidence/runs_n1/).

Checkpoints = 3 domains × 5 coverages = 15 per-cell JSONL files. The (c,k) grid the claim is
about has 5 × 3 = 15 cells, each with 20 seeds × 3 domains = **60 seed-paired runs**
(≥ 20 required).

### Throughput math

Measured trajectory cost (deterministic proposer, 4 trajectories per domain, full k=0..4):

| domain | mean s / trajectory | max s / trajectory |
|---|---|---|
| blocks | 0.90 | 1.3 |
| gripper | 111.55 | 197.8 |
| logistics | 5.83 | 7.1 |

Projected full grid = (0.90 + 111.55 + 5.83) × 20 seeds × 5 coverages = **11 828 s ≈ 3.3 h**,
inside the ≤ 8 h bound. That probe ran with the looser (1500 exp / 15 s) plan budget, so the
realised cost under the final (1200 exp / 5.0 s) budget is strictly lower. **No seed
reduction was necessary**; the coverage grid and seed-pairing are untouched.

---

## 3. Outcomes and analysis (fixed before the run)

* **Primary** — held-out plan-execution success (fraction of the 5 held-out instances on
  which the model yields a plan that executes to the goal under ground-truth semantics).
  Interaction of coverage × k estimated on **seed-paired differences**
  `Δ(seed, domain, c) = success(k=4) − success(k=1)`; the interaction contrast is
  `mean Δ at c ≥ 0.8 − mean Δ at c ≤ 0.4`. 95% CI by **seed-level bootstrap, 10 000
  resamples**, resampling seeds (the unit of independence) and carrying all coverage levels
  and all k for a resampled seed together.
* **Secondary** — model-edit distance to ground truth per round; **divergence-event rate**
  (a run in which held-out success *decreases* from one snapshot to the next within a seed).
* **Falsifier (required)** — divergence-event rate at c ≥ 0.8 vs c ≤ 0.4. If they are equal,
  the coverage mechanism is falsified regardless of the interaction CI and the paper says so.
* **Logged separately, never dropped** — `budget_exhausted_train/eval`, `no_plan_train/eval`,
  `parse_failures`, `empty_proposals`, `llm_errors`, `no_proposal_rounds`, `no_accept_rounds`.

---

## 4. Amendment register

| # | amendment | reason |
|---|---|---|
| A1 | Apparatus replaced: PATCH-BT executor → pyperplan world-model self-repair loop | v1 executor does not exist on this host; recorded in `A2_PREDECLARATION_2026-09-07.md` and §5 below |
| A2 | Verifier coverage made precise as a **stratified** subset of the lifted condition space `C` | the pre-declaration's two glosses ("fraction of the ground-truth conditions" / "fraction of the world the verifier can see") are both satisfied exactly by the stratified draw |
| A3 | Static predicates held fixed (not corrupted, not repaired, not sampled) | keeps the fact space and operator-name set identical across models, so a model change cannot be confounded with a state-space change |
| A4 | ~~`n_corrupt = 1`~~ **SUPERSEDED by A8** | the k=0-only variance rule selected a value that makes `k` degenerate; see A8 |
| A8 | `n_corrupt = 4` under the replacement rule (`n_corrupt ≥ max k`, then smallest with pooled-over-coverage k=4 success in (0,1) per domain) | A4's rule forced a one-error regime in which the loop converges in round 1, so success at k=1, 2 and 4 is identical in every run and the pre-registered interaction is 0.0000 by construction. Discovered on the first executed sub-grid, **before** the primary grid was run; the primary grid was relaunched at `n_corrupt = 4`. The 100 executed `n_corrupt = 1` blocks runs are retained as a labelled supplementary single-error arm (`evidence/runs_n1/`), not deleted. |
| A5 | Instances = 10 per domain (task01–10), not more | ≥10 required; gripper task11–12 cost ~5 s each under the *true* model and far more under corrupted ones, which would push the grid past the wallclock bound |
| A6 | **Proposer = deterministic search-based**, LLM demoted to a secondary blocks-only arm | pre-declared fallback triggered: LLM throughput failed the pilot (see §1). Stated in the paper. |
| A9 | LLM proposal parser fixed (`?`-prefix normalisation + list-name synonyms); all LLM rows produced under the buggy parser discarded and that arm re-run | the parse failures were ours, not the model's; reporting them as an LLM failure would have been a fabricated attribution |
| A10 | LLM secondary arm deleted and re-run under an exclusive writer lock | a stray second process running the pre-fix parser had written 24 of its 40 rows; the arm was contaminated and could not be repaired by deduplication |
| A7 | Plan budget tightened 1500 exp / 15 s → 1200 exp / 5.0 s before the run | ground truth needs ≤ 774 expansions and ≤ 2.6 s on the largest instance used, so the cap never binds on a correct model; it bounds pathological search under corrupted models. Exhaustion is logged. |

No seeds were cut. No coverage level was cut. Seed-pairing is intact.

---

## 5. PRESERVED — v1 escalation history (2026-09-07, before this amendment)

The first execution attempt for this paper **correctly refused to run** and escalated. Its
finding:

> **No pilot attempted.** The pre-registered executor at the path named in v1 of the
> pre-declaration contains no runnable code —
> only LaTeX compile artifacts of a paper about PATCH-BT (`.aux`, `.log`, `.out`) and an
> empty `patch_bt_agency_bundle/` folder. … Because there is no executor, there is no
> 60-second pilot to run and no way to determine "what coverage means operationally"
> without inventing one, which the pre-declaration explicitly forbids.
>
> Zero trace-runs. Zero wallclock burned on experiment execution. All 15 cells at N = 0.
> Headline interaction estimate: not computable. Divergence-event rates: not computable.
> Pre-registered claim status: **neither held nor refuted** — an infrastructure block, not
> an honest negative on the science.
>
> Deviation note: "the pre-declaration's Design section asserts the existence of 'the
> existing PATCH-BT executor' at the named path. That assertion is not true on the working
> machine as of 2026-09-07. Any re-plan that keeps this paper slot must update the
> pre-declaration to reflect the actual executor used … silent substitution of a different
> runnable, or of a synthesized fixture, would be a fabrication."

Corroborating machine-wide sweep: no behaviour-tree
or planning source anywhere under `<HOME>/code`, and no planning package (`pyperplan`,
`unified_planning`, `tarski`, `py_trees`) or planner binary (Fast Downward, VAL) installed.
**Zero ledger rows existed from v1**; nothing from v1 is carried forward.

The v2 apparatus in this document was declared in `A2_PREDECLARATION_2026-09-07.md`
(AMENDED) **before any data was collected**, and every number in the paper comes from runs
executed under it.

---

## 6. PRE-COMMITMENT — expanded LLM-proposer arm (A11), written 2026-09-07 BEFORE the run

**Why.** Two independent adversarial reviews and the domain audit converged on
the same objection: the primary grid's deterministic proposer emits
evidence-localised single condition toggles, and the corruption is four
condition toggles, so the proposal set is matched to the error family. The
result may be a property of the apparatus. A proposer whose candidate
distribution is *not* derived from the observed discrepancy is the only thing
that answers this. An LLM proposer is such a proposer, and at a neuro-symbolic
workshop it also supplies the neural component the primary arm lacks.

**A11 — the throughput bar was measured wrong, and the correction is
disclosed.** Amendment A6 demoted the LLM proposer on a pilot measurement of
`qwen3:8b` at 31--99 s per call, implying 10.5--20 h for 1200 proposal calls
against an 8 h budget. The *completed* 8-seed secondary arm
(`evidence/runs_llm/`, 40 runs) actually ran at **7.2 s per call** (1150 s of
LLM time over 159 calls, 1467 s wallclock total). The pilot figure was
5--14x pessimistic — most likely cold-model first-load latency, and it was
taken before the A9 parser fix. **The original throughput claim stands as what
we measured at the time and is reported as such; this pre-commitment records
that the bar was re-measured and cleared, and expands the arm accordingly.**

**Pre-committed design, fixed before the first row is written:**

- Grid: `DOMAINS = (blocks, gripper, logistics)` x `COVERAGES = (0.2, 0.4,
  0.6, 0.8, 1.0)` x `seeds 0..19` = **300 runs**, at exact parity with the
  primary deterministic grid (same domains, coverages, seeds, `n_corrupt = 4`,
  same planner budget, same `k in {0,1,2,4}` nesting).
- Proposer: `qwen3:8b` via local Ollama, `temperature = 0`, `seed = 7`,
  `think = false`, `num_predict = 360`, 150 s per-call timeout. Identical
  prompt and parser to the existing secondary arm (post-A9).
- **No fallback.** `runner.py` takes the `proposer == "llm"` branch, which
  never calls `evidence_candidates` or `unsolvable_candidates`. A round whose
  LLM proposal set is empty is counted as `no_proposal_rounds` and the model is
  left unchanged. There is no hybrid path and no silent substitution.
- Output: `evidence/runs_llm_full/` (new). The existing `evidence/runs_llm/`
  8-seed arm is **not** overwritten, not appended to, and not pooled.
- Namespace: `llmfull::`. Never pooled with the primary grid or with `llm::`.

**Reporting rule, fixed now:**

1. The arm is reported **whatever it shows** — including a null, a negative, or
   an interaction that contradicts the primary grid. It is a test of the
   primary result, so a disconfirming outcome is the informative one.
2. **Contamination stop-rule.** `parse_failures`, `llm_errors` and
   `empty_proposals` are logged per run. If any of these rates rises with job
   order (the signature of throttling, memory pressure, or a second writer —
   the failure that destroyed an earlier arm in this study and the
   arm), the run is **STOPPED and the arm EXCLUDED**, not repaired and not
   partially banked. The check is a comparison of the rate in the first half of
   the completed runs against the second half, in job order.
3. **Truncation rule.** If the run exceeds an 8 h wallclock bound it is stopped
   at the last *complete* (domain, coverage) cell. Partial cells are discarded,
   never reported as if full. The achieved cell count is reported as the actual
   N; no cell is padded, imputed or reweighted.
4. Reproducibility is already known to be imperfect for this proposer: the
   existing arm gave different trajectories in 4 of 7 temperature-0 repeats.
   This arm is therefore reported as one draw from a non-deterministic
   proposer, and that is stated.
5. Single-writer lock enforced by `run_llm_arm.py` (A10's fix).

---

## 7. PRE-COMMITMENT — A12, deterministic-budget replication grid

**Written 2026-09-07 BEFORE the replication grid is run. At the moment of
writing: the primary grid (300 runs, wallclock budget) is complete and
unchanged; the A11 LLM arm has written 31 of 300 rows; NO row of the
replication grid exists.**

### What is being changed, and why it is a repair rather than a choice

`core.plan()` bounds search two ways: `max_expansions = 1200` **and**
`max_seconds = 5.0`, the latter checked every 64 expansions. The wallclock
bound makes the search outcome depend on machine speed and load. This is not a
hypothesis; it was measured. Rebuilding the pinned stack (`pyperplan 2.1`,
fresh venv) and re-executing 12 primary-arm runs on a faster host reproduced
`edit_distance` and `verifier_score` **12 of 12, row for row**, but
`heldout_success` differed in **3 of 12**, all on gripper, always in the
direction of *more* success — instances that previously exhausted the 5 s bound
now finish inside it.

A metric that moves with machine load is a reproducibility defect on its face.
Removing the wallclock bound is therefore a repair of the apparatus, not a
parameter chosen to obtain a nicer answer. What *would* be illegitimate is
running both budgets and reporting whichever flatters the hypothesis; the
reporting rule below forbids exactly that, and is binding.

### The change, fixed now

- `max_seconds` becomes configurable via `NEMO_PLAN_MAX_SECONDS`, defaulting to
  `5.0` so that **the pre-registered code path is byte-identical unless the
  variable is set**. The replication grid runs with
  `NEMO_PLAN_MAX_SECONDS=inf`, which disables the wallclock check entirely.
- **`max_expansions` stays at 1200 — unchanged from A7, not re-tuned.** A7
  established that the uncorrupted model needs at most 774 expansions on the
  largest instance used, so the cap never binds on a correct model. Keeping it
  identical is what makes this a one-variable change.
- Grid: identical to the primary in every other respect — blocks, gripper,
  logistics x `c in {0.2,0.4,0.6,0.8,1.0}` x seeds 0..19, `n_corrupt = 4`,
  `k in {0,1,2,4}` nested, same instance split, same corruption RNG.
- Output: `evidence/runs_detbudget/` (new). `evidence/runs/` is **not**
  overwritten, appended to, or regenerated. Namespace: `det::`.

### Binding reporting rule

1. **Run once. Do not iterate on the cap.** If 1200 expansions turns out badly
   chosen under an unbounded clock, that fact is reported; a second cap is not
   tried.
2. **Both grids are reported side by side, whatever they show.**
3. **The wallclock grid remains the PRE-REGISTERED PRIMARY.** Every headline
   claim stays anchored to it. The expansions-only grid is reported as a
   *deterministic replication*; it supports or qualifies the primary claim and
   does not silently replace it.
4. **If the two grids agree**, the paper may say the interaction replicates
   under a fully deterministic budget, and that is a materially stronger
   result.
5. **If the two grids disagree, the disagreement is the finding** and is
   reported as prominently as agreement would have been. Disagreement would
   mean part of the original effect was a timeout artifact — a fact readers
   need more than we need a clean story. It may not be buried in an appendix,
   attributed to noise, or resolved by preferring the grid we like.
6. The replication is *confirmatory for nothing*: it re-estimates
   pre-registered quantities under a repaired apparatus. It adds no new
   hypothesis and licenses no new claim.

### Sequencing

The A11 LLM arm runs first and to completion; the replication grid starts only
after it, to avoid CPU contention inflating LLM call latency and tripping A11's
own contamination stop-rule. If only one can finish before
2026-09-10 23:59 UTC, the LLM arm has priority and this grid is handed back
unrun.
