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
           actual: Mapping[str, Any] | None = None, viewport: tuple[int, int | None] = (1600, 900),
           icon_catalogs: tuple[Path, ...] = (), summary: Mapping[str, Any] | None = None,
           detail: Mapping[str, Any] | None = None) -> RenderedReview:
    """Render `source` through `presentation` (default: the packaged preset bundle) and return the review.

    `summary` is an optional Summary Profile document; the Layout Profile must carry a `summary` slot to show it.
    `detail` is an optional Review Detail Profile document; its `legend` shows in a Layout Profile with a `legend` slot.
    """
    parts = presentation or bundle()
    paths = {kind: _write(directory / f"{kind}.yaml", value) for kind, value in parts.items()}
    draft = resolve_draft_render(
        project_path=_write(directory / "project.yaml", source), view_path=paths["view"],
        theme_path=paths["theme"], scheme_path=paths["scheme"], layout_path=paths["layout"],
        actual_path=_write(directory / "actual.yaml", actual) if actual is not None else None,
        summary_path=_write(directory / "summary.yaml", summary) if summary is not None else None,
        detail_path=_write(directory / "detail.yaml", detail) if detail is not None else None,
        icon_catalog_paths=icon_catalogs, viewport=viewport)
    return render_review(RenderRequest(
        closure=draft.closure, snapshot_root=draft.asset_root, asset_root=draft.asset_root,
        scheduler=ReferenceScheduler(), renderer=V05SvgRenderer(), draft_auto_block=draft.auto_block))


def find_node(layout: Mapping[str, Any], node_id: str) -> dict[str, Any]:
    """The Layout Profile node with `node_id`, searched depth first."""
    def visit(node: Mapping[str, Any]) -> Mapping[str, Any] | None:
        if node.get("id") == node_id:
            return node
        return next((found for child in node.get("children", ()) if (found := visit(child))), None)
    node = visit(layout["root"])
    if node is None:
        raise KeyError(node_id)
    return node  # type: ignore[return-value]


def _fix_size(parts: dict[str, dict[str, Any]], node_id: str, axis: str, size: int, token: str) -> None:
    layout = parts["layout"]
    layout["requiredThemeTokens"] = sorted({*layout["requiredThemeTokens"], token})
    find_node(layout, node_id)[axis] = {"fixed": {"token": token}}
    parts["theme"]["body"]["values"][token] = {"type": "number", "value": size}


def fix_block(parts: dict[str, dict[str, Any]], node_id: str, block: int, *, token: str = "fixed-block") -> None:
    """Give one Layout node a fixed block size from a new Theme token: a fixed host."""
    _fix_size(parts, node_id, "blockSize", block, token)


def fix_inline(parts: dict[str, dict[str, Any]], node_id: str, inline: int, *, token: str = "fixed-inline") -> None:
    """Give one Layout node a fixed inline size from a new Theme token."""
    _fix_size(parts, node_id, "inlineSize", inline, token)


def with_balloon_notes(parts: dict[str, dict[str, Any]]) -> None:
    """Let note boxes use the `tail` connector by giving their role a balloon container."""
    theme = parts["theme"]["body"]
    theme["values"]["balloon-container"] = {
        "type": "annotationContainer", "value": {"outline": "balloon", "cornerRadius": 0.2, "tailBaseEm": 0.6}}
    theme["roles"]["annotation-note-box"]["annotationContainer"] = "balloon-container"


def with_note_rail(parts: dict[str, dict[str, Any]], width: int = 300) -> None:
    """Make the Layout's `annotations` slot a rail of `width` that fills the block axis."""
    fix_inline(parts, "annotations", width, token="note-rail-width")
    find_node(parts["layout"], "annotations")["blockSize"] = "fill"


_OBSTACLES = ["mark", "text", "label-visual", "dependency-route", "leader-route",
              "annotation-box", "port", "rule"]


def candidate(candidate_id: str, *, region: Mapping[str, Any] | None = None, connector: str = "tail",
              max_positions: int = 1024, search_kind: str = "nearest-free") -> dict[str, Any]:
    """One declared annotation candidate; the default region is the plot."""
    search: dict[str, Any] = {"kind": search_kind}
    if search_kind == "nearest-free":
        search.update(maxPositions=max_positions, maxInlineEm=12)
    return {"id": candidate_id, "region": dict(region or {"kind": "plot"}), "search": search,
            "obstacles": {"classes": list(_OBSTACLES)}, "connector": {"kind": connector}}


def add_notes(source: dict[str, Any], view: dict[str, Any], targets: Iterable[str],
              candidates: Iterable[Mapping[str, Any]], *, words: int = 3, endpoint: str = "body") -> list[str]:
    """Annotate each target object with a note offering the same declared candidates; return the note ids."""
    source["annotations"] = {}
    body = view["body"]
    body["annotations"] = []
    body["visibility"]["annotations"] = {"mode": "presentation", "marker": "numbered"}
    ids = []
    for index, target in enumerate(targets):
        note_id = f"note-{index}"
        ids.append(note_id)
        source["annotations"][note_id] = {"kind": "note", "text": " ".join([f"Synthetic note {index} on {target}."] + ["and more words"] * words),
                                          "anchor": {"object": target}}
        body["annotations"].append({
            "id": note_id, "purpose": "note", "projectAnnotation": note_id,
            "anchor": {"kind": "object", "id": target, "facet": "planned", "endpoint": endpoint},
            "candidates": [deepcopy(dict(item)) for item in candidates]})
    return ids
