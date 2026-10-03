# Issue #1114: endpoint-mark routing design plan

## Baseline and scope

Published main: `12175e6a6c1f8f7d138c5a633a9f94e671533267`.
Authority: [issue #1114](https://github.com/tya5/chrona/issues/1114),
Specifications 09 and 50 §3.3, and the current #1084/#1072 work record.
Dev A owns routing lane R; dev B owns lane L and reviewer owns example YAML.

Published code offers a span's far-side corridor through its body, exempts
endpoint hosts during repairs/back-routing, and emits an unchecked direct
visible-overflow fallback. The issue's 11 crossings are reported evidence;
the current corpus count and rendered changes remain to be measured.
Published WIP `e2529728` is unaccepted reference material, not completion.
Its #1108/#1109 changes are excluded from this issue's implementation.

## Literal acceptance

> Fixtures:
>
> - start-to-at, and start-to-start, with the target to the right;
> - the mirrored end-to-end case with the target to the left;
> - a bar with no free gap above, and one with no free gap below.
>
> For each, no relation segment overlaps the interior of any bar by more than the stroke width, and the first segment leaves the port outward. A Scene check counts own- and foreign-bar crossings corpus-wide; it must be 0 after regeneration. Existing compliant routes are unchanged. On target B, `avionics-cdr` no longer crosses the Avionics bar.

## Design questions and review

- Define outward attachment versus body traversal, including comparison hosts,
  point marks, mirrored endpoints, rounding, and centred terminals.
- Apply one invariant to regular search, lane search, repair, back-route and
  visible overflow; determine an honest failure when no safe candidate fits.
- Preserve compliant candidate ordering and output; do not tune project dates,
  Theme bindings, schemas, or reviewer YAML to obtain a passing result.
- Review against required-label safety, suppression evidence, route self-overlap,
  side-entry policies and renderer-neutral Layout/Scene boundaries.

## Publication sequence

1. Publish this design plan.
2. Publish selected design, normative correction and whole-architecture review.
3. Publish implementation plan (owned files, tests and evidence).
4. Implement and publish #1114 alone; reuse WIP portions only after review.
5. Batch corpus measurement and rendered comparison; publish literal acceptance
   review and obtain exact-main release CI before closing.

Synthetic evidence must cover every fixture above, blocked-side alternatives,
safe overflow/suppression, foreign marks and already-compliant routes.
Generated Scene/SVG evidence comes from disposable regeneration and derived-sync,
never manually committed generated artifacts. Full release tests run in CI.
#1109 follows this slice; #1108 additionally waits for dev B's #1105 merge.
