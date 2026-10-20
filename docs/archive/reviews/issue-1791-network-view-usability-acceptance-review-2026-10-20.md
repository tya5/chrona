# Issue 1791 — Network View usability

Status: all three literal criteria met; the issue is closed after exact-main
three-OS release.
Current design and implementation plan: [issue Status](https://github.com/tya5/chrona/issues/1791#issuecomment-6280791712),
with the [default-applicability correction](https://github.com/tya5/chrona/issues/1791#issuecomment-6280870586)
and [diagnostic-origin correction](https://github.com/tya5/chrona/issues/1791#issuecomment-6280957186).
Normative authority: Specs 06 section 9.2 and 33 `viewDefaults`.

| # | Literal acceptance criterion | Status | Evidence |
| ---: | --- | --- | --- |
| 1 | Either the bundled presets can render a network View (a network slot in their layouts, or a documented companion preset), or the error says so in words and names what to use. | met | Missing-slot and inherited-Layout errors retain actionable pointers/details and name the compatible `--layout` remedy. The [network guide](../../guides/network-view.md) supplies a complete `network-layout.yaml` using packaged control-room-dark Theme/Scheme resources; no clone or new bundled preset is required. All 15 preset CLI cases are covered by the focused batch. |
| 2 | Errors carry the real pointer. Members contributed by a preset are not reported as authored View members. | met | Network-inapplicable defaults are not injected; compatible defaults retain precedence. Inherited tint requires value-bearing grouping on both surfaces; explicit authored forbidden members/tint still fail. Genuine inherited format/header dependencies retain validation and exact Layout-default origins. The SceneBuildError handler includes admission without changing unused-input-check order. Focused synthetic/default and real CLI tests are included below. |
| 3 | A guide section shows a network View from a CSV plan, checked by the docs tests. | met | `tests/integration/test_network_view_guide.py` reads the guide's actual file fences and commands, imports CSV in an empty workspace, and checks real SVG nodes, labels, two edges and 1200×600 PNG. The [inspected PNG](assets-1791/network-guide.png) is retained byte-for-byte. |

Contract ingress owns default applicability; use-case transport preserves typed
errors. Project scheduling, Layout geometry, Scene projection and adapters are
unchanged. No preset-name cases, corpus changes or schema migration are used.

## Verification

- Guide integration: 1 passed; actual SVG/PNG inspected.
- Documented-command/plan tests: 33 passed; live CLI documentation grammar passed.
- Owner/contract/use-case/guide/documentation regression batch: 238 passed.
- Default/network/group-tint/15-preset CLI batch: 103 passed. Twelve presets
  identify the missing network slot; three identify a genuine inherited group
  header dependency at `/viewDefaults/grouping/header`, name its Layout and
  point to the compatible network Layout guide. No fake figures were added.
- Fresh wheel `4275c24f730d61e67c1ceccf5b0891895348370c8e5fe9d496c7781583937ed7`
  passes `tools/wheel_doc_check.py`: actual documented commands, isolated venv,
  empty workspace, including the new network SVG and PNG commands.
- [PR #1794](https://github.com/tya5/chrona/pull/1794) merged as
  `f452206f4c0e8166f69cfcc4d939861555ffc9c7`; its [CI run
  39353160037](https://github.com/tya5/chrona/actions/runs/39353160037)
  passed. Official artifact [12233902529](https://github.com/tya5/chrona/actions/runs/39353160037/artifacts/12233902529)
  contains the 109-path before/after snapshot: all 50 SVGs, all 50 Scenes and
  eight of nine reports are byte-identical. Only
  `docs/diagnostics/inventory.md` changed, solely at `src/*.py` line/column
  anchors; normalizing those anchors makes the report byte-identical. No
  generated SVG/Scene was edited.
- Exact review-containing main
  [`b1a3f643040d4e8c90f1ca93578ca532b39a8a91`](https://github.com/tya5/chrona/commit/b1a3f643040d4e8c90f1ca93578ca532b39a8a91)
  passed [release 39355436136](https://github.com/tya5/chrona/actions/runs/39355436136):
  full pytest, conformance and wheel/smoke on Ubuntu, Windows and macOS, plus
  MCP-floor and newest-Python public-materializer reproduction. The issue
  closed after all rows were met ([closing acceptance](https://github.com/tya5/chrona/issues/1791#issuecomment-6281981998));
  the reviewer-maintained board was not changed.
