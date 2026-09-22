"""Schema-accepted, immutable runtime contracts for presentation closures."""

from chrona.presentation.contracts.resources import (
    ClosureIdentity,
    ColorSchemeContract,
    ContractError,
    LayoutProfileContract,
    ProjectContract,
    RenderContextContract,
    ResolvedThemeContract,
    ResourceContract,
    ThemeContract,
    ViewContract,
    freeze,
    parse_contract,
)

__all__ = [
    "ClosureIdentity", "ColorSchemeContract", "ContractError", "LayoutProfileContract",
    "ProjectContract", "RenderContextContract", "ResolvedThemeContract", "ResourceContract", "ThemeContract",
    "ViewContract", "freeze", "parse_contract",
]
