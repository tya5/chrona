# Issue 1375 — CJK group-header secondary titles

PR: [1419](https://github.com/tya5/chrona/pull/1419).
Reviewed source: `fa1f7f2a43147932cc0ab5dfbdf6c4d97b97165d`; current READY
`133332e2833ede4423e775c1dec789db91c2d5cb` adopted at `3a6e4bd2`.
The reviewer lifted the preparation hold in
[this comment](https://github.com/tya5/chrona/pull/1419#issuecomment-6115767326).

| Literal acceptance criterion | Status and evidence |
| --- | --- |
| A corpus slide declares a CJK `grouping.header.secondary`; its PNG shows the secondary titles with correct glyphs, readable on the band, with no `W_` fit warning. | Met in reviewed source: Yuya declares `secondary.entityField: titleJa`, six Japanese names, `{ordinal}・{secondary}`; packaged-font PNG inspected. PR artifact `11705711166` contains the reviewed SVG, with six→29 tag glyphs, 459→482 primitives and no new fit warning. Reconfirm the current-head generated artifact before merging. |
| Do not edit `examples/**` as a developer; the reviewer owns it. | Met: all authored corpus changes are reviewer commits. Developer changes are the guide's truthful `example-v6` reference and current-READY integration; no authored YAML or generated outputs edited. |

Architectural review: this is data/View/Theme declaration of the existing
secondary-title contract; no new geometry, resource kind, schema or layer
ownership. Other 45 SVGs were unchanged, and other 18 HALCYON Scenes differed
only in resource provenance; the new Context pins truthfully identify the
changed Project. Current-base documented-init tests: 5 passed in 7.00 s.

Release pending: current-head PR CI, fresh artifact comparison and the
three-OS release on the exact published main containing this review. Do not
close issue 1375 from the earlier green PR run alone.
