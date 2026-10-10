"""A catalogue pattern on the group band, the group-header band and the row band (#1282).

Synthetic Project grouped by owner through the packaged `control-room-dark` bundle with the packaged
`chrona-target-parts` catalogue; no test reads `examples/`.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tests.support import synthetic_review as sr

ROOT = Path(__file__).resolve().parents[2]
CATALOGUE = ROOT / "src/chrona/resources/icons/chrona-target-parts-v2026-10-09.yaml"
DOTS = "chrona-target-parts:hazard-stripes"
OWNERS = ("bus", "payload", "ground")
ROLES = ("group-band", "group-header-band", "row-band")


def _parts(*roles: str, ink: str = "warning") -> dict:
    parts = sr.bundle("control-room-dark")
    if "group-header-band" in roles and "group-band" not in roles:
        # The header band is drawn only where no group band already covers the header row.
        parts["view"]["body"]["backgroundDecoration"] = {"rows": "alternate" if "row-band" in roles else "none",
                                                         "groups": "none"}
    parts["theme"]["version"] = "chrona/theme/v0.15"
    body = parts["theme"]["body"]
    body["values"]["band.pattern"] = {"type": "pattern", "value": {"kind": "catalog", "ref": DOTS}}
    for role in roles:
        binding = body["roles"].setdefault(role, {"backgroundTreatment": "fill", "backgroundPaintOrder": 10})
        binding["pattern"] = "band.pattern"
        body["colorBindings"][f"{role}.stroke"] = ink  # the pattern's ink
        body["colorBindings"].setdefault(f"{role}.fill", "surface")  # the substrate
    return parts


def _render(tmp_path, parts):
    return sr.render(tmp_path, sr.bunched_project(groups=2, per_group=3), presentation=parts, icon_catalogs=(CATALOGUE,))


def _patterned(rendered):
    return {item.scene_id: item for item in rendered.surface.primitives
            if item.kind == "Rect" and item.pattern is not None and item.pattern.primitives}


@pytest.mark.parametrize("role,prefix", [("group-band", "group:"), ("group-header-band", "group-header-band"),
                                          ("row-band", "row-band:")])
def test_a_pattern_bound_on_a_band_role_is_carried_by_that_bands_rect_with_the_declared_ink(tmp_path, role, prefix):
    rendered = _render(tmp_path, _parts(role))
    found = _patterned(rendered)

    assert found, role
    assert all(item.scene_id.startswith(prefix) for item in found.values())
    assert all(item.visual_role == role for item in found.values())
    assert all(item.paint.stroke is not None for item in found.values())  # the ink is the role's stroke
    # The pattern is clipped to its band: its clip is the band's own extent (the one `backgroundExtents` chose).
    for item in found.values():
        assert tuple(float(value) for value in item.pattern.clip_bounds) == pytest.approx(item.bounds)


def test_the_bands_carry_the_pattern_together_where_each_is_drawn(tmp_path):
    both = _patterned(_render(tmp_path / "a" if (tmp_path / "a").mkdir() is None else tmp_path, _parts("group-band", "row-band")))
    header = _patterned(_render(tmp_path / "b" if (tmp_path / "b").mkdir() is None else tmp_path,
                                _parts("group-header-band", "row-band")))

    assert {item.visual_role for item in both.values()} == {"group-band", "row-band"}
    assert {item.visual_role for item in header.values()} == {"group-header-band", "row-band"}


def test_a_theme_without_the_pattern_is_unchanged(tmp_path):
    plain = _render(tmp_path / "a" if (tmp_path / "a").mkdir() is None else tmp_path, _parts())
    declared_nothing = _render(tmp_path / "b" if (tmp_path / "b").mkdir() is None else tmp_path, _parts())

    assert plain.artifact.content == declared_nothing.artifact.content
    assert _patterned(plain) == {}


def test_a_pattern_on_a_role_outside_the_list_is_still_refused(tmp_path):
    parts = _parts()
    parts["theme"]["body"]["values"]["band.pattern"] = {"type": "pattern", "value": {"kind": "catalog", "ref": DOTS}}
    parts["theme"]["body"]["roles"]["calendar-closed"] = {"backgroundTreatment": "fill", "backgroundPaintOrder": 11,
                                                          "pattern": "band.pattern"}

    with pytest.raises(Exception) as caught:
        _render(tmp_path, parts)

    assert "E_THEME_ROLE_PROPERTY_UNSUPPORTED" in str(caught.value) + repr(getattr(caught.value, "diagnostic_id", ""))
