"""The closed renderer-neutral presentation capability ceiling."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


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
