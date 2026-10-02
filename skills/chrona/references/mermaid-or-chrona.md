# Mermaid, a hand-placed picture, or chrona

Pick by what must stay true after the next edit. The cost to chrona is stated first.

## Use Mermaid when

- A sketch inside a README or pull request must render with no tooling.
- The task count is small and nobody will recompute the dates.
- A Mermaid line such as `after a1, 20d` is shorter than the plan chrona needs today.
  Chrona's input is the Project YAML: the worked plan in
  [authoring-model.md](authoring-model.md) is 46 lines for four objects and three
  relations. There is no shorter form yet, and a structural mistake can come back as a
  terse diagnostic (see [diagnostics.md](diagnostics.md)).
- Python is not available. Chrona needs it, and a PNG also needs `pip install
  'chrona[render]'`.

## Use a hand-drawn or agent-placed picture (SVG, or an image tool) when

- It is a one-off illustration and the dates are decoration.

The hazard is not ugliness. A hand-placed bar is correct only until someone edits the
plan, because nothing recomputes it, and the next prompt draws a different picture. If
anyone will ask "is that bar really two weeks, across the holiday?", do not hand-place it.

## Use chrona when

- Dates come from durations, working calendars, dependencies and lags.
- The plan lives in git and is edited again.
- A reviewer needs the same input to produce the same bytes next quarter.
- Actuals or a baseline are compared with the plan.
- A Theme or preset must be shared across many plans.

## What chrona does not promise

No resource leveling at this surface, no interactive editing, and a cycle is rejected
rather than analysed. A `deadline` before the scheduled date is a `W_DEADLINE` warning, not a rejection, and the
picture draws it only when the View asks (`deadlines`) and the Theme has the `deadline-mark` role; the packaged presets
do not have it yet. Say so to the user instead of implying more.
