"""
wm_repair.runner -- the recursive self-repair loop and its evaluation harness.

One RUN = (domain, seed, coverage).  Repair rounds are NESTED: the k=4 trajectory
extends k=2 which extends k=1, so snapshots at k in {0,1,2,4} come from a single
trajectory and are seed-paired by construction.
"""

from __future__ import annotations

import json
import os
import random
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from . import core
from .core import (
    KINDS, CoverageVerifier, apply_edits, edit_distance, evidence_candidates,
    execute, ground_model, load_instance, load_skeleton, model_holds, plan,
    truth_model, unsolvable_candidates, model_to_pddl, _ground_slot,
)

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")


# --------------------------------------------------------------------------
# Evidence fit (ground-truth-blind): does a candidate model explain the traces?
# --------------------------------------------------------------------------


def evidence_fit(sk, model, traces):
    """Count recorded failure events that `model` would no longer produce.

    Recomputed directly on the recorded (state, action, observed-successor)
    tuples -- no replanning, no ground-truth access."""
    fit = 0
    for ev in traces:
        aname, args = core._parse_grounded(ev["action"])
        if aname not in model:
            continue
        state = set(ev["state"])
        pre = {_ground_slot(s, aname, args, sk) for s in model[aname]["pre"]}
        pre.discard(None)
        if ev["kind"] == "precondition_violation":
            # fixed if the model now agrees the action was inapplicable
            if not pre <= state:
                fit += 1
        elif ev["kind"] == "effect_discrepancy":
            if not pre <= state:
                continue   # model would not have applied it -- not a fix
            add = {_ground_slot(s, aname, args, sk) for s in model[aname]["add"]}
            dl = {_ground_slot(s, aname, args, sk) for s in model[aname]["del"]}
            add.discard(None); dl.discard(None)
            predicted = (state - dl) | add
            if predicted == set(ev["observed_after"]):
                fit += 1
        elif ev["kind"] == "no_such_operator":
            fit += 0
    return fit


# --------------------------------------------------------------------------
# LLM proposer (local Ollama)
# --------------------------------------------------------------------------

_EDIT_RE = re.compile(r"\{[^{}]*\}")

# Accept the obvious synonyms for the three lists.  Rejecting a semantically
# unambiguous answer on vocabulary alone would misattribute a HARNESS defect to
# the model -- see the "LLM parse bug" note in evidence/DESIGN_NOTES.md.
_KIND_SYN = {
    "pre": "pre", "precondition": "pre", "preconditions": "pre", "precond": "pre",
    "add": "add", "adds": "add", "add-effect": "add", "add_effect": "add",
    "add-effects": "add", "add_effects": "add", "addlist": "add", "add_list": "add",
    "del": "del", "dels": "del", "delete": "del", "del-effect": "del",
    "del_effect": "del", "del-effects": "del", "del_effects": "del",
    "dellist": "del", "del_list": "del", "delete-effect": "del",
}


def _ollama(model_name, prompt, timeout=150, num_predict=360):
    body = json.dumps({
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "options": {"temperature": 0.0, "seed": 7, "num_predict": num_predict},
    }).encode()
    req = urllib.request.Request(
        OLLAMA_URL + "/api/generate", data=body,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())["response"]


def _evidence_summary(traces, limit=4):
    out = []
    for ev in traces[:limit]:
        if ev["kind"] == "precondition_violation":
            out.append(f"- ACTION {ev['action']} was refused by the world. "
                       f"Facts true just before: {' '.join(ev['state'][:16])}")
        elif ev["kind"] == "effect_discrepancy":
            out.append(f"- ACTION {ev['action']} succeeded but my model mispredicted. "
                       f"Facts the world produced that I did not predict: "
                       f"{' '.join(ev['missing_in_prediction']) or 'none'}; "
                       f"facts I predicted that did not happen: "
                       f"{' '.join(ev['spurious_in_prediction']) or 'none'}")
        elif ev["kind"] == "no_such_operator":
            out.append(f"- ACTION {ev['action']} does not exist in the world.")
    return "\n".join(out) if out else "- no execution failures; no plan could be found."


def llm_candidates(sk, model, traces, llm_model, stats):
    """Ask the local LLM for repair edits.  Returns a list of candidate edit-tuples.

    Every parse failure is COUNTED, never silently dropped."""
    legal = []
    for aname in sorted(model):
        slots = " ".join("(" + s[0] + ("" if not s[1] else " " + " ".join(s[1])) + ")"
                         for s in sk.slots[aname])
        legal.append(f"{aname}: {slots}")
    prompt = (
        "You are repairing a STRIPS action model from execution feedback.\n\n"
        "MY CURRENT (possibly wrong) ACTION MODEL:\n" + model_to_pddl(sk, model) +
        "\n\nLEGAL LIFTED LITERALS PER ACTION (you may only use these):\n" +
        "\n".join(legal) +
        "\n\nWHAT HAPPENED WHEN I EXECUTED MY PLAN:\n" + _evidence_summary(traces) +
        "\n\nPropose a small set of single-literal edits that would make my model "
        "match the world. Each edit TOGGLES one literal in one list.\n"
        'Answer with ONLY a JSON array, at most 4 elements, of objects of the form '
        '{"action": "<action name>", "list": "pre"|"add"|"del", '
        '"literal": "(pred arg1 arg2)"} using the action\'s own parameter names.\n'
        "JSON array:"
    )
    stats["llm_calls"] += 1
    t0 = time.time()
    try:
        resp = _ollama(llm_model, prompt)
    except Exception as e:                      # noqa: BLE001
        stats["llm_errors"] += 1
        stats["llm_error_msgs"].append(str(e)[:200])
        return []
    stats["llm_seconds"] += time.time() - t0

    edits = []
    for m in _EDIT_RE.finditer(resp):
        try:
            o = json.loads(m.group(0))
        except json.JSONDecodeError:
            stats["parse_failures"] += 1
            continue
        a = str(o.get("action", "")).lower()
        kind = _KIND_SYN.get(str(o.get("list", "")).strip().lower(), "")
        lit = str(o.get("literal", "")).strip()
        if a not in model or kind not in KINDS:
            stats["parse_failures"] += 1
            continue
        toks = lit.strip("()").split()
        if not toks:
            stats["parse_failures"] += 1
            continue
        # Parameter names in the skeleton carry a leading "?"; normalise to that
        # convention rather than stripping it (stripping made EVERY slot fail).
        slot = (toks[0].lower(),
                tuple("?" + t.lstrip("?").lower() for t in toks[1:]))
        if slot not in sk.slots[a]:
            stats["parse_failures"] += 1
            continue
        edits.append((a, kind, slot))
    if not edits:
        stats["empty_proposals"] += 1
        return []
    edits = sorted(set(edits))
    cands = [(e,) for e in edits]
    if len(edits) > 1:
        cands.append(tuple(edits))
    return cands


# --------------------------------------------------------------------------
# One repair round
# --------------------------------------------------------------------------


def rollout(sk, model, truth_task_cache, instances, budget, stats, tag):
    """Plan+execute `model` on `instances` against ground truth.

    Returns (n_success, traces)."""
    n_ok, traces, n_no_plan = 0, [], 0
    for inst in instances:
        ttask = truth_task_cache[inst.name]
        mtask = ground_model(sk, model, inst)
        p, status, exp = plan(mtask, budget)
        stats["plan_calls"] += 1
        stats["expansions"] += exp
        if status == "budget":
            stats["budget_exhausted_" + tag] += 1
        if p is None:
            stats["no_plan_" + tag] += 1
            n_no_plan += 1
            continue
        names = [op.name for op in p]
        ok, ev = execute(ttask, names, mtask)
        if ok:
            n_ok += 1
        traces.extend(ev)
    return n_ok, traces, n_no_plan


def run_one(sk, truth, instances_train, instances_eval, truth_task_cache,
            seed, coverage, n_rounds, n_corrupt, budget, proposer, llm_model,
            snapshots=(0, 1, 2, 4)):
    """One nested trajectory for (domain, seed, coverage)."""
    rng = random.Random((seed * 1_000_003) ^ 0x5EED)
    model, corruption = core.corrupt(sk, truth, rng, n_corrupt)
    ver_rng = random.Random((seed * 7_919) ^ 0xC0FFEE)
    verifier = CoverageVerifier(sk, truth, coverage, ver_rng)
    tie_rng = random.Random((seed * 31_337) ^ int(coverage * 1000))

    stats = {"plan_calls": 0, "expansions": 0, "llm_calls": 0, "llm_errors": 0,
             "llm_seconds": 0.0, "llm_error_msgs": [], "parse_failures": 0,
             "empty_proposals": 0, "no_proposal_rounds": 0, "no_accept_rounds": 0,
             "budget_exhausted_train": 0, "budget_exhausted_eval": 0,
             "no_plan_train": 0, "no_plan_eval": 0}

    out = {}

    def snapshot(k, m):
        n_ok, _, _ = rollout(sk, m, truth_task_cache, instances_eval, budget, stats, "eval")
        out[k] = {
            "heldout_success": n_ok / len(instances_eval),
            "heldout_n": len(instances_eval),
            "edit_distance": edit_distance(m, truth),
            "verifier_score": verifier.score(m),
        }

    if 0 in snapshots:
        snapshot(0, model)

    t0 = time.time()
    train_success = []
    for k in range(1, n_rounds + 1):
        n_ok, traces, n_no_plan = rollout(sk, model, truth_task_cache, instances_train,
                                          budget, stats, "train")
        train_success.append(n_ok / len(instances_train))
        if proposer == "llm":
            cands = llm_candidates(sk, model, traces, llm_model, stats) if (traces or n_no_plan) else []
        else:
            cands = evidence_candidates(sk, model, traces)
            # The blind fallback fires ONLY when the model produced no plan at
            # all (nothing to observe).  If every training instance already
            # succeeds the loop proposes nothing -- it has converged.
            if not cands and n_no_plan:
                cands = unsolvable_candidates(sk, model)
        if not cands:
            stats["no_proposal_rounds"] += 1
        else:
            cur_key = (verifier.score(model), evidence_fit(sk, model, traces))
            scored = []
            for cand in cands:
                cm = apply_edits(model, cand)
                scored.append(((verifier.score(cm), evidence_fit(sk, cm, traces)),
                               tie_rng.random(), cand, cm))
            best_key = max(s[0] for s in scored)
            if best_key > cur_key:
                pool = [s for s in scored if s[0] == best_key]
                pool.sort(key=lambda s: s[1])
                model = pool[0][3]
            else:
                stats["no_accept_rounds"] += 1
        if k in snapshots:
            snapshot(k, model)
    stats["wallclock_s"] = time.time() - t0
    stats["verifier_calls"] = verifier.calls
    return {
        "corruption": [list(c[:2]) + [list(c[2][0:1]) + [list(c[2][1])]] for c in corruption],
        "n_corrupt": len(corruption),
        "coverage_visible": verifier.n_visible,
        "coverage_visible_true": verifier.n_visible_true,
        "condition_space": len(sk.conditions),
        "snapshots": out,
        "train_success_per_round": train_success,
        "stats": {k: v for k, v in stats.items() if k != "llm_error_msgs"},
        "llm_error_msgs": stats["llm_error_msgs"][:3],
    }
