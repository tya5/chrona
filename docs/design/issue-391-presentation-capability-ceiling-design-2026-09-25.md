# Design: Closed presentation capability ceiling (#391)

**Status:** Accepted for implementation planning.

## Decision

Chrona will govern presentation expressiveness through one closed,
renderer-neutral capability ceiling.  A capability is admitted only when it
has a Gantt-semantic purpose, a primitive-family scope, an owning authoring
layer, a completed Scene representation, target-profile admission semantics,
and evidence.  A capability absent from the ceiling is not an accidental
renderer gap: it is either explicitly deferred or deliberately rejected with a
reason.

The ceiling is keyed by primitive family and semantic-role exception.  It is
never keyed by Layout slot: slots allocate space, while a `planned` mark and a
`groupHeader` label can occupy the same slot but have different meaningful
treatments.

## Ownership law

| Concern | Owner | Explicit non-owner |
| --- | --- | --- |
| semantic occurrence and primitive family | View plus semantic registry | Theme, Layout, adapter |
| granted bounds, row/track extent, packing, placement | Layout | Theme, Scene adapter |
| treatment inside granted bounds | Theme | Layout, adapter |
| colour identity and categorical relationship | Color Scheme | Theme literals, adapter |
| completed values and selected target policy | Scene and Render Context profile | adapter |
| target serialization | adapter | Theme, View, fallback policy |

This normalizes the existing architecture: a corner radius is treatment within
already granted mark geometry and therefore belongs to Theme; row pitch is
space allocation and therefore belongs to Layout.  Existing misplaced fields
are migrated atomically when their owning capability is implemented; no
compatibility alias is retained.

## Ceiling and disposition

The normative source will be a machine-readable capability registry owned by
`presentation.scene`, with a generated human-readable matrix.  The initial
registry records the following current and planned decisions.

| Primitive family | Capability family | Disposition | Reason |
| --- | --- | --- | --- |
| label | family, weight, size, line height | admitted | measured text and portable typography are already completed Scene facts |
| label | letter spacing, transform | deferred | editorial typography needs a role-scoped, measured layout design (#383), not raw adapter text attributes |
| mark | fill, stroke, opacity, corner radius, completed marker/symbol/pattern geometry | admitted | established Gantt mark treatments with completed target-neutral geometry |
| mark | role-scoped height/offset and end shape | deferred | requires #388/#384-derived row-space and mark-treatment designs |
| mark | arbitrary SVG path/image/filter | deliberately rejected | violates renderer-neutral finite Scene and asset boundaries |
| line | stroke, dash, cap/join, completed dependency marker | admitted | semantic relation and axis treatment already have finite Scene values |
| line | bezier/adapter routing control | deliberately rejected | routing remains Layout-owned and orthogonal semantic routes are intentional |
| decoration | fill, stroke, opacity, finite pattern, group/axis/calendar band | admitted | current structural review treatment |
| decoration | row-spanning row band | deferred | #389 must define cross-slot allocation and row semantics before admission |
| effect | two-stop gradient, one shadow, stroke finish | admitted, decorative only | finite portable v0.6 capability contract |
| icon | normalized monochrome vector/raster icon | admitted | Specification 64 owns normalized asset closure and accessibility |
| icon | arbitrary multicolour logo/image | deliberately rejected | needs a separate asset family and target/security contract |

`admitted`, `deferred`, and `deliberately-rejected` are registry dispositions,
not target fallback modes.  Every deferred/rejected row has an issue/design
owner and a reason.  The generated matrix is the row source for #390's
prior-art review, so a new proposal cannot add a renderer branch without first
adding or changing a declared capability row.

## Fidelity and substitution

`required` and `decorative-optional` retain their present meaning for an
individual completed treatment.  A third policy, `substitute`, is admitted at
the ceiling level but is not a free string accepted by current rich paint.

`substitute` is valid only for a future **semantic encoding capability** that
declares, in its own owning contract, all of:

1. a primary completed Scene channel;
2. one finite, target-neutral alternative completed channel;
3. the shared semantic identity that both channels preserve;
4. target-profile support predicates for each channel; and
5. a pre-adapter resolver that chooses the author-declared alternative or
   raises `E_VISUAL_CAPABILITY_SUBSTITUTION`.

Thus a categorical texture may declare a color/lightness alternative, but a
gradient or shadow cannot call itself substitutable merely because another
paint happens to exist.  The adapter receives only the already selected,
completed Scene value and never invents a replacement.  A semantic treatment
with no declared alternative remains `required`; it cannot silently disappear.

No current rich-paint treatment is eligible: Specification 63 defines each as
decorative and not the sole carrier of meaning.  I391 therefore does **not**
add a dangling `substitute` enum to Theme, Scene, or schema.  It introduces the
closed registry and a conformance rule that rejects an attempted substitution
without its capability-specific declaration.  The first semantic encoding
proposal that needs substitution must deliver the full five-part contract in
one atomic slice.

## Layer and profile connection

```text
semantic registry/View occurrence
        -> Theme + Color Scheme treatment
        -> Layout completed geometry
        -> Scene completed primitive + capability requirement
        -> selected target profile admission
        -> adapter serialization
```

The capability registry is consulted while Scene completes a treatment and
while a target profile validates it.  It does not read a Layout slot, resolve a
Theme token, choose a Color Scheme value, load package data, or inspect target
syntax.  Target profiles state support only; their inability to support a
required capability diagnoses before any adapter invocation.

## Migration and evidence

I391 replaces the distributed hard-coded capability sets with the registry as
their one owner.  Existing capability identifiers and current v0.5/v0.6/v0.7
profile behavior are retained as facts, not compatibility APIs.  Existing
Scene/schema fixtures are updated atomically if the registry changes a public
contract.

The implementation must provide:

* registry completeness tests against semantic primitive families and Scene
  capability consumers;
* accepted/deferred/rejected generated-matrix checks;
* target-profile and fidelity negative cases, including rejection of an
  unowned substitution request; and
* corpus/materializer evidence proving no unreviewed capability is inferred
  from SVG output.

## Non-goals

This design does not add editorial typography, dot grids, row bands, per-role
mark height, a generic image primitive, a plugin surface, package acquisition,
or Theme/View inheritance.  Those changes require their own ceiling-row design
and implementation plan.
