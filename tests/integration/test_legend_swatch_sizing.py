"""Legend swatch knobs: a swatch-to-label gap apart from the entry gap, an area swatch size and a point swatch size (#1111).

Synthetic Project through the packaged `executive-light` bundle with the legend slot declared `direction: inline`
(and `block`) and a Review Detail Profile legend; no test reads `examples/`.
"""
from __future__ import annotations

from datetime import date

import pytest

from chrona.usecases.render_review import RenderFailed
from tests.support import synthetic_review as sr

ROLES = ("planned", "milestone", "calendar-closed", "actual")
LABELS = {"planned": "Planned", "milestone": "Gate", "calendar-closed": "Non-working", "actual": "Actual"}
DETAIL = {"version": "chrona/review-detail-profile/v0.1", "id": "legend-detail",
          "body": {"legend": [{"role": role, "label": LABELS[role]} for role in ROLES]}}


def _render(tmp_path, *, direction="inline", slot_gap=None, swatch_gap=None, area_block=None, area_inline=None,
            point=None, roles=ROLES, gates=True):
    parts = sr.bundle("executive-light")
    node = sr.find_node(parts["layout"], "legend")
    node["direction"] = direction
    if slot_gap is not None:
        node["gap"] = {"token": "legend-entry-gap"}
        parts["layout"]["requiredThemeTokens"] = sorted({*parts["layout"]["requiredThemeTokens"], "legend-entry-gap"})
        parts["theme"]["body"]["values"]["legend-entry-gap"] = {"type": "number", "value": slot_gap}
    body = parts["theme"]["body"]
    # The bundle draws no gate key: the milestone swatch needs its own paint.
    body["roles"].setdefault("milestone", {})
    body["colorBindings"].setdefault("milestone.fill", "text")
    role = {}
    for name, value in (("swatchGap", swatch_gap), ("swatchBlockSize", area_block),
                        ("swatchInlineSize", area_inline), ("pointSwatchSize", point)):
        if value is not None:
            body["values"][f"legend-{name}"] = {"type": "number", "value": value}
            role[name] = f"legend-{name}"
    if role:
        body["roles"]["legend-swatch"] = {**body["roles"].get("legend-swatch", {}), **role}
    # A declared calendar closes the weekend, which is what makes the non-working-day key appear (#893).
    source = sr.with_calendar(sr.project({"a": sr.span("a", date(2026, 2, 2), 30),
                                           **({"g": sr.point("g", date(2026, 3, 9))} if gates else {})}))
    detail = {**DETAIL, "body": {"legend": [{"role": item, "label": LABELS[item]} for item in roles]}}
    return sr.render(tmp_path, source, presentation=parts, detail=detail)


def _sub(tmp_path, name):
    path = tmp_path / name
    path.mkdir()
    return path


def _entries(rendered):
    """Each entry's (swatch bounds, label bounds) by role, from the published Scene."""
    primitives = rendered.surface.primitives
    found = {}
    for role in ROLES:
        swatch = next((item for item in primitives if item.scene_id.startswith(f"legend-swatch:{role}")), None)
        label = next((item for item in primitives if item.scene_id == f"legend:{role}"), None)
        if swatch is not None and label is not None:
            found[role] = (swatch.bounds, label.bounds)
    return found


def _end(bounds):
    return bounds[0] + bounds[2]


@pytest.mark.parametrize("direction", ["inline", "block"])
def test_a_label_starts_swatch_gap_after_its_swatch_and_the_next_entry_an_entry_gap_after(tmp_path, direction):
    entries = _entries(_render(_sub(tmp_path, "gaps"), direction=direction, slot_gap=26, swatch_gap=6))
    assert set(entries) == set(ROLES)
    for swatch, label in entries.values():
        assert label[0] - _end(swatch) == pytest.approx(6, abs=0.01)
    if direction == "inline":
        ordered = [entries[role] for role in ROLES]
        for (_, label), (next_swatch, _) in zip(ordered, ordered[1:]):
            assert next_swatch[0] - _end(label) == pytest.approx(26, abs=0.5)  # the measured label ends at its text width
    else:
        tops = [entries[role][0][1] for role in ROLES]
        heights = [max(entries[role][0][3], entries[role][1][3]) for role in ROLES]
        for index in range(len(ROLES) - 1):
            assert tops[index + 1] - (tops[index] + heights[index]) >= 26 - 1.0


def test_without_a_swatch_gap_one_gap_serves_both_distances(tmp_path):
    entries = _entries(_render(_sub(tmp_path, "single"), slot_gap=14))
    for swatch, label in entries.values():
        assert label[0] - _end(swatch) == pytest.approx(14, abs=0.01)


def test_an_area_swatch_has_the_declared_inline_and_block_size_and_marks_keep_theirs(tmp_path):
    plain = _entries(_render(_sub(tmp_path, "plain"), area_inline=22))
    sized = _entries(_render(_sub(tmp_path, "sized"), area_inline=22, area_block=12))
    swatch = sized["calendar-closed"][0]
    assert (swatch[2], swatch[3]) == (22, 12)
    assert sized["planned"][0] == plain["planned"][0] or sized["planned"][0][2:] == plain["planned"][0][2:]
    # Declaring only the inline size leaves the area key the legacy square (a Theme that already declares it is unchanged).
    legacy = plain["calendar-closed"][0]
    assert legacy[2] == legacy[3] != 22


def test_a_point_swatch_has_the_declared_size(tmp_path):
    plain = _entries(_render(_sub(tmp_path, "plain")))["milestone"][0]
    sized = _entries(_render(_sub(tmp_path, "sized"), point=12))["milestone"][0]
    assert (sized[2], sized[3]) == (12, 12) and plain[2] != 12


def test_absent_declarations_are_byte_identical_and_unrelated_roles_are_untouched(tmp_path):
    from chrona.presentation.scene.serialization import scene_document

    first = _render(_sub(tmp_path, "a"))
    second = _render(_sub(tmp_path, "b"), swatch_gap=None)
    assert scene_document(first.scene)["surfaces"] == scene_document(second.scene)["surfaces"]


@pytest.mark.parametrize(("kwargs", "pointer"), [
    ({"swatch_gap": -1}, "/body/roles/legend-swatch/swatchGap"),
    ({"area_block": 0}, "/body/roles/legend-swatch/swatchBlockSize"),
    ({"point": 0}, "/body/roles/legend-swatch/pointSwatchSize"),
])
def test_an_out_of_range_token_is_a_theme_token_error_at_its_property(tmp_path, kwargs, pointer):
    with pytest.raises(RenderFailed) as raised:
        _render(_sub(tmp_path, "bad"), **kwargs)
    assert (raised.value.code, raised.value.source_ref) == ("E_THEME_TOKEN_TYPE", pointer)


def test_legend_labels_stay_ground_text(tmp_path):
    from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
    from chrona.presentation.scene.serialization import scene_document

    rendered = _render(_sub(tmp_path, "contrast"), slot_gap=26, swatch_gap=6, area_block=12, area_inline=22, point=12)
    findings = [item for item in evaluate_scene_contrast(scene_document(rendered.scene)) if item.purpose == "legend-label"]
    assert findings and all(item.floor == 4.5 and item.severity != "error" for item in findings)


def test_typst_and_tikz_draw_the_completed_swatch_and_label_positions(tmp_path):
    """Neither adapter reads the knobs: they draw the Layout-completed rectangle and the label's completed origin.

    (Typst and TikZ draw no symbol, so the point key is not in this fixture; they reject it as before.)
    """
    from chrona.presentation.renderers.v05_typeset import V05TikzRenderer, V05TypstRenderer

    rendered = _render(_sub(tmp_path, "adapters"), slot_gap=26, swatch_gap=6, area_block=12, area_inline=22,
                       roles=("planned", "calendar-closed"), gates=False)
    swatch, label = _entries(rendered)["calendar-closed"]
    assert (swatch[2], swatch[3]) == (22, 12) and label[0] - _end(swatch) == pytest.approx(6, abs=0.01)
    typst = V05TypstRenderer().render(rendered.surface).content.decode()
    tikz = V05TikzRenderer().render(rendered.surface).content.decode()
    assert f"left: {round(swatch[0], 3)}pt, top: {round(swatch[1], 3)}pt)[#rect(width: 22pt, height: 12pt" in typst
    assert f"left: {round(label[0], 3)}pt" in typst and f"at ({round(label[0], 3)}," in tikz


def test_the_content_sized_legend_slot_measures_the_swatch_gap(tmp_path):
    """The slot is the swatch, `swatchGap` and the widest label wide, so measurement reads the same gap as drawing."""
    def slot_width(name, gap):
        rendered = _render(_sub(tmp_path, name), direction="block", swatch_gap=gap)
        return next(item for item in rendered.surface.slots if item.source == "legend").bounds[2]

    # Both gaps are past the 180 unit floor a flow item keeps, so the slot is exactly content wide.
    assert slot_width("wide", 300) - slot_width("narrow", 200) == pytest.approx(100, abs=0.5)
