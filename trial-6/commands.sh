#!/bin/bash
# Trial 6 (redo of the 2026-10-09 product trial) on origin/main f5a51c099.
# Run from .trial6/ with a venv at ../.venv made by: python -m venv .venv && .venv/bin/python -m pip install '.[render,mcp]'
set -x
C=../.venv/bin/chrona

# 1. import (two variants: with the owner role, and plain hierarchy)
$C import plan.csv --output project.yaml --project-id relaunch --title "Platform relaunch" --calendar "standard mon-fri" --role responsible=owner
$C import plan.csv --output project-norole.yaml --project-id relaunch --title "Platform relaunch" --calendar "standard mon-fri"
$C validate project.yaml; $C schedule project.yaml > schedule.json

# 2. presets: every preset on both imports
bash render_presets.sh
INPUT=project-norole.yaml PREFIX=norole bash render_presets.sh

# 3. executive one-pager attempts (hand-written Views) and the working view
$C render project-norole.yaml --preset target-b --view exec-view.yaml --viewport 1600x900 --output out/exec-attempt1.png
$C render project-norole.yaml --view exec-view-default2.yaml --viewport 1600x900 --output out/exec-attempt3.png
$C render project-norole.yaml --view exec-view-default3.yaml --viewport 1600x900 --output out/exec-attempt4.png
$C render project-norole.yaml --preset mission-light --view exec-view-mission.yaml --viewport 1600x900 --output out/exec-attempt5.png

# 4. plan = project-norole.yaml with the launch deadline moved to 2027-06-01; baseline = copy before the slip
#    (cp project-norole.yaml plan.yaml; edit deadline; cp plan.yaml baseline.yaml)
$C validate actual-week1.yaml; $C validate actual-week2.yaml
$C render plan.yaml --actual actual-week2.yaml --output out/working-week2.png

# 5. re-plan: cloud 5wd -> 18wd in plan.yaml (the only diff against baseline.yaml)
$C schedule plan.yaml > schedule-replan.json

# 6. baseline vs current, forecast, deadlines
$C render plan.yaml --actual actual-week2.yaml --snapshot baseline.yaml --preset target-b --output out/compare-targetb.png
$C render plan.yaml --actual actual-week2.yaml --snapshot baseline.yaml --forecast --preset target-b --output out/forecast-targetb.png
$C render plan.yaml --actual actual-week2.yaml --snapshot baseline.yaml --forecast --preset target-b --view compare-view.yaml --output out/forecast-deadlines.png
$C render plan.yaml --actual actual-week2.yaml --snapshot baseline.yaml --forecast --preset technical-print --view tp-deadlines-view.yaml --output out/forecast-tp-deadlines.png
bash deadlines_all.sh

# 7. export
bash export.sh

# 8. terse
$C validate draft-typos.chrona
$C render draft.chrona --output out/terse-draft.png
$C compile draft.chrona --output draft-compiled.yaml

# 9. MCP
../.venv/bin/python mcp_client.py

# 10. 10-09 edge cases
(cd edge && ../$C validate bad.yaml)
(cd edge && ../$C render long-titles.chrona --output long-titles.png)
(cd edge && ../$C render single-gate.chrona --output single-gate.png)
(cd edge && ../$C render five-years.chrona --output five-years.png)
(cd edge && ../$C render group-gate.chrona --output group-gate.png)
(cd edge && python3 make_big.py && time ../$C render big.chrona --output big.png)
$C render plan.yaml --actual actual-week2.yaml --view edge/window-view.yaml --output edge/window.png
