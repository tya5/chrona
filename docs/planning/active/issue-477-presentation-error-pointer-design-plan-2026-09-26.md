# Design Plan — Presentation Error Pointer Transport (#477)

## Published baseline and scope

At `a6ccfa15` on public `main`, `LayoutError`, `ThemeTokenError`, and
`ScenePaintError` carry an RFC 6901 resource pointer as `path`. The render use
case preserves some of these paths, but `measure_sources` and several other
presentation operations run outside its mapped failure boundary. The CLI's
generic `ValueError` handler then emits `sourceRef: "/"`. This plan addresses
pointer transport, not Theme requirements, grouping semantics, or paint policy.
The #477 issue has no later comments. #470 is related but independent.

## Literal issue acceptance criteria

1. Every presentation-layer error that carries a resource pointer reaches the
   CLI diagnostic's `sourceRef` with that pointer. `LayoutError`,
   `ThemeTokenError` and `ScenePaintError` are the known cases.
2. A CLI test renders a Theme without `timeline.groupHeader.blockSize` under
   header grouping and asserts
   `sourceRef: /body/metrics/timeline.groupHeader.blockSize`.
3. A CLI test renders a Theme without `roles.numeric` with a `Δ` column and
   asserts the role pointer.

## Design questions and slices

1. Locate every presentation exception-to-`RenderFailed` conversion, including
   pre-Layout measurement and Scene paint. Decide one boundary that can preserve
   pointers without masking detector-owned diagnostics.
2. Define exact code, message, component and pointer transport through the
   render use case and CLI. Keep non-pointer failures and aggregated ingress
   diagnostics unchanged.
3. Review against Specifications 09, 13, 30 and 56 and designs #371/#450:
   detector-owned facts, single CLI transport, no rendering or schema-policy
   change. Record any normative change explicitly; otherwise state why none is
   needed.
4. Define focused reproductions for the two issue cases, direct coverage of
   all three known exception classes, and public materializer byte evidence.

## Publication and evidence

Publish this plan, then the selected design and whole-architecture review,
then a separately published implementation plan. Implement a small independent
slice, run focused CLI/use-case tests and the public materializer batch, inspect
CI's full matrix, and publish a literal-criteria acceptance review before
closing #477. Preserve the unrelated in-progress #466 file in the worktree.

## Unverified at plan publication

The exact exception site for the `numeric` role and any other escaping
presentation errors remains to be confirmed by the design audit. Current
materializer byte identity is a required gate, not yet evidence.
