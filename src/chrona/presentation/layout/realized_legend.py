"""Close semantic and encoded keys against final completed painted placements."""
from dataclasses import replace

from chrona.presentation.layout.legend_candidates import actual_key_label, coalesce_actual_keys
from chrona.presentation.layout.legend_diagnostics import completed_legend_diagnostics
from chrona.presentation.layout.legend_ink import actual_mark_keys, mark_ink_keys
from chrona.presentation.layout.style_legend import painted_style_occurrences
from chrona.presentation.layout.surface_legend import SurfaceLegendContext, place_legend
from chrona.presentation.layout.slot_heading import content_slot, full_slot, inline_content_slot, inline_full_slot
from chrona.presentation.model.legend_paint import effective_ink_identity
from chrona.presentation.model.semantic_registry import semantic_binding, semantic_ids


def completed_legend_slots(slots, allocated_slots, legend, headings):
    """Restore caption bands without retaining potential-only legend growth."""
    if legend is None:
        return slots
    allocated = next(slot for slot in allocated_slots if slot.source_ref == "legend")
    completed = inline_full_slot(allocated,
        full_slot(allocated, legend.slot, headings.reserved("legend")),
        headings.reserved_inline("legend"))
    return tuple(completed if slot.source_ref == "legend" else slot for slot in slots)


def reserve_potential_legend(request, legend_slot, slots, headings, metric_values, metric_for):
    """Complete the conservative batch for earlier fixed geometry decisions."""
    if legend_slot is None:
        return None, slots
    batch = place_legend(SurfaceLegendContext(request,
        inline_content_slot(content_slot(legend_slot, headings.reserved("legend")),
                            headings.reserved_inline("legend")), metric_values, metric_for))
    return batch, completed_legend_slots(slots, slots, batch, headings)


def visible_placement(placement):
    bounds = placement.bounds
    if bounds.inline_size < 0 or bounds.block_size < 0:
        return False
    if bounds.inline_size == 0 or bounds.block_size == 0:
        # Completed horizontal/vertical strokes have no area, but do have ink.
        points = getattr(placement, "points", ())
        if len(set(points)) < 2:
            return False
    clip = getattr(placement, "paint_clip", None)
    if clip is None:
        return True
    x, y, width, height = clip.bounds
    return (float(bounds.inline) < x + width and float(bounds.inline + bounds.inline_size) > x
            and float(bounds.block) < y + height and float(bounds.block + bounds.block_size) > y)


def _scene_role(semantic):
    return semantic_binding(semantic).scene_role if semantic in semantic_ids() else semantic


def _base_mark(entry, mark):
    if entry.role == "milestone":
        return mark.mark_shape == "point" and mark.semantic_id in {"planned", "forecast"}
    if entry.role == "planned":
        return mark.mark_shape != "point" and mark.semantic_id == "planned"
    if entry.role == "forecast":
        return mark.semantic_id == "forecast"
    return _scene_role(entry.role) == _scene_role(mark.semantic_id)


def _same_base_ink(mark, content, tokens, capabilities):
    realized = mark_ink_keys(mark, content, tokens, capabilities)
    if not realized or any(key.paint.channels.solid_override for key in realized):
        return False
    base = mark_ink_keys(mark, content, tokens, capabilities, base=True)
    ink = lambda keys: {(key.paint.identity, key.pattern_identity) for key in keys}
    return ink(realized) == ink(base)


def _progress_adds_actual_ink(progress_key, progress_shapes, drawn_marks, content, tokens, capabilities):
    """Keep Progress only when a visible host has distinct completed Actual ink."""
    hosts = {mark.placement_id: mark for mark in drawn_marks}
    for shape in progress_shapes:
        host = hosts.get(shape.host_placement_id)
        if host is None:
            return True
        host_keys = (actual_mark_keys(host, content, tokens, capabilities)
                     if host.semantic_id == "actual"
                     else mark_ink_keys(host, content, tokens, capabilities))
        if not host_keys:
            return True
        paints = tuple(paint for key in host_keys
                       for paint in (key.glyph.paints if key.glyph is not None else (key.paint,)))
        pattern_set = {key.pattern_identity for key in host_keys if key.pattern_identity is not None}
        patterns = next(iter(pattern_set)) if len(pattern_set) == 1 else (
            tuple(sorted(pattern_set, key=repr)) if pattern_set else None)
        if effective_ink_identity(paints, patterns) != progress_key.ink_identity:
            return True
    return False


def _final_actual_representative(candidate, realized):
    """Keep the premeasured witness while updating only final occurrence facts."""
    return replace(candidate, occurrences=realized.occurrences,
                    variance_classes=realized.variance_classes)


def filtered_realized_entries(request, marks, shapes, relations, text):
    content, tokens, capabilities = request.surface_content, request.theme_tokens, request.paint_capabilities
    drawn_marks = tuple(mark for mark in marks if visible_placement(mark))
    actual = coalesce_actual_keys(tuple(key for mark in drawn_marks
        for key in actual_mark_keys(mark, content, tokens, capabilities)))
    by_ink = {key.grouping_identity: key for key in actual}
    reserved = {entry.realized_key.grouping_identity for entry in content.legend_entries
                if entry.realized_key is not None and entry.realized_key.family == "actual"}
    if reserved:
        assert by_ink.keys() <= reserved, "final Actual ink must have a premeasured candidate"
    progress_shapes = tuple(shape for shape in shapes
                            if shape.semantic_id == "progressFill" and visible_placement(shape))
    painted = painted_style_occurrences(drawn_marks, text, fills=content.style_fills, tokens=tokens)
    roles = {_scene_role(mark.semantic_id) for mark in drawn_marks}
    roles.update(_scene_role(shape.semantic_id) for shape in shapes
                 if shape.semantic_id and (visible_placement(shape) or shape.points))
    roles.update(_scene_role(item.semantic_id) for item in relations if not item.suppressed and item.points)
    roles.update(_scene_role(item.semantic_id) for item in text
                 if item.semantic_id and item.content.strip() and item.overflow != "suppressed" and visible_placement(item))
    result = []
    for entry in content.legend_entries:
        key = entry.realized_key
        if key is not None:
            if key.family == "actual":
                realized = by_ink.get(key.grouping_identity)
                if realized is None:
                    continue
                selected = replace(_final_actual_representative(key, realized), base_label=key.base_label)
                result.append(replace(entry, realized_key=selected,
                    label=actual_key_label(key.base_label, selected, multiple=len(actual) > 1,
                                           wording={**dict(content.legend_defaults), **dict(content.legend_wording)})))
            elif (progress_shapes and key.paint.effective_channels.opacity != 0
                  and _progress_adds_actual_ink(key, progress_shapes, drawn_marks,
                                                content, tokens, capabilities)):
                result.append(entry)
            continue
        if entry.style_scope is not None or entry.role.startswith("scale:"):
            if any(occurrence in painted for occurrence in entry.style_occurrences):
                result.append(entry)
            continue
        if entry.source_ref is not None:
            if any(shape.source_ref == entry.source_ref and visible_placement(shape) for shape in shapes):
                result.append(entry)
            continue
        candidates = tuple(mark for mark in drawn_marks if _base_mark(entry, mark))
        if candidates:
            if any(_same_base_ink(mark, content, tokens, capabilities) for mark in candidates):
                result.append(entry)
        elif (entry.role not in {"planned", "forecast", "milestone"}
              and _scene_role(entry.role) in roles):
            result.append(entry)
    return tuple(result)


def recompose_realized_legend(request, legend, marks, shapes, relations, text,
                              metric_values, metric_for, warnings):
    if legend is None:
        return None
    entries = filtered_realized_entries(request, marks, shapes, relations, text)
    completed = place_legend(SurfaceLegendContext(
        replace(request, surface_content=replace(request.surface_content, legend_entries=entries)),
        legend.allocated_slot, metric_values, metric_for))
    warnings.extend(completed.warnings)
    diagnostics, provenance = completed_legend_diagnostics(
        request, entries, completed.marks, completed.shapes, completed.relations, completed.text)
    return replace(completed, diagnostics=diagnostics, diagnostic_provenance=provenance)
