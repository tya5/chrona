<!-- chrona:literal-acceptance/v1 -->

# Release Review — conditional legacy mark radius

Implementation: `b157cd39d1c76f773cfb974ccdefd993ea5862de`; [design, architecture review and implementation plan](https://github.com/tya5/chrona/issues/1198#issuecomment-6039192670).
Focused tests: 71 passed, including exact legacy ratios 0/0.2/0.5. Local conformance: 34 passed; diagnostic inventory differs only in source locations (independently normalized and compared). CI must regenerate that report and verify the shared public snapshot before acceptance.

## Literal issue acceptance

### Issue #1198

- Source: [Issue #1198](https://github.com/tya5/chrona/issues/1198)
- Observed: 2026-10-07

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A role with only `cornerRadius` renders with no error. | met | [Synthetic physical-only 0/3px/capsule render tests](https://github.com/tya5/chrona/blob/b157cd39d1c76f773cfb974ccdefd993ea5862de/tests/integration/test_mark_physical_corner_radius_role.py): completed task and legend radii match actual SVG. | — |
| 2 | A role with only `markCornerRadius` is byte-identical. | met | [Historical-resolver characterization](https://github.com/tya5/chrona/blob/b157cd39d1c76f773cfb974ccdefd993ea5862de/tests/integration/test_mark_physical_corner_radius_role.py): independent pre-change implementation versus current resolver, equal serialized Scene and SVG bytes. | — |
| 3 | A role with neither keeps today's error. | met | [End-to-end render and accessor tests](https://github.com/tya5/chrona/blob/b157cd39d1c76f773cfb974ccdefd993ea5862de/tests/unit/chrona/presentation/model/test_optional_legacy_mark_corner_radius.py): E_THEME_ROLE_REQUIRED at /body/roles/planned/markCornerRadius. | — |

## Programme-level criteria (optional)

Spec07 precedence is unchanged: Theme validates the physical binding and reads the legacy ratio only when used; Layout completes mark/legend geometry. Scene, adapters, schema, allocation and ports are unchanged. No examples edits or unresolved architecture findings. Malformed physical bindings retain their own pointer; physical zero is present.
Closure requires final PR checks, shared snapshot review, fresh trusted-ready main publication and successful three-OS pytest/conformance/wheel/materializer release on the exact published commit containing this review. The closing comment must cite the immutable PR, artifact and release receipts; local evidence alone is not release acceptance.
