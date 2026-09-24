# Issue 368 release review

The completed track planner is now the sole row-containment authority.
`minimum_track_block_extent` reuses final planned/actual, shared/stacked, and
point-milestone placement checks; the surface composer applies its maximum to
the uniform row allocator. This eliminates duplicated multipliers and the
aggregate-versus-uniform-row mismatch.

Evidence: direct multi-lane milestone boundary test, Draft auto/fixed render
coverage, public materializer checks (28 passed), focused Layout/render checks
(52 passed), import-direction gate, and three-OS CI.
