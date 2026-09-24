# Issue 368 release review

The completed track planner is now the sole row-containment authority.
`minimum_track_block_extent` reuses final planned/actual, shared/stacked, and
point-milestone placement checks; the surface composer applies its maximum to
the uniform row allocator. This eliminates duplicated multipliers and the
aggregate-versus-uniform-row mismatch.

Evidence: the public three-lane point-milestone fixture proves Draft `auto`
succeeds, while fixed 392px rejects and the one-pixel-larger 393px surface
materializes. The focused Layout/render checks pass (31 passed), public
materializer checks pass (22 passed), and the import-direction gate and
three-OS CI remain required release gates.
