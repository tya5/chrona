# Endpoint Annotation Evidence Design (#386)

**Decision:** Accepted.

## Scope

This design makes View annotations an evidenced presentation feature without
changing Project semantics or making Scene/adapters own geometry.  It adds a
dedicated Controller Z corpus slide containing two endpoint-anchored
explanatory arrows, one of which must route around the other annotation box.

## 1. Two annotation authorities, one explicit relationship

Project v0.6 annotations remain semantic notes: they record durable project
facts and normalize as note content.  They have no View-specific facet,
endpoint, side, alignment, box bounds, port, or route.

View v0.13 annotations are presentation callouts: each names a selected
object's `planned` or `actual` endpoint, a purpose, placement preference, and
text.  Their geometry is derived for a particular surface and is never written
back to Project.  A View may explain the same project object as a Project note,
but it does not reference a Project annotation identifier and does not create a
second semantic fact.  This is deliberate: an explanatory arrow is an
audience-specific presentation, while a Project note is reusable semantic
content.

## 2. Corpus evidence

Add `controller-z/views/annotations.yaml` and a matching declared Context and
manifest slide.  It retains the existing Project, Actual set, Theme, Scheme,
and executive Layout; only the View and Context differ from the executive
control.

The View enables presentation annotations and declares two annotations:

1. `firmware-slip`: `explanatory-arrow`, anchored to the **actual finish** of
   `firmware`, placed in the annotation slot.
2. `bringup-risk`: `explanatory-arrow`, anchored to the **planned finish** of
   `silicon-bringup`, also placed in that slot.

The chosen ordering and long enough texts require the second box/leader to
avoid the first box.  The committed SVG proves the resolved route rather than
asserting router behavior in prose.  The View-level source references remain
object/facet/endpoint identities, so no coordinate is authored.

## 3. Ownership flow

```text
Project facts + Actual facts + View annotation intent
                 -> Layout measures box and resolves endpoint/port/route
                 -> Scene projects annotationBox/annotationText/annotationLeader
                 -> adapter serializes completed primitives
```

Theme continues to provide the annotation/dependency visual roles.  This work
does not introduce marker geometry; the Path's completed marker is governed by
#384.  Scene does not calculate a leader and SVG does not choose a port or
avoid an obstacle.

## 4. Characterization and migration

Focused tests assert that the chosen `finish` endpoint, both annotation boxes,
and an orthogonal leader path are present in completed placements.  A
projection test asserts the Scene primitives retain their source and purpose.
The public materializer regenerates only the new slide's SVG, and its
byte-identical check is the artifact acceptance gate.

## Rejected alternatives

- **Promote View callouts into Project annotations.** This puts audience and
  viewport-specific intent in semantic Project data.
- **Use a Project note as a routed leader source.** It conflates durable note
  content with one presentation choice and leaves endpoint/facet undefined.
- **Add a synthetic unit-only fixture.** It would not prove declared Context,
  annotation slot, Theme, Scene projection, and materializer closure together.
- **Make Scene or SVG route around boxes.** It violates Layout geometry
  ownership and makes output target-dependent.

## Acceptance

- A declared corpus Context materializes two endpoint-anchored explanatory
  arrows into an annotations slot, one avoiding another annotation box.
- Every View annotation that validates is resolvable by Layout's implemented
  object/facet/endpoint contract.
- The generated SVG reproduces byte-identically and carries annotation box,
  text, and leader provenance.
- Project notes remain semantic content and no Project schema or scheduling
  behavior changes.
