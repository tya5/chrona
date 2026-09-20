# Chrona Design Documentation

| Directory | Contents |
|---|---|
| `specification/` | Numbered normative specifications (`00`–`32`) and supplemental design specifications |
| `decisions/` | Architecture Decision Records (ADRs) |
| `research/` | Non-normative investigations, including federation research |
| `planning/active/` | Current documentation, remediation, and coverage plans |
| `reviews/current/` | Current acceptance and release reviews |
| `archive/` | Completed point-in-time plans and reviews |

Machine-readable contracts live in [`../schemas/`](../schemas/) and executable
compatibility fixtures and runners live in [`../conformance/`](../conformance/).

Start with [the documentation plan](planning/active/design-documentation-plan.md), then read
the numbered specifications in order. Review records describe their stated historical
scope; they do not supersede the corresponding normative specification.

Repository topology and packaging are owned by
[Specification 32](specification/32-repository-layout-and-packaging.md). Its migration
is governed by the
[repository layout remediation plan](planning/active/repository-layout-remediation-plan-2026-09-20.md)
and [ADR-0022](decisions/ADR-0022-product-oriented-repository-layout.md).
