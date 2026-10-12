"""Layout completion of recovery centreline geometry and ordering."""
from dataclasses import replace

from chrona.presentation.layout.surface_quality import RelationHaloPlacement, RelationPlacement, TextPlacement
from chrona.presentation.model.semantic_registry import semantic_binding
from chrona.presentation.model.theme_tokens import ThemeTokenView


def complete_relation_halo(relation: RelationPlacement, tokens: ThemeTokenView,
                           text: tuple[TextPlacement, ...]) -> RelationPlacement:
    paint_order = min((relation.paint_order, *(item.paint_order - 1 for item in text)))
    if paint_order < 1:
        raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID: no paint layer below text for recovery halo")
    relation = replace(relation, paint_order=paint_order)
    width = float(tokens.dependency_halo_width(semantic_binding(relation.semantic_id).theme_role))
    xs, ys = zip(*relation.points)
    half = width / 2
    bounds = (min(xs) - half, min(ys) - half,
              max(xs) - min(xs) + width, max(ys) - min(ys) + width)
    halo = RelationHaloPlacement(relation.points, relation.path_commands, bounds,
                                 width, relation.paint_order - 1, relation.paint_clip)
    return replace(relation, halo=halo)
