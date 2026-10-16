from pathlib import Path

import pytest
import yaml

from chrona.resources import schema_validator

from tests.support.public_evidence import declared_slides
from tools.schema_equivalence import SchemaValidators, load_schema_dir, run_l2
from tools.presentation_coverage import (
    PresentationCoverageError, RunLocalYamlLoader, _validate_resource_versions,
    discover, effective_view, effective_views, live_schemas, render,
    view_default_contexts, vocabulary, _vocabulary,
)


def _root() -> Path:
    return next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def test_presentation_coverage_is_deterministic_and_complete():
    root = _root()
    slides = discover(root)
    assert [slide.identifier for slide in slides] == [slide.key for slide in declared_slides(root)]
    report = render(root)
    assert report == render(root)
    assert "## Layout slot evidence" in report
    assert "`observations`" in report
    assert "## Declared but never realized slot sources" in report
    assert "halcyon-1/overlay-briefing" in report


def test_presentation_vocabulary_uses_live_contracts_only():
    rows = vocabulary(_root())
    assert rows == tuple(sorted(rows))
    assert {row.kind for row in rows} == {"view", "layout-profile", "theme", "color-scheme"}
    assert any(row.kind == "layout-profile" and row.value == '"overlay"' for row in rows)


def test_presentation_vocabulary_follows_nested_conditional_schema_values():
    schema = {"properties": {"token": {"if": {"properties": {"kind": {"const": "marker"}}},
                                         "then": {"properties": {"value": {"properties": {"shape": {"enum": ["circle", "square"]}}}}}}}}
    values = _vocabulary({"theme": schema})
    assert {(value.path, value.value) for value in values} >= {
        (("token", "kind"), '"marker"'),
        (("token", "value", "shape"), '"circle"'),
        (("token", "value", "shape"), '"square"'),
    }


def test_presentation_coverage_accepts_a_live_derived_theme_resource():
    root = _root()
    glyph_gates = next(slide for slide in discover(root) if slide.identifier == "halcyon-1/glyph-gates")
    kind, path, document = next(item for item in glyph_gates.resources if item[0] == "theme")
    assert document.get("version") == "chrona/theme/v0.16"
    _validate_resource_versions((glyph_gates,), live_schemas(root), root)


def test_presentation_coverage_accepts_transitioning_view_during_resource_migration():
    root = _root()
    slide = next(slide for slide in discover(root) if slide.identifier == "halcyon-1/programme-board")
    view = next(document for kind, _path, document in slide.resources if kind == "view")
    assert view["version"] == "chrona/view/v0.28"
    assert "chrona/view/v0.28" in render(root)
    _validate_resource_versions((slide,), live_schemas(root), root)


def test_presentation_coverage_rejects_non_live_resource_versions():
    root = _root()
    slide = discover(root)[0]
    kind, path, document = slide.resources[0]
    stale = dict(document, version="chrona/not-live")
    changed = slide.__class__(slide.identifier, slide.root, ((kind, path, stale), *slide.resources[1:]), slide.scene)
    with pytest.raises(PresentationCoverageError, match="E_PRESENTATION_COVERAGE_VERSION"):
        _validate_resource_versions((changed,), live_schemas(root), root)


def test_presentation_coverage_is_not_a_renderer_or_svg_reader():
    source = (_root() / "tools/presentation_coverage.py").read_text(encoding="utf-8")
    assert "chrona.presentation.contracts.view_defaults" in source
    assert "renderers" not in source
    assert ".svg" not in source


def test_presentation_coverage_commits_platform_independent_lf_bytes():
    source = (_root() / "tools/presentation_coverage.py").read_text(encoding="utf-8")
    assert 'newline="\\n"' in source
    assert ".relative_to(root).as_posix()" in source


def test_run_local_loader_reuses_only_one_report_operation(tmp_path):
    path = tmp_path / "evidence.yaml"
    path.write_text("value: first\n", encoding="utf-8")
    first_run = RunLocalYamlLoader()
    assert first_run.load(path) == {"value": "first"}
    path.write_text("value: second\n", encoding="utf-8")
    assert first_run.load(path) == {"value": "first"}
    assert RunLocalYamlLoader().load(path) == {"value": "second"}


def _write_multicontext_corpus(root: Path, *, invalid_defaults: bool = False) -> Path:
    example = root / "examples" / "multi-context"
    for directory in ("contexts", "views", "layouts", "themes", "schemes", "generated"):
        (example / directory).mkdir(parents=True, exist_ok=True)
    (example / "manifest.yaml").write_text(
        "version: chrona/example-materializer/v0.1\nid: multi-context\nrole: regression-corpus\n"
        "slides:\n"
        "  - {id: first, context: contexts/first.yaml, expectedScene: generated/first.json}\n"
        "  - {id: second, context: contexts/second.yaml, expectedScene: generated/second.json}\n"
        "  - {id: third, context: contexts/third.yaml, expectedScene: generated/third.json}\n",
        encoding="utf-8")
    (example / "views/shared.yaml").write_text(
        "version: chrona/view/v0.28\nkind: view\nid: shared\nbody: {surface: table-timeline}\n",
        encoding="utf-8")
    (example / "layouts/first.yaml").write_text(
        "viewDefaults: {axis: {tiers: [{unit: month}]}}\n", encoding="utf-8")
    second_defaults = "[]" if invalid_defaults else "{axis: {tiers: [{unit: quarter}]}}"
    (example / "layouts/second.yaml").write_text(
        f"viewDefaults: {second_defaults}\n", encoding="utf-8")
    (example / "layouts/third.yaml").write_text("root: {id: page, kind: column}\n", encoding="utf-8")
    (example / "themes/theme.yaml").write_text("version: test\n", encoding="utf-8")
    (example / "schemes/scheme.yaml").write_text("version: test\n", encoding="utf-8")
    for name, layout in (("first", "first"), ("second", "second"), ("third", "third")):
        (example / f"contexts/{name}.yaml").write_text(
            "body:\n"
            "  view: {kind: view, address: views/shared.yaml}\n"
            f"  layout: {{kind: layout-profile, address: layouts/{layout}.yaml}}\n"
            "  theme: {kind: theme, address: themes/theme.yaml}\n"
            "  colorScheme: {kind: color-scheme, address: schemes/scheme.yaml}\n",
            encoding="utf-8")
        (example / f"generated/{name}.json").write_text("{}\n", encoding="utf-8")
    return example / "views/shared.yaml"


def test_effective_view_uses_production_merge_without_replacing_raw_resources(tmp_path):
    view_path = _write_multicontext_corpus(tmp_path)
    slide = discover(tmp_path)[0]
    raw = next(document for kind, _path, document in slide.resources if kind == "view")
    effective = effective_view(slide)
    assert "axis" not in raw["body"]
    assert effective["body"]["axis"]["tiers"][0]["unit"] == "month"
    assert next(document for kind, _path, document in slide.resources if kind == "view") is raw
    assert view_path.resolve() == next(path for kind, path, _document in slide.resources if kind == "view")


def test_effective_views_and_defaults_retain_every_shared_view_context_in_order(tmp_path):
    view_path = _write_multicontext_corpus(tmp_path)
    defaults = view_default_contexts(tmp_path)
    effective = effective_views(tmp_path)
    assert tuple(defaults) == (view_path.resolve(),)
    assert tuple(effective) == (view_path.resolve(),)
    assert [item.get("axis", {}).get("tiers", [{}])[0].get("unit") for item in defaults[view_path.resolve()]] == ["month", "quarter", None]
    assert [item["body"].get("axis", {}).get("tiers", [{}])[0].get("unit") for item in effective[view_path.resolve()]] == ["month", "quarter", None]


def test_view_context_helpers_do_not_reuse_a_global_yaml_cache(tmp_path):
    view_path = _write_multicontext_corpus(tmp_path)
    first = effective_views(tmp_path)[view_path.resolve()]
    layout_path = view_path.parent.parent / "layouts/first.yaml"
    layout_path.write_text("viewDefaults: {axis: {tiers: [{unit: year}]}}\n", encoding="utf-8")
    second = effective_views(tmp_path)[view_path.resolve()]
    assert first[0]["body"]["axis"]["tiers"][0]["unit"] == "month"
    assert second[0]["body"]["axis"]["tiers"][0]["unit"] == "year"


def test_view_context_helpers_reject_invalid_defaults_in_later_context(tmp_path):
    _write_multicontext_corpus(tmp_path, invalid_defaults=True)
    with pytest.raises(PresentationCoverageError, match="E_PRESENTATION_COVERAGE_VIEW_DEFAULTS:multi-context/second"):
        effective_views(tmp_path)


def _write_packaged_preset_contexts(root: Path, *, unsafe_source_root: str | None = None,
                                   unsafe_source_path: str | None = None) -> Path:
    resources = root / "src/chrona/resources"
    view_path = resources / "presets/bundles/design-default/view.yaml"
    view_path.parent.mkdir(parents=True, exist_ok=True)
    source_view = _root() / "src/chrona/resources/presets/bundles/design-default/view.yaml"
    view_path.write_bytes(source_view.read_bytes())
    entries = []
    for identifier, defaults in (
        ("design-one", "{markerPresentation: {kind: asOf, label: FIRST}}"),
        ("design-two", "{}"),
    ):
        layout_path = resources / f"designs/{identifier}/layout.yaml"
        layout_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_defaults = yaml.safe_load(defaults)
        resolved_defaults["comparison"] = {
            "deltaUnit": "working-days" if identifier == "design-one" else "calendar-days",
        }
        resolved_defaults["periodLabelPresentation"] = {"placement": "top"}
        resolved_defaults["columnStyles"] = {"field": {
            "missing": "em-dash", "align": "start", "width": "content",
            "headerOrientation": "horizontal",
        }}
        layout_path.write_text(
            yaml.safe_dump({"version": "chrona/layout-profile/v0.10", "id": identifier,
                            "viewDefaults": resolved_defaults}, sort_keys=False),
            encoding="utf-8",
        )
        source_root = (unsafe_source_root if identifier == "design-two" and unsafe_source_root
                       else f"designs/{identifier}")
        source_path = unsafe_source_path if identifier == "design-two" and unsafe_source_path else "layout.yaml"
        entries.append({
            "id": identifier,
            "members": {
                "view": {"id": "chrona-preset-design-default", "kind": "view",
                         "sourceRoot": "presets/bundles/design-default", "sourcePath": "view.yaml"},
                "layout": {"id": identifier, "kind": "layout-profile",
                           "sourceRoot": source_root, "sourcePath": source_path},
            },
        })
    library_path = resources / "presets/library.yaml"
    library_path.parent.mkdir(parents=True, exist_ok=True)
    library = {"version": "chrona/preset-library/v0.2", "entries": entries}
    library_path.write_text(yaml.safe_dump(library, sort_keys=False), encoding="utf-8")
    return view_path


def test_packaged_library_pairs_shared_view_with_every_declared_layout_default(tmp_path):
    view_path = _write_packaged_preset_contexts(tmp_path)
    defaults = view_default_contexts(tmp_path)[view_path.resolve()]
    variants = effective_views(tmp_path)[view_path.resolve()]

    assert defaults[0]["markerPresentation"] == {"kind": "asOf", "label": "FIRST"}
    assert "markerPresentation" not in defaults[1]
    assert all(value["columnStyles"]["field"]["width"] == "content" for value in defaults)
    assert len(variants) == 2
    assert variants[0]["body"]["markers"][0]["label"] == "FIRST"
    assert "label" not in variants[1]["body"]["markers"][0]
    assert all(value["body"]["tableColumns"][1]["width"] == "content" for value in variants)
    assert all(value["body"]["periods"]["label"]["placement"] == "top" for value in variants)
    assert [value["body"]["comparison"]["deltaUnit"] for value in variants] == [
        "working-days", "calendar-days",
    ]
    validator = schema_validator("view-v0.28.schema.yaml")
    assert validator.is_valid(variants[0])
    assert any(list(error.absolute_path) == ["body", "markers", 0] and "'label'" in error.message
               for error in validator.iter_errors(variants[1]))
    relative_path = view_path.relative_to(tmp_path).as_posix()
    corpus = run_l2(
        {relative_path: view_path.read_bytes()}, SchemaValidators(load_schema_dir(_root() / "schemas")),
        view_defaults={relative_path: defaults},
    )
    assert corpus.records[0]["valid"] is False


@pytest.mark.parametrize(("field", "unsafe_path"), [
    ("sourcePath", "../../../../outside.yaml"),
    ("sourceRoot", r"..\..\outside"),
    ("sourcePath", "C:/outside.yaml"),
])
def test_packaged_library_member_paths_cannot_escape_resources(tmp_path, field, unsafe_path):
    option = "unsafe_source_path" if field == "sourcePath" else "unsafe_source_root"
    _write_packaged_preset_contexts(tmp_path, **{option: unsafe_path})
    with pytest.raises(PresentationCoverageError, match="E_PRESENTATION_COVERAGE_PRESET_REFERENCE"):
        effective_views(tmp_path)


def test_non_default_integer_vocabulary_names_the_every_slide():
    """#434: a non-default `every` is derived into the report with its slide."""
    content = (Path(__file__).resolve().parents[3] / "docs/gallery/presentation-coverage.md").read_text(encoding="utf-8")
    assert "| view | `body.axis.tiers[].every` | `2` | halcyon-1/gates |" in content
