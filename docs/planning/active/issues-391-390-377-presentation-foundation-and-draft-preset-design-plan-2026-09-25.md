# Design Plan: Presentation capability foundation, quality evidence, and draft presets (#391, #390, #377)

**Status:** Active design planning.

## Purpose

This programme resolves three adjacent but distinct product boundaries in an
intentional order:

1. #391 defines the closed, target-neutral presentation capability ceiling and
   the ownership/fidelity rules for admitting future vocabulary.
2. #390 turns that ceiling into durable evidence: complete Scene delivery
   inspection, an external prior-art disposition matrix, and a documented
   visual review boundary.
3. #377 removes draft-render presentation boilerplate by admitting the already
   typed `presentation-preset/v0.1` at the public CLI and by shipping one
   explicit default preset.

The programme does not add a row-band, editorial design, Theme/View
inheritance, a package acquisition path, or a terse Project language.  Those
are follow-on decisions (#389, #383, #378, #148) that must consume the
published capability ceiling rather than create vocabulary incidentally.

## Verified starting point

* `main` at `28cedf71` has 21 reproducible corpus slides.  #375 supplies a
  read-only presentation-coverage report; #382 supplies real overlay, guide,
  barrier, and anchor evidence.
* Scene v0.2 has a finite rich-paint capability policy.  It currently models
  `required` and `decorative-optional` fidelity only.  Baseline profiles may
  omit the latter; adapters never select a fallback.
* `presentation-preset/v0.1`, its typed contract, safe relative-resource
  loading, and guided-workspace resolution already exist.  The public `chrona
  render` command still requires four separate presentation paths and no
  preset ships from `chrona.resources`.
* `tools/check_scene_primitive_delivery.py` currently inspects only
  `ScenePrimitive`; it cannot expose stale fields on the other Scene
  dataclasses.  There is no maintained external prior-art disposition matrix
  or required recorded visual review.

These facts, not the older issue measurements, are authoritative.  The former
19-slide counts and the claim that overlay lacks corpus evidence are obsolete.

## Design sequence

### D391-1 — Capability ceiling and ownership model

Inventory every current renderer-neutral primitive family and candidate visual
variation.  Publish a design that gives every candidate one of `admitted`,
`deferred`, or `deliberately-rejected` with a Gantt-semantic reason.  The
matrix is keyed by primitive family and semantic role exception, never Layout
slot.

The design must state one ownership rule:

* Layout owns granted space, track extent, packing, and placement geometry.
* Theme owns visual treatment within granted geometry, including typography,
  stroke, texture, and mark treatment.
* Color Scheme owns colour identity and categorical relationships.
* Scene owns completed target-neutral values; target profiles own support;
  adapters only project admitted completed values.

It must define whether and how a third `substitute` fidelity disposition can
express a semantic fallback without allowing an adapter to invent appearance.
The answer must include a finite, typed substitute declaration and a
pre-render diagnostic path, or explicitly defer the value rather than add an
uninterpreted enum.

### D390-1 — Evidence and inspection design

Design a structural delivery check over every public dataclass in
`presentation/scene/model.py`.  It must distinguish a field that is deliberately
inspection-only from one that must reach a presentation consumer, with an
explicit finite owner/reason registry rather than an implicit ignore list.

Design a maintained prior-art matrix derived from D391-1's rows.  Each row must
record the current Chrona disposition and a reason; it is a design review
artifact, not a runtime feature catalogue.  Define a light-weight visual
acceptance record for presentation changes that links regenerated gallery
evidence and records reviewer observations without turning subjective taste
into a non-deterministic test.

### D377-1 — Draft preset ingress and packaged default design

Design one resolver shared by explicit CLI preset input and the packaged
default.  It must produce the same typed draft closure as the four explicit
paths, resolve preset resources only relative to the preset root, preserve
explicit flags as intentional overrides, and keep immutable Context/
materializer input fully explicit.

The packaged preset is data in `chrona.resources`, not a Presentation Package
or a hidden semantic default.  The design must define its resource topology,
the exact no-flag help text, selected target/font behavior, diagnostics, and a
minimal public Project/Actual guide.  It may reuse only current capability
ceiling entries; it does not pre-approve #383's editorial vocabulary.

## Required architecture review

Before implementation, review the designs against Specifications 21, 22, 32,
55, 58, 63, and 64.  In particular verify that:

* no target adapter, package, or CLI default becomes an appearance authority;
* semantic distinctions cannot be silently omitted or substituted;
* the Scene delivery check observes structural ownership without forcing every
  serialized inspection field through SVG;
* the prior-art matrix cannot be interpreted as a generic-diagram roadmap;
* draft convenience creates neither an immutable Context shortcut nor a second
  render pipeline; and
* package acquisition remains deferred under the #348 corpus-first decision.

## Implementation planning and publication order

After the design and architecture review are published, produce separate
implementation plans and independently reviewable commits in this order:

1. I391: capability-ceiling specification, typed fidelity contract if admitted,
   producer/Scene/profile changes, fixtures, and generated inventories.
2. I390: all-Scene delivery inspection, prior-art matrix, visual review record,
   tests, and documentation checks.
3. I377: preset resolver, packaged default closure, public CLI/help, guide,
   explicit/preset/default byte characterization, and wheel smoke evidence.

Each implementation phase runs focused tests, generated-artifact checks,
conformance, structural checks, full pytest, public materializer checks where
affected, wheel/install smoke, and three-platform CI before its Issue closes.
Publication is serial: fetch `origin/main`, confirm fast-forward status, push
without force, then verify the resulting GitHub commit and CI run.

## Acceptance of this plan

This plan is complete only when the three design outputs and their architecture
review exist.  No code is authorized by this document alone.
