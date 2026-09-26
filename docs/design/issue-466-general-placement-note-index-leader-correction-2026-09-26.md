# Design Correction — Optional Note Index Cannot Gate Its Leader (#466)

**Discovery:** The shared inventory can reject an optional inline note-number index that formerly fit against a narrower text-only obstacle list. In `controller-z/annotations`, `architecture-callout` then loses its required annotation leader because the composer skips the remainder of the annotation loop. The optional index and the connector are independent completed outputs of one annotation intent.

Layout evaluates the annotation box/text, optional note index, and leader as separate outputs in that order. A note-index fit failure emits `W_LAYOUT_NOTE_INDEX_SUPPRESSED` and omits only that index and its optional visuals. It does **not** skip or suppress the already accepted box/text or the leader. The leader's existence follows the annotation purpose and selected box placement; its route still queries the shared obstacle inventory and follows the declared quality/fallback contract. An accepted index enters the inventory before the leader; a rejected index does not.

No View or Theme schema changes. The public annotation leader and box identities remain stable. This correction prevents a control-flow coupling from silently changing an annotation's semantic connector when obstacle policy becomes stricter.
