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

    def typography(self, role: str) -> tuple[str, int, Decimal, Decimal]:
        """Resolve one fully declared typography role without metric fallbacks."""
        family, weight = self.font_family(role), self.font_weight(role)
        size, line_height = self.number(role, "fontSize"), self.number(role, "lineHeight")
        if size <= 0 or line_height <= 0:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}")
        return family, weight, size, line_height

    def icon_ratios(self, role: str) -> tuple[Decimal, Decimal]:
        """Return the closed typography-relative icon scale and gap for one role."""
        scale, gap = self.number(role, "iconScale"), self.number(role, "iconGap")
        if scale < 0 or gap < 0:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}")
        return scale, gap

    def number(self, role: str, property_name: str) -> Decimal:
        value = self.token(role, property_name, "number")
        try:
            result = Decimal(str(value))
        except (InvalidOperation, ValueError) as error:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/{property_name}") from error
        if not result.is_finite():
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/{property_name}")
        return result
