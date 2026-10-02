"""Typed access to the current resolved Theme v0.2 boundary."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from chrona.presentation.annotation_kind_text import AnnotationKindTextError, KindHeader, kind_header


class ThemeTokenError(ValueError):
    """Stable diagnostic for a missing or mistyped resolved Theme token."""

    def __init__(self, diagnostic_id: str, path: str):
        super().__init__(diagnostic_id)
        self.diagnostic_id = diagnostic_id
        self.path = path


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
    accent_role: str | None
    accent_side: str | None
    accent_size: Decimal
    stamp_role: str | None = None
    stamp_corner: str | None = None
    stamp_size: Decimal = Decimal(0)


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

    def token(self, role: str, property_name: str, expected_type: str) -> Any:
        roles = self._body["roles"]
        binding = roles.get(role)
        path = f"/body/roles/{role}/{property_name}"
        if not isinstance(binding, Mapping) or not isinstance(binding.get(property_name), str):
            raise ThemeTokenError("E_THEME_ROLE_REQUIRED", path)
        token_id = binding[property_name]
        declared = self._body["values"].get(token_id)
        if not isinstance(declared, Mapping) or declared.get("type") != expected_type or "value" not in declared:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", path)
        return declared["value"]

    def color(self, role: str, property_name: str = "fill") -> str:
        value = self.token(role, property_name, "color")
        if not isinstance(value, str):
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/{property_name}")
        return value

    def opacity(self, role: str) -> float:
        """Resolve one finite, closed role opacity."""
        value = self.number(role, "opacity")
        if value < 0 or value > 1:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/opacity")
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
                raise ThemeTokenError("E_THEME_ASSET_REFERENCE", f"/body/roles/{role}/pattern")
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

    def optional_token(self, role: str, property_name: str, expected_type: str) -> Any | None:
        binding = self._body["roles"].get(role)
        if not isinstance(binding, Mapping) or property_name not in binding:
            return None
        return self.token(role, property_name, expected_type)

    def dash(self, role: str) -> tuple[float, ...]:
        """Resolve one closed dash pattern; absence is diagnosed by the caller."""
        value = self.token(role, "dash", "dashPattern")
        if not isinstance(value, list):
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/dash")
        result: list[float] = []
        for index, segment in enumerate(value):
            try:
                number = Decimal(str(segment))
            except (InvalidOperation, ValueError) as error:
                raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/dash/{index}") from error
            if not number.is_finite() or number <= 0:
                raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/dash/{index}")
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
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/fontWeight")
        return weight

    def _typography_components(self, role: str) -> tuple[str, int, Decimal, Decimal]:
        """Resolve the components used exclusively to construct TextTreatment."""
        family, weight = self.font_family(role), self.font_weight(role)
        size, line_height = self.number(role, "fontSize"), self.number(role, "lineHeight")
        if size <= 0 or line_height <= 0:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}")
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
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}")
        scale = self.optional_number(role, "horizontalScale")
        scale = (Decimal(1) if scale is None
                 else checked_horizontal_scale(scale, f"/body/roles/{role}/horizontalScale"))
        return TextTreatment(family, weight, size, line_height, spacing, transform, numeric_spacing, scale)

    def icon_ratios(self, role: str) -> tuple[Decimal, Decimal]:
        """Return the closed typography-relative icon scale and gap for one role."""
        scale, gap = self.number(role, "iconScale"), self.number(role, "iconGap")
        if scale < 0 or gap < 0:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}")
        return scale, gap

    def mark_geometry(self, role: str) -> tuple[Decimal, Decimal, int, Decimal]:
        """Return the closed lane-relative geometry for one mark semantic role."""
        height = self.number(role, "markHeight")
        offset = self.number(role, "markOffset")
        order = self.number(role, "markPaintOrder")
        corner_radius = self.number(role, "markCornerRadius")
        if height <= 0 or offset < 0 or offset + height > 1 or corner_radius < 0 or corner_radius > Decimal("0.5") or order != order.to_integral_value():
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/markHeight")
        return height, offset, int(order), corner_radius

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
        if outline == "rectangle":
            return AnnotationContainerToken(outline, corner_radius, None, None, None, None, tilt_degrees)
        if outline == "balloon":
            tail_base = self._decimal(value.get("tailBaseEm"), role, "annotationContainer/tailBaseEm")
            if tail_base is None or tail_base <= 0:
                raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/annotationContainer/tailBaseEm")
            return AnnotationContainerToken(outline, corner_radius, tail_base, None, None, None)
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
        return AnnotationContainerToken(outline, corner_radius, None, image_ref, slice_insets, content_insets)

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
        accent_role = declared("annotation-kind-accent")
        side, size = None, Decimal(0)
        if accent_role is not None:
            edge = self.token(accent_role, "edge", "edge")
            side = edge.get("side") if isinstance(edge, Mapping) else None
            size = self._decimal(edge.get("size") if isinstance(edge, Mapping) else None, accent_role, "edge/size") or Decimal(0)
            if side not in {"start", "end", "top", "bottom"} or size <= 0:
                raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{accent_role}/edge")
        stamp_role = declared("annotation-kind-stamp")
        corner, stamp_size = None, Decimal(0)
        if stamp_role is not None:
            placement = self.token(stamp_role, "stampPlacement", "stampPlacement")
            corner = placement.get("corner") if isinstance(placement, Mapping) else None
            stamp_size = self._decimal(placement.get("size") if isinstance(placement, Mapping) else None,
                                       stamp_role, "stampPlacement/size") or Decimal(0)
            if corner not in {"start-top", "end-top", "start-bottom", "end-bottom"} or stamp_size <= 0:
                raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{stamp_role}/stampPlacement")
        return AnnotationKindFrame(declared("annotation-kind-label"), declared("annotation-kind-secondary"),
                                   bar_role, padding, accent_role, side, size, stamp_role, corner, stamp_size)

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
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/{property_name}")
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
