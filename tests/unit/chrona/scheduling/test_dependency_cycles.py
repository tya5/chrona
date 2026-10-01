"""The pure cycle finder behind `validate` (#780): result shape, purity and scale. Behaviour per case is in
tests/unit/chrona/usecases/test_project_checks_cycles.py."""
import copy

from chrona.scheduling.dependency_cycles import dependency_cycle_diagnostics, find_dependency_cycles


def ring(size, lag="0d"):
    objects = {f"t{i}": {"type": "task", "schedule": {"mode": "scheduled", "amount": "1d"}} for i in range(size)}
    relations = [{"type": "dependency", "from": {"object": f"t{i}", "endpoint": "end"},
                  "to": {"object": f"t{(i + 1) % size}", "endpoint": "start"}, "lag": lag} for i in range(size)]
    return {"version": "timeline/v0.7", "project": {"id": "p"}, "objects": objects, "relations": relations}


def test_a_ring_is_one_cycle_whose_closing_relation_is_the_last_declared():
    [cycle] = find_dependency_cycles(ring(4))

    assert cycle.objects == ("t0", "t1", "t2", "t3") and cycle.closing_relation == 3 and not cycle.unsatisfiable


def test_the_finder_does_not_modify_the_project_and_is_repeatable():
    plan = ring(5)
    before = copy.deepcopy(plan)

    first = dependency_cycle_diagnostics(plan)

    assert plan == before and first == dependency_cycle_diagnostics(copy.deepcopy(plan))


def test_a_long_chain_and_a_long_ring_do_not_exhaust_the_stack():
    plan = ring(3000)
    assert len(find_dependency_cycles(plan)) == 1 and len(find_dependency_cycles(plan)[0].objects) == 3000
    del plan["relations"][-1]
    assert find_dependency_cycles(plan) == ()


def test_a_project_without_relations_has_no_cycle():
    plan = ring(3)
    plan["relations"] = []

    assert find_dependency_cycles(plan) == () and dependency_cycle_diagnostics(plan) == ()
