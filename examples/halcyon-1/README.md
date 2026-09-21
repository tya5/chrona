# HALCYON-1 smallsat mission

A fictional 26-object, 24-dependency spacecraft programme from preliminary design review to
first light, rendered three ways from one plan. Dates, observations, holidays and risks are
demonstration data.

| Slide | View | Layout | Theme / scheme |
|---|---|---|---|
| `mission-brief` | gates plus the critical spans | `briefing` | `briefing` / `mission-light` |
| `programme-board` | every object, grouped by owning team | `wallboard` | `wallboard` / `control-room-dark` |
| `launch-campaign` | the launch phase only | `print-portrait` | `print` / `print-mono` |

`generated/<slide>.svg` is produced by `chrona render-review` through
`tools/materialize_example.py`; do not edit it by hand.

## Target slides

`slides/<proposal>/` holds **hand-drawn target renderings, not renderer output**: the same
three views drawn in three layout proposals (`board`, `sidebar`, `dossier`). They are the
picture issues #41, #42 and #46 aim at, and the yardstick for the work those issues track;
`generated/` beside them is what the renderer produces today from the same project. The
generator is `docs/research/presentation/halcyon-1-target-design-2026-09-21/render_mocks.py`.
