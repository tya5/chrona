<!-- chrona:literal-acceptance/v1 -->

# Issue #1581 — opposite-as-of annotation fallback

Final PR source `81445e9a6e2f7c9108be63f5341f300b5665b41f` passed
[CI38825443697](https://github.com/tya5/chrona/actions/runs/38825443697).
Exact review-containing main `cbcd0f0ef20d4de3d28376fe59fee2dc71e45888` passed
[release38827136339](https://github.com/tya5/chrona/actions/runs/38827136339):
three-OS full tests/conformance/wheel, newest-Python public reproduction and MCP floor.
[Published design/implementation plan](https://github.com/tya5/chrona/issues/1581#issuecomment-6203105527).
All literal criteria met; issue closed.

## Literal issue acceptance

### Issue #1581

- Source: [Issue #1581](https://github.com/tya5/chrona/issues/1581)
- Observed: 2026-10-16

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic: anchor side blocked, other side free → placed on the other side, tail crosses the as-of rule once, warning names the candidate. Anchor side feasible → unchanged. | met | [Synthetic integration](../../../tests/integration/test_annotation_asof_fallback.py) verifies the exact candidate warning, one interior transverse crossing and unchanged feasible anchor-side placement without invoking the fallback. [Search](../../../tests/unit/chrona/presentation/layout/test_annotation_search.py) and [topology](../../../tests/unit/chrona/presentation/layout/test_annotation_topology.py) tests retain other obstacles, source-egress safety, strict crossing and aggregate-state limits. | — |
| 2 | The #1568 Sunday reproduction (anchors on `sunday`, `io`, `japanese`) draws no note over a bar, viewed as PNG. | met | Root viewed the unchanged original-input reproduction at 1600×900, v0.6 PNG, also after merging #1582. Scene audit: all three annotation bodies have zero bounds intersections with 83 planned/actual/snapshot mark primitives; all three leaders are completed, exactly three new warnings, no annotation overflow/exhaustion/no-route warning. [Reproduction status and evidence](https://github.com/tya5/chrona/issues/1581#issuecomment-6203721170). | — |
| 3 | All public SVG and Scene files are byte-identical. The time cost is reported. | met | Final-head CI [artifact12014169569](https://github.com/tya5/chrona/actions/runs/38825443697/artifacts/12014169569): all50 SVG +50 Scene raw bytes identical against ready153d7ba15, no added/retired paths. Only diagnostic-inventory report changes (new warning and second callsite of existing route-exhaustion warning). Quiet same-input wall time 3.89→4.59s; separate cProfile reports 3072 opposite-side state advances, 1024 per note. [Published profile](https://github.com/tya5/chrona/issues/1581#issuecomment-6203721170). | — |

## Programme-level criteria (optional)

Layout alone retries completed placements after every original fine/coarse
candidate fails. The exact as-of rule is the sole named route exemption;
nonempty strict routes cross it once, transversely. Existing obstacle classes,
position limits and aggregate route budget remain authoritative. Bodies and
tail tips/bases stay opposite; source egress stays anchor-side. The new pass
interleaves low-bend axial families lazily; original search order is unchanged.
The new warning does not replace the existing later-candidate warning.
Scene/adapters and example inputs are unchanged. Timing is evidence for this
case, not a new product threshold.
