# Reproducibility Artifact — nemo-plan-repair-coverage

**Paper:** *Recursive World-Model Self-Repair in PDDL Domains: Verifier Coverage Is the
Binding Constraint, and Under-Verified Loops Stall Rather Than Diverge.*
Enrique Zueco, David Scott Lewis, Haley Yi (AIXC Research).

**Venue:** NEmo — Neuro-Symbolic Embodied Intelligence, NeurIPS 2026 (Workshop), poster.

This repository holds the reproducibility artifacts for the paper. Absolute paths have
been replaced by placeholders (`<REPO_ROOT>`, `<HOME>`). The manuscript itself
(`main.tex` / `main.pdf`) is not part of this repository.

**Camera-ready addition.** `analysis/llm_full_excluded_camera_ready.py` recomputes,
from the raw records in `evidence/runs_llm_full/`, the descriptive table the paper's
appendix reports for the full-parity LLM-proposer grid (A11), and writes
`evidence/llm_full_excluded_camera_ready.json`. That grid was excluded by its
pre-committed contamination stop-rule; no claim in the paper rests on it.

---

## What the paper claims

On classical planning domains, the interaction between **verifier coverage** (the fraction
of the world-model's condition space the verifier can check) and **repair rounds k** has a
non-zero effect on plan-execution success in a recursive self-repair loop. At low coverage,
additional repair rounds may degrade success (the self-improvement loop amplifies model
error). The claims are pre-registered in `A2_PREDECLARATION_2026-09-07.md` (amended from
v1 — the original apparatus was absent from this host; the amendment replaces it with a
fully runnable one, declared before any data were collected).

**Outcome:** The pre-registered coverage×k interaction holds and is large. However, the
specific direction at low coverage (degradation) is **refuted** on the observed data
(the required falsifier fires); see `EXPERIMENT_REPORT.md` for the full account.

---

## How to reproduce

### Prerequisites

- **Python 3.14** (tested on 3.14.7, macOS arm64)
- `pip install pyperplan` — or use the provided venv recipe in `evidence/DESIGN_NOTES.md`
- IPC benchmark PDDL files vendored in `external/pyperplan-benchmarks/`
  (shipped in this bundle; SHA-256 in `external/pyperplan-benchmarks/SHA256SUMS.txt`)
- For the LLM secondary arm: **Ollama** with `qwen3:8b` served locally

### Reproduce in order

```bash
# 1. Set up the Python environment
python3 -m venv .venv-nemo
source .venv-nemo/bin/activate
pip install pyperplan

# 2. Run the full deterministic grid (primary arm)
#    Grid: 3 domains × 5 coverage levels × 3 repair rounds × ≥20 seeds
cd analysis
python3 run_grid.py --full

# 3. Run the LLM secondary arm (requires Ollama + qwen3:8b)
python3 run_llm_arm.py

# 3b. Run the A12 deterministic-budget replication grid.
#     Identical to the primary grid in every respect except that the wallclock
#     bound is disabled, leaving the 1200-expansion cap as the only budget.
#     Writes evidence/runs_detbudget/ (namespace det::); it never touches
#     evidence/runs/. The wallclock grid remains the pre-registered primary.
NEMO_PLAN_MAX_SECONDS=inf python3 run_grid.py --full --out ../evidence/runs_detbudget

# 4. Aggregate and verify
python3 aggregate.py
python3 guard.py --strict

# 5. Reproduce figures
python3 make_figure.py
python3 make_evidence_figure.py
```

All numeric results pass through the ledgers in `evidence/` and are verified by
`guard.py` against the stamp manifest.

---

## File inventory

| Path | Description |
|------|-------------|
| `A2_PREDECLARATION_2026-09-07.md` | Pre-registration v2 (binding design, before any data; amendment record included) |
| `CLAIMS.md` | Machine-readable claim list with ledger cross-references |
| `DOMAIN_AUDIT.md` | Domain validity audit |
| `EXPERIMENT_REPORT.md` | Post-hoc report (MIXED verdict — interaction confirmed, direction refuted) |
| `analysis/run_grid.py` | Primary deterministic grid runner |
| `analysis/run_llm_arm.py` | LLM-proposer secondary arm |
| `analysis/aggregate.py` | Ledger aggregation |
| `analysis/guard.py` | Anti-fabrication guard (E1–E7) |
| `analysis/make_figure.py` | Main figure |
| `analysis/make_evidence_figure.py` | Evidence figure (supp.) |
| `analysis/wm_repair/` | Core world-model repair loop implementation |
| `external/pyperplan-benchmarks/` | Vendored IPC benchmark PDDL (blocks, gripper, logistics) with provenance and SHA-256 sums |
| `analysis/build_manifest.py` | Manifest builder |
| `evidence/DESIGN_NOTES.md` | Full operational record, software versions, amendments |
| `evidence/nemo_plan_repair_coverage_primary_ledger.jsonl` | Primary-arm ledger |
| `evidence/nemo_plan_repair_coverage_llm_secondary_ledger.jsonl` | LLM-arm ledger |
| `evidence/nemo_plan_repair_coverage_n1_single_error_ledger.jsonl` | N=1 single-error ledger |
| `evidence/nemo_plan_repair_coverage_detbudget_ledger.jsonl` | A12 deterministic-budget replication ledger (`det::` namespace) |
| `evidence/*_aggregates.jsonl` | Per-arm aggregates |
| `evidence/nemo_plan_repair_coverage_stamp_manifest.json` | Stamp manifest |
| `evidence/manifests/` | Per-arm manifests |
| `evidence/runs/`, `evidence/runs_llm/`, `evidence/runs_n1/`, `evidence/runs_llm_full/`, `evidence/runs_detbudget/` | Per-cell per-seed run records |
| `refs.bib` | Bibliography (BibTeX) |
| `build.guard.log` | Anti-fabrication guard output for the submitted manuscript: every stamped cell resolved against the manifest |
| `lit/` | Literature notes, novelty check, citation verification log |

---

## Software versions (from `evidence/DESIGN_NOTES.md`)

| Component | Version |
|-----------|---------|
| Python | 3.14.7 |
| pyperplan | 2.1 |
| planner search | greedy best-first over hFF |
| LLM proposer | qwen3:8b via Ollama (secondary arm) |
| Platform | macOS (Darwin 24.6.0), arm64 |

---

## What is NOT included and why

| Excluded | Reason |
|----------|--------|
| `main.tex` / `main.pdf` | The manuscript is not part of the artifact repository |
| `data/` | No downloaded corpora in this paper; the IPC benchmark PDDL is vendored in `external/pyperplan-benchmarks/` (164 KB, provenance and hashes in that directory) |
| `__pycache__/` | Python bytecode |
| `.git/` | Repository history |
