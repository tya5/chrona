# Design Correction — Annotation Route Policy Versioning (#413)

**Status:** Design correction complete; amends
`issues-414-402-413-semantic-visual-realization-design-2026-09-25.md`.

## Trigger

The accepted design gives annotation leaders their own finite route limits.
The live `chrona/layout-profile/v0.6` grammar has only `relationRouting`; adding
`annotationRouting` to that version would silently change the meaning of a
closed resource contract and leave the old required closure identity inaccurate.

## Correction

Create `chrona/layout-profile/v0.7` as the only live Layout Profile contract.
It retains v0.6's reviewed surface grammar and adds required finite
`annotationRouting.maxBends` and `annotationRouting.maxDetourRatio` under
`reviewSurface`.  Its values are validated by the same bounded numeric rules
as relation routing, but are modelled and consumed separately.

Migrate every shipped Layout Profile, Render Context closure expectation,
schema inventory entry, packaging inventory, fixture, conformance resource, and
coverage input atomically to v0.7.  Delete the v0.6 runtime/schema dispatch;
do not retain a compatibility reader or silently default missing annotation
routing.  A user who supplies a v0.6 Layout Profile receives the ordinary
unsupported-resource diagnostic and must migrate explicitly.

Theme v0.10 and View v0.17 need no syntax version change: their roles and
column-source vocabulary already admit the P3 contract.  New Theme role
bindings are resource data, while typed normalizer/placement values are an
implementation closure, not View syntax.

## Ownership and acceptance

The Profile owns only finite route-quality limits. Layout owns route selection,
quality assessment, marker geometry completion, and diagnostics. Scene projects
the completed path and marker; adapters serialize it unchanged.

Acceptance requires negative v0.6 closure/schema evidence, independent
annotation/dependency route-policy tests, migration of every public resource,
and a materialized corpus slide with an explanatory-arrow leader.
