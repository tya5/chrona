"""Owns typed per-group header fit facts; reads resolved names and measured Theme text geometry."""
from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Any, Mapping

from chrona.presentation.layout.group_header_runs import GroupHeaderRunSegment, wrap_group_header_runs
from chrona.presentation.layout.model import LayoutError, geometry_sum
from chrona.presentation.layout.text import _wrap_units, measure_text_width, metric_for_role, wrap_text
from chrona.presentation.layout.vertical_text import vertical_label_required_block
from chrona.presentation.layout.window_row_admission import geometry_folded_points


class GroupHeaderInlineDemand(Exception):
    """Private measured table-width demand for a required horizontal full-name fallback."""

    def __init__(self, *, group_id: str, label: str, minimum_source_inline: Decimal,
                 available_source_inline: Decimal):
        self.group_id = group_id
        self.label = label
        self.minimum_source_inline = minimum_source_inline
        self.available_source_inline = available_source_inline
        super().__init__(f"group {group_id!r} needs table inline size {minimum_source_inline}px "
                         f"for its complete name; available {available_source_inline}px")


class GroupHeaderOwnerInlineDemand(Exception):
    """Private measured full-header floor for a bounded label owned by a shared outer container."""

    def __init__(self, *, group_id: str, label: str, owner_node_id: str,
                 minimum_owner_inline: Decimal, available_owner_inline: Decimal):
        if not owner_node_id:
            raise ValueError("group header inline owner must be a nonempty Layout node identity")
        self.group_id = group_id
        self.label = label
        self.owner_node_id = owner_node_id
        self.minimum_owner_inline = minimum_owner_inline
        self.available_owner_inline = available_owner_inline
        super().__init__(f"group {group_id!r} needs owner {owner_node_id!r} inline size "
                         f"{minimum_owner_inline}px; available {available_owner_inline}px")


@dataclass(frozen=True)
class HeaderTextRoom:
    """Measured inline text room after declared tab, insets, and band extent."""

    inline_start: Decimal
    inline_size: Decimal
    bounded: bool


def validate_group_header_room(*, header_inline_size: Decimal, label_inset: Decimal = Decimal(0),
                               label_inset_declared: bool = False, tab_reserved: Decimal = Decimal(0),
                               tab_position: str | None = None) -> None:
    """Reject an impossible authored tab/inset against the candidate header extent."""
    if tab_position is not None and tab_reserved >= header_inline_size:
        raise LayoutError("E_LAYOUT_GROUP_TAB_SIZE", "/body/roles/group-tab/tabInlineSize",
                          detail=f"group-tab:tabInlineSize:{tab_reserved}:{header_inline_size}")
    if not label_inset_declared or tab_position is None:
        return
    if tab_position == "start" and label_inset < tab_reserved:
        raise LayoutError("E_LAYOUT_GROUP_TAB_SIZE", "/body/roles/groupHeader/labelInset",
                          detail=f"actual offset={label_inset}; required reservation={tab_reserved}")
    if tab_position == "end" and label_inset + tab_reserved > header_inline_size:
        raise LayoutError("E_LAYOUT_GROUP_TAB_SIZE", "/body/roles/groupHeader/labelInset",
                          detail=(f"actual offset={label_inset}; required reservation={tab_reserved}; "
                                  f"available={header_inline_size}"))


def header_text_room(*, header_start: Decimal, header_end: Decimal,
                     label_inset: Decimal = Decimal(0), label_inset_end: Decimal = Decimal(0),
                     label_inset_declared: bool = False, tab_reserved: Decimal = Decimal(0),
                     tab_position: str | None = None, text_end_limit: Decimal | None = None
                     ) -> HeaderTextRoom:
    """Return the shared text span used by header preflight and final group composition."""
    validate_group_header_room(
        header_inline_size=header_end - header_start, label_inset=label_inset,
        label_inset_declared=label_inset_declared, tab_reserved=tab_reserved,
        tab_position=tab_position)
    start = header_start + label_inset
    end = header_end - label_inset_end
    if tab_position == "start" and not label_inset_declared:
        start += tab_reserved
    elif tab_position == "end":
        end -= tab_reserved
    if text_end_limit is not None:
        end = min(end, text_end_limit)
    return HeaderTextRoom(start, max(Decimal(0), end - start),
                          tab_position is not None or text_end_limit is not None)


def resolve_group_labels(*, projection: Any, row_admission: Any, review_rows: tuple[Any, ...],
                         declared_headers: tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...]:
    """Resolve the same admitted full group labels for measurement and completed placement."""
    labels = {row.group_id: next((item.group_label for item in row.items if item.group_label), row.group_id)
              for row in review_rows if row.group_id}
    for folded in geometry_folded_points(projection, row_admission):
        labels.setdefault(folded.group_id, next((item.group_label for item in folded.all_items if item.group_label),
                                                folded.group_id))
    declared = dict(declared_headers)
    if row_admission is not None and row_admission.omit_outside:
        row_admission.require_match(projection, row_admission.visibility_index)
        declared = {group_id: label for group_id, label in declared.items()
                    if group_id in row_admission.admitted_group_ids}
    labels.update(declared)
    return tuple(labels.items())


@dataclass(frozen=True)
class GroupHeaderFit:
    """One admitted group's full label and its preferred/fallback measured geometry."""

    group_id: str
    label: str
    vertical_required_block: float
    horizontal_lines: tuple[str, ...]
    horizontal_block_size: float
    minimum_horizontal_inline: Decimal
    horizontal_line_blocks: tuple[float, ...] = ()
    horizontal_fits: bool = True
    uses_vertical_tag: bool = True
    horizontal_run_lines: tuple[tuple[GroupHeaderRunSegment, ...], ...] | None = None
    horizontal_line_baseline_offsets: tuple[float, ...] = ()


@dataclass(frozen=True)
class GroupHeaderFitPlan:
    """Candidate-local per-group header choices, closed before rows and routes."""

    groups: tuple[GroupHeaderFit, ...]
    header_inline_start: float
    header_inline_size: float
    minimum_header_block_size: float
    source_inline_prefix: Decimal = Decimal(0)
    vertical_tag_plan: bool = True
    source_inline_demand: bool = True
    vertical_tag_block_inset: float = 0.0

    def group(self, group_id: str) -> GroupHeaderFit | None:
        return next((item for item in self.groups if item.group_id == group_id), None)

    def require_horizontal_room(self) -> None:
        """Raise the table-source minimum only when a bounded full name is required and its indivisible unit exceeds it."""
        if not self.source_inline_demand:
            return
        blocked = next((item for item in self.groups
                        if not item.uses_vertical_tag and not item.horizontal_fits), None)
        if blocked is not None:
            raise GroupHeaderInlineDemand(
                group_id=blocked.group_id, label=blocked.label,
                minimum_source_inline=self.source_inline_prefix + blocked.minimum_horizontal_inline,
                available_source_inline=self.source_inline_prefix + Decimal(str(self.header_inline_size)))

    def require_owner_horizontal_room(self, *, owner_node_id: str,
                                      available_owner_inline: Decimal) -> None:
        """Raise a full-container floor while preserving all current owner-to-text offsets."""
        blocked = next((item for item in self.groups
                        if not item.uses_vertical_tag and not item.horizontal_fits), None)
        if blocked is None:
            return
        deficit = max(Decimal(0), blocked.minimum_horizontal_inline - Decimal(str(self.header_inline_size)))
        if deficit:
            raise GroupHeaderOwnerInlineDemand(
                group_id=blocked.group_id, label=blocked.label, owner_node_id=owner_node_id,
                minimum_owner_inline=available_owner_inline + deficit,
                available_owner_inline=available_owner_inline)

    def demote(self, group_ids: frozenset[str]) -> GroupHeaderFitPlan:
        """Demote each listed preferred tag once; already-demoted names stay horizontal."""
        blocked = next((item for item in self.groups
                        if item.group_id in group_ids and item.uses_vertical_tag and not item.horizontal_fits), None)
        if blocked is not None:
            raise GroupHeaderInlineDemand(
                group_id=blocked.group_id, label=blocked.label,
                minimum_source_inline=self.source_inline_prefix + blocked.minimum_horizontal_inline,
                available_source_inline=self.source_inline_prefix + Decimal(str(self.header_inline_size)))
        return replace(self, groups=tuple(
            replace(item, uses_vertical_tag=False)
            if item.group_id in group_ids and item.uses_vertical_tag else item
            for item in self.groups))

    def vertical_tags_missing_full_fit(self, group_spans: Mapping[str, float]) -> frozenset[str]:
        """Return preferred tags whose actual inset cell cannot carry the full measured label."""
        return frozenset(
            item.group_id for item in self.groups
            if item.uses_vertical_tag
            and max(0.0, group_spans.get(item.group_id, 0.0) - self.vertical_tag_block_inset)
            < item.vertical_required_block)

    @property
    def header_sizes(self) -> tuple[tuple[str, float], ...]:
        return tuple((item.group_id, item.horizontal_block_size)
                     for item in self.groups if not item.uses_vertical_tag)


def prepare_group_header_fit_plan(*, labels: tuple[tuple[str, str], ...], theme_tokens: Any,
                                  font_metrics: Any, header_inline_start: float,
                                  header_inline_size: float, minimum_header_block_size: float,
                                  source_inline_prefix: Decimal = Decimal(0),
                                  vertical_tag_plan: bool = True,
                                  source_inline_demand: bool = True,
                                  vertical_tag_block_inset: float = 0.0,
                                  marked_runs: dict[str, tuple[tuple[str, str | None], ...]] | None = None,
                                  ) -> GroupHeaderFitPlan:
    """Measure every full name once for vertical preference and wrapped horizontal fallback."""
    treatment = theme_tokens.text_treatment("groupHeader")
    metric = metric_for_role(theme_tokens, "groupHeader", font_metrics)
    size, spacing = float(treatment.font_size), float(treatment.letter_spacing)
    line_block = size * float(treatment.line_height)
    groups: list[GroupHeaderFit] = []
    for group_id, label in labels:
        run_lines = None
        line_baseline_offsets: tuple[float, ...] = ()
        if marked_runs is not None and group_id in marked_runs:
            run_lines = wrap_group_header_runs(runs=marked_runs[group_id], available_inline=header_inline_size,
                                               theme_tokens=theme_tokens, font_metrics=font_metrics)
            lines = tuple("".join(segment.text for segment in line) for line in run_lines)
            widest = max((geometry_sum(segment.gap + segment.width for segment in line)
                          for line in run_lines), default=0.0)
            minimum_unit = max((segment.width for line in run_lines for segment in line), default=0.0)
            # Text ink bounds begin at baseline - font_size and extend by
            # block_size. Close each mixed-role line around those actual
            # extents once, before placement, and retain the shared baseline
            # offsets as measured plan facts.
            line_baseline_offsets = tuple(
                max((segment.font_size for segment in line), default=0.0)
                for line in run_lines)
            line_blocks = tuple(
                baseline + max((segment.block_size - segment.font_size for segment in line), default=0.0)
                for baseline, line in zip(line_baseline_offsets, run_lines, strict=True))
            horizontal_block_size = (minimum_header_block_size if len(run_lines) <= 1 else
                                     max(minimum_header_block_size, geometry_sum(line_blocks)))
            horizontal_fits = header_inline_size > 0 and all(
                segment.width <= header_inline_size for line in run_lines for segment in line)
        else:
            lines = ((label,) if header_inline_size <= 0 else
                     wrap_text(label, available_inline=header_inline_size, font_size=size,
                               font_metrics=metric, letter_spacing=spacing,
                               text_transform=treatment.transform,
                               numeric_spacing=treatment.numeric_spacing))
            measured_lines = tuple(measure_text_width(
                line, font_size=size, font_metrics=metric, letter_spacing=spacing,
                text_transform=treatment.transform, numeric_spacing=treatment.numeric_spacing)
                for line in lines)
            widest = max(measured_lines, default=0.0)
            units = _wrap_units(label)
            minimum_unit = max((measure_text_width(
                unit, font_size=size, font_metrics=metric, letter_spacing=spacing,
                text_transform=treatment.transform, numeric_spacing=treatment.numeric_spacing)
                for unit in units), default=0.0)
            line_blocks = tuple(line_block for _ in lines)
            horizontal_block_size = (minimum_header_block_size if len(lines) <= 1 else
                                     max(minimum_header_block_size, line_block * len(lines)))
            horizontal_fits = header_inline_size > 0 and widest <= header_inline_size
        groups.append(GroupHeaderFit(
            group_id, label,
                vertical_label_required_block(label=label, typography_role="groupHeader",
                                          theme_tokens=theme_tokens, font_metrics=font_metrics),
            lines, horizontal_block_size,
            Decimal(str(minimum_unit)), line_blocks, horizontal_fits, vertical_tag_plan, run_lines,
            line_baseline_offsets))
    return GroupHeaderFitPlan(tuple(groups), header_inline_start, header_inline_size,
                              minimum_header_block_size, source_inline_prefix,
                              vertical_tag_plan, source_inline_demand, vertical_tag_block_inset)
