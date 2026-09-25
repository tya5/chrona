# Design Correction — Fit-Policy Ingress Scope (#449)

**Status:** accepted correction to
`issue-449-visible-fit-failure-policy-design-2026-09-25.md`.

## Finding

The initial I449-1 implementation plan said that no live resource may contain
the token `diagnose`.  Source inspection shows that this would incorrectly
migrate `environment.fontMetrics.missingFont: diagnose`.  That value names a
missing-resource policy, which #449 expressly leaves render-stopping.  It is
not a fit/placement disposition.

The same inspection confirms that the live View v0.18 schema owns two distinct
fit vocabularies—label/relation overflow and axis-label overflow—while Layout
Profile v0.8 owns slot overflow.  A Layout Profile migration alone cannot
remove the old fit meaning from live View resources.

## Correction

The atomic ingress migration is:

| Resource | Retired version | New live version | Fit change |
| --- | --- | --- | --- |
| Layout Profile | v0.8 | v0.9 | slot `diagnose` → `visible-overflow` |
| View | v0.18 | v0.19 | label/relation/axis `diagnose` → `visible-overflow` |
| Render Context | v0.16 | unchanged | `missingFont: diagnose` remains unchanged |

The migration criterion is therefore: **no live fit/placement declaration may
use `diagnose`**.  Historical schemas may retain it as historical evidence,
and live missing-resource policy may retain it with its existing meaning.

`visible-overflow` is added only to the finite fit/placement enums.  It must
not be accepted as a font, resource, integrity, or generic diagnostic mode.
Every public Context must point to the migrated Layout Profile and View
resources in the same release; no v0.8 or v0.18 compatibility reader remains.

## Consequence

I449-1 must add `view-v0.19.schema.yaml`, update the resource registry and
schema inventory, migrate every live View and Layout Profile, and add negative
tests for both retired fit identities.  It must not alter `missingFont`
schemas, closure policy, or tests.  The I449 architecture review's boundary
conclusions remain unchanged.
