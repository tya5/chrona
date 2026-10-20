"""Measured presentation geometry handed from Layout to Scene."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import math
from typing import TYPE_CHECKING, Any, Callable, Literal, Mapping, Sequence

from chrona.presentation.layout.model import LayoutError, geometry_sum
from chrona.presentation.layout.text import measure_text_width, metric_for_role
from chrona.presentation.layout.tracks import resolve_flexible_tracks
from chrona.presentation.model.projection import ObservationState, shared_track_member_key
from chrona.presentation.model.actual_observation import in_progress_actual
from chrona.presentation.model.surface_content import TableCellContent, TableColumnContent

if TYPE_CHECKING:
    from chrona.presentation.layout.mark_band_allocation import MarkBandAllocation


@dataclass(frozen=True)
class TableColumnPlacement:
    column_id: str
    inline: float
    inline_size: float
    natural_inline_size: float


@dataclass(frozen=True)
class RowPlacement:
    row_id: str
    group_id: str | None
    bounds: tuple[float, float, float, float]


@dataclass(frozen=True)
class TrackPlacement:
    instance_id: str
    block: float
    actual_block: float
    block_size: float


@dataclass(frozen=True)
class MarkGeometry:
    """One role's lane-slot-relative geometry, resolved before Scene."""

    height: float
    offset: float
    paint_order: int
    corner_radius: float
    # Optional size and offset of a point mark's symbol (#1066), ratios of the track like `height` and `offset`;
    # None takes the bar band's value, so a role without the Theme properties is unchanged.
    symbol_height: float | None = None
    symbol_offset: float | None = None
    physical_corner_radius: float | Literal["capsule"] | None = None

    def __post_init__(self) -> None:
        if self.height <= 0 or self.offset < 0 or self.offset + self.height > 1 or not 0 <= self.corner_radius <= 0.5:
            raise LayoutError("E_LAYOUT_MARK_OVERFLOW", "/theme/markGeometry",
                              detail=f"height={self.height}; offset={self.offset}")
        if self.symbol_extent[1] <= 0 or self.symbol_extent[0] < 0 or self.symbol_extent[0] + self.symbol_extent[1] > 1:
            raise LayoutError("E_LAYOUT_MARK_OVERFLOW", "/theme/symbolGeometry",
                              detail=f"symbolHeight={self.symbol_extent[1]}; symbolOffset={self.symbol_extent[0]}")

    @property
    def symbol_extent(self) -> tuple[float, float]:
        """The symbol's (offset, height) ratios: the declared ones, else the bar band's."""
        return (self.offset if self.symbol_offset is None else self.symbol_offset,
                self.height if self.symbol_height is None else self.symbol_height)


@dataclass(frozen=True)
class MarkBandFrame:
    """One completed mark band in a caller-owned block coordinate frame.

    ``inline_scale`` is retained with the frame so every mark projection uses
    the same temporal scale as its track allocation.  Automatic and explicit
    rows use ``from_track``; lane projections use ``zero_origin`` and translate
    the completed result only after composition.
    """

    inline_scale: Any
    block_origin: float
    block_size: float
    role_geometries: Mapping[str, MarkGeometry]
    allocation: MarkBandAllocation | None = None

    def __post_init__(self) -> None:
        if (not math.isfinite(self.block_origin) or not math.isfinite(self.block_size)
                or self.block_size <= 0):
            raise LayoutError("E_LAYOUT_MARK_OVERFLOW", "/layout/markBandFrame")
        if self.allocation is not None and self.allocation.track_size != self.block_size:
            raise LayoutError("E_LAYOUT_MARK_OVERFLOW", "/layout/markBandFrame/allocation",
                              detail="allocation track size must equal the frame's resolved track size")

    @classmethod
    def from_track(cls, track: TrackPlacement, inline_scale: Any,
                   role_geometries: Mapping[str, MarkGeometry],
                   allocation: MarkBandAllocation | None = None) -> "MarkBandFrame":
        return cls(inline_scale, track.block, track.block_size, role_geometries, allocation)

    @classmethod
    def zero_origin(cls, inline_scale: Any, block_size: float,
                    role_geometries: Mapping[str, MarkGeometry],
                    allocation: MarkBandAllocation | None = None) -> "MarkBandFrame":
        return cls(inline_scale, 0.0, block_size, role_geometries, allocation)

    def symbol_bounds(self, role: str) -> tuple[float, float]:
        """Return a point mark's symbol block start and side (#1066); the bar band's when the role declares none."""
        if self.allocation is not None:
            block, size = self.allocation.symbol_bounds(role)
            return self.block_origin + block, size
        offset, height = self.role_geometries[role].symbol_extent
        return self.block_origin + self.block_size * offset, self.block_size * height

    def role_bounds(self, role: str) -> tuple[float, float]:
        """Return the role's block start and extent without changing formula order."""
        if self.allocation is not None:
            block, size = self.allocation.span_bounds(role)
            return self.block_origin + block, size
        geometry = self.role_geometries[role]
        return (self.block_origin + self.block_size * geometry.offset,
                self.block_size * geometry.height)


def mark_bounds(track: TrackPlacement, geometry: MarkGeometry) -> tuple[float, float]:
    """Return one completed block coordinate and extent within an assigned slot."""
    return track.block + track.block_size * geometry.offset, track.block_size * geometry.height


def table_cell_indent(*, grouped: bool, depth: int, inset: float, indent: float | None) -> float:
    """Return the hierarchy-column indent that a table row's cell occupies."""
    if depth and indent is None:
        raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources/metricValues/table.indent.inlineSize")
    return (inset if grouped else 0.0) + float(indent or 0) * depth


def header_group_cell_indent(*, grouped: bool, indent: float | None, lead: float | None) -> float:
    """Return the hierarchy-column indent of a row under field-grouping headers (#1065).

    A grouped row is one declared step below its header's label: `lead` is the distance of that label from the
    column start (a start group tab and its gap), then exactly `indent`. `lead` is None when no header row is
    drawn (a vertical group tag), and a row outside any group is not below a header: both take no indent.
    """
    if not grouped or lead is None:
        return 0.0
    if indent is None:
        raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources/metricValues/table.indent.inlineSize")
    return lead + float(indent)


def table_text_measurer(theme_tokens: Any, font_metrics: Any) -> Callable[[str, str, str], float]:
    """Measure table header and cell text in its own typography role."""
    def measure(content: str, typography_role: str, orientation: str = "horizontal") -> float:
        treatment = theme_tokens.text_treatment(typography_role)
        if orientation != "horizontal":
            return float(treatment.font_size * treatment.line_height)
        return measure_text_width(content, font_size=float(treatment.font_size),
                                  font_metrics=metric_for_role(theme_tokens, typography_role, font_metrics),
                                  letter_spacing=float(treatment.letter_spacing),
                                  text_transform=treatment.transform,
                                  numeric_spacing=treatment.numeric_spacing)
    return measure


def table_text_required_inline(text_advance: float, *, indent: float = 0.0,
                               inset: float = 0.0) -> float:
    """Compose the forward inline demand used by both table measurement and fit admission."""
    return geometry_sum((text_advance, indent, inset))


def table_text_fits_column(text_advance: float, column_inline_size: float, *,
                           indent: float = 0.0, inset: float = 0.0) -> bool:
    """Test a table text run against its column without inverse-subtraction rounding."""
    return table_text_required_inline(text_advance, indent=indent, inset=inset) <= column_inline_size


def measure_table_columns(*, columns: tuple[TableColumnContent, ...],
                          cells: tuple[TableCellContent, ...],
                          measure_text: Callable[[str, str, str], float], minimum_inline: float,
                          hierarchy_column: str | None = None,
                          cell_indents: Mapping[str, float] | None = None,
                          header_role: str = "text") -> tuple[float, ...]:
    """Return each column's natural width; the one measure for slot and columns.

    A hierarchy-column cell's extent includes its row's indent, because that
    indent is consumed from the same column allocation at placement.
    """
    indents = cell_indents or {}
    content_by_column: dict[str, list[tuple[str, str, str, float]]] = {
        column.column_id: [(column.header, header_role, column.header_orientation, 0.0)] for column in columns}
    for cell in cells:
        indent = indents.get(cell.object_id, 0.0) if cell.column_id == hierarchy_column else 0.0
        content_by_column.setdefault(cell.column_id, []).append((cell.content, cell.typography_role, "horizontal", indent))
    return tuple(
        max(minimum_inline, max((table_text_required_inline(
            measure_text(item, role, orientation), indent=indent, inset=minimum_inline)
            for item, role, orientation, indent in content_by_column[column.column_id]),
                                default=minimum_inline))
        for column in columns
    )


def table_content_inline_size(natural_widths: tuple[float, ...], gutter: float) -> float:
    """Return the inline extent of measured columns and the gutters between them."""
    return geometry_sum(natural_widths) + gutter * max(0, len(natural_widths) - 1)


def measure_table_column_minima(*, columns: tuple[TableColumnContent, ...],
                                cells: tuple[TableCellContent, ...],
                                measure_text: Callable[[str, str, str], float], minimum_inline: float,
                                hierarchy_column: str | None = None,
                                cell_indents: Mapping[str, float] | None = None,
                                header_role: str = "text") -> tuple[float, ...]:
    """Measure each bounded column's own inset, hierarchy and affix/text floor.

    A fitting short value may be narrower than an ellipsis. Otherwise the
    complete affixes and permitted ellipsis must fit in the cell's own role.
    Rotated/vertical headers occupy their native inline line-box thickness,
    not their horizontal text advance. Source closure retains the full text.
    """
    indents = cell_indents or {}

    def compact(content: str, role: str, orientation: str,
                prefix: str = "", suffix: str = "") -> float:
        natural = measure_text(content, role, orientation)
        if not content or orientation != "horizontal":
            return natural
        return min(natural, measure_text(prefix + "…" + suffix, role, "horizontal"))

    content_by_column = {column.column_id: [(compact(column.header, header_role, column.header_orientation), 0.0)]
                         for column in columns}
    for cell in cells:
        indent = indents.get(cell.object_id, 0.0) if cell.column_id == hierarchy_column else 0.0
        content_by_column.setdefault(cell.column_id, []).append(
            (compact(cell.content, cell.typography_role, "horizontal", cell.affix_prefix, cell.affix_suffix), indent))
    return tuple(max(minimum_inline, max((table_text_required_inline(width, indent=indent, inset=minimum_inline)
                                          for width, indent in content_by_column[column.column_id]),
                                         default=0.0))
                 for column in columns)


def _bounded_column_widths(columns: tuple[TableColumnContent, ...], natural: tuple[float, ...],
                            minima: tuple[float, ...], available: float) -> tuple[float, ...]:
    """Apply Spec 24's shortage rule through the shared bounded-track solver."""
    if (len(minima) != len(columns) or not math.isfinite(available)
            or any(not math.isfinite(low) or low < 0 or low > high
                   for low, high in zip(minima, natural))):
        raise LayoutError("E_LAYOUT_TABLE_OVERFLOW", "/layoutManifest/table",
                          detail="invalid mandatory column measurements")
    floor = tuple(Decimal(str(value)) for value in minima)
    budget = Decimal(str(available))
    if sum(floor, Decimal(0)) > budget:
        raise LayoutError("E_LAYOUT_TABLE_OVERFLOW", "/layoutManifest/table",
                          detail="mandatory columns and gutters exceed the table slot")
    fixed = [index for index, column in enumerate(columns) if not column.width.flexible]
    flexible = [index for index, column in enumerate(columns) if column.width.flexible]
    fixed_budget = budget - sum((floor[index] for index in flexible), Decimal(0))
    fixed_widths = resolve_flexible_tracks(
        [(floor[index], Decimal(str(natural[index])), Decimal(1)) for index in fixed], fixed_budget)
    remaining = budget - sum(fixed_widths, Decimal(0))
    weights = [1.0 if columns[index].width.maximum == "fill" else columns[index].width.fraction
               for index in flexible]
    if any(not math.isfinite(weight) or weight <= 0 for weight in weights):
        raise LayoutError("E_LAYOUT_TABLE_OVERFLOW", "/layoutManifest/table",
                          detail="invalid flexible column weight")
    flexible_widths = resolve_flexible_tracks(
        [(floor[index], None, Decimal(str(weight))) for index, weight in zip(flexible, weights)], remaining)
    by_index = dict(zip(fixed, fixed_widths)) | dict(zip(flexible, flexible_widths))
    return tuple(float(by_index[index]) for index in range(len(columns)))


def place_table_columns(*, columns: tuple[TableColumnContent, ...],
                        cells: tuple[TableCellContent, ...],
                        bounds: tuple[float, float, float, float],
                        measure_text: Callable[[str, str, str], float], minimum_inline: float,
                        overflow: str = "visible-overflow", gutter: float = 0.0,
                        hierarchy_column: str | None = None,
                        cell_indents: Mapping[str, float] | None = None,
                        header_role: str = "text",
                        mandatory_inline: tuple[float, ...] | None = None,
                        ) -> tuple[TableColumnPlacement, ...]:
    """Allocate only declared-flexible columns after measured minima close."""
    natural_widths = measure_table_columns(columns=columns, cells=cells, measure_text=measure_text,
                                           minimum_inline=minimum_inline, hierarchy_column=hierarchy_column,
                                           cell_indents=cell_indents, header_role=header_role)
    if gutter < 0:
        raise LayoutError("E_LAYOUT_TABLE_OVERFLOW", "/layoutManifest/table")
    available = bounds[2] - gutter * max(0, len(natural_widths) - 1)
    if sum(column.width.maximum == "fill" for column in columns) > 1:
        raise LayoutError("E_LAYOUT_TABLE_OVERFLOW", "/layoutManifest/table")
    # A normal visible-overflow table retains natural measured columns even
    # when they exceed its requested slot.  Ellipsis remains the sole compact
    # disposition and therefore still needs finite minima inside the slot.
    preferred_total = geometry_sum(natural_widths)
    if mandatory_inline is not None and preferred_total > available:
        widths = _bounded_column_widths(columns, natural_widths, mandatory_inline, available)
    else:
        ellipsis_floor = max(minimum_inline, measure_text("…", "text", "horizontal")) + minimum_inline
        minima = tuple(natural if column.width.minimum == "content" else ellipsis_floor
                       for column, natural in zip(columns, natural_widths, strict=True))
        base = (minima if preferred_total > available and overflow == "ellipsize-with-source"
                else natural_widths)
        flexible = tuple(index for index, column in enumerate(columns) if column.width.flexible)
        # Preserve the ordinary source-preserving compact disposition, including
        # visible mandatory overflow, when no strict bounded minima were supplied.
        remaining = max(0.0, available - geometry_sum(base))
        weights = geometry_sum(columns[index].width.fraction for index in flexible)
        widths = tuple(width + (remaining * columns[index].width.fraction / weights
                                if index in flexible and weights else 0.0)
                       for index, width in enumerate(base))
    positions = column_inline_positions(bounds[0], widths, gutter)
    return tuple(TableColumnPlacement(column.column_id, position, width, natural)
                 for column, natural, width, position in zip(columns, natural_widths, widths, positions,
                                                              strict=True))


def column_inline_positions(origin: float, widths: Sequence[float], gutter: float) -> tuple[float, ...]:
    """Return each column's inline start as one correctly rounded sum from the table origin (#1542).

    Every placement path derives x from the same origin and widths with this single accumulation, so
    wrapped, unwrapped and source-closed tables agree to the last float digit.
    """
    terms: list[float] = [origin]
    positions: list[float] = []
    for width in widths:
        positions.append(geometry_sum(terms))
        terms.extend((width, gutter))
    return tuple(positions)


def validate_table_text_roles(columns: Any, theme_tokens: Any) -> None:
    """Fail a View column whose `textRole` names a role the Theme does not declare (#1062).

    The pointer is the View property the author must change; the missing Theme role is in the detail.
    """
    for index, column in enumerate(columns):
        role = getattr(column, "text_role", None)
        if role is not None and not theme_tokens.has_role(role):
            raise LayoutError("E_THEME_ROLE_REQUIRED", f"/body/tableColumns/{index}/textRole",
                              detail=f"the Theme declares no text role {role!r} (/body/roles/{role})")


def validate_lane_table_text_roles(lane_table: Any, theme_tokens: Any) -> None:
    """Fail a lane-table column whose `textRole` names a role the Theme does not declare (#1545)."""
    for index, column in enumerate(getattr(lane_table, "columns", ()) if lane_table is not None else ()):
        role = column.text_role
        if role is not None and not theme_tokens.has_role(role):
            raise LayoutError("E_THEME_ROLE_REQUIRED", f"/body/rows/laneTable/columns/{index}/textRole",
                              detail=f"the Theme declares no text role {role!r} (/body/roles/{role})")


def validate_label_text_role(labels: Any, theme_tokens: Any) -> None:
    """Fail a View whose `visibility.labels.textRole` names a role the Theme does not declare (#1141)."""
    role = labels.get("textRole") if isinstance(labels, Mapping) else None
    if role is not None and not theme_tokens.has_role(role):
        raise LayoutError("E_THEME_ROLE_REQUIRED", "/body/visibility/labels/textRole",
                          detail=f"the Theme declares no text role {role!r} (/body/roles/{role})")


def table_text_line_block(theme_tokens: Any, typography_roles: Any) -> float:
    """Return the tallest line block among the table cell roles a row holds."""
    return max((float(theme_tokens.text_treatment(role).font_size * theme_tokens.text_treatment(role).line_height)
                for role in sorted(set(typography_roles))), default=0.0)


def _occurrence_frame_key(review_row: Any, item: Any) -> str:
    """Use the planner's existing instance identity without interpreting its contents."""
    return f"{review_row.row_id}:{item.item_id or item.object_id}"


def _occurrence_outer_extent(frame: MarkBandFrame) -> float:
    return frame.allocation.outer_extent if frame.allocation is not None else frame.block_size


def _row_track_pitch(review_row: Any, mark_block_size: float,
                     mark_band_allocation: MarkBandAllocation | None,
                     occurrence_frames: Mapping[str, MarkBandFrame] | None) -> float:
    pitch = mark_band_allocation.outer_extent if mark_band_allocation is not None else mark_block_size
    if occurrence_frames:
        pitch = max((pitch, *(
            _occurrence_outer_extent(frame)
            for item in review_row.items
            if (frame := occurrence_frames.get(_occurrence_frame_key(review_row, item))) is not None
        )))
    # A key-row lane is at least as tall as the labels it holds (#1681).
    return max([pitch] + [value for value in (getattr(item, "key_pitch", None) for item in review_row.items)
                          if value is not None])


def required_row_block_extents(*, review_rows: tuple[Any, ...], row_minimum: float,
                               row_padding: float, mark_block_size: float,
                               role_geometries: Mapping[str, MarkGeometry] | None = None,
                               mark_band_allocation: MarkBandAllocation | None = None,
                               text_line_block: float = 0.0,
                               row_text_blocks: Mapping[str, Decimal] | None = None,
                               occurrence_frames: Mapping[str, MarkBandFrame] | None = None,
                               as_of: date | None = None) -> tuple[float, ...]:
    """Close each row's minimum before any surplus distribution occurs.

    ``row_padding`` is the row's total block padding.  It is added once to the
    mark tracks and once to the table text line the row holds (Specification
    24 section 2.1).
    """
    if row_minimum <= 0 or row_padding < 0 or text_line_block < 0:
        raise LayoutError("E_LAYOUT_ROW_REQUIREMENT", "/measuredSources/metricValues/timeline.row")
    def text_requirement(row: Any) -> float:
        block = text_line_block
        if row_text_blocks is not None:
            block = max(block, float(row_text_blocks.get(row.row_id, 0)),
                        float(row_text_blocks.get(row.table_subject_id, 0)))
        return block + row_padding if block else 0.0

    return tuple(max(row_minimum, text_requirement(row), minimum_track_block_extent(
        review_row=row, mark_block_size=mark_block_size, role_geometries=role_geometries,
        mark_band_allocation=mark_band_allocation, occurrence_frames=occurrence_frames, as_of=as_of,
    ) + row_padding) for row in review_rows)


def _group_starts(review_rows: tuple[Any, ...]) -> tuple[int, ...]:
    return tuple(
        index for index, row in enumerate(review_rows)
        if row.group_id and (index == 0 or review_rows[index - 1].group_id != row.group_id)
    )


def empty_group_slots(review_rows: tuple[Any, ...], group_order: tuple[str, ...]) -> tuple[tuple[int, str], ...]:
    """Group containers that hold no ordinary row, as (index of the row they precede, group id).

    View resolved the order; a group whose points were all folded into its header keeps its place there
    (an index equal to ``len(review_rows)`` means after the last row).
    """
    first_row = {}
    for index, row in enumerate(review_rows):
        if row.group_id:
            first_row.setdefault(row.group_id, index)
    slots: list[tuple[int, str]] = []
    pending: list[str] = []
    for group_id in group_order:
        if group_id in first_row:
            slots.extend((first_row[group_id], waiting) for waiting in pending)
            pending = []
        else:
            pending.append(group_id)
    slots.extend((len(review_rows), waiting) for waiting in pending)
    return tuple(slots)


def empty_group_header_blocks(*, slots: tuple[tuple[int, str], ...], row_placements: tuple[RowPlacement, ...],
                              timeline_bounds: tuple[float, float, float, float], group_header_size: float
                              ) -> tuple[tuple[int, str, float], ...]:
    """Block origin of every row-less group header: just above the group that follows it, else after the last row."""
    result = []
    for position, (index, group_id) in enumerate(slots):
        ordinal = len([other for other, _ in slots[:position] if other == index])
        count = len([other for other, _ in slots if other == index])
        if index < len(row_placements):
            block = row_placements[index].bounds[1] - group_header_size * (count - ordinal + 1)
        else:
            end = (row_placements[-1].bounds[1] + row_placements[-1].bounds[3]) if row_placements else timeline_bounds[1]
            block = end + group_header_size * ordinal
        result.append((index, group_id, block))
    return tuple(result)


def row_block_slack(*, review_rows: tuple[Any, ...], timeline_block_size: float, group_header_size: float,
                    required_block_sizes: tuple[float, ...], empty_groups: int = 0) -> float:
    """The timeline block left once every row requirement and group header is closed (negative: rows overflow)."""
    return (timeline_block_size - group_header_size * (len(_group_starts(review_rows)) + empty_groups)
            - geometry_sum(required_block_sizes))


def place_rows(*, review_rows: tuple[Any, ...], timeline_bounds: tuple[float, float, float, float],
               group_header_size: float, required_block_sizes: tuple[float, ...],
               distribution: str, empty_groups: tuple[tuple[int, str], ...] = ()) -> tuple[RowPlacement, ...]:
    """Allocate completed row requirements and only then distribute surplus."""
    if len(required_block_sizes) != len(review_rows) or any(size <= 0 for size in required_block_sizes):
        raise LayoutError("E_LAYOUT_ROW_REQUIREMENT", "/layoutManifest/timeline")
    if distribution not in {"pack", "fill"}:
        raise LayoutError("E_LAYOUT_ROW_DISTRIBUTION", "/layoutManifest/reviewSurface/rowDistribution")
    group_starts = _group_starts(review_rows)
    available = timeline_bounds[3] - group_header_size * (len(group_starts) + len(empty_groups))
    required = geometry_sum(required_block_sizes)
    # Requirements remain P1 geometry.  A requested timeline is a minimum
    # allocation, not a refusal boundary: surplus can be distributed only when
    # it exists, otherwise rows naturally extend the completed surface.
    surplus = ((available - required) / len(review_rows)
               if distribution == "fill" and review_rows and available >= required else 0.0)
    cursor = timeline_bounds[1]
    placements: list[RowPlacement] = []
    for index, row in enumerate(review_rows):
        cursor += group_header_size * len([other for other, _ in empty_groups if other == index])
        if index in group_starts:
            cursor += group_header_size
        height = required_block_sizes[index] + surplus
        placements.append(RowPlacement(row.row_id, row.group_id,
                                       (timeline_bounds[0], cursor, timeline_bounds[2], height)))
        cursor += height
    return tuple(placements)


def place_mark_tracks(*, review_rows: tuple[Any, ...], row_placements: tuple[RowPlacement, ...],
                      mark_block_size: float, role_geometries: Mapping[str, MarkGeometry] | None = None,
                      mark_band_allocation: MarkBandAllocation | None = None,
                      occurrence_frames: Mapping[str, MarkBandFrame] | None = None,
                      as_of: date | None = None) -> tuple[TrackPlacement, ...]:
    """Allocate member tracks whose completed marks are contained by their row."""
    geometries = role_geometries or {
        "planned": MarkGeometry(1.0, 0.0, 0, 0.0),
        "actual": MarkGeometry(1.0, 0.0, 1, 0.0),
        "missing-actual": MarkGeometry(1.0, 0.0, 1, 0.0),
        "snapshot": MarkGeometry(1.0, 0.0, 0, 0.0),
        "scenario": MarkGeometry(1.0, 0.0, 0, 0.0),
    }

    def require_contained(row: RowPlacement, block: float, block_size: float, *, instance_id: str, role: str) -> None:
        row_start, row_size = row.bounds[1], row.bounds[3]
        if (mark_block_size <= 0 or block < row_start or block + block_size > row_start + row_size):
            raise LayoutError("E_LAYOUT_MARK_OVERFLOW", "/theme/roles/" + role, instance_id,
                              detail=f"role={role}; block={block}; extent={block_size}")

    def has_actual(item: Any) -> bool:
        actual = getattr(item, "actual", None) or {}
        opened = in_progress_actual(actual, as_of)
        return bool((actual.get("start") is not None and actual.get("finish") is not None)
                    or (opened is not None and opened.drawable)
                    or actual.get("at") is not None)

    placements: list[TrackPlacement] = []
    for review_row, row in zip(review_rows, row_placements, strict=True):
        pitch = _row_track_pitch(review_row, mark_block_size, mark_band_allocation, occurrence_frames)
        key_lanes = [lane for lane in (getattr(item, "key_lane", None) for item in review_row.items) if lane is not None]
        stacked_total = (max(key_lanes) + 1 if key_lanes else
                         max(1, sum(item.track != "shared" for item in review_row.items)))
        if row.bounds[3] < stacked_total * pitch:
            raise LayoutError("E_LAYOUT_MARK_OVERFLOW", "/measuredSources/metricValues/timeline.mark.blockSize",
                              detail=f"lanes={stacked_total}; extent={stacked_total * pitch}")
        lane_origin = row.bounds[1] + (row.bounds[3] - stacked_total * pitch) / 2
        stacked_index = 0
        members = sorted(
            enumerate(review_row.items),
            key=lambda pair: shared_track_member_key(pair[1], pair[0]),
        )
        for _, item in members:
            instance_id = _occurrence_frame_key(review_row, item)
            occurrence_frame = occurrence_frames.get(instance_id) if occurrence_frames else None
            item_geometries = occurrence_frame.role_geometries if occurrence_frame is not None else geometries
            item_allocation = (occurrence_frame.allocation if occurrence_frame is not None
                               else mark_band_allocation)
            track_inset = -item_allocation.outer_bounds[0] if item_allocation is not None else 0.0
            key_lane = getattr(item, "key_lane", None)
            if key_lane is not None:
                # A key-row point sits in the lane Layout packed it into (#1501); comparison variants share it.
                block = lane_origin + key_lane * pitch + track_inset
                actual_block = block
            elif item.track == "shared":
                block = lane_origin + track_inset
                actual_block = block
            else:
                # A lane has a fixed base mark extent.  Role geometry is
                # relative to this lane slot, never to the spare row space:
                # rows may be taller for labels, group treatment, or viewport
                # allocation without silently stretching marks.
                block = lane_origin + stacked_index * pitch + track_inset
                actual_block = block
                stacked_index += 1
            source_kind = getattr(item, "source_kind", "primary")
            roles = (("actual",) if has_actual(item) else ()) if source_kind == "actual" else (
                "snapshot" if source_kind in {"snapshot", "scenario"} else "planned",)
            if source_kind == "combined" and has_actual(item):
                roles += ("actual",)
            elif source_kind in {"primary", "combined"} and item.observation_state == ObservationState.DUE_UNOBSERVED:
                roles += ("missing-actual",)
            slot_size = mark_block_size
            for role in roles:
                geometry = item_geometries[role]
                local_block, local_size = (item_allocation.span_bounds(role) if item_allocation is not None
                                          else (slot_size * geometry.offset, slot_size * geometry.height))
                require_contained(row, block + local_block, local_size, instance_id=instance_id, role=role)
            placements.append(TrackPlacement(instance_id, block, actual_block, slot_size))
    return tuple(placements)


def minimum_track_block_extent(*, review_row: Any, mark_block_size: float,
                               role_geometries: Mapping[str, MarkGeometry] | None = None,
                               mark_band_allocation: MarkBandAllocation | None = None,
                               occurrence_frames: Mapping[str, MarkBandFrame] | None = None,
                               as_of: date | None = None) -> float:
    """Find the smallest integral row block accepted by the track planner.

    This deliberately invokes ``place_mark_tracks`` rather than re-encoding
    planned/actual, milestone, shared, or stacked containment arithmetic.
    """
    def fits(block_size: float) -> bool:
        try:
            place_mark_tracks(review_rows=(review_row,), row_placements=(
                RowPlacement(str(review_row.row_id), getattr(review_row, "group_id", None),
                             (0.0, 0.0, 1.0, block_size)),
            ), mark_block_size=mark_block_size, role_geometries=role_geometries,
                mark_band_allocation=mark_band_allocation, occurrence_frames=occurrence_frames, as_of=as_of)
        except LayoutError as error:
            if error.diagnostic_id != "E_LAYOUT_MARK_OVERFLOW":
                raise
            return False
        return True

    if mark_block_size <= 0:
        raise LayoutError("E_LAYOUT_MARK_OVERFLOW", "/measuredSources/metricValues/timeline.mark.blockSize")
    upper = float(mark_block_size)
    while not fits(upper):
        upper *= 2
    lower = 0.0
    for _ in range(48):
        middle = (lower + upper) / 2
        if fits(middle):
            upper = middle
        else:
            lower = middle
    # Render viewport dimensions are integral; round upward so the final
    # placement never loses a fractional containment boundary.
    return float(int(upper) if upper.is_integer() else int(upper) + 1)
