"""Typed access to the current resolved Theme v0.2 boundary."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
import math
from typing import Any, Mapping

from chrona.presentation.annotation_kind_text import AnnotationKindTextError, KindHeader, kind_header
from chrona.presentation.model.semantic_registry import is_annotation_artwork_role, is_label_chip_role


class ThemeTokenError(ValueError):
    """Stable diagnostic for a missing or mistyped resolved Theme token."""

    def __init__(self, diagnostic_id: str, path: str, detail: str | None = None):
        super().__init__(diagnostic_id)
        self.diagnostic_id = diagnostic_id
        self.path = path
        self.detail = detail


def _operand(value: Any) -> str:
    """Describe an invalid Theme operand by type without echoing authored content."""
    if value is None:
        return "NoneType"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, Mapping):
        return "mapping"
    if isinstance(value, (list, tuple)):
        return f"{type(value).__name__}(length={len(value)})"
    return type(value).__name__


def _shown(value: Any) -> str:
    """Bound a scalar Theme operand without dumping resource content."""
    if isinstance(value, int) and not isinstance(value, bool) and value.bit_length() > 320:
        return f"<int bits={value.bit_length()}>"
    if value is None or isinstance(value, (str, int, float, bool)):
        text = repr(value)
        return text if len(text) <= 96 else text[:93] + "..."
    return _operand(value)


# A role's declared horizontal compression (#585): the painted run is scaled along its own inline axis. The floor keeps
# a compressed face recognisably the same face; the ceiling makes it compression only (no extension).
HORIZONTAL_SCALE_FLOOR = Decimal("0.5")
HORIZONTAL_SCALE_CEILING = Decimal("1")


def checked_horizontal_scale(value: Decimal, pointer: str) -> Decimal:
    """Return a declared horizontal scale, or raise the typed range diagnostic at its Theme pointer."""
    if not value.is_finite() or value < HORIZONTAL_SCALE_FLOOR or value > HORIZONTAL_SCALE_CEILING:
        raise ThemeTokenError("E_THEME_TEXT_SCALE_RANGE", pointer)
    return value


@dataclass(frozen=True)
class TextTreatment:
    """Finite text values resolved before Layout measures a painted run."""

    family: str
    weight: int
    font_size: Decimal
    line_height: Decimal
    letter_spacing_em: Decimal
    transform: str
    numeric_spacing: str
    horizontal_scale: Decimal = Decimal(1)

    def paint_content(self, content: str) -> str:
        return {
            "none": content,
            "uppercase": content.upper(),
            "lowercase": content.lower(),
            "capitalize": content.title(),
        }[self.transform]

    @property
    def letter_spacing(self) -> Decimal:
        return self.font_size * self.letter_spacing_em


@dataclass(frozen=True)
class ArtworkToken:
    """One normalized vector artwork layer behind a rectangle annotation container.

    ``glyph`` is a catalogue ``set:name``; ``slice_insets`` are the fixed borders (top, right, bottom, left) in the
    glyph's viewport units; ``unit_em`` is the size of one viewport unit in em of the annotation text size.
    """

    glyph: str
    slice_insets: tuple[Decimal, Decimal, Decimal, Decimal]
    unit_em: Decimal
    role: str
    declaration_pointer: str
    layer_index: int | None


@dataclass(frozen=True)
class RectangleChipShape:
    """Explicit legacy rectangular chip; absence has the same geometry."""


@dataclass(frozen=True)
class BurstChipShape:
    """Theme-owned polygon parameters; Layout completes its geometry."""

    points: int
    inner_ratio: Decimal


@dataclass(frozen=True)
class CatalogChipShape:
    """Nine-slice policy over an unchanged pinned catalogue glyph."""

    glyph: str
    slice_insets: tuple[Decimal, Decimal, Decimal, Decimal]
    unit_em: Decimal


ChipShapeToken = RectangleChipShape | BurstChipShape | CatalogChipShape


@dataclass(frozen=True)
class BorderSideToken:
    """One side of a box border (#1049): a width in surface units and the ink it is drawn with.

    ``paint`` is ``kind`` (the annotation kind colour, through the role ``annotation-kind-accent``) or ``ink``
    (the role ``annotation-border-<side>``).
    """

    width: Decimal
    paint: str = "ink"


@dataclass(frozen=True)
class MarkStackIntent:
    """Theme-owned ordered mark groups and an optional span-frame declaration (#1149)."""

    members: tuple[tuple[str, ...], ...]
    gap: Decimal
    frame_roles: tuple[str, ...] = ()
    frame_padding: Decimal = Decimal(0)


BORDER_SIDES = ("start", "end", "top", "bottom")


@dataclass(frozen=True)
class AnnotationContainerToken:
    """One declared annotation-box outline (#466 rectangle/balloon, #465 image)."""

    outline: str
    corner_radius: Decimal
    tail_base: Decimal | None = None
    image_ref: str | None = None
    slice_insets_em: tuple[Decimal, Decimal, Decimal, Decimal] | None = None
    content_insets_em: tuple[Decimal, Decimal, Decimal, Decimal] | None = None
    # The declared tilt cycle in degrees, rectangle outlines only (#584): the annotation at position i of the
    # View's order takes tilt_degrees[i mod len]; None means no tilt.
    tilt_degrees: tuple[Decimal, ...] | None = None
    # Ordered normalized layers; an empty tuple means no artwork.
    artwork: tuple[ArtworkToken, ...] = ()
    # How the box is sized in an annotations slot (#1051): "content" (today) or "fill" (the slot's inline size,
    # at most `max_inline_em` text sizes when declared).
    inline_size: str = "content"
    max_inline_em: Decimal | None = None
    # A per-side box border on a square rectangle container (#1049): side name -> width and ink; None means none.
    border: Mapping[str, BorderSideToken] | None = None


VIEWER_FIT_RAW = "raw"
TEXT_FOLLOWS_BOX = "text-follows-box"
BOX_FOLLOWS_TEXT = "box-follows-text"
VIEWER_FIT_MODES = (VIEWER_FIT_RAW, TEXT_FOLLOWS_BOX, BOX_FOLLOWS_TEXT)
FIT_ADJUSTS = ("spacing", "spacingAndGlyphs")


@dataclass(frozen=True)
class ViewerFitToken:
    """How a box role's text and box absorb a viewer that lacks the measured font (#1050); `raw` is today's output."""

    mode: str = VIEWER_FIT_RAW
    adjust: str = "spacing"


@dataclass(frozen=True)
class AnnotationKindToken:
    """One Theme-declared annotation kind (#584): header text sources and the resolved kind colour."""

    header: KindHeader
    color: str | None
    stamp: str | None = None


@dataclass(frozen=True)
class AnnotationKindFrame:
    """The Theme's annotation-kind elements: which exist and their finite geometry (#584)."""

    label_role: str | None
    secondary_role: str | None
    bar_role: str | None
    bar_padding_em: Decimal
    stamp_role: str | None = None
    stamp_corner: str | None = None
    stamp_size: Decimal = Decimal(0)
    heading_role: str | None = None
    bar_width: str = "fill"
    bar_bleed: str = "none"
    stamp_placement: str = "column"


@dataclass(frozen=True)
class ThemeTokenView:
    """Non-persistent, typed view derived solely from resolved Theme v0.2.

    It deliberately exposes no legacy renderer-shaped maps (for example
    ``paints`` or ``strokes``).  A Scene builder asks for a semantic role and
    property, then receives the declared token value or a stable diagnostic.
    """

    resolved_theme: Mapping[str, Any]
    catalog_glyphs: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    catalog_patterns: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        body = self.resolved_theme.get("body")
        if (self.resolved_theme.get("version") != "chrona/resolved-theme/v0.2"
                or self.resolved_theme.get("kind") != "resolved-theme"
                or not isinstance(body, Mapping)
                or not isinstance(body.get("values"), Mapping)
                or not isinstance(body.get("roles"), Mapping)):
            raise ThemeTokenError("E_THEME_RESOLVED_SCHEMA", "/")
        assets = body.get("catalogAssets", {})
        if isinstance(assets, Mapping):
            if not self.catalog_glyphs and isinstance(assets.get("glyphs"), Mapping):
                object.__setattr__(self, "catalog_glyphs", assets["glyphs"])
            if not self.catalog_patterns and isinstance(assets.get("patterns"), Mapping):
                object.__setattr__(self, "catalog_patterns", assets["patterns"])

    @property
    def _body(self) -> Mapping[str, Any]:
        return self.resolved_theme["body"]

    @property
    def _catalog_glyphs(self) -> Mapping[str, Mapping[str, Any]]:
        if self.catalog_glyphs:
            return self.catalog_glyphs
        assets = self._body.get("catalogAssets", {})
        return assets.get("glyphs", {}) if isinstance(assets, Mapping) else {}

    @property
    def _catalog_patterns(self) -> Mapping[str, Mapping[str, Any]]:
        if self.catalog_patterns:
            return self.catalog_patterns
        assets = self._body.get("catalogAssets", {})
        return assets.get("patterns", {}) if isinstance(assets, Mapping) else {}

    def has_role(self, role: str) -> bool:
        """Whether this resolved Theme declares the exact semantic role."""
        return isinstance(self._body["roles"].get(role), Mapping)

    def has_binding(self, role: str, property_name: str) -> bool:
        """Whether this exact role declares a property binding.

        This is a presence query only: it does not resolve the binding, inherit
        from another role, or infer a value from fallback behavior.
        """
        binding = self._body["roles"].get(role)
        return isinstance(binding, Mapping) and property_name in binding

    def declares_text_treatment(self, role: str) -> bool:
        """Whether the Theme gives `role` its own text measurement (a `fontSize`), not only a colour binding (#1110)."""
        binding = self._body["roles"].get(role)
        return isinstance(binding, Mapping) and "fontSize" in binding

    def table_header_role(self) -> str:
        """The typography role of table column headers: `tableColumnLabel` when the Theme declares it, else `text` (#991)."""
        return "tableColumnLabel" if self.has_role("tableColumnLabel") else "text"

    def title_paint_role(self, role: str = "heading") -> str:
        """The registered title ink choice (#1164); typography remains independent.

        A fill activates the line's own paint role, including its opacity. An
        opacity alone does not activate an ink; the shared text paint is unchanged.
        """
        return role if self.optional_color(role, "fill") is not None else "text"

    def text_block_gap(self, role: str) -> Decimal:
        """Declared minimum separation after a run in a measured block stack."""
        gap = self.optional_number(role, "blockGap")
        if gap is None:
            return Decimal(0)
        if gap < 0:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/blockGap", f"value={_shown(gap)}; expected nonnegative number")
        return gap

    def text_inline_gap(self, role: str) -> Decimal:
        """Declared separation after an inline summary run; no trailing gap."""
        gap = self.optional_number(role, "inlineGap")
        if gap is None:
            return Decimal(0)
        if gap < 0:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/inlineGap", f"value={_shown(gap)}; expected nonnegative number")
        return gap

    def slot_heading_role(self) -> str:
        """The typography role of a slot heading (#1064): `slot-heading` when the Theme declares it, else `text`."""
        return "slot-heading" if self.has_role("slot-heading") else "text"

    def token(self, role: str, property_name: str, expected_type: str) -> Any:
        roles = self._body["roles"]
        binding = roles.get(role)
        path = f"/body/roles/{role}/{property_name}"
        if not isinstance(binding, Mapping) or not isinstance(binding.get(property_name), str):
            raise ThemeTokenError("E_THEME_ROLE_REQUIRED", path,
                                  f"role={_shown(role)}, property={_shown(property_name)}; bindingType={_operand(binding)}; expected token-name string")
        token_id = binding[property_name]
        declared = self._body["values"].get(token_id)
        if not isinstance(declared, Mapping) or declared.get("type") != expected_type or "value" not in declared:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", path,
                                  f"role={_shown(role)}, property={_shown(property_name)}, token={_shown(token_id)}; declaredType={_operand(declared.get('type') if isinstance(declared, Mapping) else declared)}, expectedType={_shown(expected_type)}")
        return declared["value"]

    def color(self, role: str, property_name: str = "fill") -> str:
        value = self.token(role, property_name, "color")
        if not isinstance(value, str):
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/{property_name}", f"valueType={_operand(value)}; expected string colour")
        return value

    def opacity(self, role: str) -> float:
        """Resolve one finite, closed role opacity."""
        value = self.number(role, "opacity")
        if value < 0 or value > 1:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/opacity", f"value={value}; expected number in [0, 1]")
        return float(value)

    def optional_pattern(self, role: str) -> Mapping[str, Any] | None:
        """Return one structured, schema-closed pattern treatment if declared."""
        binding = self._body["roles"].get(role)
        if not isinstance(binding, Mapping) or "pattern" not in binding:
            return None
        value = self.token(role, "pattern", "pattern")
        if not isinstance(value, Mapping):
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/pattern")
        if value.get("kind") == "catalog":
            reference = value.get("ref")
            entry = self._catalog_patterns.get(str(reference)) if isinstance(reference, str) else None
            if not isinstance(entry, Mapping):
                raise ThemeTokenError("E_THEME_ASSET_REFERENCE", f"/body/roles/{role}/pattern", f"reference={_shown(reference)}; no matching catalog pattern")
            return {"kind": "catalog", "ref": reference, **dict(entry)}
        return value

    def catalog_glyph(self, reference: str) -> Mapping[str, Any]:
        """Return one closure-validated normalized glyph by authored reference."""
        entry = self._catalog_glyphs.get(reference)
        if not isinstance(entry, Mapping):
            raise ThemeTokenError("E_THEME_ASSET_REFERENCE", "/body/values")
        return entry

    def marker(self, role: str) -> Mapping[str, Any]:
        value = self.token(role, "marker", "marker")
        if not isinstance(value, Mapping):
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/marker")
        return value

    def symbol(self, role: str = "milestoneSymbol") -> Mapping[str, Any]:
        """Resolve one role's full symbol value (a built-in shape or a glyph)."""
        value = self.token(role, "symbol", "symbol")
        if not isinstance(value, Mapping):
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/symbol")
        shape = value.get("shape")
        if isinstance(shape, str):
            return value
        if (isinstance(shape, Mapping) and set(shape) == {"catalog"}
                and isinstance(shape.get("catalog"), str)):
            return value
        raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/symbol")
        return value

    _VARIANT_SYMBOL_ROLES = {"planned": "milestoneSymbol", "actual": "milestoneSymbolActual",
                             "baseline": "milestoneSymbolBaseline"}

    def variant_symbol(self, variant: str) -> Mapping[str, Any]:
        """Resolve a planned/actual/baseline gate's symbol, falling back to milestoneSymbol.

        `milestoneSymbolActual`/`milestoneSymbolBaseline` are optional roles; a
        Theme that does not declare one keeps that variant on `milestoneSymbol`,
        so an existing Theme's rendering is unaffected by their existence.
        """
        role = self._VARIANT_SYMBOL_ROLES[variant]
        if role != "milestoneSymbol" and not self.has_role(role):
            role = "milestoneSymbol"
        symbol = self.symbol(role)
        shape = symbol.get("shape")
        if isinstance(shape, Mapping) and isinstance(shape.get("catalog"), str):
            reference = str(shape["catalog"])
            return {"shape": "catalog-glyph", "ref": reference, **dict(self.catalog_glyph(reference))}
        return symbol

    def optional_color(self, role: str, property_name: str) -> str | None:
        """Resolve an optional concrete colour without introducing a fallback."""
        binding = self._body["roles"].get(role)
        if not isinstance(binding, Mapping) or property_name not in binding:
            return None
        return self.color(role, property_name)

    def optional_number(self, role: str, property_name: str) -> Decimal | None:
        """Resolve an optional finite number without introducing a fallback."""
        binding = self._body["roles"].get(role)
        if not isinstance(binding, Mapping) or property_name not in binding:
            return None
        return self.number(role, property_name)

    def optional_choice(self, role: str, property_name: str, allowed: tuple[str, ...]) -> str | None:
        """Resolve an optional finite literal (a schema enum property), rejecting any other value."""
        binding = self._body["roles"].get(role)
        if not isinstance(binding, Mapping) or property_name not in binding:
            return None
        value = binding[property_name]
        if value not in allowed:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/{property_name}")
        return str(value)

    def optional_token(self, role: str, property_name: str, expected_type: str) -> Any | None:
        binding = self._body["roles"].get(role)
        if not isinstance(binding, Mapping) or property_name not in binding:
            return None
        return self.token(role, property_name, expected_type)

    def dash(self, role: str) -> tuple[float, ...]:
        """Resolve one closed dash pattern; absence is diagnosed by the caller."""
        value = self.token(role, "dash", "dashPattern")
        if not isinstance(value, list):
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/dash",
                                  f"role={_shown(role)}, property='dash', valueType={_operand(value)}; expected list of positive finite numbers")
        result: list[float] = []
        for index, segment in enumerate(value):
            try:
                number = Decimal(str(segment))
            except (InvalidOperation, ValueError) as error:
                raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/dash/{index}",
                                      f"role={_shown(role)}, property='dash[{index}]', valueType={_operand(segment)}; expected positive finite number") from error
            if not number.is_finite() or number <= 0:
                raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/dash/{index}",
                                      f"role={_shown(role)}, property='dash[{index}]', value={_shown(number)}; expected positive finite number")
            result.append(float(number))
        return tuple(result)

    def font_family(self, role: str = "text", property_name: str = "fontFamily") -> str:
        value = self.token(role, property_name, "fontFamily")
        if not isinstance(value, str):
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/{property_name}")
        return value

    def font_weight(self, role: str) -> int:
        value = self.token(role, "fontWeight", "fontWeight")
        try:
            weight = int(str(value))
        except (TypeError, ValueError) as error:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/fontWeight") from error
        if weight < 1:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/fontWeight",
                                  f"role={_shown(role)}, property='fontWeight', value={_shown(weight)}; expected positive integer font weight")
        return weight

    def _typography_components(self, role: str) -> tuple[str, int, Decimal, Decimal]:
        """Resolve the components used exclusively to construct TextTreatment."""
        family, weight = self.font_family(role), self.font_weight(role)
        size, line_height = self.number(role, "fontSize"), self.number(role, "lineHeight")
        if size <= 0 or line_height <= 0:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}",
                                  f"role={role!r}, fontSize={size}, lineHeight={line_height}; expected both positive numbers")
        return family, weight, size, line_height

    def text_treatment(self, role: str) -> TextTreatment:
        """Resolve the complete measured treatment selected for one text role."""
        family, weight, size, line_height = self._typography_components(role)
        spacing = self.number(role, "letterSpacing")
        transform = self.token(role, "textTransform", "textTransform")
        numeric_spacing = self.token(role, "numericSpacing", "numericSpacing")
        if (spacing < Decimal("-1") or spacing > Decimal("1")
                or transform not in {"none", "uppercase", "lowercase", "capitalize"}
                or numeric_spacing not in {"proportional", "tabular"}):
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}",
                                  f"role={_shown(role)}, letterSpacing={_shown(spacing)}, textTransform={_shown(transform)}, numericSpacing={_shown(numeric_spacing)}; expected spacing [-1, 1], transform none/uppercase/lowercase/capitalize, numeric spacing proportional/tabular")
        scale = self.optional_number(role, "horizontalScale")
        scale = (Decimal(1) if scale is None
                 else checked_horizontal_scale(scale, f"/body/roles/{role}/horizontalScale"))
        if scale != 1 and self.writing_mode(role) == "vertical":
            raise ThemeTokenError("E_THEME_TEXT_TREATMENT_CONFLICT", f"/body/roles/{role}/horizontalScale")
        return TextTreatment(family, weight, size, line_height, spacing, transform, numeric_spacing, scale)

    def writing_mode(self, role: str) -> str:
        """Return the role's declared writing mode: horizontal when absent (#585)."""
        binding = self._body["roles"].get(role)
        if not isinstance(binding, Mapping) or "writingMode" not in binding:
            return "horizontal"
        value = self.token(role, "writingMode", "writingMode")
        if value not in {"horizontal", "vertical"}:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/writingMode")
        return str(value)

    def icon_ratios(self, role: str) -> tuple[Decimal, Decimal]:
        """Return the closed typography-relative icon scale and gap for one role."""
        scale, gap = self.number(role, "iconScale"), self.number(role, "iconGap")
        if scale < 0 or gap < 0:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}",
                                  f"role={_shown(role)}, iconScale={_shown(scale)}, iconGap={_shown(gap)}; expected nonnegative values")
        return scale, gap

    def mark_geometry(self, role: str) -> tuple[Decimal, Decimal | None, int, Decimal]:
        """Return the closed lane-relative geometry for one mark semantic role."""
        height = self.number(role, "markHeight")
        offset = self.optional_number(role, "markOffset")
        order = self.number(role, "markPaintOrder")
        physical_radius = self.optional_token(role, "cornerRadius", "radius")
        corner_radius = Decimal(0) if physical_radius is not None else self.number(role, "markCornerRadius")
        if (height <= 0 or height > 1 or (offset is not None and (offset < 0 or offset + height > 1))
                or corner_radius < 0 or corner_radius > Decimal("0.5") or order != order.to_integral_value()):
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/markHeight",
                                  f"role={_shown(role)}, markHeight={_shown(height)}, markOffset={_shown(offset)}, cornerRadius={_shown(corner_radius)}, paintOrder={_shown(order)}; expected height (0,1], offset fitting track, radius [0,0.5], integral order")
        return height, offset, int(order), corner_radius

    def mark_alignment(self, role: str) -> str:
        """Return a mark's block alignment; offset-free declarations default to center (#1149)."""
        value = self.optional_choice(role, "align", ("start", "center", "end"))
        return "center" if value is None else value

    def mark_stack(self) -> MarkStackIntent | None:
        """Resolve the optional ordered mark-stack intent and its referenced physical lengths."""
        if "markStack" not in self._body:
            return None
        raw = self._body.get("markStack")
        pointer = "/body/markStack"
        if not isinstance(raw, Mapping) or set(raw) - {"members", "gap", "frame"}:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", pointer, "markStack must contain only members, gap, and optional frame")
        members_raw = raw.get("members")
        if (not isinstance(members_raw, (list, tuple)) or not members_raw
                or any(not isinstance(group, (list, tuple)) or not group for group in members_raw)):
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"{pointer}/members", "expected nonempty ordered role groups")
        allowed = {"planned", "actual", "snapshot", "scenario", "missing-actual"}
        members: list[tuple[str, ...]] = []
        seen: set[str] = set()
        ordered_seen: list[str] = []
        for index, group in enumerate(members_raw):
            if (any(not isinstance(role, str) or role not in allowed for role in group)
                    or len(set(group)) != len(group) or any(role in seen for role in group)):
                raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"{pointer}/members/{index}",
                                      "roles must be known and unique across stack groups")
            seen.update(group)
            ordered_seen.extend(group)
            members.append(tuple(group))
        gap = self._stack_number(raw.get("gap"), f"{pointer}/gap")
        frame = raw.get("frame")
        frame_roles: tuple[str, ...] = ()
        padding = Decimal(0)
        if "frame" in raw:
            if not isinstance(frame, Mapping) or set(frame) != {"roles", "padding"}:
                raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"{pointer}/frame",
                                      "frame requires only roles and padding")
            roles = frame.get("roles")
            if (not isinstance(roles, (list, tuple)) or not roles
                    or any(not isinstance(role, str) or role not in allowed or role in seen for role in roles)):
                raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"{pointer}/frame/roles",
                                      "frame roles must be known and distinct from stack members")
            if len(set(roles)) != len(roles):
                raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"{pointer}/frame/roles", "frame roles must be unique")
            frame_roles = tuple(roles)
            padding = self._stack_number(frame.get("padding"), f"{pointer}/frame/padding")
        for role in (*ordered_seen, *frame_roles):
            if self.optional_number(role, "markOffset") is not None:
                raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/markOffset",
                                      "explicit markOffset conflicts with stack allocation")
        return MarkStackIntent(tuple(members), gap, frame_roles, padding)

    def _stack_number(self, token_id: Any, pointer: str) -> Decimal:
        if not isinstance(token_id, str) or not token_id:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", pointer, "expected a number-token name")
        declared = self._body["values"].get(token_id)
        if not isinstance(declared, Mapping) or declared.get("type") != "number" or "value" not in declared:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", pointer, f"{_shown(token_id)} must name a number token")
        try:
            value = Decimal(str(declared["value"]))
        except (InvalidOperation, ValueError) as error:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", pointer, f"{_shown(token_id)} has a nonnumeric value") from error
        try:
            representable = math.isfinite(float(value))
        except (OverflowError, ValueError):
            representable = False
        if not value.is_finite() or not representable or value < 0:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", pointer,
                                  f"{_shown(token_id)} must be finite, nonnegative, and representable in Layout")
        return value

    def symbol_geometry(self, role: str) -> tuple[Decimal | None, Decimal | None]:
        """Return the optional symbol size and offset ratios of a mark role's point marks (#1066).

        Both are ratios of the track block size, like ``markHeight`` and ``markOffset``; an absent one is None and
        the symbol then takes the role's bar band value. Range checks need both values and are made by the
        geometry that combines them.
        """
        height = self.optional_number(role, "symbolHeight")
        offset = self.optional_number(role, "symbolOffset")
        if height is not None and height <= 0:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/symbolHeight")
        if offset is not None and offset < 0:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/symbolOffset")
        return height, offset

    def legend_swatch_sizes(self) -> tuple[float | None, float | None, float | None]:
        """Return the optional legend `swatchGap`, `swatchBlockSize` and `pointSwatchSize` in px (#1111).

        Each is absent by default, which keeps today's legend. A gap below 0 or a size at or below 0 is
        `E_THEME_TOKEN_TYPE` at the property of the `legend-swatch` role.
        """
        values = []
        for name, floor_ok in (("swatchGap", True), ("swatchBlockSize", False), ("pointSwatchSize", False)):
            value = self.optional_number("legend-swatch", name)
            if value is not None and (value < 0 if floor_ok else value <= 0):
                raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/legend-swatch/{name}")
            values.append(float(value) if value is not None else None)
        return values[0], values[1], values[2]

    def deadline_mark(self, role: str) -> tuple[Decimal, int]:
        """Return the deadline tick's reach and paint order (#822).

        ``markReach`` is the tick's block extent as a ratio of the planned mark it belongs to (centred on it), so a
        reach above 1 stands above and below the bar. The role is required when a View shows deadlines: there is no
        fallback to another role.
        """
        if not isinstance(self._body["roles"].get(role), Mapping):
            raise ThemeTokenError("E_THEME_ROLE_REQUIRED", f"/body/roles/{role}")
        reach, order = self.number(role, "markReach"), self.number(role, "markPaintOrder")
        if reach <= 0 or reach > 4:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/markReach")
        if order < 0 or order != order.to_integral_value():
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/markPaintOrder")
        return reach, int(order)

    def progress_track(self, role: str) -> tuple[Decimal, Decimal]:
        """Return the optional track inset and fill corner-radius ratios (#430).

        Both are absent by default, which keeps the fill full-height and square.
        """
        binding = self._body["roles"].get(role)
        declared = binding if isinstance(binding, Mapping) else {}
        inset = self.number(role, "progressInset") if "progressInset" in declared else Decimal(0)
        radius = self.number(role, "markCornerRadius") if "markCornerRadius" in declared else Decimal(0)
        if not Decimal(0) <= inset < Decimal("0.5"):
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/progressInset")
        if not Decimal(0) <= radius <= Decimal("0.5"):
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/markCornerRadius")
        return inset, radius

    def label_chip(self, role: str) -> tuple[Decimal, Decimal] | None:
        """Return a declared label chip's padding and corner-radius ratios (#428).

        A chip exists only when the Theme declares ``role`` with a fill
        background; padding is a ratio of the label's font size.
        """
        binding = self._body["roles"].get(role)
        if not isinstance(binding, Mapping) or binding.get("backgroundTreatment") != "fill":
            return None
        padding = self.number(role, "chipPadding") if "chipPadding" in binding else Decimal(0)
        radius = self.number(role, "markCornerRadius") if "markCornerRadius" in binding else Decimal(0)
        if not Decimal(0) <= padding <= Decimal(2):
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/chipPadding")
        if not Decimal(0) <= radius <= Decimal("0.5"):
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/markCornerRadius")
        return padding, radius

    def label_chip_min_block(self, role: str) -> Decimal | None:
        """A label chip's declared smallest block size in px (`chipMinBlockSize`), or None (#1150)."""
        binding = self._body["roles"].get(role)
        if not isinstance(binding, Mapping) or "chipMinBlockSize" not in binding:
            return None
        size = self.number(role, "chipMinBlockSize")
        if size <= 0:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/chipMinBlockSize")
        return size

    def label_chip_shape(self, role: str) -> ChipShapeToken:
        """Resolve shape policy without activating a chip or completing geometry."""
        if not self.has_binding(role, "chipShape"):
            return RectangleChipShape()
        value = self.token(role, "chipShape", "chipShape")
        pointer = f"/body/roles/{role}/chipShape"
        if not isinstance(value, Mapping):
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", pointer)
        kind = value.get("kind")
        if kind == "rectangle" and set(value) == {"kind"}:
            return RectangleChipShape()
        if kind == "burst" and set(value) == {"kind", "points", "innerRatio"}:
            points, ratio = value["points"], value["innerRatio"]
            if (isinstance(points, bool) or not isinstance(points, (int, float)) or points < 2
                    or isinstance(points, float) and (not math.isfinite(points) or not points.is_integer())):
                raise ThemeTokenError("E_THEME_TOKEN_TYPE", pointer + "/points")
            if isinstance(ratio, bool) or not isinstance(ratio, (int, float)):
                raise ThemeTokenError("E_THEME_TOKEN_TYPE", pointer + "/innerRatio")
            inner_ratio = self._decimal(ratio, role, "chipShape/innerRatio")
            if inner_ratio is None or not 0 < inner_ratio <= 1:
                raise ThemeTokenError("E_THEME_TOKEN_TYPE", pointer + "/innerRatio")
            result: ChipShapeToken = BurstChipShape(int(points), inner_ratio)
        elif kind == "catalog" and set(value) == {"kind", "glyph", "sliceInsets", "unitEm"}:
            glyph, insets, unit = self._catalog_slice_geometry(value, role, "chipShape")
            result = CatalogChipShape(glyph, insets, unit)
        else:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", pointer)
        binding = self._body["roles"][role]
        if binding.get("viewerFit") == BOX_FOLLOWS_TEXT:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/viewerFit")
        radius = self.optional_token(role, "cornerRadius", "radius")
        if radius is not None and radius != 0:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/cornerRadius")
        if (self.optional_number(role, "markCornerRadius") or Decimal(0)) != 0:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/markCornerRadius")
        if self.has_binding(role, "pattern"):
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/pattern")
        return result

    def annotation_container(self, role: str) -> "AnnotationContainerToken | None":
        """Return a declared annotation container's outline geometry (#466, #465).

        Absence (or a plain rectangle binding) means the role keeps today's
        plain rectangle box, byte-identical to a Theme without this token.
        """
        binding = self._body["roles"].get(role)
        if not isinstance(binding, Mapping) or "annotationContainer" not in binding:
            return None
        value = self.token(role, "annotationContainer", "annotationContainer")
        if not isinstance(value, Mapping) or value.get("outline") not in {"rectangle", "balloon", "image"}:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/annotationContainer")
        outline = value["outline"]
        corner_radius = self._decimal(value.get("cornerRadius"), role, "annotationContainer/cornerRadius")
        if corner_radius is None or corner_radius < 0:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/annotationContainer/cornerRadius")
        tilt = value.get("tiltDegrees")
        tilt_degrees: tuple[Decimal, ...] | None = None
        if tilt is not None:
            pointer = f"/body/roles/{role}/annotationContainer/tiltDegrees"
            if (outline != "rectangle" or not isinstance(tilt, (list, tuple)) or not tilt
                    or any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in tilt)):
                # A balloon tail and an image's slice tiles do not rotate by this rule.
                raise ThemeTokenError("E_THEME_TOKEN_TYPE", pointer)
            angles = tuple(self._decimal(item, role, "annotationContainer/tiltDegrees") for item in tilt)
            if any(angle is None or abs(angle) > 15 for angle in angles):
                raise ThemeTokenError("E_THEME_TOKEN_TYPE", pointer)
            tilt_degrees = angles  # type: ignore[assignment]
        # A rectangle or balloon may also declare a content inset (#991): padding between the box edge and its text.
        padding = (self._insets(value["contentInsetEm"], role, "annotationContainer/contentInsetEm")
                   if outline != "image" and "contentInsetEm" in value else None)
        # `contentPaddingEm` (#1150) is measured from the artwork's inner edge, so swapping the glyph keeps it.
        edge_padding = None
        if "contentPaddingEm" in value:
            if padding is not None or outline != "rectangle" or not value.get("artwork"):
                raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/annotationContainer/contentPaddingEm")
            edge_padding = self._insets(value["contentPaddingEm"], role, "annotationContainer/contentPaddingEm")
        artwork = self._artwork(value.get("artwork"), role, outline, padding if edge_padding is None else edge_padding)
        if edge_padding is not None:
            # The artwork's inner edge on a side is its widest fixed border there (slice inset x unit, in em).
            padding = tuple(max(layer.slice_insets[side] * layer.unit_em for layer in artwork) + edge_padding[side]
                            for side in range(4))  # type: ignore[assignment]
        inline_size = value.get("inlineSize", "content")
        if inline_size not in {"content", "fill"}:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/annotationContainer/inlineSize")
        max_inline_em = self._decimal(value.get("maxInlineEm"), role, "annotationContainer/maxInlineEm")
        if max_inline_em is not None and (inline_size != "fill" or max_inline_em <= 0
                                          or isinstance(value["maxInlineEm"], bool)):
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/annotationContainer/maxInlineEm")
        border = self._border(value.get("border"), role, outline, corner_radius)
        sizing = {"inline_size": inline_size, "max_inline_em": max_inline_em, "border": border}
        if outline == "rectangle":
            return AnnotationContainerToken(outline, corner_radius, None, None, None, padding, tilt_degrees, artwork, **sizing)
        if outline == "balloon":
            tail_base = self._decimal(value.get("tailBaseEm"), role, "annotationContainer/tailBaseEm")
            if tail_base is None or tail_base <= 0:
                raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/annotationContainer/tailBaseEm")
            return AnnotationContainerToken(outline, corner_radius, tail_base, None, None, padding, **sizing)
        # outline == "image" (#465): a nine-slice-stretchable icon-catalog
        # raster entry bound as the container's backdrop. cornerRadius must
        # be exactly 0 -- the artwork supplies its own corner treatment.
        if corner_radius != 0:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/annotationContainer/cornerRadius")
        image_ref = value.get("image")
        if not isinstance(image_ref, str) or not image_ref or image_ref.count(":") != 1:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/annotationContainer/image")
        slice_insets = self._insets(value.get("sliceInsetsEm"), role, "annotationContainer/sliceInsetsEm")
        content_insets = self._insets(value.get("contentInsetEm"), role, "annotationContainer/contentInsetEm")
        return AnnotationContainerToken(outline, corner_radius, None, image_ref, slice_insets, content_insets, **sizing)

    def viewer_fit(self, role: str, *, box_follows: bool = True) -> ViewerFitToken:
        """Return a box role's declared viewer-fit mode (#1050); absence is `raw`, today's output.

        ``box-follows-text`` paints a background that ends where the viewer's text ends, so it is valid only for a
        plain, square, untilted, content-sized rectangle with no artwork and no end, top or bottom border: every
        other declaration is refused at its pointer, never silently degraded. A role whose text has no box of its own
        to follow (``box_follows`` false: a legend, a table cell, a title, a group tag) admits no
        ``box-follows-text`` (#1096).
        """
        mode = self.optional_choice(role, "viewerFit", VIEWER_FIT_MODES) or VIEWER_FIT_RAW
        if mode == BOX_FOLLOWS_TEXT and not box_follows:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/viewerFit")
        adjust = self.optional_choice(role, "viewerFitAdjust", FIT_ADJUSTS)
        if adjust is not None and mode != TEXT_FOLLOWS_BOX:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/viewerFitAdjust")
        if mode == BOX_FOLLOWS_TEXT:
            if is_label_chip_role(role):
                physical = self.optional_token(role, "cornerRadius", "radius")
                if physical is not None:
                    if physical != 0:
                        raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/cornerRadius")
                elif (self.optional_number(role, "markCornerRadius") or Decimal(0)) != 0:
                    raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/markCornerRadius")
                self.color(role, "fill")
            container = self.annotation_container(role)
            if container is not None:
                base = f"/body/roles/{role}/annotationContainer"
                conflicts = (("outline", container.outline != "rectangle"),
                             ("cornerRadius", container.corner_radius != 0),
                             ("tiltDegrees", container.tilt_degrees is not None),
                             ("artwork", bool(container.artwork)),
                             ("inlineSize", container.inline_size != "content"),
                             *((f"border/{side}", side in (container.border or {})) for side in ("end", "top", "bottom")))
                for name, conflict in conflicts:
                    if conflict:
                        raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"{base}/{name}")
        return ViewerFitToken(mode, adjust or "spacing")

    def _border(self, value: Any, role: str, outline: str, corner_radius: Decimal) -> "Mapping[str, BorderSideToken] | None":
        """Validate the optional per-side ``border`` of an annotation container (#1049): a square rectangle only."""
        if value is None:
            return None
        pointer = f"/body/roles/{role}/annotationContainer/border"
        if (outline != "rectangle" or not isinstance(value, Mapping) or not value
                or set(value) - set(BORDER_SIDES)):
            # A balloon's tail and an image's own frame take no border: refused, never silently ignored. A rectangle
            # follows its radius with the strips (#1087).
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", pointer)
        sides: dict[str, BorderSideToken] = {}
        for side, entry in value.items():
            where = f"{pointer}/{side}"
            if not isinstance(entry, Mapping) or "width" not in entry or set(entry) - {"width", "paint"}:
                raise ThemeTokenError("E_THEME_TOKEN_TYPE", where)
            raw = entry["width"]
            width = (self._decimal(raw, role, f"annotationContainer/border/{side}/width")
                     if isinstance(raw, (int, float)) and not isinstance(raw, bool) else None)
            paint = entry.get("paint", "ink")
            if width is None or width < 0 or paint not in {"kind", "ink"}:
                raise ThemeTokenError("E_THEME_TOKEN_TYPE", where)
            sides[side] = BorderSideToken(width, paint)
        return sides

    def _artwork(self, value: Any, role: str, outline: str, padding: Any) -> tuple[ArtworkToken, ...]:
        """Normalize the legacy object or ordered list once, before Layout."""
        if value is None:
            return ()
        base = "annotationContainer/artwork"
        pointer = "/body/roles/" + role + "/" + base
        if outline != "rectangle" or padding is None:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", pointer)
        if isinstance(value, Mapping):
            return (self._artwork_layer(value, role, base, None),)
        if not isinstance(value, list) or not value:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", pointer)
        return tuple(self._artwork_layer(layer, role, f"{base}/{index}", index)
                     for index, layer in enumerate(value))

    def _artwork_layer(self, value: Any, role: str, base: str, index: int | None) -> ArtworkToken:
        pointer = f"/body/roles/{role}/{base}"
        required = {"glyph", "sliceInsets", "unitEm"}
        allowed = required | ({"role"} if index is not None else set())
        if not isinstance(value, Mapping) or not required <= set(value) or not set(value) <= allowed:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", pointer)
        paint_role = value.get("role", "annotation-artwork")
        if not is_annotation_artwork_role(paint_role):
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", pointer + "/role")
        glyph, insets, unit_em = self._catalog_slice_geometry(value, role, base)
        return ArtworkToken(glyph, insets, unit_em, paint_role, pointer, index)

    def _catalog_slice_geometry(self, value: Mapping[str, Any], role: str, base: str
                                ) -> tuple[str, tuple[Decimal, Decimal, Decimal, Decimal], Decimal]:
        """The same declared nine-slice geometry and pointers for every glyph use."""
        pointer = f"/body/roles/{role}/{base}"
        glyph = value["glyph"]
        if not isinstance(glyph, str) or glyph.count(":") != 1 or not all(glyph.split(":")):
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", pointer + "/glyph")
        insets = self._insets(value["sliceInsets"], role, base + "/sliceInsets")
        unit = value["unitEm"]
        unit_em = (self._decimal(unit, role, base + "/unitEm")
                   if isinstance(unit, (int, float)) and not isinstance(unit, bool) else None)
        if unit_em is None or unit_em <= 0:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", pointer + "/unitEm")
        entry = self._catalog_glyphs.get(glyph)
        if isinstance(entry, Mapping):
            # The pinned glyph's viewport bounds the fixed borders: a border larger than the glyph has no source.
            viewport = entry.get("viewport")
            try:
                width, height = Decimal(str(viewport["inlineSize"])), Decimal(str(viewport["blockSize"]))
            except (KeyError, TypeError, ValueError, InvalidOperation) as error:
                raise ThemeTokenError("E_THEME_TOKEN_TYPE", pointer + "/glyph") from error
            if insets[1] + insets[3] > width or insets[0] + insets[2] > height:
                raise ThemeTokenError("E_THEME_TOKEN_TYPE", pointer + "/sliceInsets")
        return glyph, insets, unit_em

    def annotation_kind(self, kind: str | None) -> "AnnotationKindToken | None":
        """Return the Theme's declaration for one Project annotation kind (#584).

        A kind the Theme does not declare, and an annotation with no kind, get no kind
        treatment: absence is today's plain annotation, not a fallback.
        """
        declared = self._body.get("annotationKinds")
        entry = declared.get(kind) if isinstance(declared, Mapping) and kind is not None else None
        if not isinstance(entry, Mapping):
            return None
        try:
            header = kind_header(str(kind), entry)
        except AnnotationKindTextError as error:
            raise ThemeTokenError(error.code, f"/body/annotationKinds/{kind}") from error
        color, stamp = entry.get("color"), entry.get("stamp")
        return AnnotationKindToken(header, str(color) if isinstance(color, str) else None,
                                   str(stamp) if isinstance(stamp, str) else None)

    def annotation_kind_frame(self) -> AnnotationKindFrame:
        """Return which annotation-kind elements this Theme declares and their geometry (#584)."""
        def declared(role: str) -> str | None:
            return role if self.has_role(role) else None
        bar_role = declared("annotation-kind-bar")
        padding = Decimal(0)
        if bar_role is not None:
            padding = self.optional_number(bar_role, "chipPadding") or Decimal(0)
            if not Decimal(0) <= padding <= Decimal(2):
                raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{bar_role}/chipPadding")
        stamp_role = declared("annotation-kind-stamp")
        corner, stamp_size, stamp_placement = None, Decimal(0), "column"
        if stamp_role is not None:
            placement = self.token(stamp_role, "stampPlacement", "stampPlacement")
            stamp_placement = placement.get("placement", "column") if isinstance(placement, Mapping) else None
            corner = placement.get("corner") if isinstance(placement, Mapping) else None
            stamp_size = self._decimal(placement.get("size") if isinstance(placement, Mapping) else None,
                                       stamp_role, "stampPlacement/size") or Decimal(0)
            valid_corner = isinstance(corner, str) and corner in ("start-top", "end-top", "start-bottom", "end-bottom")
            valid_placement = isinstance(stamp_placement, str) and stamp_placement in ("column", "bar-end")
            corner_matches = valid_corner if stamp_placement == "column" else corner is None
            if not valid_placement or not corner_matches or stamp_size <= 0:
                raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{stamp_role}/stampPlacement")
        bar_bleed = self.optional_choice("annotation-kind-bar", "barBleed", ("none", "border")) or "none"
        return AnnotationKindFrame(declared("annotation-kind-label"), declared("annotation-kind-secondary"),
                                   bar_role, padding, stamp_role, corner, stamp_size,
                                   declared("annotation-heading"),
                                   self.optional_choice("annotation-kind-bar", "barWidth", ("fill", "hug")) or "fill",
                                   bar_bleed, stamp_placement)

    def _insets(self, value: Any, role: str, property_name: str) -> tuple[Decimal, Decimal, Decimal, Decimal]:
        """Return a validated (top, right, bottom, left) em-relative inset quadruple."""
        if not isinstance(value, Mapping):
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/{property_name}")
        sides = tuple(self._decimal(value.get(side), role, f"{property_name}/{side}")
                      for side in ("top", "right", "bottom", "left"))
        if any(side is None or side < 0 for side in sides):
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/{property_name}")
        return sides  # type: ignore[return-value]

    def _decimal(self, value: Any, role: str, property_name: str) -> Decimal | None:
        if value is None:
            return None
        try:
            number = Decimal(str(value))
        except (InvalidOperation, ValueError) as error:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/{property_name}") from error
        if not number.is_finite():
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/{property_name}")
        return number

    def summary_bar_height(self, role: str) -> Decimal:
        """Return the positive lane-relative block-size ratio for a summary bar."""
        height = self.number(role, "markHeight")
        if height <= 0 or height > 1:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/markHeight")
        return height

    def background(self, role: str) -> tuple[str, int]:
        """Return a completed finite treatment and paint order for one background."""
        binding = self._body["roles"].get(role)
        path = f"/body/roles/{role}"
        if not isinstance(binding, Mapping):
            raise ThemeTokenError("E_THEME_ROLE_REQUIRED", path)
        treatment, order = binding.get("backgroundTreatment"), binding.get("backgroundPaintOrder")
        if treatment not in {"fill", "outline", "none"} or not isinstance(order, int) or not 0 <= order <= 1000:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", path)
        return treatment, order

    def optional_background(self, role: str) -> tuple[str, int] | None:
        """Return a declared background treatment, or none when not applicable."""
        binding = self._body["roles"].get(role)
        if not isinstance(binding, Mapping):
            return None
        if "backgroundTreatment" not in binding and "backgroundPaintOrder" not in binding:
            return None
        return self.background(role)

    def contrast_treatment(self, role: str) -> str:
        """Return the finite completed state-text treatment for one role."""
        binding = self._body["roles"].get(role)
        path = f"/body/roles/{role}/contrastTreatment"
        treatment = binding.get("contrastTreatment") if isinstance(binding, Mapping) else None
        if treatment not in {"required", "deemphasized"}:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", path)
        return treatment

    def number(self, role: str, property_name: str) -> Decimal:
        value = self.token(role, property_name, "number")
        try:
            result = Decimal(str(value))
        except (InvalidOperation, ValueError) as error:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/{property_name}") from error
        if not result.is_finite():
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/{property_name}",
                                  f"role={_shown(role)}, property={_shown(property_name)}, valueType={_operand(value)}; expected finite number")
        return result


def effective_draft_numeric_theme(resolved_theme: Mapping[str, Any], roles: tuple[str, ...]) -> Mapping[str, Any]:
    """Overlay selected draft roles without mutating the declared Theme contract."""
    if not roles:
        return resolved_theme
    body = resolved_theme["body"]
    values = dict(body["values"])
    bindings = dict(body["roles"])
    for role in roles:
        token_id = f"__draft_proportional_{role}"
        if token_id in values or role not in bindings:
            raise ThemeTokenError("E_THEME_ROLE_REQUIRED", f"/body/roles/{role}/numericSpacing")
        values[token_id] = {"type": "numericSpacing", "value": "proportional"}
        bindings[role] = {**bindings[role], "numericSpacing": token_id}
    return {**resolved_theme, "body": {**body, "values": values, "roles": bindings}}
