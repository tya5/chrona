"""Project-generic View vocabulary (#479 I479-1)."""
from __future__ import annotations

import json
from hashlib import sha256
import sys
from pathlib import Path

import pytest
import yaml

from chrona.app.cli import main
from chrona.storage.snapshot_paths import snapshot_directory

ROOT = Path(__file__).resolve().parents[2]
HALCYON = ROOT / "examples/halcyon-1"


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _dump(path: Path, value: dict) -> Path:
    path.write_text(yaml.safe_dump(value, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def _render(tmp_path: Path, monkeypatch, *, project: dict | None = None, view_edit=None, theme_edit=None) -> dict:
    preset = tmp_path / "preset"
    monkeypatch.setattr(sys, "argv", ["chrona", "preset", "copy", "mission-light", "--output", str(preset)])
    main()
    view_path = next(preset.glob("**/view.yaml"))
    theme_path = next(preset.glob("**/theme.yaml"))
    # These tests exercise generic grouping, ordering and color-encoding
    # vocabulary, whose original contract is automatic row composition.
    view = _load(view_path)
    view["body"]["rows"]["mode"] = "automatic"
    for key in ("packing", "laneTable", "laneKeys"):
        view["body"]["rows"].pop(key, None)
    view["body"].setdefault("tableColumns", [{
        "id": "Title", "source": "title", "missing": "em-dash", "align": "start",
        "width": "content", "headerOrientation": "horizontal",
    }])
    _dump(view_path, view)
    if view_edit:
        view = _load(view_path)
        view_edit(view["body"])
        _dump(view_path, view)
    if theme_edit:
        theme = _load(theme_path)
        theme_edit(theme["body"])
        _dump(theme_path, theme)
    project_value = project if project is not None else _load(HALCYON / "project.yaml")
    store_root = tmp_path / "store"
    store_config = tmp_path / "store-config.yaml"
    store_config.write_text(yaml.safe_dump({
        "version": "chrona/store-config/v0.1",
        "stores": [{"provider": "local", "identity": "halcyon-1-example", "root": "store",
                    "integrity": "required"}],
    }, sort_keys=False), encoding="utf-8")
    # HALCYON's Project extension is an immutable local-snapshot reference.
    # Stage the exact published package bytes under its declared address and
    # complete the reference with the digest required by the configured Store.
    for extension in project_value.get("extensions", ()):
        reference = extension.get("resource", {})
        address = reference["address"]
        revision = reference["revision"]["token"]
        package_bytes = (HALCYON / address).read_bytes()
        package_path = snapshot_directory(store_root, revision) / address
        package_path.parent.mkdir(parents=True, exist_ok=True)
        package_path.write_bytes(package_bytes)
        reference["contentIdentity"] = f"sha256:{sha256(package_bytes).hexdigest()}"
    project_path = _dump(tmp_path / "project.yaml", project_value)
    scene_path = tmp_path / "scene.json"
    monkeypatch.setattr(sys, "argv", [
        "chrona", "render", str(project_path), "--preset", str(preset / "preset.yaml"),
        "--store-config", str(store_config), "--output", str(tmp_path / "out.svg"),
        "--emit-scene", str(scene_path),
    ])
    main()
    return json.loads(scene_path.read_text(encoding="utf-8"))["surfaces"][0]


def _group_headers(surface: dict) -> list[str]:
    headers = [item for item in surface["primitives"] if item["id"].startswith("group-header:")
               and item.get("kind") == "Text"]
    return [item["id"].removeprefix("group-header:") for item in sorted(headers, key=lambda item: item["bounds"]["block"])]


def _earliest_start_order(surface: dict, project: dict) -> list[str]:
    """Groups ordered by the leftmost scheduled planned mark of their members."""
    earliest: dict[str, float] = {}
    for item in surface["primitives"]:
        if not item["id"].startswith("planned:"):
            continue
        owner = project["objects"].get(item["id"].split(":")[1], {}).get("fields", {}).get("owner")
        if owner:
            earliest[owner] = min(earliest.get(owner, float("inf")), item["bounds"]["inline"])
    return sorted(earliest, key=lambda owner: (earliest[owner], owner))


def test_groups_order_by_their_earliest_planned_start(tmp_path, monkeypatch):
    def edit(body: dict) -> None:
        body["grouping"]["order"] = {"by": "earliestPlannedStart"}
    surface = _render(tmp_path, monkeypatch, view_edit=edit)
    headers = _group_headers(surface)
    assert len(headers) > 1
    assert headers == _earliest_start_order(surface, _load(HALCYON / "project.yaml"))


def test_a_project_without_the_grouping_field_draws_no_group_header(tmp_path, monkeypatch):
    project = _load(HALCYON / "project.yaml")
    for obj in project["objects"].values():
        obj.get("fields", {}).pop("owner", None)
    surface = _render(tmp_path, monkeypatch, project=project)
    assert not any(item["id"].startswith("group-header:") for item in surface["primitives"])


def test_first_appearance_domain_takes_palette_slots_in_projection_order(tmp_path, monkeypatch):
    def view_edit(body: dict) -> None:
        body["colorEncoding"] = {"scale": "owner", "target": "planned", "source": {"field": "owner"},
                                 "domain": "firstAppearance"}
    def theme_edit(body: dict) -> None:
        body["colorScales"]["owner"] = {"palette": ["series-1", "series-2", "series-3"]}
    surface = _render(tmp_path, monkeypatch, view_edit=view_edit, theme_edit=theme_edit)
    project = _load(HALCYON / "project.yaml")
    fills: dict[str, set[str]] = {}
    for item in surface["primitives"]:
        if item["id"].startswith("planned:") and item.get("paint", {}).get("fill"):
            owner = project["objects"].get(item["id"].split(":")[1], {}).get("fields", {}).get("owner")
            if owner:
                fills.setdefault(owner, set()).add(item["paint"]["fill"])
    assert len(fills) > 3
    distinct = {owner: next(iter(values)) for owner, values in fills.items() if len(values) == 1}
    # three palette slots, then one neutral Other for the rest: no hue is reused (#1628)
    assert len(set(distinct.values())) == 4


def test_labels_both_requires_a_table_title_column(tmp_path, monkeypatch, capsys):
    def edit(body: dict) -> None:
        body["visibility"]["labels"]["placement"] = "both"
        body["tableColumns"] = [column for column in body["tableColumns"] if column["source"] != "title"]
        if not body["tableColumns"]:
            body["tableColumns"] = [{
                "id": "#", "source": "rowIndex", "missing": "em-dash", "align": "start",
                "width": "content", "headerOrientation": "horizontal",
            }]
    with pytest.raises(SystemExit):
        _render(tmp_path, monkeypatch, view_edit=edit)
    assert "E_VIEW_LABELS_BOTH_TABLE_TITLE" in capsys.readouterr().out


def test_labels_both_renders_plot_labels_like_plot(tmp_path, monkeypatch):
    (tmp_path / "plot").mkdir()
    (tmp_path / "both").mkdir()
    plot = _render(tmp_path / "plot", monkeypatch)
    both = _render(tmp_path / "both", monkeypatch,
                   view_edit=lambda body: body["visibility"]["labels"].__setitem__("placement", "both"))
    assert plot["primitives"] == both["primitives"]


def test_first_appearance_leaves_an_item_without_the_field_in_its_role_paint(tmp_path, monkeypatch):
    project = _load(HALCYON / "project.yaml")
    project["objects"]["structure"]["fields"].pop("owner")
    def view_edit(body: dict) -> None:
        body["colorEncoding"] = {"scale": "owner", "target": "planned", "source": {"field": "owner"},
                                 "domain": "firstAppearance"}
    def theme_edit(body: dict) -> None:
        body["colorScales"]["owner"] = {"palette": ["series-1", "series-2", "series-3"]}
    surface = _render(tmp_path, monkeypatch, project=project, view_edit=view_edit, theme_edit=theme_edit)
    fills = {item["id"].split(":")[1]: item["paint"].get("fill") for item in surface["primitives"]
             if item["id"].startswith("planned:")}
    assert fills["structure"] not in {fills["pdr"], fills["payload-delivery"]}
