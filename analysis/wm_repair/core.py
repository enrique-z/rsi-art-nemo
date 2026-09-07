"""
wm_repair.core -- world-model self-repair loop over PDDL domain models.

Apparatus for papers/nemo-plan-repair-coverage (A2 pre-declaration v2, 2026-09-07).

The agent holds a CORRUPTED copy of a ground-truth PDDL domain. It plans with the
corrupted model, executes the plan against a ground-truth simulator, observes
failures, and proposes repairs. A verifier that can see only a fraction `c` of the
domain's condition space adjudicates candidate repairs.

Everything here is deterministic given (domain, instance set, seed, coverage, k).
No fabricated data: all PDDL comes from the pyperplan IPC benchmark tree, all
outcomes are computed by executing operators.
"""

from __future__ import annotations

import heapq
import os
import itertools
import json
import random
from dataclasses import dataclass, field
from pathlib import Path

from pyperplan.pddl.parser import Parser
from pyperplan.pddl.pddl import Action, Effect, Predicate
from pyperplan import grounding
from pyperplan.task import Task, Operator
from pyperplan.heuristics.relaxation import hFFHeuristic
from pyperplan.search import searchspace

KINDS = ("pre", "add", "del")


# --------------------------------------------------------------------------
# Lifted model representation
# --------------------------------------------------------------------------


def _type_ancestors(t):
    out = []
    while t is not None:
        out.append(t.name)
        t = t.parent
    return out


def _compatible(param_types, target_types):
    """True if a parameter declared with `param_types` can fill a predicate
    argument slot declared with `target_types` (subtype-aware)."""
    anc = set()
    for pt in param_types:
        anc.update(_type_ancestors(pt))
    return any(tt.name in anc for tt in target_types)


@dataclass
class DomainSkeleton:
    """The immutable scaffolding of a domain: signatures, types, statics.

    Only the *mutable* (non-static) condition space is ever corrupted or
    repaired.  Static predicates (those that appear in no action effect of the
    GROUND-TRUTH domain) encode sort structure -- e.g. `room`/`ball`/`gripper`
    in gripper, `in-city` in logistics -- and are held fixed so that the true
    model and every candidate model ground into the SAME fact space and the
    same set of operator names.  This assumption is recorded in DESIGN_NOTES.md.
    """

    name: str
    domain: object                      # pyperplan Domain (ground truth)
    statics: tuple                      # static predicate names
    action_sig: dict                    # action name -> signature list
    static_pre: dict                    # action name -> list[Predicate] (static, verbatim)
    slots: dict                         # action name -> tuple of slots
    pred_sig: dict                      # predicate name -> signature list
    conditions: tuple                   # ordered tuple of (action, kind, slot)

    def slot_predicate(self, slot):
        """Build a pyperplan Predicate for a lifted slot bound to action params."""
        pname, params = slot
        tsig = self.pred_sig[pname]
        return Predicate(pname, [(p, tsig[i][1]) for i, p in enumerate(params)])


def load_skeleton(domain_pddl: Path, sample_problem_pddl: Path) -> DomainSkeleton:
    parser = Parser(str(domain_pddl), str(sample_problem_pddl))
    dom = parser.parse_domain()
    statics = tuple(sorted(grounding._get_statics(dom.predicates.values(), dom.actions.values())))

    action_sig, static_pre, slots = {}, {}, {}
    pred_sig = {p.name: list(p.signature) for p in dom.predicates.values()}
    mutable_preds = sorted(n for n in pred_sig if n not in statics)

    for aname in sorted(dom.actions):
        a = dom.actions[aname]
        action_sig[aname] = list(a.signature)
        static_pre[aname] = [p for p in a.precondition if p.name in statics]
        s = []
        for pname in mutable_preds:
            tsig = pred_sig[pname]
            choices = []
            for _, target_types in tsig:
                ok = [pn for pn, ptypes in a.signature if _compatible(ptypes, target_types)]
                choices.append(ok)
            for combo in itertools.product(*choices):
                s.append((pname, tuple(combo)))
        slots[aname] = tuple(sorted(s))

    conditions = tuple(
        (aname, kind, slot)
        for aname in sorted(dom.actions)
        for kind in KINDS
        for slot in slots[aname]
    )
    return DomainSkeleton(
        name=dom.name, domain=dom, statics=statics, action_sig=action_sig,
        static_pre=static_pre, slots=slots, pred_sig=pred_sig, conditions=conditions,
    )


def truth_model(sk: DomainSkeleton) -> dict:
    """Extract the ground-truth model as {action: {kind: frozenset(slots)}}."""
    m = {}
    for aname in sorted(sk.domain.actions):
        a = sk.domain.actions[aname]
        pre = {(p.name, tuple(v for v, _ in p.signature)) for p in a.precondition
               if p.name not in sk.statics}
        add = {(p.name, tuple(v for v, _ in p.signature)) for p in a.effect.addlist
               if p.name not in sk.statics}
        dl = {(p.name, tuple(v for v, _ in p.signature)) for p in a.effect.dellist
              if p.name not in sk.statics}
        legal = set(sk.slots[aname])
        assert pre <= legal and add <= legal and dl <= legal, (aname, pre - legal, add - legal, dl - legal)
        m[aname] = {"pre": frozenset(pre), "add": frozenset(add), "del": frozenset(dl)}
    return m


def model_holds(model, cond) -> bool:
    aname, kind, slot = cond
    return slot in model[aname][kind]


def toggle(model, cond):
    """Return a new model with `cond` flipped."""
    aname, kind, slot = cond
    new = {a: {k: set(v) for k, v in d.items()} for a, d in model.items()}
    if slot in new[aname][kind]:
        new[aname][kind].discard(slot)
    else:
        new[aname][kind].add(slot)
    return {a: {k: frozenset(v) for k, v in d.items()} for a, d in new.items()}


def apply_edits(model, edits):
    m = model
    for c in edits:
        m = toggle(m, c)
    return m


def edit_distance(model, other) -> int:
    """Number of condition-level disagreements (symmetric difference)."""
    d = 0
    for aname in model:
        for kind in KINDS:
            d += len(model[aname][kind] ^ other[aname][kind])
    return d


def model_to_actions(sk: DomainSkeleton, model) -> list:
    """Materialise a model as pyperplan Action objects for grounding."""
    acts = []
    for aname in sorted(model):
        pre = list(sk.static_pre[aname]) + [sk.slot_predicate(s) for s in sorted(model[aname]["pre"])]
        eff = Effect()
        eff.addlist = {sk.slot_predicate(s) for s in sorted(model[aname]["add"])}
        eff.dellist = {sk.slot_predicate(s) for s in sorted(model[aname]["del"])}
        acts.append(Action(aname, list(sk.action_sig[aname]), pre, eff))
    return acts


def model_to_pddl(sk: DomainSkeleton, model) -> str:
    """Human/LLM-readable rendering of a model (used by the LLM proposer)."""
    out = []
    for aname in sorted(model):
        params = " ".join(f"?{p}" if not p.startswith("?") else p
                          for p, _ in sk.action_sig[aname])
        def fmt(slots):
            if not slots:
                return "()"
            return " ".join("(" + s[0] + ("" if not s[1] else " " + " ".join(s[1])) + ")"
                            for s in sorted(slots))
        stat = " ".join("(" + p.name + " " + " ".join(v for v, _ in p.signature) + ")"
                        for p in sk.static_pre[aname])
        out.append(
            f"(:action {aname}\n"
            f"  :parameters ({params})\n"
            f"  :static-precondition {stat if stat else '()'}\n"
            f"  :precondition {fmt(model[aname]['pre'])}\n"
            f"  :add-effect {fmt(model[aname]['add'])}\n"
            f"  :del-effect {fmt(model[aname]['del'])})"
        )
    return "\n".join(out)


# --------------------------------------------------------------------------
# Problem instances / grounding / simulator
# --------------------------------------------------------------------------


@dataclass
class Instance:
    name: str
    objects: dict
    init: frozenset
    goals: frozenset
    type_map: dict


def load_instance(sk: DomainSkeleton, domain_pddl: Path, problem_pddl: Path) -> Instance:
    # NB: the problem MUST be parsed against the skeleton's own Domain object.
    # pyperplan's Type has identity-based equality, so type_map lookups only
    # resolve when the Type instances come from the same parse.
    parser = Parser(str(domain_pddl), str(problem_pddl))
    prob = parser.parse_problem(sk.domain)
    objects = dict(prob.objects)
    objects.update(sk.domain.constants)
    init = grounding._get_partial_state(prob.initial_state)
    goals = grounding._get_partial_state(prob.goal)
    type_map = grounding._create_type_map(objects)
    return Instance(problem_pddl.stem, objects, init, goals, type_map)


def ground_model(sk: DomainSkeleton, model, inst: Instance) -> Task:
    """Ground `model` on `inst` in the shared fact space fixed by the true statics."""
    acts = model_to_actions(sk, model)
    ops = list(grounding._ground_actions(acts, inst.type_map, list(sk.statics), inst.init))
    ops.sort(key=lambda o: o.name)
    facts = grounding._collect_facts(ops) | inst.goals | inst.init
    return Task(inst.name, facts, inst.init, inst.goals, ops)


# --------------------------------------------------------------------------
# Bounded planner (deterministic, expansion-capped A*/GBFS over hFF)
# --------------------------------------------------------------------------


# A12: the wallclock bound is the only host-dependent part of the search.
# Default is 5.0 so the PRE-REGISTERED code path is byte-identical unless
# NEMO_PLAN_MAX_SECONDS is set; the deterministic replication grid sets it to
# inf, which disables the check entirely. max_expansions is NOT changed.
PLAN_MAX_SECONDS = float(os.environ.get("NEMO_PLAN_MAX_SECONDS", "5.0"))


def plan(task: Task, max_expansions: int = 1200, max_seconds: float = None):
    """Greedy best-first search with hFF, expansion- and time-capped.

    Returns (plan_ops or None, status, expansions).  status in
    {'plan', 'unsolvable', 'budget'}.
    """
    import time as _time
    if max_seconds is None:
        max_seconds = PLAN_MAX_SECONDS
    _t0 = _time.time()
    if not task.operators:
        return None, "unsolvable", 0
    h = hFFHeuristic(task)
    root = searchspace.make_root_node(task.initial_state)
    open_ = []
    tie = 0
    heapq.heappush(open_, (h(root), 0, tie, root))
    closed = {task.initial_state}
    expansions = 0
    while open_:
        _, _, _, node = heapq.heappop(open_)
        expansions += 1
        if expansions > max_expansions:
            return None, "budget", expansions
        if (expansions & 63) == 0 and _time.time() - _t0 > max_seconds:
            return None, "budget", expansions
        if task.goal_reached(node.state):
            return node.extract_solution(), "plan", expansions
        for op in task.operators:
            if not op.applicable(node.state):
                continue
            succ = op.apply(node.state)
            if succ in closed:
                continue
            closed.add(succ)
            child = searchspace.make_child_node(node, op, succ)
            hv = h(child)
            if hv == float("inf"):
                continue
            tie += 1
            heapq.heappush(open_, (hv, child.g, tie, child))
    return None, "unsolvable", expansions


def execute(true_task: Task, plan_names, model_task: Task):
    """Execute a plan (list of operator names) against the ground-truth task.

    Returns (success, trace).  `trace` records, for the first divergence, the
    step index, the action, the state the agent was in, the preconditions the
    agent believed, and the observed vs predicted successor state.

    An action whose ground-truth preconditions are unmet ABORTS execution
    (precondition violation).  An action that succeeds but yields a state the
    agent's model did not predict is recorded as an effect discrepancy and
    execution continues from the TRUE state.
    """
    true_ops = {o.name: o for o in true_task.operators}
    model_ops = {o.name: o for o in model_task.operators}
    state = true_task.initial_state
    events = []
    for i, name in enumerate(plan_names):
        top = true_ops.get(name)
        mop = model_ops.get(name)
        if top is None:
            events.append({"step": i, "action": name, "kind": "no_such_operator",
                           "state": sorted(state)})
            return False, events
        if not top.applicable(state):
            events.append({
                "step": i, "action": name, "kind": "precondition_violation",
                "state": sorted(state),
                "unmet": sorted(top.preconditions - state),
                "believed_pre": sorted(mop.preconditions) if mop else [],
            })
            return False, events
        pre_state = state
        predicted = mop.apply(state) if (mop and mop.applicable(state)) else None
        state = top.apply(state)
        if predicted is not None and predicted != state:
            events.append({
                "step": i, "action": name, "kind": "effect_discrepancy",
                "state": sorted(pre_state),
                "observed_after": sorted(state),
                "missing_in_prediction": sorted(state - predicted),
                "spurious_in_prediction": sorted(predicted - state),
            })
    return true_task.goal_reached(state), events


# --------------------------------------------------------------------------
# Corruption operator
# --------------------------------------------------------------------------


def corrupt(sk: DomainSkeleton, truth, rng: random.Random, n_edits: int):
    """Apply `n_edits` distinct condition toggles to the ground-truth model.

    Each toggle either DROPS a true condition or ADDS a false one, drawn so that
    half (rounded) are drops and the rest are additions -- a fixed, seeded
    perturbation of preconditions and effects, exactly as pre-declared.
    """
    true_conds = [c for c in sk.conditions if model_holds(truth, c)]
    false_conds = [c for c in sk.conditions if not model_holds(truth, c)]
    n_drop = n_edits // 2
    n_add = n_edits - n_drop
    drops = rng.sample(true_conds, min(n_drop, len(true_conds)))
    adds = rng.sample(false_conds, min(n_add, len(false_conds)))
    edits = sorted(drops + adds)
    return apply_edits(truth, edits), tuple(edits)


# --------------------------------------------------------------------------
# Verifier with coverage c
# --------------------------------------------------------------------------


class CoverageVerifier:
    """Checks candidate models against a random fraction `c` of the condition space.

    The visible set V is STRATIFIED: it contains round(c * |C*|) of the domain's
    TRUE conditions and round(c * |C \\ C*|) of its false ones, so V literally
    contains a fraction c of the ground-truth domain's conditions AND is a
    fraction c of the whole condition space the verifier could see.  Everything
    outside V is invisible: the verifier cannot detect a missing true condition
    nor a spurious false one there.
    """

    def __init__(self, sk: DomainSkeleton, truth, coverage: float, rng: random.Random):
        true_c = [c for c in sk.conditions if model_holds(truth, c)]
        false_c = [c for c in sk.conditions if not model_holds(truth, c)]
        n_t = int(round(coverage * len(true_c)))
        n_f = int(round(coverage * len(false_c)))
        self.visible = frozenset(rng.sample(true_c, n_t) + rng.sample(false_c, n_f))
        self.truth = truth
        self.coverage = coverage
        self.n_visible_true = n_t
        self.n_visible = len(self.visible)
        self.calls = 0

    def score(self, model) -> float:
        """Fraction of visible conditions on which `model` agrees with truth."""
        self.calls += 1
        if not self.visible:
            return 0.0
        agree = sum(1 for c in self.visible
                    if model_holds(model, c) == model_holds(self.truth, c))
        return agree / len(self.visible)


# --------------------------------------------------------------------------
# Repair proposers
# --------------------------------------------------------------------------


def _slot_for_fact(sk, aname, args, fact):
    """Invert a grounded fact into every lifted slot of `aname` consistent with it."""
    inner = fact.strip("()").split()
    pname, objs = inner[0], inner[1:]
    if pname not in sk.pred_sig or pname in sk.statics:
        return []
    params = [p for p, _ in sk.action_sig[aname]]
    binding = {}
    for p, o in zip(params, args):
        binding.setdefault(o, []).append(p)
    choices = []
    for o in objs:
        if o not in binding:
            return []
        choices.append(binding[o])
    out = []
    for combo in itertools.product(*choices):
        slot = (pname, tuple(combo))
        if slot in sk.slots[aname]:
            out.append(slot)
    return out


def _parse_grounded(name):
    inner = name.strip("()").split()
    return inner[0], inner[1:]


def evidence_candidates(sk: DomainSkeleton, model, events):
    """Deterministic, evidence-localised repair candidates.

    Each candidate is a tuple of condition toggles.  Candidates are derived ONLY
    from what the agent can observe: which action failed, the observable state,
    and the discrepancy between predicted and observed successor states.  The
    ground-truth model is never read here.
    """
    cands = set()
    for ev in events:
        aname, args = _parse_grounded(ev["action"])
        if aname not in sk.slots:
            continue
        if ev["kind"] == "precondition_violation":
            # The model let the planner apply an action the world refused: the
            # true precondition contains something false in the observed state.
            state = set(ev["state"])
            for slot in sk.slots[aname]:
                cond = (aname, "pre", slot)
                if model_holds(model, cond):
                    continue
                # a candidate precondition must be FALSE in the observed state
                gf = _ground_slot(slot, aname, args, sk)
                if gf is not None and gf not in state:
                    cands.add(((aname, "pre", slot),))
        elif ev["kind"] == "effect_discrepancy":
            for fact in ev["missing_in_prediction"]:
                for slot in _slot_for_fact(sk, aname, args, fact):
                    if not model_holds(model, (aname, "add", slot)):
                        cands.add(((aname, "add", slot),))
                    if model_holds(model, (aname, "del", slot)):
                        cands.add(((aname, "del", slot),))
            for fact in ev["spurious_in_prediction"]:
                for slot in _slot_for_fact(sk, aname, args, fact):
                    if model_holds(model, (aname, "add", slot)):
                        cands.add(((aname, "add", slot),))
                    if not model_holds(model, (aname, "del", slot)):
                        cands.add(((aname, "del", slot),))
        elif ev["kind"] == "no_such_operator":
            for slot in sorted(model[aname]["pre"]):
                cands.add(((aname, "pre", slot),))
    return sorted(cands)


def _ground_slot(slot, aname, args, sk):
    pname, params = slot
    order = [p for p, _ in sk.action_sig[aname]]
    m = dict(zip(order, args))
    try:
        objs = [m[p] for p in params]
    except KeyError:
        return None
    return "(" + pname + ("" if not objs else " " + " ".join(objs)) + ")"


def unsolvable_candidates(sk: DomainSkeleton, model, max_c=None):
    """Candidates when the model yields no plan at all: relax preconditions and
    restore missing effects.  Still ground-truth-blind."""
    cands = []
    for aname in sorted(model):
        for slot in sorted(model[aname]["pre"]):
            cands.append(((aname, "pre", slot),))
        for slot in sk.slots[aname]:
            if not model_holds(model, (aname, "add", slot)):
                cands.append(((aname, "add", slot),))
    return cands if max_c is None else cands[:max_c]
