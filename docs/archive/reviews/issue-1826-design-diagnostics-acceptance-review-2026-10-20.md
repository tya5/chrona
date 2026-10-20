# Issue 1826 — design diagnostics acceptance review

**Disposition:** closed; all three literal acceptance rows are met.
**Review-containing main:** `53bbcc9900ebba3d6490ad0dfe1ccb81b84c7948`.
**Release:** [39444807924](https://github.com/tya5/chrona/actions/runs/39444807924)
passed full pytest, conformance and wheel on Ubuntu, macOS and Windows, as
well as MCP-floor and newest-Python reproduction. The Windows wheel gate ran
and passed after the UTF-8 test-child correction.

| Literal acceptance | Result and direct evidence |
| --- | --- |
| every pair of drawn legend swatches is checked with the existing Spec 60 measure, under normal vision and the scheme's declared colour-vision types. A synthetic case warns for the ΔE 2.7 pair and for identical swatches with different meanings. | met — `test_legend_diagnostics.py` covers normal and declared vision types, the ΔE 2.7 and identical-different-meaning pairs, paired subjects, and hidden/text-only controls. The [official artifact review](https://github.com/tya5/chrona/pull/1831#issuecomment-6291305105) records per-slide output counts and SVG inspection. |
| a halo is excluded from the decoration contrast check by its declared purpose (it is a separator, not a figure). target-b can then drop decoration: none (reviewer YAML follows). | met — `test_contrast_policy.py` verifies the canonical separator purpose and conservative behavior for malformed, missing-purpose and Text cases; ordinary bands, marks, Text and graphical legend floors remain covered. |
| content-width legends measure with the same rounding they place with (no false ellipsis), the one-row height is the measured row height, and a synthetic test covers both. | met — `test_legend_measurement_closure.py` covers shared Decimal measurement/placement at multiple origins and genuine shortage; `test_legend_known_width_completion.py` covers fixed-parent, wrapped, short and Draft-auto rendering. |

Layout owns completed legend measurement and ink; Scene remains passive, and
the adapter serializes completed geometry. Contrast uses the existing
Spec 60 measure and declared scheme visions. The halo exemption is purpose-
based and does not exempt malformed or unknown uses. No schema version,
project-specific rule, new threshold or tolerance was introduced.

The [final artifact review for the combined implementation](https://github.com/tya5/chrona/pull/1834#issuecomment-6292534493)
confirms 50/50 SVG and Scene payloads unchanged relative to that PR's base;
the #1826 output changes are documented in its [implementation artifact
audit](https://github.com/tya5/chrona/pull/1831#issuecomment-6291305105).
The separate block-stack/tall-swatch measurement defect remains tracked in
[#1830](https://github.com/tya5/chrona/issues/1830).
