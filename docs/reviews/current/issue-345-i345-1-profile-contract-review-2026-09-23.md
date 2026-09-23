# #345 I345-1 Profile Contract Review

**Decision:** Accepted

Theme v0.5 and Render Context v0.9 replace their preceding public contracts in
one migration. Every public Theme and Context now declares the new version; all
Contexts name the baseline visual profile. The typed closure carries that exact
profile without an adapter default. Draft and materialized Context generators
also emit v0.9 baseline profiles.

The new Theme vocabulary only names closed token bindings and Scheme-bound
color properties. It introduces neither literal colors nor target syntax.
Profile selection is a Context evaluation input, not a package or renderer
hint. Old schemas and readers are removed; focused schema, contract, closure,
color, CLI, and inventory tests pass.
