# Presentation Semantic Validation

**Status:** Proposed

Structural schemas are followed by owner-semantic checks. Required diagnostics are:

| Code | Condition | Result |
|---|---|---|
| `PRES-SNAPSHOT-REVISION` | Snapshot Project revision is absent, moving, or incompatible | evaluation rejected |
| `PRES-ACTUAL-ALIGNMENT` | resolved Actual object ID does not exist | observation diagnosed; no text matching |
| `PRES-VIEW-ACTUAL-REQUIRED` | View requires Actual but Context omits it | evaluation rejected |
| `PRES-TARGET-CAPABILITY` | Scene distinction cannot be represented by target | evaluation diagnosed/rejected by requirement |
| `PRES-SCENE-DELTA-SCOPE` | local input emits unexplained global replacement | conformance failure |

The semantic runner consumes the canonical fixtures, emits stable diagnostics, and
asserts that an Actual-only change is represented by local SceneDelta operations. It
does not mutate Project schedule or accept renderer defaults.

`examples/presentation/validate_conformance.py` is the first runner entry point. It
performs structural schema validation and the declared local/global SceneDelta checks.
Owner-semantic checks are added case-by-case without weakening structural validation.
