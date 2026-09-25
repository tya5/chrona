"""Validation-only aggregation for a declared presentation resource set."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from chrona.presentation.contracts.resources import (
    ClosureIdentity,
    ContractError,
    ResourceContract,
    SchemaContractError,
    SchemaErrorExplanations,
    explain_resource_schema_errors,
    parse_contract,
)


@dataclass(frozen=True)
class PresentationDiagnostic:
    """One ordered ingress finding, before a render closure can exist."""

    code: str
    resource_kind: str
    resource_identity: str
    pointer: str
    rule: str | None
    message: str
    phase: str


@dataclass(frozen=True)
class PresentationResourceSource:
    """One resource whose membership in the ingress set is already known."""

    identity: ClosureIdentity
    value: Mapping[str, object]


@dataclass(frozen=True)
class PresentationContractCollection:
    """Schema-safe contracts and all independent ingress findings.

    ``contracts`` is deliberately not a closure: it permits collection to
    continue after a sibling fails, but cannot be rendered or resolved.
    """

    contracts: tuple[ResourceContract, ...]
    diagnostics: tuple[PresentationDiagnostic, ...]


class PresentationIngressRejected(ValueError):
    """The known presentation resource set has one or more ingress findings."""

    def __init__(self, diagnostics: tuple[PresentationDiagnostic, ...]) -> None:
        super().__init__("E_PRESENTATION_REJECTED")
        self.diagnostics = diagnostics


def collect_presentation_contracts(
    sources: Sequence[PresentationResourceSource],
) -> PresentationContractCollection:
    """Validate every declared resource in declaration order.

    Schema-invalid values never reach contract semantics.  Schema-valid
    siblings continue independently, so a View error cannot hide a Theme
    error.  The source order is the declared closure order; schema errors are
    already pointer/rule/message ordered by ``explain_schema_errors``.
    """
    contracts: list[ResourceContract] = []
    diagnostics: list[PresentationDiagnostic] = []
    schema_reports: list[tuple[PresentationResourceSource, SchemaErrorExplanations | None]] = []
    for source in sources:
        schema_reports.append((source, explain_resource_schema_errors(source.identity, source.value)))

    schema_error_count = sum(report.error_count for _source, report in schema_reports if report is not None)
    for source, report in schema_reports:
        if report is not None:
            violations = (report.legacy,) if schema_error_count == 1 else report.aggregate
            diagnostics.extend(PresentationDiagnostic(
                "E_RESOURCE_SCHEMA", source.identity.kind, source.identity.id,
                violation.pointer, violation.rule, violation.message, "schema",
            ) for violation in violations)
            continue
        try:
            contracts.append(parse_contract(source.identity, source.value))
        except SchemaContractError as error:
            violation = error.violation
            diagnostics.append(PresentationDiagnostic(
                "E_RESOURCE_SCHEMA", source.identity.kind, source.identity.id,
                violation.pointer if violation is not None else error.source_ref,
                violation.rule if violation is not None else None,
                violation.message if violation is not None else str(error), "schema",
            ))
        except ContractError as error:
            diagnostics.append(PresentationDiagnostic(
                error.diagnostic_id, source.identity.kind, source.identity.id,
                "/", None, error.detail or error.diagnostic_id, "contract",
            ))
    return PresentationContractCollection(tuple(contracts), tuple(diagnostics))
