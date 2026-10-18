# Issue 1701 — native hierarchy evidence

Reference evidence only; do not merge this branch.

Renderer source: [3cbe209113e4f1a340bf613eaec2571086197f1d](https://github.com/tya5/chrona/commit/3cbe209113e4f1a340bf613eaec2571086197f1d),
including ready main5fe41db8e. The adjacent synthetic Project/Actual inputs
have no responsible-role binding. Each of the15 preset names has a PNG, SVG
and serialized Scene; all three containment levels remain visible. The default
keeps its existing hierarchy rows; other presets declare path names. A header
covering Atlas leaves Borealis/Curie in the member name, without repeating Atlas.
The coordinating developer inspected every native PNG. These PNG bytes equal
the independently reviewed pre-integration batch for all15 presets.

Generate and verify with the source checkout's own venv:

```sh
.venv/bin/python -m pytest -q tests/integration/test_hierarchy_preset_names.py --basetemp=/tmp/chrona-1701-review-evidence
```

The18-test batch also covers bound-role names and retains a separate one-span,
full-window suppression case: it has a pointed diagnostic, not a fit waiver.
This evidence does not replace current-head PR checks, official public artifact
review or the exact-main full release required before closing1701.
