#!/usr/bin/env python3
"""
make_evidence_figure.py -- the ONE dense evidence figure, via recompute-assert-draw.

RECOMPUTE: every plotted number is recomputed here from the raw per-run JSONL in
           evidence/runs/, not read from the aggregate ledger.
ASSERT:    each recomputed value is asserted equal to the corresponding ledger /
           stamp-manifest row.  Any drift aborts before a pixel is drawn.
DRAW:      only then is the figure rendered.

Panel A  held-out plan-execution success vs k, one line per verifier coverage,
         with seed-clustered 95% bootstrap CIs on each point.
Panel B  seed-paired delta success(k=4) - success(k=1) vs coverage, with CI --
         the contrast the pre-registered interaction is built from.
Panel C  model-edit distance to ground truth vs k, low vs high coverage.
Panel D  divergence-event rate (held-out success decreasing between consecutive
         snapshots) low vs high coverage -- the required falsifier.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aggregate as A

HERE = Path(__file__).resolve().parent
EVID = HERE.parent / "evidence"
TOL = 1e-6


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=str(EVID / "runs"))
    ap.add_argument("--tag", default="primary")
    ap.add_argument("--out", default=str(HERE.parent / "figures" / "coverage_k_evidence.pdf"))
    ap.add_argument("--boot", type=int, default=A.N_BOOT)
    ap.add_argument("--claim-prefix", default="")
    a = ap.parse_args()

    # ---------------- RECOMPUTE ----------------
    rows = A.load(Path(a.runs))
    idx = A.build_index(rows)
    seeds = sorted(idx)
    covs = sorted({round(r["coverage"], 1) for r in rows})

    succ, succ_ci = {}, {}
    for c in covs:
        for k in A.KS:
            p, lo, hi, _ = A.bootstrap(seeds, lambda ss, c=c, k=k: A.cell_mean(idx, ss, c, k), a.boot)
            succ[(c, k)] = p
            succ_ci[(c, k)] = (lo, hi)

    delta, delta_ci = {}, {}
    for c in covs:
        p, lo, hi, _ = A.bootstrap(seeds, lambda ss, c=c: A.delta_41(idx, ss, (c,)), a.boot)
        delta[c] = p
        delta_ci[c] = (lo, hi)

    ed = {}
    for lab, cs in (("low", A.LOW), ("high", A.HIGH)):
        for k in A.KS:
            ed[(lab, k)] = A.edit_mean(idx, seeds, cs, k)

    div, div_ci = {}, {}
    for lab, cs in (("low", A.LOW), ("high", A.HIGH)):
        p, lo, hi, _ = A.bootstrap(seeds, lambda ss, cs=cs: A.divergence_rate(idx, ss, cs), a.boot)
        div[lab] = p
        div_ci[lab] = (lo, hi)

    inter, ilo, ihi, _ = A.bootstrap(seeds, lambda ss: A.interaction(idx, ss), a.boot)

    # ---------------- ASSERT ----------------
    man = json.loads((EVID / "manifests" / f"{a.tag}.json").read_text())["ledger_rows"]
    led = {json.loads(l)["claim_id"]: json.loads(l)
           for l in (EVID / f"{A.PAPER}_{a.tag}_ledger.jsonl").read_text().splitlines() if l.strip()}

    def chk(key, val):
        key = a.claim_prefix + key
        if key not in man:
            raise SystemExit(f"ASSERT FAIL: '{key}' absent from stamp manifest")
        if abs(float(man[key]["value"]) - round(val, 4)) > 1e-4:
            raise SystemExit(f"ASSERT FAIL: '{key}' manifest={man[key]['value']} recomputed={round(val,4)}")
        if led[key]["verdict"] != "SUPPORTED":
            raise SystemExit(f"ASSERT FAIL: '{key}' ledger verdict={led[key]['verdict']}")

    for c in covs:
        for k in A.KS:
            chk(f"success::c{c:.1f}_k{k}", succ[(c, k)])
    chk("primary::interaction_coverage_x_k", inter)
    chk("falsifier::divergence_rate_low", div["low"])
    chk("falsifier::divergence_rate_high", div["high"])
    for lab in ("low", "high"):
        for k in A.KS:
            chk(f"editdist::{lab}_k{k}", ed[(lab, k)])
    print(f"[assert] {len(covs)*len(A.KS) + 3 + 2*len(A.KS)} recomputed values match the ledger", flush=True)

    # ---------------- DRAW ----------------
    plt.rcParams.update({"font.size": 7.2, "axes.linewidth": 0.6,
                         "xtick.major.width": 0.6, "ytick.major.width": 0.6,
                         "legend.frameon": False, "axes.spines.top": False,
                         "axes.spines.right": False})
    fig, axes = plt.subplots(1, 4, figsize=(11.0, 2.5))
    cmap = plt.get_cmap("viridis")
    colors = {c: cmap(i / max(1, len(covs) - 1)) for i, c in enumerate(covs)}
    ks = list(A.KS)

    # A: success vs k per coverage
    ax = axes[0]
    for c in covs:
        y = [succ[(c, k)] for k in ks]
        lo = [succ[(c, k)] - succ_ci[(c, k)][0] for k in ks]
        hi = [succ_ci[(c, k)][1] - succ[(c, k)] for k in ks]
        ax.errorbar(ks, y, yerr=[lo, hi], marker="o", ms=3, lw=1.2, capsize=2,
                    color=colors[c], label=f"c={c:.1f}")
    ax.set_xticks(ks)
    ax.set_xlabel("repair rounds $k$")
    ax.set_ylabel("held-out execution success")
    ax.set_title("A  success vs repair rounds", loc="left", fontsize=7.6)
    ax.legend(fontsize=6, ncol=2, loc="best")
    ax.set_ylim(-0.02, 1.02)

    # B: paired delta vs coverage
    ax = axes[1]
    y = [delta[c] for c in covs]
    lo = [delta[c] - delta_ci[c][0] for c in covs]
    hi = [delta_ci[c][1] - delta[c] for c in covs]
    ax.errorbar(covs, y, yerr=[lo, hi], marker="s", ms=3.5, lw=1.2, capsize=2, color="#333333")
    ax.axhline(0, color="#999999", lw=0.6, ls="--")
    ax.set_xlabel("verifier coverage $c$")
    ax.set_ylabel(r"$\Delta$ success ($k$=4 $-$ $k$=1)")
    ax.set_title(f"B  paired gain; interaction {inter:+.3f} [{ilo:+.3f}, {ihi:+.3f}]",
                 loc="left", fontsize=7.0)
    ax.set_xticks(covs)

    # C: edit distance vs k
    ax = axes[2]
    for lab, col, mk in (("low", "#c0392b", "v"), ("high", "#1f6f8b", "^")):
        ax.plot(ks, [ed[(lab, k)] for k in ks], marker=mk, ms=3.5, lw=1.2, color=col,
                label=f"c {'<=0.4' if lab=='low' else '>=0.8'}")
    ax.set_xticks(ks)
    ax.set_xlabel("repair rounds $k$")
    ax.set_ylabel(r"edit distance to $M^*$")
    ax.set_title("C  model drift from truth", loc="left", fontsize=7.6)
    ax.legend(fontsize=6)

    # D: divergence rate (falsifier)
    ax = axes[3]
    labs = ["c$\\leq$0.4", "c$\\geq$0.8"]
    vals = [div["low"], div["high"]]
    errs = [[div[l] - div_ci[l][0] for l in ("low", "high")],
            [div_ci[l][1] - div[l] for l in ("low", "high")]]
    ax.bar(labs, vals, color=["#c0392b", "#1f6f8b"], width=0.55)
    ax.errorbar(labs, vals, yerr=errs, fmt="none", ecolor="#222222", capsize=3, lw=1.0)
    ax.set_ylabel("divergence-event rate")
    ax.set_title("D  falsifier: divergence rate", loc="left", fontsize=7.6)

    fig.tight_layout()
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight")
    fig.savefig(out.with_suffix(".png"), dpi=200, bbox_inches="tight")
    print(f"[draw] {out}", flush=True)


if __name__ == "__main__":
    main()
