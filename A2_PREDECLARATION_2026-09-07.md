# A2 Pre-declaration — nemo-plan-repair-coverage (AMENDED 2026-09-07, supersedes v1)

**Date:** 2026-09-07 (UTC) · **Venue:** NEmo — Neuro-Symbolic Embodied Intelligence, NeurIPS 2026
(`NeurIPS.cc/2026/Workshop/NEmo`, deadline 2026-09-10 23:59 UTC) · **Track:** Short paper (4 pages
body) · **Blind:** double (NeurIPS 2026 template, `dblblindworkshop`).

## Amendment record (mandatory — read before citing v1)

Version 1 of this pre-declaration specified experiments on an existing behavior-tree plan-repair
executor believed to be available locally. **That executor does not exist.** An asset audit found
only pdflatex byproducts at the recorded location and no behavior-tree or planning code anywhere
on this host; no planning package (pyperplan, unified-planning, tarski,
py_trees) or planner binary (Fast Downward, VAL) was installed. Zero traces were run under v1 and
no ledger rows exist from it. This amendment replaces the apparatus with one that is actually
runnable, keeps the same scientific question, and is declared **before** any data is collected.

## Pre-registered claim (primary)

An agent that recursively repairs **its own symbolic world model** (PDDL action preconditions and
effects) from execution failures improves monotonically only when the verifier it repairs against
checks a sufficient fraction of the true model's conditions. Formally: on classical planning
domains, the **verifier coverage × repair-round (k) interaction** has a non-zero effect on
plan-execution success; at low coverage, additional repair rounds **degrade** success (the
self-improvement loop amplifies model error), while at high coverage they improve it.

## Design (fixed before any run)

- **Apparatus (new, runnable):** a self-repair loop over PDDL domain models.
  - Environment: classical IPC domains shipped with an installable planner (`pyperplan` and/or
    `unified-planning`, both pip-installable pure Python; a ground-truth domain file defines the
    real dynamics). Domains: at least 3 (e.g. blocksworld, gripper, logistics), ≥10 problem
    instances each. Exact domains/instances and their provenance recorded in
    `evidence/DESIGN_NOTES.md` before the first full run.
  - The agent holds a **corrupted copy** of the domain (preconditions/effects perturbed by a
    seeded corruption operator — drop/add/flip a fixed number of literals). It plans with its
    corrupted model, executes against the **ground-truth simulator**, observes failures, and
    proposes model repairs. Proposer: an LLM served locally via Ollama (`qwen3:8b` or
    `qwen2.5-coder:14b`; recorded before the run) — if LLM throughput or parse reliability fails
    the pilot, a deterministic search-based repair proposer is used instead and stated explicitly
    in the paper (never hidden).
  - **Verifier coverage c** — the operationalisation of "coverage": the repair loop is allowed to
    check its candidate model against a random subset containing a fraction *c* of the ground-truth
    domain's conditions (preconditions + effects), sampled per seed and held fixed within a run.
    c ∈ {0.2, 0.4, 0.6, 0.8, 1.0}. This is the fraction of the world the verifier can see —
    everything else must be inferred, exactly the partial-verification regime real embodied agents
    face.
  - Repair rounds k ∈ {1, 2, 4}; ≥20 seed-paired runs per (c, k) cell; the same corrupted start
    model and problem set across k for a given seed (nested design: k=4 extends k=2 extends k=1).
- **Primary outcome:** plan-execution success rate on held-out problem instances (instances never
  used during repair). Interaction between c and k estimated on seed-paired differences; 95% CI by
  seed-level bootstrap (≥10,000 resamples). Unit of independence = seed.
- **Secondary:** model-edit distance to ground truth (did repairs move the model closer or further
  from truth?); rate of *divergence events* (success decreasing from k to k+1 within a seed).
- Every number enters the paper only via `evidence/` ledger rows → stamped cells.

## Refutation criterion / honest-negative fallback

If the paired 95% CI on the coverage×k interaction includes zero, the claim is refuted and the
paper reports the honest negative: "verifier coverage does not measurably modulate recursive model
repair on these domains" — submitted in the same track.

## Rival mechanisms (gate 13b)

1. **Corruption-severity confound** — low-coverage cells might coincide with harder corruptions;
   mitigated by using the *same* seeded corruption across all coverage levels within a seed.
2. **Repair-budget exhaustion** — apparent divergence at high k could be timeouts/parse failures,
   not erroneous repairs; budget exhaustion and proposal-parse failures are logged separately and
   reported, never silently dropped.
3. **Planner stochasticity** — success drift unrelated to model quality; bounded by a fixed planner
   configuration and by the k=1 arm as a within-seed control.

**Discriminator/falsifier:** if divergence events occur at the same rate in high-coverage (c ≥ 0.8)
and low-coverage (c ≤ 0.4) cells, the coverage mechanism is falsified regardless of the interaction
CI, and the paper says so.

## Feasibility bound

60-second foreground pilot (1 domain × 1 seed × 1 round) must run end-to-end on the real planner
before any full run. Full grid (5 c × 3 k × ≥20 seeds × ≥3 domains) targeted at ≤8 h wallclock; if
projections exceed that, reduce the number of seeds — never the seed-pairing or the coverage grid —
and record the reduction as a further amendment before running.
