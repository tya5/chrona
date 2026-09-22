# Issue 145 Network View Envelope Design Correction

## Decision

`View.window` remains required for `dependency-network` in View v0.8.  It is
the existing, renderer-neutral schedule envelope carried by the common
`ReviewProjection`, not a claim that a network surface owns a time axis.  The
unchanged projection pipeline uses it to resolve selected schedule facts before
any surface adapter is chosen.  Removing it would force a surface branch in
the use case or invent an untyped default, contrary to Issue 145's closure
boundary.

This corrects the earlier statement that `window` is forbidden for a network
View.  The network Layout and Scene adapters MUST NOT derive coordinates,
slots, labels, or primitives from that envelope.  It remains available only as
the common typed projection fact.

## Surface-specific authoring contract

For `dependency-network`, View v0.8 requires the current common selection,
grouping, ordering, comparison, visibility, layout intent, rows, and window
contracts.  It forbids authoring whose only meaning is a table/timeline
surface:

* `tableColumns`;
* `axis`;
* `markers`;
* `shading`;
* `timePresentation`;
* `annotations` and `annotationPresentation`.

The schema enforces this as a surface discriminator rule.  `visibility`
retains its common typed form; network adapter semantics support node text and
relations only in this release.  A rejected field is a View contract error,
not silently ignored geometry.

The table/timeline route retains its existing field vocabulary and byte
characterization.  A future composite surface must introduce its own View
version and explicit authoring contract; it cannot inherit forbidden network
fields through an implicit fallback.

## Boundary review

| Boundary | Result |
| --- | --- |
| View projection | Keeps one typed schedule envelope and produces selected graph facts. |
| Layout | Never reads `projection.window` on the network route; it uses only the network slot, measured labels, profile writing mode, and routing policy. |
| Scene | Dispatches complete placements only, with no View-field inspection. |
| Use case / closure | Remain unchanged apart from neutral source registration established by the layout-closure correction. |
| Renderer | Remains primitive- and Theme-binding-driven. |

## Acceptance

1. A valid network View carries `window` but fails validation if it contains
   any forbidden table/timeline-only field.
2. A network Layout/Scene structural test proves that its composer/adapter does
   not inspect `projection.window`, axis, marker, shading, annotation, or table
   authoring data.
3. Existing table/timeline resources remain accepted and materialize with
   byte-identical output.
