# Architecture Review — Detail-Panel Visual Reservation Correction (#445)

**Correction under review:** `issue-445-detail-panel-visual-reservation-correction-2026-09-26.md`  
**Status:** Accepted.

The correction identifies a real Layout-only dependency: icon reservations
change text measurement, and text measurement determines panel block extent.
The approved order computes both before Scene projection.  Extracting a shared
private reservation helper is preferred to duplicate geometry arithmetic or a
second post-icon reflow pass.

Implementation must prove that a detail visual uses the completed text
baseline, that its reserved inline width is applied exactly once, and that
suppressed optional text cannot receive a visual target.  No new cross-layer
contract, renderer feature, or View syntax is authorized.
