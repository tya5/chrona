"""Completed Layout facts survive actual Scene/SVG and public warning transport."""
from copy import deepcopy
from datetime import date

import pytest

from chrona.resources import default_preset_resource, default_preset_root, safe_load
from chrona.usecases.draft_render import warning_payloads
from tests.support import synthetic_review as sr


CODE = "W_LAYOUT_AUTO_BLOCK_SIZE"


def test_tall_rows_warn_once_without_resizing_and_within_limit_does_not(tmp_path):
    source = sr.project({f"t{i}": sr.span(f"t{i}", date(2027, 1, 4), 14) for i in range(21)})
    parts = sr.bundle()
    baseline = sr.render(tmp_path, source, presentation=parts, viewport=(1600, None))
    assert baseline.surface.canvas_bounds[3] > 900
    parts["layout"]["reviewSurface"]["maxBlockSize"] = 900
    tall = sr.render(tmp_path, source, presentation=parts, viewport=(1600, None))
    warnings = [w for w in warning_payloads(tall) if w["code"] == CODE]
    assert len(warnings) == 1
    warning = warnings[0]
    assert warning["rowCount"] == len(tall.surface.rows) == 21
    assert warning["actualBlockSize"] == tall.surface.canvas_bounds[3]
    assert warning["maxBlockSize"] == 900
    assert warning["sourceRef"] == "/reviewSurface/maxBlockSize"
    assert "selection/grouping" in warning["message"]
    assert "paging is a future option" in warning["message"]
    assert tall.surface.primitives == baseline.surface.primitives
    assert tall.surface.canvas_bounds == baseline.surface.canvas_bounds
    assert tall.artifact.content == baseline.artifact.content
    parts["layout"]["reviewSurface"]["maxBlockSize"] = tall.surface.canvas_bounds[3]
    fitting = sr.render(tmp_path, source, presentation=parts, viewport=(1600, None))
    assert fitting.surface.auto_block_warning is None
    assert not any(w["code"] == CODE for w in warning_payloads(fitting))
    assert fitting.surface.primitives == baseline.surface.primitives


def test_bundled_limit_is_declared_in_standalone_default_not_catalogue():
    root = default_preset_root()
    preset = safe_load(default_preset_resource().read_bytes())
    declaration = preset["body"]["resources"]["layout"]
    default = safe_load(root.joinpath(declaration["path"]).read_bytes())
    catalogue = safe_load(root.joinpath("bundles/editorial/layout.yaml").read_bytes())
    assert default["id"] == declaration["id"] == "chrona-builtin-editorial-readable-default"
    assert default["reviewSurface"]["maxBlockSize"] == 3600
    original = deepcopy(default)
    original["id"] = catalogue["id"]
    original["reviewSurface"].pop("maxBlockSize")
    assert original == catalogue


def test_limit_does_not_enable_unsupported_network_auto_height_or_warn_for_fixed_height(tmp_path):
    from tests.integration.test_title_ink import _network_parts
    from chrona.usecases.render_review import RenderFailed

    parts = _network_parts()
    parts["layout"]["reviewSurface"]["maxBlockSize"] = 0
    source = sr.project({"a": sr.span("a", date(2027, 1, 4), 2)})
    rendered = sr.render(tmp_path, source, presentation=parts, viewport=(1600, 900))
    assert not any(w["code"] == CODE for w in warning_payloads(rendered))
    assert rendered.surface.auto_block_warning is None
    with pytest.raises(RenderFailed) as caught:
        sr.render(tmp_path, source, presentation=parts, viewport=(1600, None))
    assert caught.value.code == "E_LAYOUT_DRAFT_AUTO_UNSUPPORTED"
