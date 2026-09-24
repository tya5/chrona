# Architecture Review: Overlay review-height token correction (#382)

**Decision:** Approved.

The observed 780px preferred-size limit is a real feasibility boundary, not a
rendering concern.  A named Theme metric is the existing architecture's
designated owner for concrete layout dimensions.  Adding it atomically with the
single consumer Layout is cleaner than raw geometry, clipping, or selection
changes, and it keeps required-token validation effective.
