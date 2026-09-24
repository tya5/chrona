# Design Correction: Overlay required-sidebar scope (#382)

**Decision:** Accepted.

The overlay evidence slide uses a title-only sidebar.  Its fixed inline width
and measured title establish the `sidebar-end` barrier; the required table and
timeline anchor from that fact and the block guide.  Optional summary, notes,
and legend slots are intentionally absent.

This retains a complete required review surface while refusing to turn #382
into a new detail-rail sizing policy.  Existing wallboard layouts remain the
owner of their optional detail arrangement.  The correction narrows corpus
content, not Layout grammar, View selection, Scene behavior, or renderer
policy.
