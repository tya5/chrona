<!-- chrona:literal-acceptance/v1 -->

# Release Review — Independent Conformance Feedback (#451)

## Literal issue acceptance

### Issue #451

- Source: [Issue #451](https://github.com/tya5/chrona/issues/451)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A failing run names every failing check, not just the first. | met | [runner](../../../conformance/run_conformance.py); [runner tests](../../../tests/unit/tools/test_run_conformance.py) | — |
| 2 | A stale-document failure shows the differing lines and the command that fixes them. | met | [shared report](../../../tools/derived_artifact_report.py); [inventory test](../../../tests/unit/tools/test_diagnostic_inventory.py) | — |
| 3 | A gate failure does not prevent pytest from running and reporting. | met | [CI workflow](../../../.github/workflows/conformance.yml); [workflow test](../../../tests/unit/tools/test_conformance_workflow.py) | — |
| 4 | A failure on one OS does not cancel the other OS jobs. | met | [CI workflow](../../../.github/workflows/conformance.yml); [outcome test](../../../tests/unit/tools/test_check_ci_outcomes.py) | — |

## Programme-level criteria (optional)

The [a8f16eee CI run](https://github.com/tya5/chrona/actions/runs/36206139144)
showed `E_DIAGNOSTIC_INVENTORY_STALE` with a bounded unified diff and its
refresh command. The [1ef92262 CI run](https://github.com/tya5/chrona/actions/runs/36207193826)
demonstrated the failure path on all three OS jobs:
`example-reachability` was named, its missing paths appeared in pytest, and
macOS, Ubuntu and Windows all completed rather than fail-fast cancelling.
The supporting-file registration was repaired at 5b909ce8. Its
[CI matrix](https://github.com/tya5/chrona/actions/runs/36207540414) is green
on Ubuntu, macOS, Windows and newest-Python reproduction, including dependent
wheel smoke. Focused feedback tests: 27 passed. The final review commit's
CI is still observed before issue closure.

## Architecture conclusion

Conformance owns aggregation and actionable reporting, while each check
retains its own validation authority. CI runs gates and tests independently,
then combines their outcomes; wheel smoke remains dependent on both. No
product contract is moved into the CI wrapper.
