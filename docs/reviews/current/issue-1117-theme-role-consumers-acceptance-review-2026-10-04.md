<!-- chrona:literal-acceptance/v1 -->

# Issue #1117: every declared Theme role needs a consumer, acceptance review

Source: [Issue #1117](https://github.com/tya5/chrona/issues/1117), re-fetched 2026-10-04 after the merges (body unchanged, 1566 characters; four comments, all this work's claim, status and handover blocks; no new acceptance rows). The rows below are the three literal bullets of its acceptance list. Work record: [issue-1117-theme-role-consumers-2026-10-04.md](../../planning/active/issue-1117-theme-role-consumers-2026-10-04.md); living contract [Specification 07](../../specification/07-style-and-theme.md) (role consumers).

Slices: design record [PR #1128](https://github.com/tya5/chrona/pull/1128) (`06603a02`); check, tool and removal of the dead lines [PR #1132](https://github.com/tya5/chrona/pull/1132) (`fa9b1af6`); conformance registration [PR #1145](https://github.com/tya5/chrona/pull/1145) (`43c042dc`), after reviewer PR #1061 (`c8ab6d9a`) dropped target B's dead lines. Each had conformance, three pytest shards, newest-Python reproduction and derived-ready green before merge.

## Literal issue acceptance

### Issue #1117

- Source: [Issue #1117](https://github.com/tya5/chrona/issues/1117)
- Observed: 2026-10-04

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | The three unread declarations are gone from every bundled and corpus Theme (the reviewer's target-B files are edited by the reviewer). | met | `table-header.fill`, `annotation-text.fill` and `range.fill` were removed from 55 Theme files (127 lines: the eight bundled presets, controller-z, controller-z-ja, aster-ssd, orion-asic, halcyon-1 except target B, `tests/fixtures`) in PR #1132, the two derived Themes that pin a changed base re-pinned; the reviewer's PR #1061 dropped target B's. [`check_theme_role_consumers.py`](../../../tools/check_theme_role_consumers.py) prints `Theme role consumers: PASS` on the repository, and it is registered as the conformance check `theme-role-consumers` in [`run_conformance.py`](../../../conformance/run_conformance.py), pinned once by [`test_run_conformance.py`](../../../tests/unit/tools/test_run_conformance.py). Regenerated corpus (64 slides): every SVG byte identical, 63 Scenes change only in the Theme `contentIdentity` of the provenance. | none |
| 2 | A synthetic Theme declaring a role no consumer names fails at its pointer; existing Themes still resolve. | met | The decision is a typed warning at render, not a failure, because a Theme shared by several Views may keep a role another View names (work record D2): [`test_theme_role_consumers.py`](../../../tests/integration/test_theme_role_consumers.py) shows `W_THEME_ROLE_UNREAD:/body/roles/<name>` for an unknown or misspelt role, no report for registered roles, `group:` names and a role a column `textRole` names, and the warning surfaced as a render warning; a role no closure of the repository reads fails the corpus tool and so conformance ([`test_check_theme_role_consumers.py`](../../../tests/unit/tools/test_check_theme_role_consumers.py): a dead role fails, one named by any of several closures does not, derived Themes are read through their base). Every bundled and corpus Theme still resolves (full suite and conformance green). The owner's approval (2026-10-04) fixed this shape: a warning at render plus a failing corpus check. | none |
| 3 | Synthetic tests with no `examples/` input; mutation check. | met | The two test files ([`test_theme_role_consumers.py`](../../../tests/integration/test_theme_role_consumers.py), [`test_check_theme_role_consumers.py`](../../../tests/unit/tools/test_check_theme_role_consumers.py)) build synthetic Themes, Views and Contexts; nine of nine mutations (registered roles reported, group names reported, documents ignored, bindings or roles not declared, union instead of intersection, derived Themes read, exit code, warning dropped) each fail a test. | none |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

Theme declares; the closure, which knows the View and the Profiles, checks consumers; Layout, Scene and adapters are untouched. No schema property was added; the intended change is the removal of three unread lines.

Disclosures:

- No image was read: every SVG is byte identical, so no drawn pixel moved; the only Scene change is the provenance identity of the Theme.
- The structural test is deliberately generous (a role counts as read when any string of the View or a Profile equals it), so it can miss a dead role whose name also appears as unrelated text; it never reports a role a document names.
- A derived Theme (`extends`) is read through its base file, so a dead line only in a derived Theme's own replacements is not seen by the corpus tool.

Exact review-bearing-main three-OS CI must pass before closing #1117; that run is recorded in the closing comment.
