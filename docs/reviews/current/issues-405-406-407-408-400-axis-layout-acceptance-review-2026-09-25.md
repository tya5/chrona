# Axis Layout Acceptance Review (#405, #406, #407, #408; #400 axis scope)

**Status:** accepted
**Date:** 2026-09-25
**Design and plan lineage:** `1b4431dd`, `5b52f0db`, `c414a973`, `45c0b6ee`,
`603e015f`, `dafed01c`, and the published I2/I3 amendments through
`65a795a2`.
**Implementation:** `f7826dde`
**Release repairs:** `f078313f`, `29c258d9`

## Scope and disposition

This review accepts the complete axis contract work for #405, #406, #407, and
#408, plus the axis-label visible-failure portion of #400.  It does **not**
close #400: its row-density classification, draft/immutable path policy, and
finite failure-registry publication remain separately required work.

| Requirement | Evidence | Result |
| --- | --- | --- |
| Roles are declared rather than inferred from a level's array position | View v0.17 `axis.tiers` normalizes to typed `AxisTier`; Layout composes independently declared `band`, `grid-major`, `grid-minor`, and `labels` placements. | Pass (#405) |
| One tier has one effective unit and configurable cadence | `every` is carried into typed placement outcomes and drives deterministic interval selection. | Pass (#405, #406) |
| Author-reachable automatic fitting exists | `unit: auto` is normalized as an ordered candidate set; Layout measures candidates, records its choice, and applies the declared label policy. | Pass (#406) |
| Half-year and fiscal calendars are deterministic | `half` is a finite unit; fiscal start month comes only from the selected Project calendar, with no locale or title inference. | Pass (#407) |
| Label vocabulary belongs to the author | finite per-unit label forms are validated by the View schema and formatted in Layout, rather than selected by host locale. | Pass (#408) |
| An omitted fitting label cannot become silent loss | Layout records candidate IDs and reasons, emits `W_LAYOUT_AXIS_LABEL_THINNED` and `W_LAYOUT_AXIS_DENSITY`, and preserves typed interval disposition. `diagnose` raises `E_PRESENTATION_AXIS_OVERFLOW`. | Pass (#400 axis scope) |
| Semantic visual targets retain the authority boundary | Layout resolves axis band/label targets against its typed placement maps; Scene projects completed primitives and does not parse axis placement identities. | Pass |

## Verification evidence

* Axis, placement, Scene-projection, and public-materializer focused tests
  passed locally, including visible diagnostics for Orion and the HALCYON
  replan baseline.
* Regenerated public corpus evidence covers 19 slides across Aster SSD,
  Controller Z (including the Japanese fiscal calendar), HALCYON, and Orion.
* `python conformance/run_conformance.py`: PASS, including example inventory,
  temporal fixtures, revision-store conformance, vocabulary, traceability, and
  Chrona conformance.
* `tools/diagnostic_inventory.py` regenerated its checked diagnostic inventory.
* `git diff --check`: pass before publication.
* GitHub Actions run [36116328790](https://github.com/tya5/chrona/actions/runs/36116328790)
  passed for the released Windows-portability repair `29c258d9`.

## Architecture review

The result preserves the Project -> View -> Layout -> Scene -> adapter chain.
Project owns calendar facts; View owns finite author intent; Layout owns metric
selection, interval construction, fitting, suppression, diagnostics, and
completed geometry; Scene only projects those placements; adapters serialize
the completed scene.  In particular, neither Scene nor an output adapter can
compute a tick, choose a label coordinate, route an axis visual, or manufacture
a density warning.  This keeps #400's remaining cross-failure policy work in
Layout, where it can classify failures without creating a renderer-specific
exception path.

## Release disposition

#405, #406, #407, and #408 meet their stated acceptance boundary and may be
closed.  Keep #400 open until its non-axis requirements have their own design,
implementation, materializer evidence, and acceptance review.
