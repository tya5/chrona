# Schema inventory

`schema-inventory-v0.1.yaml` is the exact machine-checked lifecycle index.
Only `live` entries are authorable current contracts. `transitioning` entries
are migration-only and record their successor and removal slice.

| Kind | Live schema |
| --- | --- |
| actual-intake-batch | actual-intake-batch-v0.2.schema.yaml |
| actual-set | actual-set-v0.3.schema.yaml |
| automation-result | automation-result-v0.1.schema.yaml |
| color-scheme | color-scheme-v0.2.schema.yaml |
| command-request | command-request-v0.2.schema.yaml |
| layout-profile | layout-profile-v0.4.schema.yaml |
| icon-catalog | icon-catalog-v0.4.schema.yaml |
| theme-asset-source | theme-asset-source-v0.1.schema.yaml |
| profile-package | profile-v0.3.schema.yaml |
| project | project-v0.7.schema.yaml |
| render-context | render-context-v0.13.schema.yaml |
| review-detail-profile | review-detail-profile-v0.1.schema.yaml |
| inspection-scene | scene-v0.7.schema.yaml |
| snapshot-ref | snapshot-ref-v0.2.schema.yaml |
| store-config | store-config-v0.1.schema.yaml |
| summary-profile | summary-profile-v0.2.schema.yaml |
| theme | theme-v0.13.schema.yaml |
| derived-theme | theme-v0.14.schema.yaml |
| view | view-v0.14.schema.yaml |

The v0.3 icon catalog remains readable during migration to v0.4 and is not
reinterpreted. New Theme asset imports emit v0.4 catalogs; the importer
normalizes glyph paths and pattern tiles, verifies density, and preserves the
source SPDX license and complete notice.

Theme v0.11/v0.12 remain readable during the v0.13/v0.14 migration. The
successor pair adds Theme glyph and pattern catalogue references while keeping
the referenced geometry in the pinned catalogue closure.

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
`render-context-v0.9.schema.yaml` and its v0.10 successor bind immutable Project and presentation
references, viewport, locale, measured font assets, and one declared target.
`layout-profile-v0.4.schema.yaml` defines the current intent-oriented composition
grammar. `review-detail-profile-v0.1.schema.yaml` owns selected group descriptions,
milestone IDs, and source-labelled review detail.
