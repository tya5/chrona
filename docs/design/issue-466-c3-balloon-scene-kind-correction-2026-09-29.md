# #466 C3 — balloon Scene kind correction

The C3 public materializer emits a Theme-bound balloon as one completed
`Symbol` with a closed outline, not a `Rect` or a free `Path`. The 3-OS CI
[run 36450654908](https://github.com/tya5/chrona/actions/runs/36450654908)
exposed stale role admission (`annotation-note-box` allowed only `Rect`) and
stale wording in Specifications 07/08. The geometry and rendered behavior are
correct; the declared Scene contract is incomplete.

Admit `Symbol` as well as `Rect` for all annotation box roles that may bind
`annotationContainer`. `Rect` remains the unbound rectangle; `Symbol` carries
the Layout-completed balloon or image-backed outline, with one resolved paint
and exact bounds. `Path` remains the connector/relation kind. No adapter may
convert kinds or recalculate the outline. Do not special-case only
`annotation-note-box`: the shared Theme token is available to callout,
highlight, note and arrow boxes. Keep their existing property allowlist.

This is a role-contract and normative wording correction, not a new View,
Theme or Scene schema/version. The same CI run also found a builtin float
`sum` in the new route-length ranking; use `math.fsum` for completed float
geometry under the existing Layout precision rule. Route ranking semantics
and the 1024-state bound remain unchanged.
