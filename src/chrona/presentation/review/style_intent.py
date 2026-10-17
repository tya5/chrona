"""Lower admitted View presentation inputs to the shared typed Style rules."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from chrona.presentation.model.semantic_registry import semantic_binding, semantic_ids
from chrona.presentation.style import (
    StyleEncodingOutcome, StyleFieldSource, StyleRule, StyleSelector,
)


def lower_legacy_color_encoding(encoding: Mapping[str, Any] | None) -> tuple[StyleRule, ...]:
    """Preserve View encoding syntax without a second predicate evaluator.

    Ingress has already resolved ``fieldRole`` availability. Legacy ``target``
    names a canonical Scene role, not a purpose: planned and forecast match,
    but a gate with the same planned purpose does not. Legend admission for
    authored scoped Style rules does not apply to this existing View input.
    """
    if encoding is None:
        return ()
    domain = encoding["domain"]
    outcome = StyleEncodingOutcome(
        "fill", StyleFieldSource(field_name=encoding["source"]["field"]),
        encoding["scale"], domain if isinstance(domain, str) else tuple(domain),
    )
    return tuple(
        StyleRule(f"view-colorEncoding:{semantic}", StyleSelector(semantic=semantic),
                  outcome, "/body/colorEncoding")
        for semantic in semantic_ids()
        if semantic_binding(semantic).primitive_kind == "mark"
        and semantic_binding(semantic).scene_role == encoding["target"]
    )
