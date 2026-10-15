<!-- chrona:literal-acceptance/v1 -->

# Issue #1563 — as-of design voice

Implementation: [PR1569](https://github.com/tya5/chrona/pull/1569), merged as
`ad68387adf3c45e18499d152169280bd49bc8ae1`.
Exact-head [CI38751337024](https://github.com/tya5/chrona/actions/runs/38751337024)
passed at `b6a34348a4ec6c695ca999304de54b90db4e410d`.
The issue stays open until the three-OS release on the published commit
containing this review succeeds; implementation PR CI is not that release.

## Literal issue acceptance

### Issue #1563

- Source: [Issue #1563](https://github.com/tya5/chrona/issues/1563)
- Observed: 2026-10-15

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic tests for the knobs and for View-over-design precedence. | met | [Synthetic tests](https://github.com/tya5/chrona/blob/ad68387adf3c45e18499d152169280bd49bc8ae1/tests/integration/test_preset_asof_design_voice.py): four date/chip combinations and explicit View precedence; copied-preset closure/version tests and exact-head CI pass. | — |
| 2 | Each of the five design presets and wallboard-dark renders its own as-of wording on halcyon-1, viewed as PNG. | met | Six PNGs inspected; [PR count table](https://github.com/tya5/chrona/pull/1569) records inherited labels, 2 changed primitives/design, wallboard chip addition and unchanged dependency counts. Reproduce: `chrona render examples/halcyon-1/project.yaml --actual examples/halcyon-1/actual.yaml --preset <id> --format png --output <path>`. | — |
| 3 | All public SVG and Scene files are byte-identical. | met | [Exact-head run](https://github.com/tya5/chrona/actions/runs/38751337024), artifact11981687331: all50SVG+50Scene bytes identical, no additions/retirements. Only two diagnostic reports have source-line shifts; reproduction and CI pass. | — |

## Programme-level criteria (optional)

No additional criteria.

## Architecture conclusion

Existing Layout marker presentation supplies wording/date; explicit View wins.
Theme owns chip paint; Layout owns geometry. Shared closure validates declared
members after defaults and preserves identity/version provenance. Scene and
adapters gained no placement, routing or measurement responsibility.
Evidence discovery validates every declared packaged View/Layout pair;
no schema exemption, examples edit or manually patched derived file was used.
