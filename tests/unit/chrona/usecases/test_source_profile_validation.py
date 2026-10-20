from __future__ import annotations

from types import SimpleNamespace

import pytest

from chrona.core.diagnostics import Diagnostic
from chrona.core.ports import ScheduleOutcome
from chrona.usecases import render_review as render_usecase


class _StopAfterScheduling(Exception):
    pass


class _Closure:
    def __init__(self, project, snapshot_project, package_sets):
        self.project = project
        self.snapshot_project = snapshot_project
        self._package_sets = package_sets
        self.profile_packages = tuple(package for packages in package_sets.values() for package in packages)
        self.context = SimpleNamespace(forecast=False, environment=SimpleNamespace(locale="en-US"))
        self.actual_set = None

    def profile_packages_for(self, project):
        return self._package_sets[id(project)]


class _Scheduler:
    def __init__(self, *, reject=False):
        self.calls = []
        self.reject = reject

    def schedule(self, project, *, extension_diagnostics=()):
        self.calls.append((project, tuple(extension_diagnostics)))
        diagnostics = tuple(extension_diagnostics) if self.reject else ()
        return ScheduleOutcome(placements={}, diagnostics=diagnostics)


def _package(package_id, marker):
    return SimpleNamespace(package_id=package_id, profile_input={"marker": marker})


def _project(name):
    return SimpleNamespace(scheduler_input={"project": {"id": name}}, identity=name)


def _view(*, scenario=False):
    item = SimpleNamespace(source_kind="scenario", scenario_id="case-a")
    rows = (SimpleNamespace(items=(item,)),) if scenario else ()
    return SimpleNamespace(
        wording=None, comparison=SimpleNamespace(baseline="planned", scenario_id=None),
        rows=SimpleNamespace(items=rows),
    )


def test_project_review_uses_each_projects_own_manifests_and_scenario_overlay(monkeypatch):
    primary, snapshot = _project("primary"), _project("snapshot")
    primary_package, snapshot_package = _package("delivery", "primary-definition"), _package("delivery", "snapshot-definition")
    closure = _Closure(primary, snapshot, {
        id(primary): (primary_package,),
        id(snapshot): (snapshot_package,),
    })
    primary_input = primary.scheduler_input
    snapshot_input = snapshot.scheduler_input
    scenario_input = {"project": {"id": "primary"}, "overlay": "applied"}
    validator_calls = []

    def validate(project, manifests):
        validator_calls.append((project, manifests))
        return [Diagnostic("I_VALIDATED", "validated")]

    class Scheduler(_Scheduler):
        def schedule(self, project, *, extension_diagnostics=()):
            self.calls.append((project, tuple(extension_diagnostics)))
            return ScheduleOutcome(placements={}, diagnostics=())

    scheduler = Scheduler()
    primary_manifests = {"delivery": primary_package.profile_input}
    monkeypatch.setattr(render_usecase, "validate_profiles", validate)
    monkeypatch.setattr(
        render_usecase,
        "resolve_scenario",
        lambda project, scenario_id: SimpleNamespace(project=scenario_input, provenance=(scenario_id,)),
    )

    def stop_projection(*args, **kwargs):
        raise _StopAfterScheduling

    monkeypatch.setattr(render_usecase, "build_review_projection", stop_projection)

    with pytest.raises(_StopAfterScheduling):
        render_usecase._project_review(primary_input, _view(scenario=True), closure,
                                       primary_manifests, scheduler)

    assert [project for project, _ in validator_calls] == [primary_input, snapshot_input, scenario_input]
    assert [manifests for _, manifests in validator_calls] == [
        {"delivery": {"marker": "primary-definition"}},
        {"delivery": {"marker": "snapshot-definition"}},
        {"delivery": {"marker": "primary-definition"}},
    ]
    assert [project for project, _ in scheduler.calls] == [primary_input, snapshot_input, scenario_input]
    assert all(len(diagnostics) == 1 and diagnostics[0].id == "I_VALIDATED"
               for _, diagnostics in scheduler.calls)


def test_project_review_rejects_profile_diagnostic_before_projection(monkeypatch):
    primary = _project("primary")
    closure = _Closure(primary, None, {id(primary): (_package("delivery", "primary-definition"),)})
    rejection = Diagnostic("E_PROFILE_INVALID", "profile is invalid", "/extensions/0")
    scheduler = _Scheduler(reject=True)
    projected = False

    monkeypatch.setattr(render_usecase, "validate_profiles", lambda _project, _manifests: [rejection])

    def should_not_project(*args, **kwargs):
        nonlocal projected
        projected = True
        raise AssertionError("projection must not run after profile rejection")

    monkeypatch.setattr(render_usecase, "build_review_projection", should_not_project)

    with pytest.raises(render_usecase.RenderRejected) as error:
        render_usecase._project_review(primary.scheduler_input, _view(), closure, {}, scheduler)

    assert error.value.diagnostics == (rejection,)
    assert scheduler.calls == [(primary.scheduler_input, (rejection,))]
    assert not projected
