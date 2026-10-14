# Issue #1356 installed-wheel initialization review

Source: [issue #1356](https://github.com/tya5/chrona/issues/1356).
Design and implementation plan: [living work record](https://github.com/tya5/chrona/issues/1356#issuecomment-6156816124).
Normative design: [Spec 32 §4.2](../../specification/32-repository-layout-and-packaging.md#42-installed-wheel-corpus-initialization-1356), published4619257c.
Implementation:2e11bb90. The issue has no literal acceptance table; the following
gates implement its selected proposal(a), not an invented quotation.

| Gate | Status | Evidence |
| --- | --- | --- |
| Installed wheel with render extra initializes an available corpus, warning about absent providers. | met | Fresh non-editable wheel environment without CJK:14 available,5 deferred; CLI succeeds. Target-B materializes with byte-identical SVG. `tools/wheel_doc_check.py` succeeds, including both formerly clone-only HALCYON init blocks. |
| Provider-present corpus and existing callers continue to work. | met | Focused caller batch263 passed,2 skipped,8 deselected; three relative-path failures corrected by resolving the closure root. Documented-path/CLI rerun8 passed; CLI init subset3 passed. After adopting reviewer PR1473, affected init/font tests30 passed and closure-input/render-review/role-admission/Title-Card batch97 passed (4 corpus tests deselected). Explicit directory result replaces Path assumptions. |
| Invalid declarations, pins and duplicate providers remain hard failures. | met | Provider/font-set/initializer/diagnostic batch37 passed; expanded malformed-Context admission suite7 passed (missing locator/address, invalid provider, unknown set, unsafe address). Only typed zero-entry-point facts are deferrable. |
| Deferred closures cannot leave partial usable Store members. | met | [Initializer tests](../../../tests/unit/chrona/usecases/test_init_provider_deferral.py) cover staging discard, source-only pruning, all-deferred and hard-error paths; configuration is published last. |
| No authored example changes or rendering fallback. | met | Implementation changes resource admission and initialization only; source examples are untouched. Rendering still rejects unavailable declared fonts. |
| Current-head public snapshot and full three-OS release. | met | PR1475 head a2e6f585 passed CI38486928856; artifact11860435128 retained all101 members and all92 Scene/SVG bytes. [Exact-main release38488112476](https://github.com/tya5/chrona/actions/runs/38488112476) on READY85ed35f1 passed full pytest/conformance/wheel on all three OSes, MCP floor and newest-Python public materializers. Issue1356 is closed. |

Architecture: font-resource owner supplies typed availability; materializer validates
canonical Contexts and checks every available asset before reporting absence;
initializer owns corpus selection and complete snapshot promotion. CLI serializes
the result. No View, Theme, Layout, Scene or adapter ownership changes, font
substitution, project-specific core rule or new manifest schema. Diagnostic
declarations are admitted before optional-provider decisions (Specs9/13/15/32/42).
Python API migration is intentional under Spec32's alpha API policy.

Initial CI artifact11859485614: all101 members retained, all92 Scene/SVG files
byte-identical; only two diagnostic inventories changed. The font-pin comparison's
classification anchor is migrated to `_font_copy_plan`, retaining
`pinned-deliberately` and its identity-byte producer. Repository discovery and
classification validation have a regression test; generated reports are not hand-edited.
