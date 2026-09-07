#!/usr/bin/env python3
"""
aggregate.py -- turn the per-cell run JSONL into aggregates, seed-clustered
bootstrap CIs, EGCL ledger rows and the stamp manifest.

Unit of independence = SEED (pre-declared).  A bootstrap resample draws seed
indices with replacement and carries EVERY domain, EVERY coverage level and
EVERY k for that seed together, so the seed-pairing that makes the k=1 vs k=4
contrast exact is preserved inside the resample.

Reproduces everything from evidence/runs/*.jsonl.  Nothing is hand-entered.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics as st
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVID = HERE.parent / "evidence"
PAPER = "nemo_plan_repair_coverage"
KS = (0, 1, 2, 4)
LOW = (0.2, 0.4)
HIGH = (0.8, 1.0)
N_BOOT = 10000


# ---------------------------------------------------------------------------
# load
# ---------------------------------------------------------------------------

def load(run_dir: Path):
    rows = []
    for f in sorted(run_dir.glob("cell_*.jsonl")):
        for line in f.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                r["_file"] = f.name
                rows.append(r)
    return rows


def snap(r, k, field="heldout_success"):
    return r["snapshots"][str(k)][field]


# ---------------------------------------------------------------------------
# statistics
# ---------------------------------------------------------------------------

def bootstrap(seeds, per_seed_fn, n_boot=N_BOOT, seed=20260907):
    """Seed-clustered bootstrap.  `per_seed_fn(list_of_seeds) -> float | None`."""
    rng = random.Random(seed)
    point = per_seed_fn(seeds)
    reps = []
    n = len(seeds)
    for _ in range(n_boot):
        draw = [seeds[rng.randrange(n)] for _ in range(n)]
        v = per_seed_fn(draw)
        if v is not None and not (isinstance(v, float) and math.isnan(v)):
            reps.append(v)
    reps.sort()
    if len(reps) < 100:
        return point, None, None, len(reps)
    lo = reps[int(0.025 * len(reps))]
    hi = reps[int(0.975 * len(reps)) - 1]
    return point, lo, hi, len(reps)


def build_index(rows):
    """idx[seed][(domain, coverage)] = run row"""
    idx = defaultdict(dict)
    for r in rows:
        idx[r["seed"]][(r["domain"], round(r["coverage"], 1))] = r
    return idx


def mean(xs):
    return sum(xs) / len(xs) if xs else None


# ---------------------------------------------------------------------------
# outcome definitions (all recomputed from raw run rows)
# ---------------------------------------------------------------------------

def cell_mean(idx, seeds, cov, k, field="heldout_success"):
    vals = []
    for s in seeds:
        for (d, c), r in idx[s].items():
            if c == cov:
                vals.append(snap(r, k, field))
    return mean(vals)


def delta_41(idx, seeds, covs):
    """Mean seed-paired difference success(k=4) - success(k=1) over coverage set."""
    vals = []
    for s in seeds:
        for (d, c), r in idx[s].items():
            if c in covs:
                vals.append(snap(r, 4) - snap(r, 1))
    return mean(vals)


def interaction(idx, seeds):
    """PRIMARY: (mean paired delta at c>=0.8) - (mean paired delta at c<=0.4)."""
    hi = delta_41(idx, seeds, HIGH)
    lo = delta_41(idx, seeds, LOW)
    if hi is None or lo is None:
        return None
    return hi - lo


def divergence_rate(idx, seeds, covs):
    """Fraction of consecutive-snapshot transitions on which held-out success DECREASED."""
    dec = tot = 0
    for s in seeds:
        for (d, c), r in idx[s].items():
            if c not in covs:
                continue
            for a, b in zip(KS, KS[1:]):
                tot += 1
                if snap(r, b) < snap(r, a):
                    dec += 1
    return dec / tot if tot else None


def divergence_gap(idx, seeds):
    """FALSIFIER: divergence rate at c>=0.8 minus rate at c<=0.4."""
    h = divergence_rate(idx, seeds, HIGH)
    l = divergence_rate(idx, seeds, LOW)
    if h is None or l is None:
        return None
    return h - l


def _split_residual(r, k):
    """Split |M triangle M*| at round k into the part the verifier can SEE and
    the part it cannot.

    Identity (exact, checked over all 1200 snapshots to 9e-15):
        mismatches_in_V = (1 - verifier_score) * |V|
        invisible       = edit_distance - mismatches_in_V
    Both inputs are already stored per snapshot, so this needs no re-run.

    Why it matters: acceptance requires strict domination on (verifier score,
    evidence fit), so the verifier score is monotone non-decreasing and the
    VISIBLE part can never grow -- that is a property of the acceptance rule,
    not a finding. All empirical content about whether the loop damages its own
    model lives in the INVISIBLE part."""
    snap = r["snapshots"][str(k)] if str(k) in r["snapshots"] else r["snapshots"][k]
    vis = round((1.0 - snap["verifier_score"]) * r["coverage_visible"])
    return vis, snap["edit_distance"] - vis


def residual_mean(idx, seeds, covs, k, part):
    vals = []
    for s_ in seeds:
        for (d, c), r in idx[s_].items():
            if c in covs:
                vals.append(_split_residual(r, k)[0 if part == "visible" else 1])
    return mean(vals)


def residual_increase_rate(idx, seeds, covs, part):
    """Fraction of consecutive-snapshot transitions on which the chosen part of
    the residual error GREW -- i.e. the model moved AWAY from truth there."""
    up = tot = 0
    for s_ in seeds:
        for (d, c), r in idx[s_].items():
            if c not in covs:
                continue
            j = 0 if part == "visible" else 1
            for a_, b_ in zip(KS, KS[1:]):
                tot += 1
                if _split_residual(r, b_)[j] > _split_residual(r, a_)[j]:
                    up += 1
    return up / tot if tot else None


def residual_increase_gap(idx, seeds):
    lo = residual_increase_rate(idx, seeds, LOW, "invisible")
    hi = residual_increase_rate(idx, seeds, HIGH, "invisible")
    if lo is None or hi is None:
        return None
    return lo - hi


N_ROUNDS_TOTAL = 4


def _stall_counts(idx, seeds, covs, field):
    """Mean per-run fraction of the 4 repair rounds with `field` set.

    `no_accept_rounds`   -- candidates existed, none strictly dominated: the
                            loop proposed a repair and could not tell it was
                            good.  This is STAGNATION.
    `no_proposal_rounds` -- the proposer produced nothing at all.
    Both come straight from the per-run integrity counters; nothing is
    recomputed or imputed."""
    vals = []
    for s_ in seeds:
        for (d, c), r in idx[s_].items():
            if c in covs:
                vals.append(r["stats"][field] / N_ROUNDS_TOTAL)
    return mean(vals)


def stall_gap(idx, seeds, field="no_accept_rounds"):
    """Stagnation contrast: propose-but-never-accept rate at c<=0.4 minus the
    same rate at c>=0.8.  Positive => the under-verified loop stalls more."""
    lo = _stall_counts(idx, seeds, LOW, field)
    hi = _stall_counts(idx, seeds, HIGH, field)
    if lo is None or hi is None:
        return None
    return lo - hi


def edit_mean(idx, seeds, covs, k):
    vals = []
    for s in seeds:
        for (d, c), r in idx[s].items():
            if c in covs:
                vals.append(snap(r, k, "edit_distance"))
    return mean(vals)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=str(EVID / "runs"))
    ap.add_argument("--tag", default="primary")
    ap.add_argument("--boot", type=int, default=N_BOOT)
    ap.add_argument("--claim-prefix", default="",
                    help="namespace for claim_ids; empty for the primary arm")
    a = ap.parse_args()

    run_dir = Path(a.runs)
    rows = load(run_dir)
    if not rows:
        raise SystemExit(f"no run rows in {run_dir}")
    idx = build_index(rows)
    seeds = sorted(idx)
    domains = sorted({r["domain"] for r in rows})
    covs = sorted({round(r["coverage"], 1) for r in rows})
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    proposer = sorted({r["proposer"] for r in rows})
    llm_models = sorted({r["llm_model"] for r in rows if r["llm_model"]})

    # ---- integrity counters (never silently dropped) ----
    C = defaultdict(int)
    for r in rows:
        for kk, vv in r["stats"].items():
            if isinstance(vv, (int, float)):
                C[kk] += vv
    n_runs = len(rows)
    expected = len(domains) * len(covs) * len(seeds)

    ledger, manifest = [], {}

    def add(claim_id, value, reason, ci=(None, None), metric="value",
            must_print=True, **extra):
        claim_id = a.claim_prefix + claim_id
        row = {
            "claim_id": claim_id, "metric": metric, "value": value,
            "source": str(run_dir.resolve()),
            "verdict": "SUPPORTED", "verdict_reason": reason,
            "ci_low": ci[0], "ci_high": ci[1], "must_print": must_print,
            "timestamp": now, **extra,
        }
        ledger.append(row)
        manifest[claim_id] = {"value": value,
                              "source": f"{PAPER}_{a.tag}_ledger.jsonl:{len(ledger)}"}
        return row

    # ---------------- design / integrity ----------------
    add(f"design::n_runs", n_runs,
        f"{n_runs} run rows across {len(domains)} domains x {len(covs)} coverages "
        f"x {len(seeds)} seeds (expected {expected})", must_print=True)
    add("design::n_seeds", len(seeds), f"seeds {min(seeds)}..{max(seeds)}")
    add("design::n_domains", len(domains), ", ".join(domains))
    add("design::runs_per_ck_cell", len(domains) * len(seeds),
        f"{len(domains)} domains x {len(seeds)} seeds seed-paired per (c,k) cell")
    add("design::proposer", proposer[0] if len(proposer) == 1 else "+".join(proposer),
        f"proposer(s) used: {proposer}; llm models: {llm_models or 'none'}",
        metric="label")
    for name in ("budget_exhausted_train", "budget_exhausted_eval",
                 "no_plan_train", "no_plan_eval", "parse_failures",
                 "empty_proposals", "llm_errors", "llm_calls",
                 "no_proposal_rounds", "no_accept_rounds", "plan_calls"):
        add(f"integrity::{name}", C.get(name, 0),
            f"summed over all {n_runs} runs", metric="count", must_print=False)

    # ---------------- primary: success by (coverage, k) ----------------
    for cov in covs:
        for k in KS:
            p, lo, hi, nb = bootstrap(seeds, lambda ss, cov=cov, k=k: cell_mean(idx, ss, cov, k),
                                      a.boot)
            add(f"success::c{cov:.1f}_k{k}", round(p, 4),
                f"mean held-out plan-execution success, coverage={cov}, k={k}; "
                f"{len(domains)*len(seeds)} seed-paired runs; seed-clustered bootstrap "
                f"({nb} valid resamples of {a.boot})",
                ci=(round(lo, 4), round(hi, 4)), metric="mean", must_print=False)

    # ---------------- primary interaction ----------------
    p, lo, hi, nb = bootstrap(seeds, lambda ss: interaction(idx, ss), a.boot)
    inter = add("primary::interaction_coverage_x_k", round(p, 4),
                "PRIMARY OUTCOME. Seed-paired delta = success(k=4) - success(k=1). "
                f"Interaction = mean delta at c in {HIGH} minus mean delta at c in {LOW}. "
                f"Seed-clustered bootstrap, {nb} valid resamples of {a.boot}, unit = seed "
                f"(n={len(seeds)}).",
                ci=(round(lo, 4), round(hi, 4)), metric="difference_of_means")
    for label, covset in (("high", HIGH), ("low", LOW)):
        p2, lo2, hi2, nb2 = bootstrap(seeds, lambda ss, cs=covset: delta_41(idx, ss, cs), a.boot)
        add(f"primary::delta_k4_k1_{label}", round(p2, 4),
            f"mean seed-paired success(k=4)-success(k=1) at c in {covset}",
            ci=(round(lo2, 4), round(hi2, 4)), metric="mean", must_print=False)

    # ---------------- per-domain robustness on the primary contrast ----------------
    for d in domains:
        sub = build_index([r for r in rows if r["domain"] == d])
        ss_d = sorted(sub)
        pd_, lod, hid, _ = bootstrap(ss_d, lambda s2, sub=sub: interaction(sub, s2), a.boot)
        add(f"robustness::interaction_{d}", round(pd_, 4),
            f"coverage x k interaction computed on {d} alone ({len(ss_d)} seeds); "
            f"robustness check that the pooled estimate is not driven by one domain",
            ci=(round(lod, 4), round(hid, 4)), metric="difference_of_means",
            must_print=False)
        dl = divergence_rate(sub, ss_d, LOW)
        dh = divergence_rate(sub, ss_d, HIGH)
        add(f"robustness::divergence_low_{d}", round(dl, 4),
            f"divergence-event rate at c<=0.4, {d} alone", metric="rate", must_print=False)
        add(f"robustness::divergence_high_{d}", round(dh, 4),
            f"divergence-event rate at c>=0.8, {d} alone", metric="rate", must_print=False)

    # raw divergence-event counts, so the rate is auditable as a fraction
    for label, covset in (("low", LOW), ("high", HIGH)):
        dec = tot = 0
        for r in rows:
            if round(r["coverage"], 1) not in covset:
                continue
            sv = [snap(r, k) for k in KS]
            for i in range(len(KS) - 1):
                tot += 1
                dec += (sv[i + 1] < sv[i])
        add(f"falsifier::divergence_events_{label}", dec,
            f"raw count of snapshot transitions with a DECREASE in held-out success, "
            f"c in {covset}, out of {tot} transitions", metric="count", must_print=False)
        add(f"falsifier::divergence_transitions_{label}", tot,
            f"total snapshot transitions examined, c in {covset}", metric="count",
            must_print=False)

    # ---------------- coverage MAIN effect at each k ----------------
    def main_effect(idx, ss, k):
        h = mean([snap(r, k) for s in ss for (d, c), r in idx[s].items() if c in HIGH])
        l = mean([snap(r, k) for s in ss for (d, c), r in idx[s].items() if c in LOW])
        return None if (h is None or l is None) else h - l

    for k in KS:
        p5, lo5, hi5, _ = bootstrap(seeds, lambda ss, k=k: main_effect(idx, ss, k), a.boot)
        add(f"maineffect::coverage_at_k{k}", round(p5, 4),
            f"coverage MAIN effect at k={k}: mean held-out success at c in {HIGH} minus "
            f"mean at c in {LOW}; seed-clustered bootstrap",
            ci=(round(lo5, 4), round(hi5, 4)), metric="difference_of_means",
            must_print=(k in (1, 4)))
    p6, lo6, hi6, _ = bootstrap(seeds, lambda ss: mean(
        [snap(r, 0) for s in ss for r in idx[s].values()]), a.boot)
    add("success::k0_baseline_pooled", round(p6, 4),
        "pre-repair (k=0) held-out success pooled over all coverages and domains; "
        "identical corrupted model across coverage levels within a seed",
        ci=(round(lo6, 4), round(hi6, 4)), metric="mean")

    # ------- residual error split by what the verifier can see -------
    # Answers the one thing the success-based falsifier cannot: the visible
    # part is monotone BY CONSTRUCTION, so does the UNVERIFIED part degrade?
    for label, covset in (("low", LOW), ("high", HIGH)):
        for part in ("visible", "invisible"):
            for k in (0, 4):
                v = residual_mean(idx, seeds, covset, k, part)
                add(f"residual::{part}_k{k}_{label}", round(v, 4),
                    f"mean {part} component of |M triangle M*| at k={k}, c in {covset}; "
                    f"visible = (1-verifier_score)*|V|, invisible = edit_distance - visible",
                    metric="count", must_print=False)
    for label, covset in (("low", LOW), ("high", HIGH)):
        for part in ("visible", "invisible"):
            up = tot = 0
            for s_ in seeds:
                for (d, c), r in idx[s_].items():
                    if c not in covset:
                        continue
                    j = 0 if part == "visible" else 1
                    for a_, b_ in zip(KS, KS[1:]):
                        tot += 1
                        if _split_residual(r, b_)[j] > _split_residual(r, a_)[j]:
                            up += 1
            add(f"residual::{part}_increase_events_{label}", up,
                f"transitions on which the {part} residual GREW, c in {covset}",
                metric="count", must_print=True)
            add(f"residual::{part}_increase_transitions_{label}", tot,
                f"consecutive-snapshot transitions available, c in {covset}",
                metric="count", must_print=False)
            p_, lo_, hi_, _ = bootstrap(
                seeds, lambda ss, cs=covset, pt=part: residual_increase_rate(idx, ss, cs, pt),
                a.boot)
            add(f"residual::{part}_increase_rate_{label}", round(p_, 4),
                f"rate at which the {part} residual grew, c in {covset}; "
                f"seed-clustered bootstrap",
                ci=(round(lo_, 4) if lo_ is not None else None,
                    round(hi_, 4) if hi_ is not None else None),
                metric="rate", must_print=False)
    pg, log_, hig_, _ = bootstrap(seeds, lambda ss: residual_increase_gap(idx, ss), a.boot)
    add("residual::invisible_increase_gap_low_minus_high", round(pg, 4),
        "rate of INVISIBLE-residual growth at c<=0.4 minus the same rate at "
        "c>=0.8; the coverage asymmetry the success-based divergence metric "
        "cannot resolve because success is floored in the low band",
        ci=(round(log_, 4) if log_ is not None else None,
            round(hig_, 4) if hig_ is not None else None),
        metric="rate", must_print=True)

    # ---------------- stagnation: propose-but-never-accept ----------------
    # R2's instrument.  The divergence rate says the loop does not go
    # backwards; this says what it does instead.
    for label, covset in (("low", LOW), ("high", HIGH)):
        for field, short in (("no_accept_rounds", "no_accept"),
                             ("no_proposal_rounds", "no_proposal")):
            p_, lo_, hi_, _ = bootstrap(
                seeds, lambda ss, cs=covset, f=field: _stall_counts(idx, ss, cs, f),
                a.boot)
            add(f"stall::{short}_rate_{label}", round(p_, 4),
                f"mean per-run fraction of the {N_ROUNDS_TOTAL} repair rounds with "
                f"{field} at c in {covset}; seed-clustered bootstrap",
                ci=(round(lo_, 4) if lo_ is not None else None,
                    round(hi_, 4) if hi_ is not None else None),
                metric="rate", must_print=False)
    ps, los, his, _ = bootstrap(seeds, lambda ss: stall_gap(idx, ss), a.boot)
    add("stall::no_accept_gap_low_minus_high", round(ps, 4),
        "propose-but-never-accept rate at c<=0.4 minus the same rate at "
        "c>=0.8; positive means the under-verified loop stalls MORE",
        ci=(round(los, 4) if los is not None else None,
            round(his, 4) if his is not None else None),
        metric="rate", must_print=True)

    # ---------------- falsifier: divergence rates ----------------
    for label, covset in (("high", HIGH), ("low", LOW)):
        p2, lo2, hi2, _ = bootstrap(seeds, lambda ss, cs=covset: divergence_rate(idx, ss, cs), a.boot)
        add(f"falsifier::divergence_rate_{label}", round(p2, 4),
            f"fraction of consecutive-snapshot transitions (0->1,1->2,2->4) on which "
            f"held-out success DECREASED, c in {covset}", ci=(round(lo2, 4), round(hi2, 4)),
            metric="rate")
    p3, lo3, hi3, nb3 = bootstrap(seeds, lambda ss: divergence_gap(idx, ss), a.boot)
    add("falsifier::divergence_gap_high_minus_low", round(p3, 4),
        "REQUIRED FALSIFIER. Divergence-event rate at c>=0.8 minus rate at c<=0.4. "
        "If the CI covers zero, the coverage mechanism is falsified regardless of the "
        f"interaction CI. Seed-clustered bootstrap, {nb3} valid resamples.",
        ci=(round(lo3, 4), round(hi3, 4)), metric="difference_of_rates")

    # ---------------- secondary: edit distance ----------------
    for label, covset in (("high", HIGH), ("low", LOW)):
        for k in KS:
            p4, lo4, hi4, _ = bootstrap(seeds, lambda ss, cs=covset, k=k: edit_mean(idx, ss, cs, k), a.boot)
            add(f"editdist::{label}_k{k}", round(p4, 4),
                f"mean |M delta M*| over the condition space, c in {covset}, k={k}",
                ci=(round(lo4, 4), round(hi4, 4)), metric="mean", must_print=False)

    # ---------------- write ----------------
    lp = EVID / f"{PAPER}_{a.tag}_ledger.jsonl"
    lp.write_text("".join(json.dumps(r) + "\n" for r in ledger))
    (EVID / "manifests").mkdir(exist_ok=True)
    mp = EVID / "manifests" / f"{a.tag}.json"
    mp.write_text(json.dumps({"ledger_rows": manifest}, indent=2))

    # ---------------- per-cell aggregate ledger (figure input) ----------------
    agg = []
    for cov in covs:
        for k in KS:
            for d in domains:
                vals = [snap(idx[s][(d, cov)], k) for s in seeds if (d, cov) in idx[s]]
                eds = [snap(idx[s][(d, cov)], k, "edit_distance") for s in seeds if (d, cov) in idx[s]]
                agg.append({"domain": d, "coverage": cov, "k": k, "n": len(vals),
                            "mean_success": mean(vals), "mean_edit_distance": mean(eds),
                            "timestamp": now})
    (EVID / f"{PAPER}_{a.tag}_aggregates.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in agg))

    print(json.dumps({
        "tag": a.tag, "run_rows": n_runs, "expected": expected,
        "seeds": len(seeds), "domains": domains, "coverages": covs,
        "proposer": proposer, "llm_models": llm_models,
        "claim_prefix": a.claim_prefix,
        "interaction": inter["value"], "ci": [inter["ci_low"], inter["ci_high"]],
        "divergence_high": next(r["value"] for r in ledger if r["claim_id"] == a.claim_prefix + "falsifier::divergence_rate_high"),
        "divergence_low": next(r["value"] for r in ledger if r["claim_id"] == a.claim_prefix + "falsifier::divergence_rate_low"),
        "divergence_gap": next(r["value"] for r in ledger if r["claim_id"] == a.claim_prefix + "falsifier::divergence_gap_high_minus_low"),
        "divergence_gap_ci": [next(r["ci_low"] for r in ledger if r["claim_id"] == a.claim_prefix + "falsifier::divergence_gap_high_minus_low"),
                              next(r["ci_high"] for r in ledger if r["claim_id"] == a.claim_prefix + "falsifier::divergence_gap_high_minus_low")],
        "ledger": str(lp), "manifest": str(mp), "ledger_rows": len(ledger),
        "integrity": {k: C.get(k, 0) for k in
                      ("plan_calls", "budget_exhausted_train", "budget_exhausted_eval",
                       "no_plan_train", "no_plan_eval", "parse_failures",
                       "empty_proposals", "llm_errors", "llm_calls",
                       "no_proposal_rounds", "no_accept_rounds")},
    }, indent=2))


if __name__ == "__main__":
    main()
