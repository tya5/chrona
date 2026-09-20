# I3 Public Surface-Adapter Design Review

**Scope:** Restart boundary after the second I3 design correction at
`be455b796ee63957cd1b0af7fd023e6042ac543f`.
**Conclusion:** The primitive data contract and migration completion criteria that
required correction have been added to Specification 08 §5.3, the derived fixture, and
the I3 completion plan. Implementation MUST NOT start until these artifacts are
validated and published in the same revision.

## Inconsistencies found

| ID | Finding | Design cause | Correction |
|---|---|---|---|
| I3-R01 | Scene contained surface slots/rows but no surface-specific axis/tick/mark/Text primitive contract | The adapter could still reconstruct geometry | Add the core primitive set, identity, and Text payload/baseline to Specification 08 §5.3 and the derived fixture |
| I3-R02 | The scope migrated by the same I3 across table-timeline, review, and minimal was ambiguous | Core primitive migration could be mistaken for I3 completion | Plan I3-A through I3-F/V1 ordering, unmigrated families, and the completion condition for every adapter |
| I3-R03 | The failure contract for a missing Scene was only general guidance | An adapter could justify a settings fallback | Fix stable surface/primitive diagnostics and prohibited recoveries |
| I3-R04 | Existing Detail heading/subtitle templates and group opacity were absent from the I3-C completion inventory | A serializer could drop editorial wording or default opacity while still claiming Scene-only geometry | Require Scene-owned `title-text` / optional `subtitle-text` wording and complete resolved group paint-token serialization before I3-C resumes |
| I3-R05 | The normalized Scene input did not carry `unmatchedCount`, although Detail templates permit it | Scene could only consult the projection or parse coverage wording | Add a closed six-key `templateValues` map to `SurfaceContentInput` and prohibit reconstruction |

## Layer consistency

The direction `ResolvedPresentationInput → SceneSurface → SVG adapter` is fixed.
The Scene Builder owns a surface instance; the adapter only selects and serializes it.
Although core primitive families and later families are separated, both are explicitly
owned by the Scene Builder. Therefore table, review, and minimal retain no exception
for adapter-private geometry.

## Preconditions for implementation

- `validate_presentation_scene_input.py`, `validate_presentation_g2_g4_design.py`, and
  the shared-presentation validator succeed.
- The surface, diagnostic, and primitive tables in Specification 08 §5.3, the I3
  completion plan, and the derived fixture are mutually consistent.
- This design unit is published serially to GitHub `main`, and its SHA is fixed as the
  parent of I3-B.

After those conditions, the first implementation is I3-B only. Rewriting the
review/minimal adapters, connectors, annotations, and table cells is outside I3-B and
MUST NOT be implemented together with it.

## Reopening record: single-point TextLayout

After the first I3-B publication at `6412b80`, execution confirmed that
`singlePointSpanDays: 1` cannot satisfy measured axis/item-text width on a surface.
Because the existing design assigns display span to settings, an adapter cannot recover
by adding days or slot width. Specification 29, the base fixture, and the fixed-value
inventory are synchronized to a seven-day display span and an explicit overflow
diagnostic. This design correction is published before I3-B implementation is fixed.

The regression additionally found that a base-fixture change did not propagate to the
preset `base.contentIdentity`. Digest verification was added to the design validator,
and the fixture-reference synchronization is published first. TextLayout implementation
does not resume until that verification succeeds.

## Reopening record: editorial title and group paint closure

The first I3-C serializer regression exposed two omitted existing authorities: Detail
owns heading/subtitle templates, and Theme group paints own opacity. Specification 08,
Specification 30, the I3 plan, and the derived fixture now require final title wording
to enter Scene Text payloads and require the adapter to serialize the complete resolved
group paint token. This correction is published and validated before I3-C implementation
resumes.

## Reopening record: I3-F summary and entry boundaries

The I3-F pre-implementation trace found that Specification 30 required formatted
summary strings, while the Python tuple shape still allowed Scene to manufacture
`metricId: value` wording. It also found that the plan's phrase “review/minimal
summaries” conflicted with the derived fixture, where only review owns the summary
family. Specifications 08/30, the I3 plan, and the fixture now close the DTO as
`(panelId, headingText, ((metricId, formattedText), ...))`, assign summaries to review
and table only, and require an explicit resolved summary slot. The application entry
normalizes content once; the selected serializer still receives only `SceneSurface`.
This design correction must be validated and published before I3-F implementation.

## Reopening record: V1 Scene manifest

The V1 evidence trace found that Specification 08 required the temporal domain, range,
origin, and unit ratio in a Scene manifest, while the Python Scene had neither a closed
manifest DTO nor an adapter-visible scale fragment. Specification 08 §3.4,
Specification 30, the derived fixture, and the I3 plan now close one immutable manifest
shape and attach the identical scale record to each completed `SceneSurface`.

This preserves the serializer boundary: an adapter can emit target metadata without
receiving the full Scene or reconstructing scale evidence. The manifest remains derived,
non-authoritative inspection evidence and records counts rather than authoring payloads.
Implementation MUST NOT resume until this correction validates and is published as an
independent design revision.
