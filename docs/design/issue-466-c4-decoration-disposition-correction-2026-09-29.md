# #466 C4 — decoration disposition ownership correction

The first C4 public-materializer trial failed with `E_THEME_TOKEN_TYPE`:
classifying `annotation-note-box` as a decoration made Scene call
`ThemeTokenView.background()` on that role. The current Scene builder assumes
every decoration has a `backgroundTreatment`, but the note box is a painted
annotation container, not a background treatment. Its Theme declaration and
completed `Rect`/`Symbol` are valid.

`DECORATION` describes contrast/perceptibility responsibility. It does not
imply ownership of the optional background-treatment property. A Scene
`DecorationDisposition(..., "absent")` is emitted only when the effective
Theme role explicitly declares `backgroundTreatment: none`; an ordinary
painted decoration without that property has no absence disposition and is
proved by its emitted primitive. Add one typed Theme accessor that returns no
background treatment when neither background property is declared, but uses
the existing strict `background()` validation if either is present. The Scene
builder consumes that accessor; it does not inspect raw Theme maps or exempt
the note role by name.

This preserves background-role behavior, note-box decoration witness, Theme
validation, and Scene/adaptor ownership. No schema, View, Layout geometry,
placement, contrast floor or compatibility path changes. Verify a painted
note box, explicit `none`, malformed partial treatment, all public
materializers and the C4 contrast report before acceptance.
