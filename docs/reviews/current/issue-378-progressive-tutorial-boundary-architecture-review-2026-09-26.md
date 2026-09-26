# Architecture Review — Progressive Tutorial Source Boundaries (#378 I378-3)

## Cross-design check

- Project v0.7 owns objects, calendars, relations, hierarchy, scenarios, and
  extension declarations; it does not own immutable baseline selection.
- Actual Set owns observed dates and progress, independently of Project.
- View owns comparison and scenario selection. A scenario declaration without
  a selecting View is not observable evidence.
- Render Context owns snapshot input references; the snapshot-ref and baseline
  Project are read through the immutable snapshot reader, not Draft discovery.
- The profile-package extension is pinned by Project and copied into the
  materializer closure. Its custom fields and object types are interpreted at
  contract ingress, not by the SVG adapter.
- Layout, Scene, and renderer responsibilities are unchanged. The tutorial
  only chooses already-supported source and command boundaries.

## Resolution

The prior all-Project-fixture wording was structurally inaccurate for the
last three stages. The corrected Draft/immutable split preserves the issue's
learning order and executable acceptance without adding a parallel resource
grammar, duplicating the corpus, or claiming an unselected source changed the
render. No unresolved architecture conflict blocks implementation.
