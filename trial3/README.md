# Outsider trial 3 inputs (reference branch, not for merging)

Fresh-agent trial on main 9d888beb (2026-10-17). Used by #1626, #1627, #1632.

- `plan.csv`: the 25-row source.
- `project.yaml`: `chrona import plan.csv --role responsible=owner --output project.yaml`, then calendar holidays added and `design-freeze` moved to `fixed-point at 2026-11-27`.
- `baseline.yaml`: `project.yaml` before the gate move.
- `norole.yaml`: the same import without `--role`.
- `actual.yaml`: Actual Set at asOf 2026-11-10.

Renders viewed:
- `chrona render project.yaml --preset {target-b,technical-print,wallboard-dark,editorial} -o plan-<preset>.png`
- `chrona render norole.yaml --preset target-b -o norole-target-b.png`
- `chrona render project.yaml --actual actual.yaml --snapshot baseline.yaml --preset {target-b,sunday} -o week1-<preset>.png`
