import json
from decimal import Decimal
from types import SimpleNamespace

from chrona.usecases.diagnostic_messages import describe_warning, warning_message
from chrona.usecases.warning_ledger import collect_render_warnings


def _contributor(slot_id, *, inline_start=0, inline_end=0, block_start=0, block_end=0):
    return SimpleNamespace(
        slot_id=slot_id,
        bounds=SimpleNamespace(inline=Decimal("0"), block=Decimal("0"),
                               inline_size=Decimal("120"), block_size=Decimal("80")),
        overrun=SimpleNamespace(inline_start=Decimal(str(inline_start)),
                                inline_end=Decimal(str(inline_end)),
                                block_start=Decimal(str(block_start)),
                                block_end=Decimal(str(block_end))),
    )


def _warning(*, surface_id="table-timeline", block_size=90):
    return SimpleNamespace(
        code="W_LAYOUT_CANVAS_EXCEEDS_VIEWPORT",
        source_ref="/body/environment/viewport",
        surface_id=surface_id,
        declared=SimpleNamespace(inline_size=Decimal("100"), block_size=None),
        actual=SimpleNamespace(inline=Decimal("-2"), block=Decimal("0"),
                               inline_size=Decimal("104"), block_size=Decimal(str(block_size))),
        contributors=(_contributor("timeline", inline_start=2, inline_end=2),
                      _contributor("detail-panel", block_end=10)),
        contributor_count=2,
    )


def _collect(canvas_warning):
    return collect_render_warnings(
        surface_diagnostics=(), tabular_warnings=(), glyph_warnings=(), fit_warnings=(),
        perceptibility_warnings=(), scale_collisions=(), attachment_warnings=(),
        canvas_warning=canvas_warning,
    )


def test_canvas_warning_has_json_safe_facts_stable_surface_identity_and_readable_message():
    record, = _collect(_warning())

    assert record.payload["code"] == "W_LAYOUT_CANVAS_EXCEEDS_VIEWPORT"
    assert record.payload["surfaceId"] == "table-timeline"
    assert record.payload["sourceRef"] == "/body/environment/viewport"
    assert record.payload["declared"] == {"inlineSize": 100.0, "blockSize": None}
    assert record.payload["actual"] == {
        "inlineStart": -2.0, "blockStart": 0.0, "inlineSize": 104.0, "blockSize": 90.0,
    }
    assert record.payload["contributors"] == [
        {"slotId": "timeline",
         "bounds": {"inlineStart": 0.0, "blockStart": 0.0, "inlineSize": 120.0, "blockSize": 80.0},
         "overrun": {"inlineStart": 2.0, "inlineEnd": 2.0, "blockStart": 0.0, "blockEnd": 0.0}},
        {"slotId": "detail-panel",
         "bounds": {"inlineStart": 0.0, "blockStart": 0.0, "inlineSize": 120.0, "blockSize": 80.0},
         "overrun": {"inlineStart": 0.0, "inlineEnd": 0.0, "blockStart": 0.0, "blockEnd": 10.0}},
    ]
    assert record.payload["contributorCount"] == 2
    json.dumps(record.payload, allow_nan=False)

    message = warning_message(describe_warning(record.payload))
    assert "completed canvas exceeds the declared viewport" in message
    assert "surface table-timeline" in message
    assert "declared 100xauto" in message
    assert "actual origin -2,0 size 104x90" in message
    assert "timeline (inline-start 2, inline-end 2)" in message
    assert "detail-panel (block-end 10)" in message


def test_canvas_warning_identity_uses_surface_and_source_not_extent_and_preserves_multiplicity():
    first, = _collect(_warning(surface_id="table-timeline", block_size=90))
    same_identity_new_extent, = _collect(_warning(surface_id="table-timeline", block_size=110))
    other_surface, = _collect(_warning(surface_id="dependency-network", block_size=90))

    assert first.identity == same_identity_new_extent.identity
    assert first.identity != other_surface.identity
    assert first.payload["diagnostic"] == first.identity
    assert other_surface.payload["diagnostic"] == other_surface.identity
    assert len(_collect(_warning())) == 1


def test_no_canvas_warning_keeps_existing_warning_collection_unchanged():
    assert collect_render_warnings(
        surface_diagnostics=(), tabular_warnings=(), glyph_warnings=(), fit_warnings=(),
        perceptibility_warnings=(), scale_collisions=(), attachment_warnings=(),
    ) == ()
