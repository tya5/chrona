# Issues #360, #362, and #361 — Font Closure and Japanese Corpus Design Plan

**Status:** Proposed

## Purpose and dependency order

This programme corrects the font distribution and closure policy before adding
Japanese corpus evidence.  The delivery order is intentionally strict:

```text
#360 small default + opt-in CJK resource boundary
  -> #362 metrics-only SVG closure and target-local font-byte policy
    -> #361 Japanese corpus/gallery evidence
```

The order prevents a Japanese example from becoming a special-case asset
reader, and prevents a metrics-only Context from depending on a font packaging
mechanism that has not been defined.  Each completed phase is published before
the next phase begins.

## Published facts

- `chrona` currently force-includes two static Noto Sans CJK JP TTF files and
  their metrics into its primary wheel.  The code path that supplies a draft
  default also hard-codes that family and its resource names.
- The current `declared-metrics-v2` schema requires both metrics and font bytes
  for every face.  `FontMetrics` resolves both together, and the materializer
  copies both into every snapshot.
- Layout consumes font advances, ascent, descent, and cap height; completed SVG
  serialization does not load font bytes.  PNG/PDF adapters do load and
  identity-pin those bytes.
- The public corpus is a generic materializer contract.  Gallery pages consume
  committed corpus SVGs as read-only documentation; they do not resolve fonts
  or become a second rendering path.

## Design questions to close before implementation

1. Define a distributable optional-resource package rather than pretending that
   a Python extra can selectively change the contents of the primary wheel.
   The selected solution must let `pip install chrona[fonts-cjk]` acquire an
   independently versioned OFL CJK provider and must work from an installed
   wheel, not only from this checkout.
2. Define a typed resource locator for a font metric payload and an optional
   font-byte payload.  It must resolve local Context files, primary packaged
   defaults, and an installed resource provider without an adapter-specific
   path convention or host-font lookup.
3. Separate metric closure from byte closure.  SVG must validate and consume
   pinned metrics alone; PNG/PDF must require the declared, identity-pinned
   bytes.  Materialization must reject draft substitution and copy only bytes
   needed by the declared target.
4. Define `missingFont: substitute` as a draft-only measurement policy with a
   structured warning, including its exact fallback face, source family,
   codepoints, and text.  It must never turn an immutable Context or corpus
   slide into permissive evidence.
5. Define the default descriptor, generic CSS fallback, and one-command font
   importer without putting named font knowledge in product code or bypassing
   immutable identities.
6. Define a Japanese Controller Z evidence slice whose CJK dependency is
   explicit in its Context/CI setup and whose gallery treatment remains a
   normal read-only corpus consumer.

## Planned design work

### D360-1 — Font resource distribution and descriptor contract

Publish an English design that chooses a small OFL Latin Regular/Bold primary
default and an independently packaged JP-only Noto Sans CJK provider.  It must
specify package identity, descriptor discovery, versions, resource layout,
license/notice provenance, and the `chrona[fonts-cjk]` dependency relation.
The primary package must stay below the issue's 5 MB wheel gate without CJK.

The descriptor is the same declared metrics document an author can use.  The
core loads a selected default descriptor as data; it has no hard-coded family,
weight, or filename.  The design also specifies how the Theme's measured
family and declared generic CSS fallback are represented and serialized.

### D362-1 — Target-local font-byte closure

Publish the Context schema and typed runtime design.  Every selected face has
required metrics identity and optional byte locator/identity.  Resolution
returns a metric face independently from a raster font file.  Target admission
is explicit: SVG requires metrics; PNG/PDF require bytes.  The design names
the public diagnostics, exact materializer copy rules, artifact-identity
rules, and the rejected `substitute` materialization boundary.

### D360-2 — Import and authoring contract

Specify `chrona font import` as a deterministic authoring command.  It accepts
TTF/OTF/TTC input plus family/weight/index/axis selection, emits a static or
copied face where required, metrics JSON, and atomically updates a local
descriptor with content identities.  It does not import host fonts at render
time.  The design covers collision handling, existing descriptor entries,
licensing messaging, and output paths on all supported operating systems.

### D361-1 — Japanese corpus and gallery evidence

Specify a new `controller-z-ja` corpus root (or an equally isolated adjacent
set) with Japanese board text and `ja-JP` Context locale.  It reuses a normal
Controller Z semantic register; no translated vocabulary becomes a semantic
fork.  Its Context pins the CJK provider descriptor.  The target matrix
separates always-reproducible SVG evidence from PNG/PDF evidence requiring the
installed CJK extra.  Gallery metadata links the committed SVG as it does for
every other corpus slide.

### D360/362/361-2 — Whole-architecture review

Review the design against the immutable Context, Layout/Scene/adapters,
materializer, package-resource, authoring, corpus, and gallery boundaries.
The review must explicitly reject: host-font lookup, network asset fetches,
renderer-local fallback policy, Scene font measurement, a gallery asset
resolver, and a CJK-only exception in the materializer.

## Implementation-plan requirements

The subsequent implementation plan must divide work into independently
reviewable/publication slices:

1. provider-neutral font locator and metrics/bytes type separation with schema
   migration and structural tests;
2. small primary default, packaged descriptor, generic SVG fallback, optional
   CJK provider build/install/wheel gates, and corpus default regeneration;
3. target-local raster enforcement, draft substitution warnings, snapshot copy
   policy, and public diagnostics;
4. deterministic font-import command, documentation, and cross-platform tests;
5. Japanese corpus/gallery fixture, explicit extra installation in CI, generated
   SVG/target evidence, and release review.

No slice may leave an existing public materializer Context unrenderable.  A
temporary compatibility reader is not allowed: all public Contexts migrate
atomically to the accepted contract.

## Acceptance and release gates

- primary installed wheel is under 5 MB and contains only the declared Latin
  default; the optional CJK provider installs through the documented extra;
- default and CJK descriptors are data-driven and identity-pinned;
- SVG works from a metrics-only Context and serializes the declared generic
  fallback; PNG/PDF reject missing byte assets deterministically;
- draft substitution reports a structured warning, while materialization
  rejects it;
- the importer produces a usable identity-pinned descriptor without manual
  descriptor editing;
- every declared corpus slide reproduces through the public materializer, with
  the CJK extra explicitly installed where its target requires bytes;
- focused tests per slice, full pytest, conformance/structural gates,
  installed-wheel smoke, wheel-size check, generated SVG diff review, and all
  Ubuntu/macOS/Windows CI jobs pass before closing the issues.

