"""Generic object-reference diagnostics survive the public Core/render entrypoints (#344)."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from chrona.core.validation import validate_project
from chrona.extensions.profiles import validate_profiles
from chrona.scheduling.scheduler import schedule
from chrona.usecases import render_review


PACKAGE = {
    "version": "chrona/profile/v0.3",
    "packageId": "acme-reference",
    "contentIdentity": "sha256:" + "1" * 64,
    "requires": {"projectFormat": "timeline/v0.7"},
    "profiles": {
        "acme-reference.work": {
            "extends": "task",
            "fields": {
                "owner": {"type": "objectReference", "targetProfiles": ["acme-reference.team"]},
                "reviewers": {"type": "objectReference", "targetProfiles": ["acme-reference.team"], "cardinality": "many"},
            },
        },
        "acme-reference.team": {"extends": "entity"},
        "acme-reference.other": {"extends": "entity"},
    },
}


def _project(*, owner="team-a", reviewers=None):
    return {
        "version": "timeline/v0.7",
        "project": {"id": "object-reference-test"},
        "extensions": [{"packageId": "acme-reference", "path": "extensions/acme-reference.yaml",
                        "revision": "git:" + "1" * 40}],
        "entities": {"team-a": {"type": "acme-reference.team", "title": "Team A"}},
        "objects": {
            "work": {
                "type": "acme-reference.work",
                "title": "Work",
                "schedule": {"mode": "fixed-span", "start": "2026-10-01", "end": "2026-10-03"},
                "fields": {"owner": owner, "reviewers": ["team-a"] if reviewers is None else reviewers},
            },
            "other": {
                "type": "acme-reference.other",
                "title": "Other",
                "schedule": {"mode": "fixed-span", "start": "2026-10-03", "end": "2026-10-05"},
            },
        },
    }


class _RenderScheduler:
    def schedule(self, project, *, extension_diagnostics=()):
        return schedule(project, extension_diagnostics=extension_diagnostics)


class _ReachedProjection(Exception):
    pass


@pytest.mark.parametrize(("project", "pointer"), [
    (_project(owner="missing"), "/objects/work/fields/owner"),
    (_project(owner="other"), "/objects/work/fields/owner"),
    (_project(reviewers="team-a"), "/objects/work/fields/reviewers"),
    (_project(reviewers=["team-a", "missing"]), "/objects/work/fields/reviewers/1"),
])
def test_reference_failures_keep_the_same_pointer_through_validate_schedule_and_render(project, pointer):
    package = deepcopy(PACKAGE)
    manifests = {"acme-reference": package}
    profile_diagnostics = validate_profiles(project, manifests)
    expected = [("E_PROFILE_FIELD_TYPE", pointer)]
    assert [(item.id, item.path) for item in profile_diagnostics] == expected

    core_diagnostics = validate_project(project, extension_diagnostics=profile_diagnostics)
    assert [(item.id, item.path) for item in core_diagnostics if item.id == "E_PROFILE_FIELD_TYPE"] == expected

    scheduled = schedule(project, extension_diagnostics=profile_diagnostics)
    assert not scheduled.ok
    assert [(item.id, item.path) for item in scheduled.diagnostics] == expected

    with pytest.raises(render_review.RenderRejected) as caught:
        render_review._project_review(project, None, None, manifests, _RenderScheduler())
    assert [(item.id, item.path) for item in caught.value.diagnostics] == expected


def test_valid_reference_passes_validate_schedule_and_render_source_closure(monkeypatch):
    project = _project()
    manifests = {"acme-reference": deepcopy(PACKAGE)}
    diagnostics = validate_profiles(project, manifests)
    assert diagnostics == []
    assert validate_project(project, extension_diagnostics=diagnostics) == []
    assert schedule(project, extension_diagnostics=diagnostics).ok

    class _Closure:
        context = SimpleNamespace(forecast=False, environment=SimpleNamespace(locale="en-US"))
        actual_set = None
        snapshot_project = None
        profile_packages = ()

    view = SimpleNamespace(
        comparison=SimpleNamespace(baseline="planned", scenario_id=None),
        rows=SimpleNamespace(items=()),
        wording=None,
    )

    def reached_projection(*_args, **_kwargs):
        raise _ReachedProjection

    monkeypatch.setattr(render_review, "build_review_projection", reached_projection)
    with pytest.raises(_ReachedProjection):
        render_review._project_review(project, view, _Closure(), manifests, _RenderScheduler())
