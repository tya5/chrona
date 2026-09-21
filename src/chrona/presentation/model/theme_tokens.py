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

    def font_family(self, role: str = "text", property_name: str = "fontFamily") -> str:
        value = self.token(role, property_name, "fontFamily")
        if not isinstance(value, str):
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/{property_name}")
        return value

    def number(self, role: str, property_name: str) -> Decimal:
        value = self.token(role, property_name, "number")
        try:
            result = Decimal(str(value))
        except (InvalidOperation, ValueError) as error:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/{property_name}") from error
        if not result.is_finite():
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/{property_name}")
        return result
