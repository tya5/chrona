# Architecture review — programme-board annotation fallback (#504)

Reviewed the [correction](../../design/issue-504-annotation-fallback-correction-2026-09-29.md) against the [R2 fill-only search design](../../design/issue-504-fill-only-label-search-correction-2026-09-29.md), Specifications 38/50, the declared annotation candidate contract, and Scene perceptibility. View owns the ordered candidate policy; Layout owns measured placement and collision; Scene projects the completed box. The fallback uses existing vocabulary and diagnostics, so no normative schema or ownership change is needed.

The tradeoff is a missing decorative tail on a note when its route cannot be completed. This is preferable to covering required names, and remains visible in the existing candidate-fallback diagnostic. Approved for resource migration and the R2 public-evidence gate; any residual perceptibility error stops release.
