#!/usr/bin/env python3
"""Figure scaffold -- recompute → assert → draw.

DEFAULT PATTERN:
  Every aggregate drawn by a figure script MUST be recomputed from raw per-unit
  evidence, asserted against the ledger within TOLERANCE, and only then drawn.
  This turns "the figure could drift from the prose" into "the build fails".
  Costs nothing: the figure must load the data anyway.

REQUIRED EDITS (search for TODO):
  - Set PAPER, RAW, LEDGER, OUT paths
  - Replace AGGREGATES dict with your paper's aggregate keys and recompute logic
  - Replace the draw block with your actual figure code

F-025 PATTERN (figure_claims.json):
  After drawing, write evidence/figure_claims.json with the claim_ids this
  figure draws.  The guard reads that file so a ledger row REPORTED IN A
  FIGURE counts as reported -- no redundant table required beside the figure.
  The link is auditable: this file reads the ledger and writes the declaration.

Usage:
  python3 analysis/make_figure.py            # normal build
  python3 analysis/make_figure.py --selftest # verify assertion machinery only
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["pdf.fonttype"] = 42   # embed Type 42, never Type 3
matplotlib.rcParams["ps.fonttype"] = 42
import matplotlib.pyplot as plt  # noqa: E402 (after backend set)

# ---------------------------------------------------------------------------
# Paths -- TODO: replace PAPER with your paper's short slug
# ---------------------------------------------------------------------------

HERE     = Path(__file__).resolve().parent
PAPER    = "TODO_paper_slug"                          # TODO: e.g. "chembl_censoring"
EVIDENCE = HERE.parent / "evidence"
RAW      = EVIDENCE / f"{PAPER}_raw.json"             # TODO: real raw evidence file
LEDGER   = EVIDENCE / f"{PAPER}_ledger.jsonl"         # TODO: real ledger file
OUT      = HERE.parent / f"fig_{PAPER}.pdf"           # TODO: adjust if needed
CLAIMS_OUT = EVIDENCE / "figure_claims.json"

# ---------------------------------------------------------------------------
# Tolerance -- declare once, used in every assertion
# ---------------------------------------------------------------------------

TOL = 5e-4      # ledger values are rounded to 4 dp; adjust for your metric precision


# ---------------------------------------------------------------------------
# Recompute functions -- TODO: replace with your paper's aggregate logic
# ---------------------------------------------------------------------------

def recompute_aggregates(raw: dict) -> dict[str, float]:
    """Return {claim_id: recomputed_value} from raw per-unit evidence.

    TODO: replace the two example keys below with your paper's actual
    aggregate computation.  Each key must match a claim_id in the ledger.

    Guidelines:
      - Use numpy array operations, NOT np.vectorize in inner loops (see
        template/analysis/PERFORMANCE.md).
      - Hoist boolean masks out of any iterative loop before calling this.
    """
    # TODO: replace with real keys from your experiment
    # Example: compute mean over per-unit observations
    units = raw.get("units", [])                    # TODO: real field name
    if not units:
        raise ValueError("raw evidence has no 'units' field -- check RAW path")

    values = np.array([u["outcome"] for u in units], dtype=float)  # TODO: field name

    return {
        # TODO: add one entry per aggregate the figure draws
        "main::n_units":    float(len(values)),
        "main::mean":       float(values.mean()),
        "main::sd":         float(values.std(ddof=1)),
    }


# ---------------------------------------------------------------------------
# Core: assert recomputed aggregates against ledger
# ---------------------------------------------------------------------------

def load_ledger(path: Path) -> dict[str, dict]:
    """Return {claim_id: row} from a JSONL ledger."""
    rows: dict[str, dict] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            row = json.loads(line)
            rows[row["claim_id"]] = row
    return rows


def assert_aggregates(
    recomputed: dict[str, float],
    ledger: dict[str, dict],
    tol: float = TOL,
) -> list[str]:
    """Assert every recomputed aggregate against its ledger row.

    Returns the list of claim_ids checked (for figure_claims.json).
    Calls sys.exit(1) on the first disagreement -- hard abort, not a warning.
    The build MUST fail when evidence and ledger are out of sync.
    """
    drawn: list[str] = []
    for cid, got in recomputed.items():
        if cid not in ledger:
            sys.exit(
                f"[assert] claim_id '{cid}' not found in ledger -- "
                f"run the aggregates script before make_figure.py"
            )
        row = ledger[cid]
        if row.get("verdict", "") != "SUPPORTED":
            sys.exit(
                f"[assert] claim_id '{cid}' has verdict '{row.get('verdict')}' "
                f"in ledger -- only SUPPORTED rows may be drawn."
            )
        want = float(row["value"])
        if abs(got - want) > tol:
            sys.exit(
                f"[assert] {cid}: recomputed {got:.8g} disagrees with ledger "
                f"{want:.8g} (tol {tol}).  Evidence and ledger are out of sync."
            )
        drawn.append(cid)
    return drawn


# ---------------------------------------------------------------------------
# Draw -- TODO: replace with your actual figure
# ---------------------------------------------------------------------------

def draw(raw: dict, ledger: dict[str, dict], out: Path) -> None:
    """Produce the figure PDF.

    At this point every aggregate has been asserted; reading from ledger here
    is safe and preferred for annotation marks (mean, CI endpoints), because
    the assertion above guarantees ledger == recomputed.

    TODO: replace the stub below with your paper's actual figure code.
    """
    fig, ax = plt.subplots(figsize=(4, 3))

    # TODO: replace with real per-unit data
    units = raw.get("units", [])
    values = np.array([u["outcome"] for u in units], dtype=float)

    ax.hist(values, bins=20, color="0.5", edgecolor="white", linewidth=0.5)

    # annotate with the ledger mean (guaranteed == recomputed above)
    mean_val = float(ledger["main::mean"]["value"])
    ax.axvline(mean_val, color="black", lw=1.2, ls="--", label=f"mean = {mean_val:.3f}")

    ax.set_xlabel("outcome (TODO: units)")      # TODO
    ax.set_ylabel("targets")                    # TODO
    ax.set_title("TODO: figure title")         # TODO
    ax.legend(fontsize=8)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    fig.savefig(out, bbox_inches="tight", dpi=400)
    plt.close(fig)
    print(f"[figure] wrote {out}")


# ---------------------------------------------------------------------------
# Selftest -- synthetic fixture, no real data files needed
# ---------------------------------------------------------------------------

SELFTEST_N = 20  # number of synthetic units


def _make_synthetic_fixture(perturb_ledger: bool = False) -> tuple[dict, dict]:
    """Return (raw_dict, ledger_dict) for selftest.

    If perturb_ledger=True the ledger mean is shifted by 0.5 (above TOL),
    so assert_aggregates MUST abort non-zero.
    """
    rng = np.random.default_rng(42)
    values = rng.normal(loc=2.0, scale=0.5, size=SELFTEST_N)

    raw = {"units": [{"outcome": float(v)} for v in values]}

    true_mean = float(values.mean())
    ledger_mean = (true_mean + 0.5) if perturb_ledger else true_mean

    ledger: dict[str, dict] = {
        "main::n_units": {
            "claim_id": "main::n_units",
            "value": float(SELFTEST_N),
            "verdict": "SUPPORTED",
            "verdict_reason": "synthetic selftest fixture",
            "must_print": True,
        },
        "main::mean": {
            "claim_id": "main::mean",
            "value": round(ledger_mean, 4),
            "verdict": "SUPPORTED",
            "verdict_reason": "synthetic selftest fixture",
            "must_print": True,
        },
        "main::sd": {
            "claim_id": "main::sd",
            "value": round(float(values.std(ddof=1)), 4),
            "verdict": "SUPPORTED",
            "verdict_reason": "synthetic selftest fixture",
            "must_print": False,  # decomposition/robustness row: recorded for audit,
            # must_print=False because the range it supports is what gets typeset,
            # not the SD itself. (canonical D2 example)
        },
    }
    return raw, ledger


def run_selftest() -> int:
    """Run the assertion machinery on a synthetic fixture.

    Demonstrates:
      (i)  PASS  when recomputed aggregates agree with the ledger.
      (ii) non-zero abort when a recomputed aggregate disagrees (mean perturbed by 0.5).

    Returns 0 if both cases behave as expected, 1 otherwise.
    """
    print("[selftest] case (i): expect PASS on a consistent fixture")
    raw, ledger = _make_synthetic_fixture(perturb_ledger=False)
    try:
        recomputed = recompute_aggregates(raw)
        drawn = assert_aggregates(recomputed, ledger)
        print(f"[selftest] PASS -- {len(drawn)} claim_ids asserted without disagreement")
        print(f"[selftest]   {drawn}")
    except SystemExit as exc:
        print(f"[selftest] UNEXPECTED FAILURE: {exc}")
        return 1

    print()
    print("[selftest] case (ii): expect non-zero abort when ledger mean is perturbed +0.5")
    raw_bad, ledger_bad = _make_synthetic_fixture(perturb_ledger=True)
    try:
        recomputed_bad = recompute_aggregates(raw_bad)
        assert_aggregates(recomputed_bad, ledger_bad)
        print("[selftest] ERROR: assert_aggregates did NOT abort on a mismatched aggregate")
        return 1
    except SystemExit as exc:
        msg = str(exc)
        if "disagrees with ledger" in msg:
            print(f"[selftest] PASS -- non-zero abort correctly triggered:")
            print(f"[selftest]   {msg[:120]}")
        else:
            print(f"[selftest] UNEXPECTED EXIT message: {exc}")
            return 1

    print()
    print("[selftest] all cases passed")
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--selftest", action="store_true",
                        help="Run assertion machinery on a synthetic fixture and exit")
    args = parser.parse_args(argv)

    if args.selftest:
        return run_selftest()

    # --- load real evidence ---
    if not RAW.exists():
        sys.exit(f"[figure] raw evidence not found: {RAW}\n"
                 f"         run the aggregates script first, or update the RAW path")
    if not LEDGER.exists():
        sys.exit(f"[figure] ledger not found: {LEDGER}\n"
                 f"         run the aggregates script first, or update the LEDGER path")

    raw    = json.loads(RAW.read_text())
    ledger = load_ledger(LEDGER)

    # --- recompute ---
    recomputed = recompute_aggregates(raw)

    # --- assert (aborts on any disagreement) ---
    drawn = assert_aggregates(recomputed, ledger)

    # --- draw ---
    draw(raw, ledger, OUT)

    # --- F-025: declare drawn claim_ids so guard counts them as reported ---
    CLAIMS_OUT.write_text(
        json.dumps({"figure": OUT.name, "claim_ids": sorted(set(drawn))}, indent=1) + "\n"
    )
    print(f"[figure] declared {len(set(drawn))} claim_ids -> {CLAIMS_OUT}")
    print("[figure] all recomputed aggregates reproduce the ledger within tolerance")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
