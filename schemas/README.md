# Schema inventory

`schema-inventory-v0.1.yaml` is the exact machine-checked lifecycle index.
Only `live` entries are authorable current contracts. `transitioning` entries
are migration-only and record their successor and removal slice.
The table below mirrors the `live` entries; the inventory is the authority.

Historical schema files that nothing reads any more are not kept here. They
live in [`docs/archive/schemas/`](../docs/archive/schemas/README.md), outside
this directory, so the wheel does not ship them; version control history is the
record.

| Kind | Live schema |
| --- | --- |
| builtin-axis-name-tables | axis-name-tables-v0.1.schema.yaml |
| actual-intake-batch | actual-intake-batch-v0.2.schema.yaml |
| actual-set | actual-set-v0.3.schema.yaml |
| authoring-workspace | authoring-workspace-v0.1.schema.yaml |
| authoring-command | authoring-command-v0.1.schema.yaml |
| authoring-command-result | authoring-command-result-v0.1.schema.yaml |
| automation-result | automation-result-v0.2.schema.yaml |
| color-scheme | color-scheme-v0.2.schema.yaml |
| command-request | command-request-v0.3.schema.yaml |
| layout-profile | layout-profile-v0.10.schema.yaml |
| icon-catalog | icon-catalog-v0.5.schema.yaml |
| theme-asset-source | theme-asset-source-v0.2.schema.yaml |
| presentation-resource-foundation | presentation-resource-v0.1.schema.yaml |
| schema-part-common | common-v0.1.schema.yaml |
| schema-part-graphics | graphics-v0.1.schema.yaml |
| presentation-preset | presentation-preset-v0.1.schema.yaml |
| builtin-preset-library | preset-library-v0.2.schema.yaml |
| example-registry | example-registry-v0.1.schema.yaml |
| presentation-materialization-receipt | presentation-materialization-receipt-v0.1.schema.yaml |
| profile-package | profile-v0.3.schema.yaml |
| project | project-v0.7.schema.yaml |
| render-context | render-context-v0.17.schema.yaml |
| review-detail-profile | review-detail-profile-v0.1.schema.yaml |
| inspection-scene | scene-v0.7.schema.yaml |
| revision-store-resource-reference | revision-store-resource-ref-v0.1.schema.yaml |
| revision-store-resource-reference | revision-store-resource-ref-v0.2.schema.yaml |
| snapshot-ref | snapshot-ref-v0.3.schema.yaml |
| store-config | store-config-v0.1.schema.yaml |
| summary-profile | summary-profile-v0.2.schema.yaml |
| theme | theme-v0.15.schema.yaml |
| derived-theme | theme-v0.16.schema.yaml |
| view | view-v0.28.schema.yaml |
| schema-part-vocabulary | vocabulary-v0.1.schema.yaml |

The three `schema-part-*` entries, `presentation-resource-foundation` and
`revision-store-resource-reference` are shared parts:
other live schemas reference their definitions by URN (`urn:chrona:common-v0.1`,
`urn:chrona:vocabulary-v0.1`, `urn:chrona:graphics-v0.1`, and the two older parts), so
a pattern, enum or drawing shape is written once. A part's definitions are frozen by
digest in the inventory. Spec 56 section 7 gives the rules, and
`python -m tools.schema_equivalence --base-rev origin/main` is the gate that proves a
change keeps every schema's accepted set.

`revision-store-resource-reference` has two live files: v0.1 stays published because the transitioning
Command Request v0.2, Automation Result v0.1 and Snapshot Reference v0.2 reference its URN and `extensions/profiles.py` and the
revision-store conformance fixtures validate against it directly, and v0.2 constrains `address` to the strict
`storeAddress` definition of `common` (#710). A kind adopts v0.2 only through its own version bump.

The v0.3 icon catalog remains readable during migration to v0.4 and is not
reinterpreted. New Theme asset imports emit v0.4 catalogs; the importer
normalizes glyph paths and pattern tiles, verifies density, and preserves the
source SPDX license and complete notice.

Theme v0.15 is the authored contract and v0.16 its derived inheritance form.
Theme v0.11/v0.12/v0.13/v0.14 are archived after migration; copied or standalone
resources using those versions receive the unsupported-version diagnostic.

Scene v0.6 remains readable during the v0.7 migration. The successor records
Layout-completed pattern tile geometry and paint without resolving Theme or
catalogue references in Scene or adapters.

# Project Schema v0.3 Notes

The structural schema intentionally does not encode every semantic rule.

Rules requiring semantic validation include:

- object profile determines whether schedule is Point or Span;
- fixed span requires `start < end`;
- dependency endpoint must exist on the referenced object type;
- WorkPeriod calendar must resolve;
- scheduled amount must be positive;
- fixed-target dependency is a validation condition;
- referenced IDs must exist;
- parent references form an acyclic forest and explicit WBS codes are unique;
- a rollup has descendants and derives their completed schedule envelope;
- calendar exceptions must not contain contradictory duplicate dates.

Schema validation is therefore stage 1, not full Core conformance.

## Presentation schemas

`presentation-resource-v0.1.schema.yaml` supplies shared envelope and reference
definitions for the listed Presentation resources. The current
`render-context-v0.17.schema.yaml` binds immutable Project and presentation
references, viewport, locale, measured font assets, and one declared target.
`layout-profile-v0.10.schema.yaml` defines the current intent-oriented composition
grammar. `review-detail-profile-v0.1.schema.yaml` owns selected group descriptions,
milestone IDs, and source-labelled review detail.
