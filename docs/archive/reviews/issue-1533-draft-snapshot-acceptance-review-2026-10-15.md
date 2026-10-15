# Issue 1533 acceptance review

Implementation: `ea74667cb` (input), `415c4fd7d` (CLI reference), `ffcc0b155`
(approved declarative generic View default).
[Design/architecture/implementation plan](https://github.com/tya5/chrona/issues/1533#issuecomment-6190843702);
[Option A approval and no-flag condition](https://github.com/tya5/chrona/issues/1533#issuecomment-6191147968).
[PR1555](https://github.com/tya5/chrona/pull/1555) merged as `72cdd2b89`;
exact head `c4b133125` passed [CI38731365139](https://github.com/tya5/chrona/actions/runs/38731365139).
Derived sync and exact-SHA gate passed. Review-containing ready main
`787eeea8f1e1e5fbeab0a4cc89ca5f4d65f85854` passed
[release38733015984](https://github.com/tya5/chrona/actions/runs/38733015984):
Ubuntu/macOS/Windows full pytest, conformance and wheel/smoke, MCP floor and
newest-Python public materializers. All literal rows are met; issue1533 is closed.

| Literal criterion | Status | Evidence |
| --- | --- | --- |
| Add chrona render ... --snapshot <project.yaml>, the same Snapshot Project role/validation and ghost / ghost-when-changed semantics | met | Normal Project parser, matching id/E_CLOSURE_ID, exact bytes/digest and typed snapshot-project role. No fabricated SnapshotRef or Store input. Closure and public-usecase tests cover valid, malformed, unsupported and mismatched Projects. |
| Without the flag, nothing changes; every preset on halcyon-1 and chrona-roadmap stays byte-identical and gains no new diagnostic | met | Batched public CLI before415c4fd7d/afterffcc0b155:15 ids ×2 projects, all30 SVGs and complete stdout/stderr byte-identical. No exceptions or ignored diagnostics; PR count table names every id. Synthetic generic-View test also retains actual finish-delta/variance/legend geometry and warnings. |
| Name the CLI member in Spec and CLI golden | met | Specs06/08, generated CLI reference and116-case golden; only2 new golden rows (success and missing Project file). |
| render --preset target-b over halcyon-1 with --snapshot set to its baseline draws dashed baseline outlines on the changed rows, viewed as PNG | met | Exact public CLI command below, no --view override: PNG inspected;6 Snapshot primitives, visible dashed frames on changed AIT/launch rows. No Snapshot data or example files edited. |
| Shared generic View selects baseline:snapshot declaratively; explicitly selected View retains its baseline; CLI input never promotes it | met | Single packaged View field changes; explicit primary View with a Snapshot still draws no ghost and retains primary marks. Generic-View no-Snapshot regression test covers actuals, variance and legend. |
| MCP or preset-library member is out of scope | met | Neither tool schemas nor preset members change; Snapshot path is CLI/Draft ingress only. |

```sh
.venv/bin/chrona render examples/halcyon-1/project.yaml --preset target-b --actual examples/halcyon-1/actual.yaml --snapshot examples/halcyon-1/snapshots/baseline-2027-06/project.yaml --format png --output /tmp/target-b-snapshot.png --emit-scene /tmp/target-b-snapshot.scene.json
.venv/bin/python -m pytest -q tests/unit/chrona/usecases/test_draft_snapshot.py tests/unit/chrona/presentation/model/test_draft_closure.py tests/unit/chrona/presentation/model/test_snapshot_context_closure.py
```

Batch method: capture every id from `chrona preset list` on both named Projects,
with each Project's Actual Set and SVG target, without `--snapshot`; run four
independent CLI processes at a time and compare SVG plus full stdout/stderr.
All30 commands succeeded on both sides. Pre-resource-edit HALCYON target-b
SVG and inspection Scene also match before/after the input implementation.
Focused evidence:277 CLI/usecase/closure tests; final27 closure/Snapshot tests.
After the resource default, all128 CLI characterization/Snapshot tests pass.
The CLI reference's `--check --execute` succeeds after regeneration.
After merging ready main,27 closure/Snapshot tests pass. Exact-head
[artifact11971240922](https://github.com/tya5/chrona/actions/runs/38731365139/artifacts/11971240922)
retains all50 SVG and50 Scene bytes, without additions/retirements. Report
changes are source-location shifts plus the intended E_CLOSURE_ID validation site.

Architecture: Draft ingress freezes the local Project without persisting a
SnapshotRef/Context member. The existing renderer consumes its typed role;
the read ledger does not invent a snapshot-ref read. View owns baseline choice;
Core comparison, Layout geometry, Scene and adapters are unchanged. No compatibility
fallback, implicit promotion or project-specific branch was added. The generated
CLI reference is current; final PR and exact-main release checks pass without
a waived gate.
