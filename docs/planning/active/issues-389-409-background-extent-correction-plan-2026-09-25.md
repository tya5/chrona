# Design Correction Plan — Background Extent Ownership (#389, #409)

**Trigger:** The post-review correction to #389 found that the accepted I3
background plan made every row and group band cross the table--timeline
boundary.  That would put a translucent row fill below calendar closure over
the timeline, recreating the compositing defect #409 removed.

## Required sequence

1. Inventory the already-published View, Theme, Layout Profile, Layout and
   Scene contracts, and distinguish an author-selected decoration from the
   physical region in which it is placed.
2. Publish a design correction that assigns finite background extent to the
   review-surface Layout Profile, keeps `rowDecoration` coordinate-free in the
   View, and retains background treatment/order in Theme.
3. Review the corrected ownership against Specifications 24, 33, 50, 55 and
   63, especially completed placement ownership and the no-stacked-fill
   invariant.
4. Publish a bounded implementation amendment.  It must replace, not extend,
   the v0.5 Layout Profile ingress; migrate all public layouts and Context
   closures atomically to v0.6.
5. Only then implement, test, materialize and publish I3.

## Decision questions

| Question | Required answer |
| --- | --- |
| Who chooses whether rows or groups are decorated? | The View's finite `rowDecoration` mode. |
| Who chooses the physical reach of a background role? | The review-surface Layout Profile. |
| Who owns treatment, opacity and paint order? | Theme's finite background-role contract. |
| Who turns the three declarations into coordinates? | Layout alone. |
| May a renderer infer or widen an extent? | No. Scene and adapters project completed bounds verbatim. |

## Completion gate

The correction is complete only when the design, review and implementation
amendment agree on the four finite roles, their region vocabulary, the v0.6
migration, and the geometric overlap invariant.  No I3 source change may be
published before that gate.
