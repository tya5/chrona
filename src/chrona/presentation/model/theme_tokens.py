"""Typed access to the current resolved Theme v0.2 boundary."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping


class ThemeTokenError(ValueError):
    """Stable diagnostic for a missing or mistyped resolved Theme token."""

    def __init__(self, diagnostic_id: str, path: str):
        super().__init__(diagnostic_id)
        self.diagnostic_id = diagnostic_id
        self.path = path


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
class ThemeTokenView:
    """Non-persistent, typed view derived solely from resolved Theme v0.2.

    It deliberately exposes no legacy renderer-shaped maps (for example
    ``paints`` or ``strokes``).  A Scene builder asks for a semantic role and
    property, then receives the declared token value or a stable diagnostic.
    """

    resolved_theme: Mapping[str, Any]

    def __post_init__(self) -> None:
        body = self.resolved_theme.get("body")
        if (self.resolved_theme.get("version") != "chrona/resolved-theme/v0.2"
                or self.resolved_theme.get("kind") != "resolved-theme"
                or not isinstance(body, Mapping)
                or not isinstance(body.get("values"), Mapping)
                or not isinstance(body.get("roles"), Mapping)):
            raise ThemeTokenError("E_THEME_RESOLVED_SCHEMA", "/")

    @property
    def _body(self) -> Mapping[str, Any]:
        return self.resolved_theme["body"]

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
        return value

    def marker(self, role: str) -> Mapping[str, Any]:
        value = self.token(role, "marker", "marker")
        if not isinstance(value, Mapping):
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/marker")
        return value

    def symbol(self, role: str = "milestoneSymbol") -> str:
        value = self.token(role, "symbol", "symbol")
        if not isinstance(value, Mapping) or not isinstance(value.get("shape"), str):
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/symbol")
        return value["shape"]

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
        return TextTreatment(family, weight, size, line_height, spacing, transform, numeric_spacing)

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
