from pathlib import Path

import pytest

from tools.presentation_coverage import PresentationCoverageError, _validate_resource_versions, discover, live_schemas, render, vocabulary, _vocabulary


def _root() -> Path:
    return next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def test_presentation_coverage_is_deterministic_and_complete():
    root = _root()
    assert len(discover(root)) == 21
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


def test_presentation_coverage_rejects_non_live_resource_versions():
    root = _root()
    slide = discover(root)[0]
    kind, path, document = slide.resources[0]
    stale = dict(document, version="chrona/not-live")
    changed = slide.__class__(slide.identifier, slide.root, ((kind, path, stale), *slide.resources[1:]), slide.scene)
    with pytest.raises(PresentationCoverageError, match="E_PRESENTATION_COVERAGE_VERSION"):
        _validate_resource_versions((changed,), live_schemas(root))


def test_presentation_coverage_is_not_a_renderer_or_svg_reader():
    source = (_root() / "tools/presentation_coverage.py").read_text(encoding="utf-8")
    assert "chrona." not in source
    assert ".svg" not in source


def test_presentation_coverage_commits_platform_independent_lf_bytes():
    source = (_root() / "tools/presentation_coverage.py").read_text(encoding="utf-8")
    assert 'newline="\\n"' in source
