from hashlib import sha256
import json
from pathlib import Path
import sys

import yaml

from chrona.app.cli import main
from chrona.presentation.contracts import ClosureIdentity, PresentationPresetContract, parse_contract


ROOT = Path(__file__).parents[2]


def test_controller_z_public_preset_names_the_executive_context_resources():
    root = ROOT / "examples/controller-z"
    preset = yaml.safe_load((root / "executive-light.preset.yaml").read_bytes())
    contract = parse_contract(ClosureIdentity("presentation-preset", preset["id"], "evidence", "sha256:" + sha256(yaml.safe_dump(preset, sort_keys=True).encode()).hexdigest()), preset)
    assert isinstance(contract, PresentationPresetContract)
    context = yaml.safe_load((root / "contexts/executive.yaml").read_bytes())["body"]
    expected = {"view": context["view"], "theme": context["theme"], "colorScheme": context["colorScheme"], "layout": context["layout"]}
    for slot, declaration in contract.resources.items():
        assert (declaration["id"], declaration["kind"], declaration["path"]) == (expected[slot]["id"], expected[slot]["kind"], expected[slot]["address"])
        assert (root / declaration["path"]).is_file()


def test_editorial_corpus_copy_is_byte_identical_to_the_packaged_bundle():
    """#383/#429: the corpus Context cannot reference the wheel-packaged bundle
    directly (see the design correction), so HALCYON-1 carries a byte-identical
    copy under its own views/themes/layouts/schemes/profiles. This guards
    against the two silently drifting apart."""
    bundle = ROOT / "src/chrona/resources/presets/bundles/editorial"
    corpus = ROOT / "examples/halcyon-1"
    pairs = {
        "view.yaml": corpus / "views/editorial.yaml",
        "theme.yaml": corpus / "themes/editorial.yaml",
        "layout.yaml": corpus / "layouts/editorial.yaml",
        "scheme.yaml": corpus / "schemes/editorial.yaml",
        "detail.yaml": corpus / "profiles/editorial-detail.yaml",
    }
    for bundle_name, corpus_path in pairs.items():
        bundle_path = bundle / bundle_name
        assert bundle_path.is_file() and corpus_path.is_file()
        assert bundle_path.read_bytes() == corpus_path.read_bytes(), (bundle_name, corpus_path)


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
        "executive-light": "examples/controller-z/schemes/executive-light.yaml",
        "elevated-light": "examples/controller-z/schemes/executive-light.yaml",
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
    monkeypatch.setattr(sys, "argv", [
        "chrona", "render", str(ROOT / "examples/halcyon-1/project.yaml"),
        "--actual", str(ROOT / "examples/halcyon-1/actual.yaml"),
        "--view", str(ROOT / "examples/halcyon-1/views/editorial.yaml"),
        "--theme", str(ROOT / "examples/halcyon-1/themes/editorial.yaml"),
        "--scheme", str(ROOT / "examples/halcyon-1/schemes/editorial.yaml"),
        "--layout", str(ROOT / "examples/halcyon-1/layouts/editorial.yaml"),
        "--detail", str(ROOT / "examples/halcyon-1/profiles/editorial-detail.yaml"),
        "--output", str(output),
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
    assert entry["gallerySet"] == "generated-design-directions"
    bundle = ROOT / "src/chrona/resources/presets/bundles/editorial"
    for name, member in entry["members"].items():
        assert member["sourceRoot"] == "presets/bundles/editorial"
        declared = yaml.safe_load((bundle / member["sourcePath"]).read_bytes())
        assert declared["id"] == member["id"]


def test_readable_default_resources_are_mirrored_and_selected_without_mutating_editorial():
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
        assert package_bytes == corpus_path.read_bytes(), name
        declared = yaml.safe_load(package_bytes)
        assert declared["id"] == resources["view" if name == "view.yaml" else "theme"]["id"]
        assert resources["view" if name == "view.yaml" else "theme"]["path"] == \
            f"bundles/editorial-readable-default/{name}"
        if name == "view.yaml":
            labels = declared["body"]["visibility"]["labels"]
            assert (labels["placement"], labels["content"], labels["side"]) == ("plot", ["title"], "end")
            assert declared["version"] == "chrona/view/v0.28"
            assert declared["body"]["rows"] == {"mode": "automatic"}
            assert [column["id"] for column in declared["body"]["tableColumns"]] == ["Task", "Plan"]
            assert declared["body"]["visibility"]["fallback"]["labels"] == ["end", "start", "suppress"]
            assert declared["body"]["backgroundDecoration"]["rows"] == "alternate"
        else:
            body = declared["body"]
            assert body["values"]["opacity.row-band"]["value"] == 0.12
            assert body["roles"]["row-band"]["opacity"] == "opacity.row-band"
            assert body["colorBindings"]["row-band.fill"] == "category:default"
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
    assert resources["layout"]["path"] == "bundles/editorial/layout.yaml"
    assert resources["detailProfile"]["path"] == "bundles/editorial/detail.yaml"
    assert default["body"]["compatibleColorSchemes"] == [
        {"id": "chrona-builtin-editorial", "kind": "color-scheme", "path": "bundles/editorial/scheme.yaml"}
    ]
    library = yaml.safe_load((ROOT / "src/chrona/resources/presets/library.yaml").read_bytes())
    editorial = next(item for item in library["entries"] if item["id"] == "editorial")
    assert editorial["gallerySet"] == "generated-design-directions"
    assert editorial["members"]["view"]["sourceRoot"] == "presets/bundles/editorial"
    assert editorial["members"]["view"]["id"] == "chrona-preset-editorial-lanes"
    assert editorial["members"]["view"]["sourcePath"] == "view-lanes.yaml"
    reference_package = ROOT / "src/chrona/resources/presets/bundles/editorial/view.yaml"
    reference_corpus = corpus / "views/editorial.yaml"
    assert reference_package.read_bytes() == reference_corpus.read_bytes()
    assert yaml.safe_load(reference_package.read_bytes())["id"] == "chrona-preset-editorial"
    lane_package = ROOT / "src/chrona/resources/presets/bundles/editorial/view-lanes.yaml"
    assert lane_package.read_bytes() == (corpus / "views/editorial-lanes.yaml").read_bytes()
    assert editorial["members"]["theme"]["sourceRoot"] == "presets/bundles/editorial"
    assert editorial["members"]["theme"]["sourcePath"] == "theme.yaml"
