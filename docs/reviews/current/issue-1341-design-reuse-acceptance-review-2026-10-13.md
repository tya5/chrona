<!-- chrona:literal-acceptance/v1 -->

# Design reuse release review (#1341, #1344)

Observed: 2026-10-13. This is a developer mechanism review, not a claim that
reviewer-owned design migration is complete. Current implementation authority:
[work plan](../../planning/active/issue-1341-design-reuse-completion-work-plan-2026-10-13.md).

## Literal issue acceptance

### Issue #1341

- Source: [#1341](https://github.com/tya5/chrona/issues/1341)
- Observed: 2026-10-13

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Target B and the four other approved designs reproduce byte-identically on HALCYON, with Theme/Layout/profiles containing no HALCYON id or wording, and with Views containing connection members only. | not met | PRs #1455–#1457 preserve all92 public Scene/SVG files; this does not prove migrated-resource purity. The checker reports878 context-qualified lexical candidates, not semantic impurities or a purity certificate. Migration/provenance disposition is requested in [6138676694](https://github.com/tya5/chrona/issues/1341#issuecomment-6138676694). | — |
| 2 | `examples/chrona-roadmap` renders each design by writing only its own thin View and Context. | not met | [PR1457](https://github.com/tya5/chrona/pull/1457) has actual SVG controls. Permanent five-design roadmap adoption remains reviewer-owned; it is not evidenced by unchanged existing outputs. | — |

### Issue #1344

- Source: [#1344](https://github.com/tya5/chrona/issues/1344)
- Observed: 2026-10-13

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | HALCYON is unchanged once its period declares the role. | narrowed | [Owner6097145885](https://github.com/tya5/chrona/issues/1344#issuecomment-6097145885) replaces Project roles with explicit View connections. PR1457 preserves92/92 public Scene/SVG files without adding period roles. | [Current connection design](../../planning/active/issue-1341-design-reuse-completion-work-plan-2026-10-13.md) |
| 2 | The roadmap renders the Title Card countdown against its own period. | not met | [PR1457](https://github.com/tya5/chrona/pull/1457) verifies View-bound period selection in synthetic actual SVG. Permanent roadmap/Title Card adoption remains reviewer-owned. | — |
| 3 | A project without the role renders without error. | narrowed | [Owner6097145885](https://github.com/tya5/chrona/issues/1344#issuecomment-6097145885) selects absent binding omission with info instead of roles. PR1457 tests unbound slots/legacy Summary figures, empty-panel omission and errors for explicitly invalid targets. Heading/Theme missing-figure behavior is deliberately unchanged. | [Current connection design](../../planning/active/issue-1341-design-reuse-completion-work-plan-2026-10-13.md) |

## Programme-level criteria (optional)

Developer mechanism gates are below; they do not replace the literal rows.

## Release evidence

- PR1455 release [38343299409](https://github.com/tya5/chrona/actions/runs/38343299409)
  and PR1456 release [38344844826](https://github.com/tya5/chrona/actions/runs/38344844826)
  succeeded.
- PR1457 exact-head [38347439477](https://github.com/tya5/chrona/actions/runs/38347439477)
  succeeded; independently inspected snapshot11788782848 has92/92 identical
  Scene/SVG files,0 retirements and only2 inventory/coverage reports changed.
  Containing-main release [38348700557](https://github.com/tya5/chrona/actions/runs/38348700557)
  on `d9c87d659652c1035099adc9e9b90610c4231d3b` succeeded.
- PR1458 exact-head [38349311779](https://github.com/tya5/chrona/actions/runs/38349311779)
  succeeded. Independently inspected snapshot11790031958 has92/92 identical
  Scene/SVG files,0 additions/retirements and only2 diagnostic inventories changed.
  Focused checker/conformance/materializer tests:46 passed; immutable-materializer
  integration controls:4 passed. Read-only corpus audit:0 reference errors,
  878 findings across35 resources and40 contexts with findings.
  PR1458 merged at `a84bc82488fcb350897b5b0854999fbbb17717c8`; synced-main release
  and the release containing this review remain pending.

## Architecture conclusion

Ingress closes declared View design defaults and connections before validation;
Theme/Layout/profiles retain design ownership. The pure profile connection owner
does not measure text or compute geometry. Layout, Scene and adapters retain their
existing responsibilities. Materialization owns reference/Store/pin admission;
the tooling audit reuses it without rendering or rewriting resources. Resource
identity is preserved, not normalized away to satisfy byte wording. No authored
`examples/**` or board writes occurred. Both issues remain open until release
evidence and the explicit literal disposition are complete.
