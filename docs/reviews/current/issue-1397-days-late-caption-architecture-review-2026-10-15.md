# Issue 1397 row 3 — architecture review

Decision: the [caption design](../../design/issue-1397-days-late-caption-design-2026-10-15.md)
is ready for implementation planning. This is a design review, not acceptance
of unimplemented behavior.

| Authority / adjacent contract | Consistency finding |
| --- | --- |
| Specs 04/05, Core deadlines | Carry the existing count and verdict; no Layout date arithmetic or new domain facts. |
| Spec 06, figures and count templates | Shared count forms and parser, closed local placeholder; no fictitious per-object FigureSpec. |
| Spec 07, Theme and typography | Text role supplies text metrics and fill; mark stroke is not repurposed. Optional dedicated role keeps project tuning outside Core. |
| Spec 49, semantic/contrast registry | New caption purpose is ground text at 4.5:1; the provisional 3:1 mark-ink recommendation is rejected. Existing explicit text fallback pattern is retained. |
| Spec 50, Layout closure and collision ownership | Layout owns envelope, measurement and two candidates. Optional captions consume remaining space after existing content; they cannot silently remove a dependency line. |
| Spec 56, schema discipline | Optional in-place View addition references common count format; runtime normalization implements defaults. No resource migration. |
| Scene and adapters | Completed text projection and existing paint gates only; no adapter measurements, template parsing or route changes. |
| PR1521, outlined strokes / wobble | Shared Layout envelope must cover outline and maximum declared wobble even on profiles that omit wobble. Caption tests must pin this integration after row1 merges. |

Independent static audit confirmed the Core count handoff, existing parser,
text placement helpers and obstacle machinery, and identified the substantive
3:1-versus-4.5:1 draft inconsistency. This design resolves it before code.
No examples edits, compatibility shim, new generic figure scope, or global
collision-policy rewrite is justified. Implementation must still prove actual
SVG text, fallback/drop counts, default-off bytes and full release evidence.

Integration exposed an existing invariant: TextPlacement.host_placement_id
is a restricted paint-host link, not generic attachment. The design keeps it
unset for outside captions and carries typed subjects directly for provenance.
This corrects the mistaken host-field mapping before resuming that slice; the
existing host validator and public Scene schema remain unchanged.
