"""Complete the automatic-row identity warning from accepted Layout facts."""
from __future__ import annotations

from dataclasses import replace

from chrona.presentation.layout.surface_completion import SurfaceLayoutComposition
from chrona.presentation.model.diagnostic_sources import DiagnosticProvenance, DiagnosticSubject


def complete_row_identity_warning(
    composition: SurfaceLayoutComposition, *, row_mode: str,
    has_table_columns: bool, name_selected: bool,
) -> SurfaceLayoutComposition:
    """Count affected ordinary rows once, never temporal absences or labels."""
    if row_mode != "automatic" or has_table_columns or not name_selected:
        return composition
    placement = composition.placement
    suppressed_sources = {
        item.source_ref for item in placement.text
        if item.semantic_id == "memberLabel" and item.overflow == "suppressed"
    }
    affected_rows = {
        row.row_id for row in composition.review_rows
        if any(item.object_id in suppressed_sources for item in row.items)
    }
    if not affected_rows:
        return composition
    diagnostic = f"W_LAYOUT_ROW_IDENTITY_MISSING:count={len(affected_rows)}"
    provenance = DiagnosticProvenance(diagnostic, (DiagnosticSubject("/body/tableColumns"),))
    return replace(composition, placement=replace(
        placement, diagnostics=(*placement.diagnostics, diagnostic),
        diagnostic_provenance=(*placement.diagnostic_provenance, provenance)))
