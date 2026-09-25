# Implementation Amendment — Builtin Preset Genericity (#378)

Amend I378-1: replace catalog entries that point into corpus-specific Views
with package-owned complete generic bundles.  Before publishing the copy
command, run each copied preset against the #376 starter and assert all three
starter object ids appear in the SVG.  Retain gallery links only as evidence;
do not copy Context resource paths into the library.
