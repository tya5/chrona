from hashlib import sha256
import json
from pathlib import Path
import sys

import yaml

from chrona.app.cli import main
from chrona.presentation.contracts import ClosureIdentity, PresentationPresetContract, ViewContract, parse_contract
from tests.support import synthetic_review as sr
from tests.support.draft_packages import stage_project_package_store
from tests.support.preset_policy import assert_view_copy_except_axis as _assert_view_copy_except_axis


ROOT = Path(__file__).parents[2]


def test_controller_z_public_preset_names_the_executive_context_resources():
    root = ROOT / "tests/fixtures/controller-z"
    preset = yaml.safe_load((root / "executive-light.preset.yaml").read_bytes())
    contract = parse_contract(ClosureIdentity("presentation-preset", preset["id"], "evidence", "sha256:" + sha256(yaml.safe_dump(preset, sort_keys=True).encode()).hexdigest()), preset)
    assert isinstance(contract, PresentationPresetContract)
    context = yaml.safe_load((root / "contexts/executive.yaml").read_bytes())["body"]
    expected = {"view": context["view"], "theme": context["theme"], "colorScheme": context["colorScheme"], "layout": context["layout"]}
    for slot, declaration in contract.resources.items():
        assert (declaration["id"], declaration["kind"], declaration["path"]) == (expected[slot]["id"], expected[slot]["kind"], expected[slot]["address"])
        assert (root / declaration["path"]).is_file()


def _assert_packaged_view_contract(path: Path, expected_id: str) -> dict:
    raw = path.read_bytes()
    document = yaml.safe_load(raw)
    assert document["id"] == expected_id
    identity = ClosureIdentity("view", expected_id, "builtin", "sha256:" + sha256(raw).hexdigest())
    assert isinstance(parse_contract(identity, document), ViewContract)
    return document


def test_editorial_non_view_corpus_copies_match_and_packaged_view_is_independent():
    """Packaged Views own general policy; authored corpus Views remain independent.

    HALCYON reads the packaged Editorial Theme, Scheme and detail profile in place (#1397), so the
    corpus keeps no copy of them; its Layout permits only the packaged table cap.
    """
    bundle = ROOT / "src/chrona/resources/presets/bundles/editorial"
    corpus = ROOT / "examples/halcyon-1"
    packaged = {
        "theme": "theme.yaml",
        "colorScheme": "scheme.yaml",
    }
    for context_name in ("13-gallery-editorial.yaml", "16-gallery-editorial-lanes.yaml"):
        body = yaml.safe_load((corpus / "contexts" / context_name).read_bytes())["body"]
        slots = {slot: body[slot] for slot in packaged} | {"detailProfile": body["inputs"]["detailProfile"]}
        for slot, reference in slots.items():
            name = packaged.get(slot, "detail.yaml")
            assert reference["store"] == {"provider": "package", "identity": "chrona.resources"}, (context_name, slot)
            assert reference["address"] == f"presets/bundles/editorial/{name}", (context_name, slot)
            assert reference["revision"] == {"token": "bundled"}, (context_name, slot)
            assert reference["id"] == yaml.safe_load((bundle / name).read_bytes())["id"], (context_name, slot)
    for name in ("themes/editorial.yaml", "schemes/editorial.yaml", "profiles/editorial-detail.yaml"):
        assert not (corpus / name).exists(), name
    packaged_layout = yaml.safe_load((bundle / "layout.yaml").read_bytes())
    corpus_layout = yaml.safe_load((corpus / "layouts/editorial.yaml").read_bytes())
    assert sr.find_node(packaged_layout, "table").pop("maxInlineShare") == 0.4
    assert packaged_layout == corpus_layout
    _assert_packaged_view_contract(bundle / "view.yaml", "chrona-preset-editorial")
    _assert_view_copy_except_axis(bundle / "view.yaml", corpus / "views/editorial.yaml")


def test_packaged_library_schemes_match_the_example_copies_except_project_categories():
    """#574: the library's colour schemes resolve from the wheel-packaged bundles,
    never from examples/. A bundle may not name an example project's group values
    (test_project_generic_presets), so each packaged scheme equals its example copy
    minus the `categories` entries keyed by those values."""
    bundles = ROOT / "src/chrona/resources/presets/bundles"
    copies = {
        "mission-light": "examples/halcyon-1/schemes/mission-light.yaml",
        "control-room-dark": "examples/halcyon-1/schemes/control-room-dark.yaml",
        "print-mono": "examples/halcyon-1/schemes/print-mono.yaml",
        "executive-light": "tests/fixtures/controller-z/schemes/executive-light.yaml",
        "elevated-light": "tests/fixtures/controller-z/schemes/executive-light.yaml",
    }
    project_categories = {"bus", "payload", "ait", "ground", "launch", "ops", "factory-team", "fw-team", "validation-team"}
    library = yaml.safe_load((ROOT / "src/chrona/resources/presets/library.yaml").read_bytes())
    entries = {entry["id"]: entry for entry in library["entries"]}
    for preset_id, corpus_path in copies.items():
        member = entries[preset_id]["members"]["colorScheme"]
        assert (member["sourceRoot"], member["sourcePath"]) == (f"presets/bundles/{preset_id}", "scheme.yaml")
        packaged = yaml.safe_load((bundles / preset_id / "scheme.yaml").read_bytes())
        corpus = yaml.safe_load((ROOT / corpus_path).read_bytes())
        categories = corpus["body"]["categories"]
        corpus["body"]["categories"] = {key: value for key, value in categories.items() if key not in project_categories}
        assert packaged == corpus, preset_id
    assert "examples/" not in (ROOT / "src/chrona/resources/presets/library.yaml").read_text(encoding="utf-8")


def test_legend_swatch_marks_are_never_checked_against_the_timeline_bottom(tmp_path, monkeypatch, capsys):
    """A legend swatch drawn as a point-shaped mark (#427, e.g. a milestone diamond)
    lives in the legend slot below the plot by construction. It must never be
    checked against the timeline's own bottom edge, which always reports a
    spurious W_LAYOUT_MARK_OVERFLOW with available block clamped to 0 -- found
    building the Editorial and Technical print presets' legends (I429-2)."""
    output = tmp_path / "editorial.svg"
    project_path = ROOT / "examples/halcyon-1/project.yaml"
    project = yaml.safe_load(project_path.read_bytes())
    store_config = stage_project_package_store(tmp_path / "project-store", project, project_path.parent)
    monkeypatch.setattr(sys, "argv", [
        "chrona", "render", str(project_path),
        "--actual", str(ROOT / "examples/halcyon-1/actual.yaml"),
        "--view", str(ROOT / "examples/halcyon-1/views/editorial.yaml"),
        "--theme", str(ROOT / "src/chrona/resources/presets/bundles/editorial/theme.yaml"),
        "--scheme", str(ROOT / "src/chrona/resources/presets/bundles/editorial/scheme.yaml"),
        "--layout", str(ROOT / "examples/halcyon-1/layouts/editorial.yaml"),
        "--detail", str(ROOT / "src/chrona/resources/presets/bundles/editorial/detail.yaml"),
        "--store-config", str(store_config), "--output", str(output),
    ])
    main()
    output = capsys.readouterr()
    assert output.err == ""
    envelope = json.loads(output.out)
    assert envelope["status"] == "ok" and envelope["diagnostics"] == []
    warnings = envelope["warnings"]
    assert not [item for item in warnings if item.get("code") == "W_LAYOUT_MARK_OVERFLOW"]


def test_editorial_library_entry_matches_the_bundle_resources():
    library = yaml.safe_load((ROOT / "src/chrona/resources/presets/library.yaml").read_bytes())
    entry = next(item for item in library["entries"] if item["id"] == "editorial")
    assert "gallerySet" not in entry  # no gallery set shows Editorial (#1403)
    bundle = ROOT / "src/chrona/resources/presets/bundles/editorial"
    for name, member in entry["members"].items():
        assert member["sourceRoot"] == "presets/bundles/editorial"
        declared = yaml.safe_load((bundle / member["sourcePath"]).read_bytes())
        assert declared["id"] == member["id"]


def test_readable_default_resources_are_selected_from_the_packaged_authority():
    corpus = ROOT / "examples/halcyon-1"
    default = yaml.safe_load((ROOT / "src/chrona/resources/presets/default.yaml").read_bytes())
    resources = default["body"]["resources"]
    assert default["id"] == "chrona-default-draft"
    bundle = ROOT / "src/chrona/resources/presets/bundles/editorial-readable-default"
    pairs = {
        "view.yaml": corpus / "views/editorial-readable-default.yaml",
        "theme.yaml": corpus / "themes/editorial-readable-default.yaml",
    }
    for name, corpus_path in pairs.items():
        package_bytes = (bundle / name).read_bytes()
        declared = yaml.safe_load(package_bytes)
        assert declared["id"] == resources["view" if name == "view.yaml" else "theme"]["id"]
        assert resources["view" if name == "view.yaml" else "theme"]["path"] == \
            f"bundles/editorial-readable-default/{name}"
        if name == "view.yaml":
            _assert_packaged_view_contract(bundle / name, resources["view"]["id"])
            _assert_view_copy_except_axis(bundle / name, corpus_path, first_run=True)
            labels = declared["body"]["visibility"]["labels"]
            assert (labels["placement"], labels["content"], labels["side"]) == ("plot", ["title"], "end")
            assert declared["version"] == "chrona/view/v0.28"
            assert declared["body"]["rows"] == {"mode": "automatic"}
            assert [column["id"] for column in declared["body"]["tableColumns"]] == ["Task", "Plan"]
            assert declared["body"]["tableColumns"][1]["endDisplay"] == "inclusive"
            assert declared["body"]["visibility"]["fallback"]["labels"] == ["end", "start", "suppress"]
            assert declared["body"]["backgroundDecoration"]["rows"] == "rules"
            assert declared["body"]["grouping"] == {"by": "hierarchy", "depth": "all", "rollup": "header"}
            assert declared["body"]["hierarchyColumn"] == "Task"
        else:
            body = declared["body"]
            expected = yaml.safe_load(corpus_path.read_bytes())
            migrated = expected["body"]
            migrated["values"].pop("opacity.row-band")
            migrated["values"]["timeline-row-height"]["value"] = {
                "expr": "{timeline-mark-size} + {timeline-row-padding}"}
            migrated["roles"].pop("row-band")
            migrated["roles"]["row-rule"] = {"strokeWidth": "stroke-width"}
            migrated["roles"]["group-band"]["backgroundPaintOrder"] = 8
            migrated["roles"]["group-header-band"]["backgroundPaintOrder"] = 9
            migrated["colorBindings"].pop("row-band.fill")
            migrated["colorBindings"]["row-rule.stroke"] = "neutral"
            # The packaged default alone declares the shared deadline-mark role (#1397 row 2).
            for value, number in (("deadline-mark-width", 2), ("deadline-mark-reach", 1.7), ("deadline-mark-order", 5)):
                migrated["values"][value] = {"type": "number", "value": number}
            migrated["roles"]["deadline-mark"] = {
                "strokeWidth": "deadline-mark-width", "markReach": "deadline-mark-reach",
                "markPaintOrder": "deadline-mark-order"}
            migrated["colorBindings"]["deadline-mark.stroke"] = "text"
            # The packaged default stacks a year-bearing tier over a week tier, both light on the
            # navy band, and sizes the axis as the sum of the two lanes (#1724 P2).
            migrated["values"]["axis-lane-quarter"]["value"] = 32
            migrated["values"]["axis-lane-month"]["value"] = 34
            migrated["values"]["timeline-axis-height"]["value"] = {
                "expr": "{axis-lane-quarter} + {axis-lane-month}"}
            migrated["colorBindings"]["axis-label3.fill"] = "surface"
            assert declared == expected  # keep every unaffected Theme declaration
    assert resources["view"] == {
        "id": "chrona-preset-editorial-readable-default", "kind": "view",
        "path": "bundles/editorial-readable-default/view.yaml",
    }
    assert resources["theme"] == {
        "id": "chrona-builtin-editorial-readable-default", "kind": "theme",
        "path": "bundles/editorial-readable-default/theme.yaml",
    }
    assert resources["colorScheme"] == {
        "id": "chrona-builtin-editorial", "kind": "color-scheme", "path": "bundles/editorial/scheme.yaml",
    }
    assert resources["layout"] == {
        "id": "chrona-builtin-editorial-readable-default", "kind": "layout-profile",
        "path": "bundles/editorial-readable-default/layout.yaml",
    }
    assert resources["detailProfile"]["path"] == "bundles/editorial/detail.yaml"
    assert default["body"]["compatibleColorSchemes"] == [
        {"id": "chrona-builtin-editorial", "kind": "color-scheme", "path": "bundles/editorial/scheme.yaml"}
    ]
    library = yaml.safe_load((ROOT / "src/chrona/resources/presets/library.yaml").read_bytes())
    editorial = next(item for item in library["entries"] if item["id"] == "editorial")
    assert "gallerySet" not in editorial  # no gallery set shows Editorial (#1403)
    assert editorial["members"]["view"]["sourceRoot"] == "presets/bundles/editorial"
    assert editorial["members"]["view"]["id"] == "chrona-preset-editorial-lanes"
    assert editorial["members"]["view"]["sourcePath"] == "view-lanes.yaml"
    reference_package = ROOT / "src/chrona/resources/presets/bundles/editorial/view.yaml"
    _assert_packaged_view_contract(reference_package, "chrona-preset-editorial")
    _assert_view_copy_except_axis(reference_package, corpus / "views/editorial.yaml")
    lane_package = ROOT / "src/chrona/resources/presets/bundles/editorial/view-lanes.yaml"
    lane_view = _assert_packaged_view_contract(lane_package, editorial["members"]["view"]["id"])
    assert lane_view["body"]["rows"]["mode"] == "lanes"
    _assert_view_copy_except_axis(lane_package, corpus / "views/editorial-lanes.yaml")
    assert editorial["members"]["theme"]["sourceRoot"] == "presets/bundles/editorial"
    assert editorial["members"]["theme"]["sourcePath"] == "theme.yaml"
