# Design: Presentation vocabulary coverage (#375)

**Decision:** Accepted.

## 1. Purpose and boundaries

`tools/presentation_coverage.py` will generate
`docs/gallery/presentation-coverage.md`: a deterministic, non-gating curation
backlog for declared presentation vocabulary and completed presentation
evidence.  It is not a schema validator, render gate, authoring input, or a
replacement for the semantic `corpus_coverage.py` report.

The report has three deliberately separate facts:

1. **Declared vocabulary** — a finite `const`/`enum` value from a live View,
   Layout Profile, Theme, or Color Scheme schema appears at the corresponding
   path in a resource reachable from a declared corpus slide.
2. **Placed slot** — a completed Scene surface lists a Layout slot with that
   source.
3. **Realized slot** — at least one completed Scene primitive is explicitly
   bound to that placed slot.

No result is inferred by parsing SVG attributes, Scene identifiers, primitive
coordinates, or source-code role literals.

## 2. Inputs and version policy

The tool discovers every `regression-corpus` manifest and every declared slide
context.  For each context it reads only the locally declared `view`, `layout`,
`theme`, and `colorScheme` resource addresses and its declared `expectedScene`.
It rejects missing/escaping/non-local presentation references or missing Scene
evidence with a stable tool error.  It does not read unrelated project inputs.

The schema inventory is the version authority.  At execution it selects the
single `live` schema for each of `view`, `layout-profile`, `theme`, and
`color-scheme`; the resource document version must match that schema.  This
supersedes the stale v0.12/v0.5 names in #375's original proposal and prevents
the tool from measuring retired grammar.

Finite vocabulary extraction follows the established direct-schema traversal:
`const` and `enum` leaves are collected through properties, arrays, maps, and
applicators, with JSON-pointer-like paths.  Open maps and values inferred only
by implementation policy remain out of scope.

## 3. Scene completion correction

The initial `scene-v0.1` contract exposes surface slots and completed
primitives, but has no primitive-to-slot link.  A consumer can therefore see
that a slot was allocated but cannot truthfully determine whether it emitted
content without reimplementing producer policy.  This is a design gap exposed
by #375, not a reason to parse SVG or infer containment.

I375-0 introduces `chrona/scene/v0.2`.  Each primitive has a required typed
`slotId` that refers to exactly one slot on its surface.  Layout carries slot
ownership with placement data; Scene projection transfers it without routing,
measurement, geometry containment, or purpose-based classification.  The
serializer validates the reference.  `scene-v0.1` remains historical evidence
in the schema inventory; all current corpus evidence and the fixture adapter
move to v0.2.  No compatibility reader is retained: consumers selecting the
current coverage contract must consume v0.2.

This is a public-contract correction owned by #375 because it is the first
consumer that requires the missing fact.  It does not reopen #385's completed
v0.1 publication acceptance.

## 4. Report model

Rows use stable `(contract, schema path, JSON value)` identity and show sorted
declared slide identifiers as evidence.  Slot rows use `(slot source)` identity
and show sorted slide identifiers separately for declaration, placement, and
realization.  The report has explicit uncovered sections for finite vocabulary
and for declared-but-never-realized slot sources.  It also reports the current
Scene contract version and all source artifact paths, making a missing or stale
input reviewable rather than silently ignored.

Every declared corpus slide gains `expectedScene` evidence generated through
the public materializer.  The tool reads only these checked-in JSON documents;
it does not invoke rendering.  `--check` compares report bytes and verifies
the complete expected-Scene inventory.  The gallery index links this report as
the presentation selector beside the semantic report.

## 5. Architecture alignment review

| Boundary | Owner | #375 rule |
| --- | --- | --- |
| Context closure | manifests and Context resource references | Tool reads declared presentation resources only. |
| Layout placement | Layout | Slot ownership originates with Layout placement values. |
| Scene | Scene projection/serializer | Carries completed slot binding and validates references; no coverage policy. |
| Coverage | read-only tool | Aggregates serialized documents and schemas only. |
| Gallery | generated documentation | Links the curation result; does not calculate it. |
| #382 | corpus design | Consumes the resulting uncovered overlay vocabulary; is not implemented here. |

The design avoids a second vocabulary registry, an SVG parser, a Scene builder
import, and a coverage condition in CI.  It preserves the existing
closure → View → Layout → Scene → adapter direction.

## 6. Acceptance

* A complete checked-in v0.2 Scene set exists for every declared corpus slide.
* The report is byte deterministic, `--check`-verified, and linked from the
  gallery index.
* It identifies finite live-schema values and declared/placed/realized slot
  evidence without SVG or producer-code parsing.
* `milestones`, `annotations`, `group-details`, and `observations` are named
  correctly from evidence rather than a hand-maintained list.
* The report is non-gating; #382 is able to use it to select overlay work.
