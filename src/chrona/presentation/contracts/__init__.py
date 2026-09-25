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
    IconPath,
    IconRasterSource,
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
    validate_icon_catalog_entry,
    explain_schema_errors,
    freeze,
    parse_contract,
)
from chrona.presentation.contracts.diagnostics import (
    PresentationContractCollection,
    PresentationDiagnostic,
    PresentationResourceSource,
    collect_presentation_contracts,
)

__all__ = [
    "ActualSetContract", "AuthoringWorkspaceContract", "ClosureIdentity", "ColorSchemeContract", "ContractError", "SchemaContractError", "LayoutProfileContract", "IconCatalogContract", "IconEntry", "IconPath", "IconRasterSource", "PresentationPresetContract", "ProfilePackageContract",
    "ProjectContract", "RenderContextContract", "RenderEnvironment", "RenderTarget", "TypesetterIdentity", "ResourceReference", "ResolvedThemeContract", "ResourceContract", "ThemeContract",
    "ReviewDetailProfileContract", "SnapshotRefContract", "SummaryProfileContract", "ViewContract", "freeze", "parse_contract", "validate_icon_catalog_entry", "explain_schema_errors",
    "PresentationContractCollection", "PresentationDiagnostic", "PresentationResourceSource", "collect_presentation_contracts",
]
