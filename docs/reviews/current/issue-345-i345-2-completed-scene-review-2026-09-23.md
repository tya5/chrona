# #345 I345-2 Completed Scene Review

**Decision:** accepted.

`ScenePaint` now carries immutable, renderer-neutral linear-gradient,
drop-shadow, and stroke-finish values.  The sole Theme/Scheme resolver resolves
all colours before Scene construction, checks finite bounded parameters, and
does not expose token identifiers or target syntax.  The Context-selected
profile is represented outside adapters; an unsupported decorative-optional
treatment is omitted during Scene completion, while required treatment is a
stable pre-render failure.

Layout still supplies geometry only.  No Scene field carries a clip rectangle,
and no renderer is consulted by Theme, Scheme, Layout, or Scene composition.
Focused resolver, Scene composition, renderer-free profile, and existing Scene
builder checks passed (`44 passed`).
