# #322 Example Roles Architecture Review

**Result:** Accepted for implementation.

The current three manifests and eight public slides are the regression corpus;
their materializer and byte assertions remain authoritative.  Teaching content
belongs under `docs/guides`, while gallery narration belongs under `docs/gallery`
and only references declared corpus slides.  This avoids duplicating closures,
adding an example-specific renderer branch, or allowing documentation to become
an alternate authoring model.  An inventory tool may read schemas and metadata,
but it must not infer product policy from coverage percentages.
