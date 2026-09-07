# EXPERIMENT_REPORT — nemo-plan-repair-coverage

**Date:** 2026-09-07 UTC
**Apparatus:** v2 (pyperplan world-model self-repair loop) per `A2_PREDECLARATION_2026-09-07.md`
**Verdict:** **MIXED.** The pre-registered coverage×k **interaction holds** and is large.
The pre-registered **mechanism** — that low verifier coverage makes additional repair rounds
*degrade* performance — is **refuted**, and the required falsifier **fires**.

> The v1 escalation (pre-registered PATCH-BT executor absent from this host; zero runs, zero
> ledger rows) is preserved in `evidence/DESIGN_NOTES.md` §5 and
> `evidence/DESIGN_NOTES.v1.bak`. Nothing from v1 is carried forward.

---

## 1. Pilot status — **PASSED**

60-second foreground pilot ran end-to-end on the real planner in **0.7 s**: blocks, seed 0,
c=0.6, one repair round — corrupted model → plan → execute against ground-truth semantics →
repair proposal → verifier adjudication → held-out evaluation.

Ground-truth sanity check: with the uncorrupted domain the planner finds and successfully
executes a plan on **30/30** instances (10 per domain).

## 2. Planner, domains, proposer

| | |
|---|---|
| planner | **pyperplan 2.1** (`pip install pyperplan`, venv `.venv-nemo`), greedy best-first over hFF, capped at 1200 expansions / 5.0 s per call |
| domains | **blocks**, **gripper**, **logistics** — IPC benchmarks vendored from `github.com/aibasel/pyperplan` @ `586b99f0`, checksummed in `external/pyperplan-benchmarks/SHA256SUMS.txt` |
| instances | 10 per domain (task01–10); **train** 01/03/05/07/09, **held-out** 02/04/06/08/10 — held-out instances are never used during repair |
| corruption | `n_corrupt = 4` seeded condition toggles (2 drops of true conditions, 2 additions of false ones), **identical across all coverage levels within a seed** |
| coverage `c` | stratified random subset `V ⊆ C` containing a fraction `c` of the domain's conditions *and* of its whole condition space; verifier scores candidates by agreement with truth **on `V` only** |
| **proposer** | **DETERMINISTIC search-based** — the pre-declaration's own fallback clause, triggered because the LLM proposer failed the pilot on throughput (§7) |

## 3. Runs completed

| arm | runs | seeds | domains | per (c,k) cell |
|---|---|---|---|---|
| **primary** (deterministic, `n_corrupt=4`) | **300** | 20 | 3 | **60 seed-paired runs** (≥20 required) |
| supplementary single-error (`n_corrupt=1`, blocks) | 100 | 20 | 1 | 20 |
| secondary LLM proposer (`qwen3:8b`, blocks) | 40 | 8 | 1 | 8 |

Full grid wallclock ≈ **50 min** (projected 3.3 h; the tightened plan budget beat the
projection). No seeds were cut, no coverage level was cut, seed-pairing intact.

## 4. Primary result — held-out plan-execution success

Mean over 60 seed-paired runs per cell, seed-clustered bootstrap 95% CI (10 000 resamples,
unit = seed):

| coverage `c` | k=0 | k=1 | k=2 | k=4 |
|---|---|---|---|---|
| 0.2 | 0.013 [0.003, 0.027] | 0.027 [0.013, 0.040] | 0.073 [0.030, 0.127] | 0.173 [0.087, 0.273] |
| 0.4 | 0.013 [0.003, 0.027] | 0.023 [0.010, 0.037] | 0.150 [0.073, 0.233] | 0.293 [0.193, 0.397] |
| 0.6 | 0.013 [0.003, 0.027] | 0.017 [0.007, 0.030] | 0.173 [0.070, 0.300] | 0.420 [0.263, 0.583] |
| 0.8 | 0.013 [0.003, 0.027] | 0.037 [0.010, 0.073] | 0.250 [0.150, 0.370] | 0.657 [0.540, 0.767] |
| 1.0 | 0.013 [0.003, 0.027] | 0.043 [0.017, 0.080] | 0.317 [0.210, 0.433] | 0.900 [0.813, 0.970] |

**Negative control:** at k=0 every coverage level reads exactly 0.013 — before any repair all
five arms share an identical corrupted model, so coverage *must* have zero effect there. The
coverage main effect at k=0 is **+0.0000 [+0.0000, +0.0000]**. Any nonzero value would have
indicated a leak.

### Headline interaction estimate

Seed-paired difference `Δ = success(k=4) − success(k=1)`; interaction = mean Δ at c ≥ 0.8
minus mean Δ at c ≤ 0.4.

> **interaction = +0.530, 95% CI [+0.447, +0.615]** — excludes zero.
>
> components: Δ at c ≥ 0.8 = **+0.738 [+0.652, +0.820]**; Δ at c ≤ 0.4 = **+0.208 [+0.127, +0.297]**

**The pre-registered primary claim HOLDS.** Verifier coverage strongly modulates how much
recursive model repair buys per round.

**Robustness — not driven by one domain.** The interaction is positive with a CI excluding
zero in each domain computed alone:

| domain | interaction | 95% CI |
|---|---|---|
| blocks | +0.560 | [+0.390, +0.725] |
| gripper | +0.600 | [+0.435, +0.760] |
| logistics | +0.430 | [+0.275, +0.585] |

**Coverage main effect grows with k** — the effect is genuinely about *recursion*, not a
one-shot advantage: k=0 **+0.000** [0.000, 0.000]; k=1 **+0.015** [−0.003, +0.045] (includes
zero); k=2 **+0.172** [+0.097, +0.248]; k=4 **+0.545** [+0.458, +0.630].

## 5. Falsifier — **FIRES**

Pre-declared: *"if divergence events occur at the same rate in high-coverage (c ≥ 0.8) and
low-coverage (c ≤ 0.4) cells, the coverage mechanism is falsified regardless of the
interaction CI, and the paper says so."*

| | rate | 95% CI | raw |
|---|---|---|---|
| c ≤ 0.4 | 0.0056 | [0.0000, 0.0139] | **2 / 360** transitions |
| c ≥ 0.8 | 0.0083 | [0.0000, 0.0222] | **3 / 360** transitions |
| **gap (high − low)** | **+0.0028** | **[−0.0056, +0.0111]** | — |

The CI covers zero, and the point estimate points the *wrong way* (marginally **more**
divergence at high coverage). Divergence events are vanishingly rare in both bands.

**We therefore report the pre-registered mechanism as REFUTED.** Low verifier coverage does
**not** make the self-repair loop amplify model error. The pre-declaration's wording — *"at
low coverage, additional repair rounds **degrade** success (the self-improvement loop
amplifies model error)"* — is not what happens. What happens is **stalling, not divergence**:
under-verified repair simply stops making progress.

This is the substantive correction the falsifier existed to force, and it changes the paper's
message. On these domains the risk of recursive self-improvement under weak verification is
*stagnation*, not self-poisoning.

## 6. Secondary — model-edit distance to ground truth

Mean `|M △ M*|` over the condition space (starts at 4 by construction):

| coverage band | k=0 | k=1 | k=2 | k=4 |
|---|---|---|---|---|
| c ≤ 0.4 | 4.000 | 3.525 | 3.225 | **3.017** |
| c ≥ 0.8 | 4.000 | 3.075 | 2.208 | **1.183** |

Both bands move **toward** truth, never away — the mechanistic counterpart of the falsifier
result. High coverage removes 70.4% of the seeded error by k=4; low coverage removes 24.6%
and has nearly flattened by k=2. The low-coverage loop does not corrupt its model; it runs
out of ability to tell good repairs from bad ones and stops improving.

## 7. Proposer: the pre-declared LLM fallback, and why it fired

Ollama was up; `qwen3:8b` and `qwen2.5-coder:14b` available.

* `qwen2.5-coder:14b` — **3/3 calls timed out** at >120 s. Unusable.
* `qwen3:8b`, thinking disabled (`think:false`, verified: raw output carried no reasoning
  tokens) — 31.6 s on the first probe, 55–99 s on real prompts.
* The full grid needs **1200 proposal calls** → 10.5–20 h of LLM time alone, against an ≤8 h
  bound.

**Throughput failure ⇒ the pre-declaration's fallback clause fires ⇒ the primary grid uses
the deterministic search-based proposer.** Stated here, in `evidence/DESIGN_NOTES.md` (A6),
and it must be stated in the paper. It is not hidden.

**Correction — the parse failures were ours, not the model's.** Early LLM runs logged 16
parse failures per trajectory. Inspecting a raw response showed **two bugs in our own
parser**: it stripped the leading `?` from parameter names (so no proposal could ever match a
legal slot) and rejected `"precondition"` as a synonym for `"pre"`. The very first rejected
proposal was `put-down / precondition / (holding ?x)` — *the exact seeded corruption*, i.e.
the correct repair, discarded by our code. After the fix the same prompt yields **0 parse
failures**. **Every LLM row produced under the buggy parser was deleted and that arm re-run**;
publishing them would have attributed a harness defect to the model.

The arm was then found **contaminated a second time**: a stray second writer process still
running the pre-fix parser had produced 24 of its 40 rows (timestamps out of order; the
tell-tale `parse_failures = 16` signature in three of five cells). Deduplication could not
repair it, so the whole arm was discarded and re-run under an exclusive writer lock. A
by-product worth recording: repeated configurations (same seed, same corruption,
`temperature = 0`, fixed `seed`) produced **different** repair trajectories in 4 of 7 cases —
the local LLM proposer is **not reproducible** on this stack.

## 8. Supplementary single-error arm (`n_corrupt = 1`, blocks, 100 runs)

Retained from the first configuration, whose selection rule was superseded (amendment A4 →
A8; that rule picked a corruption magnitude which makes `k` degenerate). It is reported
because it isolates the coverage effect at a single repair step:

| c | k=0 | k=1 = k=2 = k=4 |
|---|---|---|
| 0.2 | 0.370 | 0.610 |
| 0.4 | 0.370 | 0.610 |
| 0.6 | 0.370 | 0.800 |
| 0.8 | 0.370 | 0.950 |
| 1.0 | 0.370 | **1.000** |

Coverage main effect at k=1 = **+0.365 [+0.210, +0.540]**. With one seeded error the loop
converges in round 1 and halts, so success at k=1, 2 and 4 is identical in **every one of the
100 runs** and the interaction is **0.0000 by construction, not by evidence** — which is
precisely why this configuration was replaced for the primary grid.

## 9. Integrity counters (summed over the 300 primary runs; never dropped)

| counter | value |
|---|---|
| plan calls | 12 000 |
| budget exhausted (train / eval) | 193 / 240 |
| no plan found (train / eval) | 3207 / 3199 |
| rounds proposing nothing | 110 |
| rounds accepting nothing | 458 |
| proposal parse failures / LLM errors | 0 / 0 (deterministic proposer) |

`no_plan_*` is high by design: `n_corrupt = 4` frequently makes the agent's model
unplannable, which is the regime the repair loop exists to escape. Budget exhaustion affects
193/6000 train and 240/6000 eval plan calls (3.2% / 4.0%); the cap never binds on the
uncorrupted model (≤774 expansions, ≤2.6 s on the largest instance used).

## 10. LLM secondary arm — directionally consistent, but far weaker and underpowered

Re-run cleanly under the writer lock: `qwen3:8b`, blocks, 5 coverages × 8 seeds = **40 runs**
(40 unique configurations, 0 duplicates), `n_corrupt = 4`. Health after the parser fix: 159
proposal calls, **0 LLM errors**, **10 parse failures** (down from 337 on the contaminated
arm), 0 empty proposals, 1 round with no proposal.

**Held-out success is 0.000 in every cell except c=0.8, k=4 = 0.125 [0.000, 0.375].** The LLM
proposer never repairs a 4-error model enough to restore plan execution on held-out
instances, where the deterministic proposer reaches 0.900 at c=1.0.

Model-edit distance does move, and in the same direction as the primary arm:

| coverage band | k=0 | k=1 | k=2 | k=4 |
|---|---|---|---|---|
| c ≤ 0.4 | 4.000 | 3.500 | 3.438 | **3.438** |
| c ≥ 0.8 | 4.000 | 3.250 | 2.750 | **2.625** |

Interaction on this arm = **+0.0625 [+0.0000, +0.1875]** — the lower bound touches zero, so at
8 seeds **this arm cannot resolve the interaction**. It is reported as directional support
only: high coverage moves the model closer to truth than low coverage under an LLM proposer
too (4.00→2.63 vs 4.00→3.44), but the arm is underpowered and the proposer is substantially
weaker at repair than the deterministic one.

Numbers live in `evidence/nemo_plan_repair_coverage_llm_secondary_ledger.jsonl` under the
`llm::` namespace, with their own N, and are **never pooled** with the primary grid.

## 11. Verdict

| pre-registered element | outcome |
|---|---|
| coverage × k interaction non-zero | **HELD** — +0.530 [+0.447, +0.615], CI excludes zero, replicated in all 3 domains |
| additional rounds **degrade** success at low coverage | **REFUTED** — low-coverage runs still improve (+0.208 paired gain); they do not degrade |
| divergence-event rate higher at low coverage (falsifier) | **FALSIFIER FIRES** — 0.0056 vs 0.0083, gap +0.0028 [−0.0056, +0.0111], covers zero |
| model-edit distance moves toward truth faster at high coverage | **HELD** — 4.00→1.18 vs 4.00→3.02 |

**Overall: MIXED.** The honest claim is that verifier coverage strongly governs *how far*
recursive world-model repair gets, but that the failure mode under weak verification is
**stagnation, not divergence** — the pre-registered amplification mechanism did not occur.
Both halves must appear in the abstract.

## 12. Reproduction

```bash
V=<REPO_ROOT>/.venv-nemo/bin/python
$V analysis/run_grid.py --full --proposer deterministic --seeds 20 --n-corrupt 4 \
      --out evidence/runs
$V analysis/aggregate.py          --runs evidence/runs --tag primary --boot 10000
$V analysis/verify_independent.py --runs evidence/runs --tag primary --boot 10000
$V analysis/build_manifest.py
$V analysis/make_evidence_figure.py --runs evidence/runs --tag primary \
      --out figures/coverage_k_evidence.pdf
```

* **Ledgers** — `evidence/nemo_plan_repair_coverage_{primary,n1_single_error,llm_secondary}_ledger.jsonl`
  plus `*_aggregates.jsonl`; raw per-run rows in `evidence/runs*/cell_*.jsonl`.
* **Stamp manifest** — `analysis/build_manifest.py` merges the per-arm manifests in
  `evidence/manifests/` into the single
  `evidence/nemo_plan_repair_coverage_stamp_manifest.json` that `guard.py` consumes, aborting
  on any claim-id collision. (Arms are namespaced `""`, `n1::`, `llm::`; without this the
  guard would silently check the paper against whichever manifest sorted first.)
* **Figure** — `figures/coverage_k_evidence.pdf`, built by recompute-assert-draw: every
  plotted value is recomputed from raw JSONL and asserted against the ledger (31 values) and
  its SUPPORTED verdict before anything is drawn.
* **Independent check** — `analysis/verify_independent.py` recomputes the headline numbers
  with code sharing no functions with `aggregate.py` and a different bootstrap RNG stream:
  **24/24 agreement** on the primary arm, 24/24 on the supplementary arm.
