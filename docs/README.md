# Chrona Design Documentation

| Directory | Contents |
|---|---|
| `specification/` | Active numbered normative specifications (`00`–`30`, `32`–`33`) and supplemental design specifications; retired IDs remain reserved |
| `guides/` | Task-oriented user and maintainer guidance |
| `decisions/` | Architecture Decision Records (ADRs) |
| `research/` | Non-normative investigations, including federation research |
| `planning/active/` | Current documentation, remediation, and coverage plans |
| `reviews/current/` | Current acceptance and release reviews |
| `archive/` | Completed point-in-time plans and reviews |

Machine-readable contracts live in [`../schemas/`](../schemas/) and executable
compatibility fixtures and runners live in [`../conformance/`](../conformance/).

For how `src/chrona` is arranged and which way its dependencies point, see the
[source architecture guide](guides/source-architecture.md).

Start with the [task-oriented specification guide](specification/README.md). Numbers are
stable document identifiers rather than a mandatory reading order. Review records
describe their stated historical scope; they do not supersede the corresponding
normative specification.

For the current immutable review entry and its reusable resource split, see the
[render-review YAML layout guide](guides/render-review-yaml-layout.md).

Repository topology and packaging are owned by
[Specification 32](specification/32-repository-layout-and-packaging.md). Its migration
is governed by the
[repository layout remediation plan](planning/active/repository-layout-remediation-plan-2026-09-20.md)
and [ADR-0022](decisions/ADR-0022-product-oriented-repository-layout.md).

The active M24 successor for intent-oriented, low-magic-number authoring is governed by
the [declarative layout language plan](planning/active/declarative-layout-language-plan-2026-09-20.md).
