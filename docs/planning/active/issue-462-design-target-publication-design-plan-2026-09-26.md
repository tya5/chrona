# Design Plan — Publish Approved Visual Targets (#462)

## Published baseline and authority

At `1a89848316add6e54cf64c9990cef3a584c105a7`, `main` has neither
the fourteen PR #461 targets nor the HALCYON-1 target B artwork. Issue #462
is open; [PR #461](https://github.com/tya5/chrona/pull/461) is open,
mergeable and its four CI jobs passed at head
`1ea9668f3140cb495a951903c5625d75c5720f52`. The closed
[PR #45](https://github.com/tya5/chrona/pull/45) still exposes generator,
SVG and PNG blobs on `design/halcyon-1-target` at
`ec0af04caf89fe034c2307243c608098714d122a`.
[Issue #453](https://github.com/tya5/chrona/issues/453) links to the old
`examples/halcyon-1/slides/board/02-programme-board.png` location.
These are published facts; whether PR #461 remains conflict-free at merge
time and whether all moved B artifacts reproduce from the old generator must
still be checked. No previous local work is assumed.

## Literal issue acceptance

1. PR #461 is merged.
2. Target B's generator and rendered images are on `main` outside `examples/`.
3. #453 links to target B on `main`.

## Design questions and slices

1. Confirm that research targets are non-product reference artifacts, and
   decide the stable directory, source/image pairing and identity for B.
   Review against the `examples/` reachability boundary, gallery and corpus
   documentation, and #453's role as a gap map. Publish design and whole-
   architecture review before moving files.
2. Decide how #453's mutable GitHub issue body will link to an immutable
   `main` path; ensure it names B, not a generated Chrona result. Confirm
   whether the branch's SVG is required alongside PNG to reproduce B.
3. Merge PR #461 as a separately verifiable publication unit, after a fresh
   base/head/CI/mergeability check. Then bring B's source and renderings into
   `docs/research/presentation/` on the updated base; update #453 only after
   the files are remotely visible.

## Evidence and migration

No schema or runtime contract changes are expected. The prior PR #45 paths
remain historical links, not a compatibility promise. Acceptance requires
exact file/tree and byte checks against published PR #45, fourteen target
directories on `main`, repository conformance/reachability, PR merge state,
and a fresh read of #453's actual issue body. Record each literal criterion in
an acceptance review before closing #462.
