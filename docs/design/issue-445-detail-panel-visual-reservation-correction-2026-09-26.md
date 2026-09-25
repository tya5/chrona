# Design Correction — Detail-Panel Visual Reservation (#445)

**Corrects:** `issue-445-detail-panel-readability-design-2026-09-26.md`  
**Status:** Accepted correction before implementation.

## Finding

The existing View visual-target feature permits leading/trailing icons on both
`group-detail` and `milestone` text.  Its Layout resolver reduces available
inline text width and can increase a wrapped entry's line count.  Completing
panel height before that reservation would leave final text bounds larger than
the panel that claims to contain them.  Re-running a generic icon resolver
afterwards also cannot repair the vertical cursors of later entries.

## Corrected decision

Detail-panel composition reserves requested leading/trailing visual geometry
before it measures and wraps each entry.  The reservation uses the same
closed VisualRequest, icon asset, typography role, icon scale, and gap
calculation as the existing Layout visual resolver.  A shared private Layout
helper supplies this reservation to both paths; it must not be duplicated in
Review, Scene, or an adapter.

For each detail entry, Layout performs this ordered closure:

```text
closed visual intent -> exact icon/gap reservation -> measured text lines
  -> final entry block/cursor -> final panel slot -> icon baseline geometry
```

The generic visual resolver may then project icons from the already-completed
text baseline, but it must neither apply reservation a second time nor change
completed detail-panel lines/bounds.  It validates that the source lines fit
the pre-reserved allocation.  The final panel extent therefore includes every
icon-induced line and remains the sole block-allocation authority.

## Consequences

- The implementation extracts only a Layout-local reservation/placement
  helper; it does not expose an icon layout type or alter View syntax.
- Unknown icon, duplicate side, impossible reserved width, and invalid icon
  ratios retain their existing Layout diagnostics at the same boundary.
- Visual requests targeting a suppressed `clip-optional` entry remain
  invalid, because the requested semantic text has no projected visual host.
- Focused coverage adds a narrow detail-panel visual fixture proving the icon
  is positioned from the final baseline and does not cause text/panel
  intersection.

## Architecture review

This correction strengthens rather than changes the Intent → Layout → Scene
direction.  Both text and icon geometry are already Layout decisions; keeping
their shared inline budget in one helper prevents a second typography/layout
algorithm from entering Scene.  It remains within #445's panel-completion
scope and does not expand #446's general evaluator.
