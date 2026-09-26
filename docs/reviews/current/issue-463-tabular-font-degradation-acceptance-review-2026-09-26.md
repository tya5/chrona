<!-- chrona:literal-acceptance/v1 -->

# Acceptance Review — Draft Tabular-Digit Degradation (#463)

**Implementation:** [`cb38bf19`](https://github.com/tya5/chrona/commit/cb38bf1936411efe4f88b493718781ccac85397b).
**Plan:** [implementation plan](../../planning/active/issue-463-tabular-font-degradation-implementation-plan-2026-09-26.md).
**Design:** [selected contract](../../design/issue-463-tabular-font-degradation-design-2026-09-26.md)
and [architecture review](issue-463-tabular-font-degradation-architecture-review-2026-09-26.md).

## Literal issue acceptance

### Issue #463

- Source: [Issue #463](https://github.com/tya5/chrona/issues/463)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | `chrona render --system-fonts` with Hiragino Sans or Georgia and a bundled Theme succeeds, with a warning naming the numeric role. | met | [Host-face CLI test](../../../tests/unit/chrona/presentation/renderers/test_target_registry.py) runs both installed macOS faces through `chrona render --system-fonts`, asserts successful SVG and `W_FONT_TABULAR_UNAVAILABLE` with `role=numeric`; the Scene warning carries the role and face. | — |
| 2 | The committed corpus is unchanged, since its packaged faces have tabular digits. | met | [Implementation commit](https://github.com/tya5/chrona/commit/cb38bf1936411efe4f88b493718781ccac85397b) has no `examples/` or contrast-report changes (`git diff --name-only cb38bf19^ cb38bf19 -- examples docs/diagnostics/presentation-contrast.md` is empty); the public materializer byte-reproduction test passed after #463. Later #459 deliberately regenerated corpus paint, independently of font degradation. | — |

## Programme-level criteria (optional)

No additional programme criteria.

## Verification and generated evidence

- Focused target-registry and Theme-overlay tests exercise effective proportional measurement/paint agreement, warning transport, preserved bundled tabular mode, and refusal when even proportional metrics are unavailable.
- `python conformance/run_conformance.py` passed at the combined #459/#463 public base. The first [CI run](https://github.com/tya5/chrona/actions/runs/36217597562) found two incomplete CLI warning test doubles on each OS; [the correction](https://github.com/tya5/chrona/commit/6246fc2a6c6bc7db843bc165684eda31f573789e) passed all 57 CLI tests locally. The [final CI run](https://github.com/tya5/chrona/actions/runs/36217779916) passed macOS, Ubuntu and Windows conformance/full pytest/wheel jobs and newest-Python public-materializer reproduction.
- No public Scene/SVG artifact was changed in the #463 implementation commit. The draft-only effective Theme overlay leaves resource closure and frozen source Theme untouched.

## Architecture conclusion

Font resolution records the exact selected face's capability; the render use case derives one effective per-role draft Theme view for both Layout measurement and Scene text transport. The Scene carries a typed warning, and adapters paint the completed spacing mode. Neither adapters nor Layout silently choose a different face. Portable packaged-font behavior remains deterministic; system-font degradation is explicit and limited to opt-in draft rendering. No unresolved design gap is accepted.
