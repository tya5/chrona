"""Schema-accepted, immutable runtime contracts for presentation closures."""

from chrona.presentation.contracts.resources import (
    ActualSetContract,
    ClosureIdentity,
    ColorSchemeContract,
    ContractError,
    SchemaContractError,
    LayoutProfileContract,
    ProfilePackageContract,
    ProjectContract,
    RenderContextContract,
    ResolvedThemeContract,
    ResourceContract,
    ReviewDetailProfileContract,
    SnapshotRefContract,
    SummaryProfileContract,
    ThemeContract,
    ViewContract,
    freeze,
    parse_contract,
)

__all__ = [
    "ActualSetContract", "ClosureIdentity", "ColorSchemeContract", "ContractError", "SchemaContractError", "LayoutProfileContract", "ProfilePackageContract",
    "ProjectContract", "RenderContextContract", "ResolvedThemeContract", "ResourceContract", "ThemeContract",
    "ReviewDetailProfileContract", "SnapshotRefContract", "SummaryProfileContract", "ViewContract", "freeze", "parse_contract",
]
