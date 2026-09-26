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
    warnings = [json.loads(line) for line in capsys.readouterr().err.splitlines() if line.startswith("{")]
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
