from pathlib import Path

from chrona.presentation.model.semantic_registry import semantic_binding, semantic_ids
from chrona.presentation.scene.capabilities import _ROLE_PROPERTY_CONTRACTS, theme_role_contract
from chrona.presentation.model.point_paint import resolve_point_paint_role
from tools.theme_role_reference import check_reference, render_reference


def test_generated_reference_covers_semantics_and_registered_role_contracts():
    page = render_reference()

    for semantic_id in semantic_ids():
        binding = semantic_binding(semantic_id)
        assert "| " + " | ".join((semantic_id, binding.primitive_kind, binding.purpose,
                                    binding.scene_role, binding.theme_role)) + " |" in page
    for role in _ROLE_PROPERTY_CONTRACTS:
        assert f"| {role} |" in page
        contract = theme_role_contract(role)
        if contract is not None:
            assert contract.consumer in page
            for property_name in contract.properties:
                assert property_name in page


def test_reference_distinguishes_paint_from_geometry_and_uses_authored_token_ids():
    page = render_reference()

    assert "`as-of.stroke`" in page
    assert "`planned.fill`" in page
    assert "`milestone.fill`" in page
    assert "`gate.fill`" in page
    assert "`actual.fill`" in page
    assert "`milestoneSymbol` is point-glyph geometry" in page
    selected = resolve_point_paint_role("planned", gate_declared=False)
    gate = resolve_point_paint_role("planned", gate_declared=True)
    assert f"its selected targets are `{selected}.fill` / `{gate}.fill`" in page
    assert "point-symbol token may use" in page
    assert "smallCapsScale" in page
    assert "Layout Profile's top-level `viewDefaults.progressFill.source`" in page
    assert "View's `body.progressFill.source`" in page
    assert "an explicit View value replaces that default" in page
    assert "including progress on completed Actual marks" in page
    assert "`swatchShape: circle`" in page
    assert "`critical-edge`" in page
    assert "Color Schemes provide the colors selected by Theme `colorBindings`" in page


def test_checked_in_reference_is_exactly_generated(tmp_path):
    reference = Path(__file__).resolve().parents[3] / "skills/chrona/references/theme-role-reference.md"
    assert check_reference(reference)

    stale = tmp_path / "theme-role-reference.md"
    stale.write_text("stale\n", encoding="utf-8")
    assert not check_reference(stale)


def test_row_pitch_reference_names_the_minimum_and_completed_demand_owners():
    page = render_reference()
    assert "`timeline.row.minBlockSize` is a minimum, not a fixed row pitch" in page
    assert "fontSize × lineHeight × wrapped line count" in page
    assert "`timeline.row.paddingBlock`" in page
    assert "`timeline.mark.blockSize`" in page
    assert "selected role/occurrence geometry" in page
    assert "fill distribution can enlarge it further" in page
