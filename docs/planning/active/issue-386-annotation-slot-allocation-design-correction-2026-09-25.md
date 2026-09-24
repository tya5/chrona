# Design Correction: Annotation Slot Allocation (#386)

**Status:** Accepted correction to the #386 design and implementation plan.

## Trigger

The first planned Controller Z View/Context was materialized through the
public path and failed with `E_PRESENTATION_LABEL_UNPLACEABLE`.  The existing
`executive-review` Layout declares an optional `annotations` slot with both
dimensions `content`; it does not reserve a measured region for two required
explanatory-arrow boxes.  The original #386 design incorrectly treated slot
existence as allocation evidence.

## Corrected decision

The evidence slide receives a dedicated `annotations-review` Layout Profile.
It is a review-row composition with an explicit, required annotation rail:

```text
table | timeline stack | annotations rail
```

The rail has a declared inline allocation and fill block extent.  It is not a
post-Layout overlay and it does not make the router choose surface geometry.
The View/Context selects this Layout; the existing executive Layout remains an
unchanged no-annotation control.

## Consequences

- #386's corpus delta is View + Layout + Context, not View + Context only.
- Layout owns capacity for required annotation content before measuring routes.
- The new Layout must declare the same required Theme-token interface and
  preserve the existing table/timeline slots and semantic sources.
- The implementation plan gains a Layout acceptance test that proves two
  required annotation boxes fit without suppression and a materializer proof
  that the control slide remains byte-identical.

## Architecture review

The correction strengthens, rather than changes, the authority boundary:
Layout allocation precedes annotation box placement and leader routing.  A
renderer or Scene fallback would have hidden the insufficient allocation and
violated the completed-placement contract.  The dedicated resource also keeps
the gallery/corpus comparison attributable: the executive slide proves the
control; the annotation slide proves the explicit surface allocation needed by
its intended content.
