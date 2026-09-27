"""The closed renderer-neutral presentation capability ceiling."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from re import fullmatch


class CapabilityDisposition(StrEnum):
    ADMITTED = "admitted"
    DEFERRED = "deferred"
    DELIBERATELY_REJECTED = "deliberately-rejected"


@dataclass(frozen=True)
class PresentationCapability:
    """One reviewable capability decision, independent of target syntax."""

    identifier: str
    primitive_family: str
    disposition: CapabilityDisposition
    owner: str
    reason: str
    reference: str
    substitution_owner: str | None = None


LINEAR_GRADIENT = "paint.linear-gradient"
DROP_SHADOW = "effect.drop-shadow"
LINE_CAP = "stroke.line-cap"
LINE_JOIN = "stroke.line-join"
ICON_VECTOR = "icon.vector"
ICON_RASTER = "icon.raster"
MARKER_GEOMETRY = "mark.marker-geometry"
PATTERN_GEOMETRY = "paint.pattern-geometry"
SYMBOL_OUTLINE = "mark.symbol-outline"


_CAPABILITIES = (
    PresentationCapability("label.typography", "label", CapabilityDisposition.ADMITTED, "Theme",
                           "Measured portable typography is a completed Scene fact.", "specification-63"),
    PresentationCapability("label.editorial-typography", "label", CapabilityDisposition.DEFERRED, "Theme",
                           "Letter spacing and transform require measured role-scoped design.", "issue-383"),
    PresentationCapability("mark.treatment", "mark", CapabilityDisposition.ADMITTED, "Theme",
                           "Finite fill, stroke, opacity, radius, marker, symbol, and pattern treatments are current Scene facts.", "specification-63"),
    PresentationCapability("mark.role-geometry", "mark", CapabilityDisposition.DEFERRED, "Layout",
                           "Role-scoped height, offset, and end shape require a row-space design.", "issues-384-388"),
    PresentationCapability("mark.arbitrary-asset", "mark", CapabilityDisposition.DELIBERATELY_REJECTED, "none",
                           "Arbitrary target assets break the finite renderer-neutral Scene boundary.", "specification-63"),
    PresentationCapability("line.treatment", "line", CapabilityDisposition.ADMITTED, "Theme",
                           "Finite stroke, dash, cap, join, and completed dependency markers are current treatment.", "specification-63"),
    PresentationCapability("line.adapter-routing", "line", CapabilityDisposition.DELIBERATELY_REJECTED, "none",
                           "Routing is Layout-owned and cannot become adapter control.", "specification-32"),
    PresentationCapability("decoration.treatment", "decoration", CapabilityDisposition.ADMITTED, "Theme",
                           "Finite group, axis, calendar, fill, stroke, opacity, and pattern treatment is current vocabulary.", "specification-63"),
    PresentationCapability("decoration.row-band", "decoration", CapabilityDisposition.DEFERRED, "Layout",
                           "Cross-slot row allocation needs a dedicated row-band design.", "issue-389"),
    PresentationCapability(LINEAR_GRADIENT, "effect", CapabilityDisposition.ADMITTED, "Theme",
                           "Two-stop completed gradient is decorative rich paint.", "specification-63"),
    PresentationCapability(DROP_SHADOW, "effect", CapabilityDisposition.ADMITTED, "Theme",
                           "One completed shadow is decorative rich paint.", "specification-63"),
    PresentationCapability(LINE_CAP, "effect", CapabilityDisposition.ADMITTED, "Theme",
                           "Completed stroke cap is finite rich paint.", "specification-63"),
    PresentationCapability(LINE_JOIN, "effect", CapabilityDisposition.ADMITTED, "Theme",
                           "Completed stroke join is finite rich paint.", "specification-63"),
    PresentationCapability(ICON_VECTOR, "icon", CapabilityDisposition.ADMITTED, "View",
                           "Normalized vector icon closure is owned by the icon catalog contract.", "specification-64"),
    PresentationCapability(ICON_RASTER, "icon", CapabilityDisposition.ADMITTED, "View",
                           "Verified raster icon closure is owned by the icon catalog contract.", "specification-64"),
    PresentationCapability("icon.generic-image", "icon", CapabilityDisposition.DELIBERATELY_REJECTED, "none",
                           "A generic image requires a separate asset-family and security contract.", "specification-64"),
    PresentationCapability(MARKER_GEOMETRY, "mark", CapabilityDisposition.ADMITTED, "Theme",
                           "Completed marker geometry is target-neutral.", "issue-384"),
    PresentationCapability(PATTERN_GEOMETRY, "mark", CapabilityDisposition.ADMITTED, "Theme",
                           "Completed finite pattern geometry is target-neutral.", "issue-384"),
    PresentationCapability(SYMBOL_OUTLINE, "mark", CapabilityDisposition.ADMITTED, "Theme",
                           "Completed point-symbol outline is target-neutral.", "issue-384"),
)

_BY_IDENTIFIER = {item.identifier: item for item in _CAPABILITIES}


def capability_ceiling() -> tuple[PresentationCapability, ...]:
    """Return every admitted, deferred, and deliberately rejected decision."""
    return _CAPABILITIES


def admitted_capability_ids(*identifiers: str) -> frozenset[str]:
    """Return named admitted runtime IDs and reject an undeclared request."""
    selected = identifiers or tuple(item.identifier for item in _CAPABILITIES)
    unknown = [identifier for identifier in selected
               if identifier not in _BY_IDENTIFIER or _BY_IDENTIFIER[identifier].disposition is not CapabilityDisposition.ADMITTED]
    if unknown:
        raise ValueError(f"E_VISUAL_CAPABILITY_CEILING:{unknown[0]}")
    return frozenset(selected)


def validate_substitution_request(capability_id: str) -> None:
    """Reject a substitution request until its semantic encoding owns an alternative."""
    capability = _BY_IDENTIFIER.get(capability_id)
    if capability is None or capability.substitution_owner is None:
        raise ValueError("E_VISUAL_CAPABILITY_SUBSTITUTION")


# Theme admission is a consumer projection of the same presentation ceiling.
# These sets describe completed renderer-neutral uses, not current YAML usage.
_TEXT_MEASUREMENT = frozenset(("fontFamily", "fontWeight", "fontSize", "lineHeight",
                               "letterSpacing", "textTransform", "numericSpacing"))
_ICON_MEASUREMENT = frozenset(("iconScale", "iconGap"))
_AXIS_MEASUREMENT = frozenset(("laneBlockSize", "labelInset"))
_RECT_PAINT = frozenset(("fill", "stroke", "strokeWidth", "dash", "opacity",
                         "gradientStart", "gradientEnd", "gradientAngle", "gradientFidelity",
                         "shadowColor", "shadowOffsetX", "shadowOffsetY", "shadowBlur",
                         "shadowOpacity", "shadowFidelity", "strokeLineCap", "strokeLineJoin",
                         "strokeFinishFidelity"))
_PATH_PAINT = frozenset(("stroke", "strokeWidth", "dash", "opacity", "shadowColor",
                         "shadowOffsetX", "shadowOffsetY", "shadowBlur", "shadowOpacity",
                         "shadowFidelity", "strokeLineCap", "strokeLineJoin", "strokeFinishFidelity"))
_TEXT_PAINT = frozenset(("fill", "opacity", "gradientStart", "gradientEnd", "gradientAngle",
                         "gradientFidelity", "shadowColor", "shadowOffsetX", "shadowOffsetY",
                         "shadowBlur", "shadowOpacity", "shadowFidelity"))
_SHARED_TEXT_ICON_PAINT = frozenset(("fill", "opacity"))
_CANVAS_PAINT = frozenset(("fill", "opacity", "gradientStart", "gradientEnd", "gradientAngle",
                           "gradientFidelity", "shadowColor", "shadowOffsetX", "shadowOffsetY",
                           "shadowBlur", "shadowOpacity", "shadowFidelity"))
_PATTERNED_RECT_PAINT = _RECT_PAINT | frozenset(("pattern",))
_LAYOUT_TYPOGRAPHY = _TEXT_MEASUREMENT | _ICON_MEASUREMENT
_LAYOUT_GEOMETRY = _AXIS_MEASUREMENT | frozenset((
    "cellGap", "chipPadding", "markHeight", "markOffset", "markPaintOrder", "markCornerRadius",
    "progressInset", "summaryBarHeight", "swatchInlineSize", "annotationContainer", "marker", "symbol",
))
_LAYOUT_POLICY = frozenset(("backgroundTreatment", "backgroundPaintOrder"))
_CLOSURE_POLICY = frozenset(("contrastTreatment",))
_PAINT_GEOMETRY = frozenset(("strokeWidth",))
_SCENE_PAINT = (_RECT_PAINT | _PATH_PAINT | _TEXT_PAINT | _CANVAS_PAINT
                | frozenset(("pattern",))) - _PAINT_GEOMETRY


def _property_owner(property_name: str) -> str:
    if property_name in _LAYOUT_TYPOGRAPHY:
        return "Layout typography"
    if property_name in _LAYOUT_GEOMETRY:
        return "Layout/Scene completed geometry"
    if property_name in _LAYOUT_POLICY:
        return "Layout background policy"
    if property_name in _CLOSURE_POLICY:
        return "Theme contrast policy"
    if property_name in _PAINT_GEOMETRY:
        return "Layout relation width and Scene paint"
    if property_name in _SCENE_PAINT:
        return "Scene paint"
    raise AssertionError(f"unclassified Theme property consumer: {property_name}")


@dataclass(frozen=True)
class RolePropertyContract:
    """A named Theme consumer with the exact properties that reach it."""

    consumer: str
    properties: frozenset[str]
    scene_kinds: frozenset[str] = frozenset()
    property_owners: tuple[tuple[str, str], ...] = ()

    def owner_of(self, property_name: str) -> str | None:
        return dict(self.property_owners).get(property_name)


def _role_contracts() -> dict[str, RolePropertyContract]:
    roles: dict[str, RolePropertyContract] = {}

    def register(names: str, consumer: str, properties: frozenset[str],
                 *, scene_kinds: frozenset[str] = frozenset()) -> None:
        for name in names.split():
            if name in roles:
                raise AssertionError(f"duplicate Theme role contract: {name}")
            roles[name] = RolePropertyContract(
                consumer, properties, scene_kinds,
                tuple((property_name, _property_owner(property_name)) for property_name in sorted(properties)),
            )

    register("text", "Layout text and Scene Text/Icon", _TEXT_MEASUREMENT | _ICON_MEASUREMENT | _SHARED_TEXT_ICON_PAINT,
             scene_kinds=frozenset(("Text", "Icon")))
    register("heading groupHeader legend numeric summary", "Layout text measurement",
             _TEXT_MEASUREMENT | _ICON_MEASUREMENT)
    register("axis", "Layout axis-tier measurement and inline visual reservation",
             _TEXT_MEASUREMENT | _ICON_MEASUREMENT | _AXIS_MEASUREMENT)
    register("axisMonth axisQuarter axis2 axis3", "Layout axis-tier measurement",
             _TEXT_MEASUREMENT | _ICON_MEASUREMENT | _AXIS_MEASUREMENT)
    register("annotation", "Layout annotation text and Scene Text",
             _TEXT_MEASUREMENT | _ICON_MEASUREMENT | _TEXT_PAINT, scene_kinds=frozenset(("Text",)))
    register("metric subtitle", "Layout text and Scene Text", _TEXT_MEASUREMENT | _ICON_MEASUREMENT | _TEXT_PAINT,
             scene_kinds=frozenset(("Text",)))
    register("annotation-callout-text annotation-highlight-text annotation-note-text annotation-arrow-text",
             "Layout annotation text and Scene Text", _TEXT_MEASUREMENT | _TEXT_PAINT,
             scene_kinds=frozenset(("Text",)))
    register("variance-ahead variance-on-track variance-behind missing-actual-cell",
             "Scene state Text and contrast policy", _TEXT_PAINT | frozenset(("contrastTreatment",)),
             scene_kinds=frozenset(("Text",)))
    register("member-label-inside-planned member-label-inside-actual member-label-inside-snapshot member-label-inside-scenario",
             "Scene inside-label Text", _TEXT_PAINT, scene_kinds=frozenset(("Text",)))
    register("axis-label2 axis-label3 group-header note-index", "Scene Text", _TEXT_PAINT,
             scene_kinds=frozenset(("Text",)))
    register("background", "Scene canvas", _CANVAS_PAINT, scene_kinds=frozenset(("Canvas",)))
    register("planned actual snapshot scenario",
             "Layout marks and Scene Rect/Symbol", _PATTERNED_RECT_PAINT | frozenset((
                 "markHeight", "markOffset", "markPaintOrder", "markCornerRadius")),
             scene_kinds=frozenset(("Rect", "Symbol")))
    register("missing-actual", "Layout mark and Scene Rect", _PATTERNED_RECT_PAINT | frozenset((
        "markHeight", "markOffset", "markPaintOrder", "markCornerRadius")), scene_kinds=frozenset(("Rect",)))
    register("network-node", "Scene Rect", _PATTERNED_RECT_PAINT, scene_kinds=frozenset(("Rect",)))
    register("milestone", "Scene Symbol", _PATTERNED_RECT_PAINT, scene_kinds=frozenset(("Symbol",)))
    register("progress-fill", "Layout progress mark and Scene Rect", _RECT_PAINT | frozenset((
        "pattern", "progressInset", "markPaintOrder", "markCornerRadius")), scene_kinds=frozenset(("Rect",)))
    register("summary-bar", "Layout summary mark and Scene Rect", _PATTERNED_RECT_PAINT | frozenset(("markHeight",)),
             scene_kinds=frozenset(("Rect",)))
    register("milestoneSymbol milestoneSymbolActual milestoneSymbolBaseline", "Layout/Scene symbol geometry",
             frozenset(("symbol",)))
    register("icon-mark", "Layout icon size and Scene Icon", _ICON_MEASUREMENT | _SHARED_TEXT_ICON_PAINT,
             scene_kinds=frozenset(("Icon",)))
    register("dependency-critical network-edge critical-edge axis-major axis-minor axis-rule axis-cell-separator as-of",
             "Layout relation and Scene Path", _PATH_PAINT, scene_kinds=frozenset(("Path",)))
    register("dependency", "Scene Path and Layout legend swatch marker", _PATH_PAINT | frozenset(("marker",)),
             scene_kinds=frozenset(("Path",)))
    register("annotation-callout-leader annotation-note-leader", "Layout annotation leader and Scene Path", _PATH_PAINT,
             scene_kinds=frozenset(("Path",)))
    register("annotation-arrow-leader", "Layout explanatory arrow and Scene Path",
             _PATH_PAINT | frozenset(("marker",)), scene_kinds=frozenset(("Path",)))
    register("asOf", "Layout as-of relation width", frozenset(("dash", "strokeWidth")))
    register("relationSourceTerminal relationTargetTerminal", "Layout relation terminal geometry",
             frozenset(("marker",)))
    register("annotation-callout-box annotation-highlight-box annotation-note-box annotation-arrow-box",
             "Layout annotation container and Scene Rect", _PATTERNED_RECT_PAINT | frozenset(("annotationContainer",)),
             scene_kinds=frozenset(("Rect",)))
    register("group-band row-band group-header-band calendar-closed", "Layout background and Scene Rect",
             _RECT_PAINT | frozenset(("backgroundTreatment", "backgroundPaintOrder")),
             scene_kinds=frozenset(("Rect",)))
    register("axis-band-decoration axis-band-decoration2", "Layout axis band and Scene Rect",
             _PATTERNED_RECT_PAINT | frozenset(("backgroundTreatment", "backgroundPaintOrder", "cellGap")),
             scene_kinds=frozenset(("Rect",)))
    register("as-of-label-chip member-label-chip finish-delta-chip", "Layout label chip and Scene Rect",
             _PATTERNED_RECT_PAINT | frozenset(("backgroundTreatment", "chipPadding", "markCornerRadius")),
             scene_kinds=frozenset(("Rect",)))
    register("legend-swatch", "Layout legend swatch size", frozenset(("swatchInlineSize",)))
    register("baseline", "Retired Theme paint alias", frozenset())
    return roles


_ROLE_PROPERTY_CONTRACTS = _role_contracts()
_OPEN_AXIS_PROPERTIES = _TEXT_MEASUREMENT | _AXIS_MEASUREMENT
_OPEN_LEGEND_PROPERTIES = _RECT_PAINT


def theme_role_contract(role: str) -> RolePropertyContract | None:
    """Expose the finite known-role entry for structural consumer checks."""
    return _ROLE_PROPERTY_CONTRACTS.get(role)


def theme_role_property_consumer(role: str, property_name: str) -> str | None:
    """Return the capable owner, or None for a role/property with no consumer.

    An unknown name may be produced by either an axis tier or the #427
    fixed-square legend fallback. Known names never inherit that fallback.
    """
    contract = _ROLE_PROPERTY_CONTRACTS.get(role)
    if contract is not None:
        return contract.consumer if property_name in contract.properties else None
    # The registered group colour namespace takes precedence over both
    # open-name producers; it is not an arbitrary axis/legend role.
    if role.startswith("group:"):
        return ("Layout group colour encoding"
                if property_name == "fill" and fullmatch(r"group:[A-Za-z][A-Za-z0-9_-]*", role)
                else None)
    if property_name in _OPEN_AXIS_PROPERTIES:
        return "View-named axis-tier measurement"
    if property_name in _OPEN_LEGEND_PROPERTIES:
        return "Detail Profile legend fixed-square Rect"
    return None
