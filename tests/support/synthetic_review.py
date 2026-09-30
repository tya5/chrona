"""Synthetic Projects and review renders for core-rule tests (#575).

A core rule is judged by a small project built here from plain dictionaries,
rendered through a packaged preset bundle. Nothing in this module reads
`examples/`; a corpus edit therefore cannot change what these fixtures prove.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

from chrona.presentation.model.closure import resolve_draft_render
from chrona.presentation.renderers.v05_svg import V05SvgRenderer
from chrona.resources import builtin_preset_source_root, safe_load
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.render_review import RenderRequest, RenderedReview, render_review

PRESET = "executive-light"
_KINDS = {"view": "view.yaml", "theme": "theme.yaml", "scheme": "scheme.yaml", "layout": "layout.yaml"}


def span(object_id: str, start: date, days: int, *, owner: str = "a", title: str | None = None) -> dict[str, Any]:
    """One fixed-span task: `days` calendar days from `start`."""
    return {"type": "task", "title": title or object_id.title(), "fields": {"owner": owner},
            "schedule": {"mode": "fixed-span", "start": start.isoformat(),
                         "end": (start + timedelta(days=days)).isoformat()}}


def point(object_id: str, at: date, *, owner: str = "a", title: str | None = None) -> dict[str, Any]:
    """One fixed-point gate."""
    return {"type": "gate", "title": title or object_id.title(), "fields": {"owner": owner},
            "schedule": {"mode": "fixed-point", "at": at.isoformat()}}


def project(objects: Mapping[str, Mapping[str, Any]], relations: Iterable[Mapping[str, Any]] = ()) -> dict[str, Any]:
    """A Project document holding exactly the given objects."""
    owners = sorted({str(value["fields"]["owner"]) for value in objects.values() if "owner" in value.get("fields", {})})
    return {"version": "timeline/v0.7", "project": {"id": "synthetic", "title": "Synthetic"},
            "entities": {owner: {"type": "team", "title": f"Team {owner}"} for owner in owners},
            "objects": {key: deepcopy(dict(value)) for key, value in objects.items()},
            "relations": [dict(item) for item in relations]}


def bunched_project(*, groups: int = 4, per_group: int = 6, start: date = date(2026, 1, 5)) -> dict[str, Any]:
    """Many overlapping tasks with long titles: a project that cannot fit a small canvas without shortage."""
    objects: dict[str, Any] = {}
    for group in range(groups):
        for index in range(per_group):
            key = f"g{group}-t{index}"
            objects[key] = span(key, start + timedelta(days=index * 3), 40,
                                owner=f"team-{group}", title=f"Synthetic long task title {group}.{index}")
    return project(objects)


def chain_project(*, groups: int = 3, per_group: int = 4, gap: int = 45, length: int = 15,
                  start: date = date(2026, 1, 5)) -> dict[str, Any]:
    """Per group, tasks in sequence joined by finish-to-start relations, so a lane holds a whole chain."""
    objects: dict[str, Any] = {}
    relations: list[dict[str, Any]] = []
    for group in range(groups):
        for index in range(per_group):
            key = f"g{group}-t{index}"
            objects[key] = span(key, start + timedelta(days=index * (length + gap) + group * 7), length,
                                owner=f"team-{group}", title=f"Long synthetic title {group}.{index}")
            if index:
                relations.append({"id": f"r{group}-{index}", "type": "dependency", "lag": "0d",
                                  "from": {"object": f"g{group}-t{index - 1}", "endpoint": "end"},
                                  "to": {"object": key, "endpoint": "start"}})
    return project(objects, relations)


def bundle(preset: str = PRESET) -> dict[str, dict[str, Any]]:
    """The four presentation resources of a packaged preset bundle, as fresh dictionaries."""
    root = builtin_preset_source_root(f"presets/bundles/{preset}")
    return {kind: safe_load(root.joinpath(name).read_bytes()) for kind, name in _KINDS.items()}


def lane_view(view: Mapping[str, Any], *, packing: Iterable[str] = ("explicit", "attached", "chain", "dates"),
              table: bool = True) -> dict[str, Any]:
    """The View with lane rows and plot labels, the row mode the lane rules apply to."""
    value = deepcopy(dict(view))
    body = value["body"]
    body.pop("tableColumns", None)
    body["rows"] = {"mode": "lanes", "packing": list(packing)}
    if table:
        body["rows"]["laneTable"] = {"label": "group", "count": True}
    body["visibility"]["labels"] = {"placement": "plot"}
    return value


def _write(path: Path, value: Mapping[str, Any]) -> Path:
    path.write_text(yaml.safe_dump(dict(value), sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def render(directory: Path, source: Mapping[str, Any], *, presentation: Mapping[str, Mapping[str, Any]] | None = None,
           actual: Mapping[str, Any] | None = None, viewport: tuple[int, int | None] = (1600, 900)) -> RenderedReview:
    """Render `source` through `presentation` (default: the packaged preset bundle) and return the review."""
    parts = presentation or bundle()
    paths = {kind: _write(directory / f"{kind}.yaml", value) for kind, value in parts.items()}
    draft = resolve_draft_render(
        project_path=_write(directory / "project.yaml", source), view_path=paths["view"],
        theme_path=paths["theme"], scheme_path=paths["scheme"], layout_path=paths["layout"],
        actual_path=_write(directory / "actual.yaml", actual) if actual is not None else None,
        viewport=viewport)
    return render_review(RenderRequest(
        closure=draft.closure, snapshot_root=draft.asset_root, asset_root=draft.asset_root,
        scheduler=ReferenceScheduler(), renderer=V05SvgRenderer(), draft_auto_block=draft.auto_block))

