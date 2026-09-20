# M23 Review Detail final reuse/release review — 2026-09-20

**Disposition:** Pass

## Sequence and published checkpoints

M23 followed the design-first publication gate. D23 completed and published at
`3d8d37d` before I23 began. Generic implementation published at `8840289`. A23 then
found the duplicated Preset slot-source enum; work paused until the design addendum
published at `f6d8dd3`. Visual inspection found an adapter Theme-role defect, fixed with
regression evidence at `56b6801`. Controller Z acceptance published at `837fffa`.
The final consistency pass found missing roadmap ownership and published that design
closure at `a679f37` before this final review.

## Acceptance evidence

- The Review Detail Profile schema and semantic resolver reject duplicate identifiers,
  non-rectangular observation cells, missing provenance, unknown groups, and unknown,
  unselected, or non-Point milestone references.
- Required/optional slot binding is deterministic. Required missing content and required
  overflow diagnose with owned source IDs.
- Group explanations, observation cells/provenance, and milestone entries are completed
  Scene primitives. SVG receives no Detail resource and performs no panel layout.
- Legend authority remains `presentation-settings/v0.2.detail.legend`; M23 adds no
  parallel legend configuration.
- Project and Review Projection remain authoritative for milestone title/date. Literal
  observation rows remain read-only presentation evidence and never become Actual,
  summary metrics, or scheduler input.
- A profile-independent render is byte-identical through the extended path.
- The Controller Z SVG reproduces byte-for-byte from YAML, its raster check reports zero
  overflow, and its PNG passed visual review.
- `python -m pytest -q`: 246 passed; two existing `jsonschema.RefResolver`
  deprecation warnings remain non-failing.
- `timeline-design/docs/fixtures/run_conformance.py`: every stage passes, including the
  Review Detail and five-positive-case Presentation Settings/Preset validators.

## Reuse classification

| Change | Classification | Reuse result |
|---|---|---|
| `review_detail.py` | Shared presentation service | Generic schema/semantic resolution; no sample identity. |
| `presentation_scene.py` | Shared Scene builder | Reuses measured text, Layout slots, Theme roles, source metadata, and stable ordering. |
| `presentation_svg.py` | Output adapter | Serializes completed primitives only; no Detail parsing or geometry. |
| CLI/review normalization | Adapter boundary | Adds an optional profile input and binds it before Scene construction. |
| Controller Z YAML/SVG/PNG | Acceptance resource | Exercises only public generic resources and paths. |

No M23 change is experimental and no later milestone needs a parallel model. Date-only
Core, Project, Schedule, Actual, View, Style, summary metric, and revision authority are
unchanged.

## Release decision

M23 is complete for the declared SVG capability. Raster is acceptance evidence, not a
new published output capability. PDF, interactive detail editing, workflow status,
automatic health inference, and supplier-system ingestion remain outside this milestone.
