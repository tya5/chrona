# Issue 1791 — Network View usability

Status: focused and clean-wheel verification complete; PR snapshot and
exact-main release pending.
Current design and implementation plan: [issue Status](https://github.com/tya5/chrona/issues/1791#issuecomment-6280791712),
with the [default-applicability correction](https://github.com/tya5/chrona/issues/1791#issuecomment-6280870586)
and [diagnostic-origin correction](https://github.com/tya5/chrona/issues/1791#issuecomment-6280957186).
Normative authority: Specs 06 section 9.2 and 33 `viewDefaults`.

| # | Literal acceptance criterion | Evidence / disposition |
| ---: | --- | --- |
| 1 | Either the bundled presets can render a network View (a network slot in their layouts, or a documented companion preset), or the error says so in words and names what to use. | Missing-slot errors retain the Layout pointer, detail and `--layout` remedy. The [network guide](../../guides/network-view.md) supplies a complete `network-layout.yaml`, used with packaged control-room-dark Theme/Scheme resources; no clone or new bundled preset is required. Release pending. |
| 2 | Errors carry the real pointer. Members contributed by a preset are not reported as authored View members. | Network-inapplicable defaults are not injected; compatible defaults retain precedence. Inherited tint requires value-bearing grouping on both surfaces; explicit authored forbidden members/tint still fail. Genuine inherited format/header dependencies retain validation and their exact Layout default origins. The existing SceneBuildError handler now includes admission without changing unused-input-check order. Focused synthetic/default and real CLI tests are required below. Release pending. |
| 3 | A guide section shows a network View from a CSV plan, checked by the docs tests. | `tests/integration/test_network_view_guide.py` reads the guide's actual file fences and commands, imports CSV in an empty workspace and checks actual SVG nodes, labels, two edges and 1200×600 PNG. [Inspected PNG](assets-1791/network-guide.png). Local test passed; release pending. |

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
- Local conformance passes every check except stale generated diagnostic
  inventory source anchors. No generated file was edited; CI's single derived
  snapshot must supply that report and prove the intended public byte delta.
- Official snapshot and exact review-containing main three-OS release pending.
