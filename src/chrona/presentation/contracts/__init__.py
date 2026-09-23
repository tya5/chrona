"""Schema-accepted, immutable runtime contracts for presentation closures."""

from chrona.presentation.contracts.resources import (
    ActualSetContract,
    AuthoringWorkspaceContract,
    ClosureIdentity,
    ColorSchemeContract,
    ContractError,
    SchemaContractError,
    LayoutProfileContract,
    IconCatalogContract,
    IconEntry,
    IconSource,
    PresentationPresetContract,
    ProfilePackageContract,
    ProjectContract,
    RenderContextContract,
    RenderEnvironment,
    RenderTarget,
    TypesetterIdentity,
    ResourceReference,
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
    "ActualSetContract", "AuthoringWorkspaceContract", "ClosureIdentity", "ColorSchemeContract", "ContractError", "SchemaContractError", "LayoutProfileContract", "IconCatalogContract", "IconEntry", "IconSource", "PresentationPresetContract", "ProfilePackageContract",
    "ProjectContract", "RenderContextContract", "RenderEnvironment", "RenderTarget", "TypesetterIdentity", "ResourceReference", "ResolvedThemeContract", "ResourceContract", "ThemeContract",
    "ReviewDetailProfileContract", "SnapshotRefContract", "SummaryProfileContract", "ViewContract", "freeze", "parse_contract",
]
