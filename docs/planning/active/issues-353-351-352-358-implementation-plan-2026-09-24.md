# Issues #353, #351, #352, and #358 — Implementation Plan

**Implements:** `issues-353-351-352-358-output-portability-design-2026-09-24.md`

## P353-1 — Capability diagnostic closure

Update Scene diagnostic detail/message construction, declare Pillow in the
render extra, and add focused malformed/fidelity/limit tests.

**Acceptance:** each code, pointer, offending value/bound, and public message
is asserted; a clean render-extra test collection imports Pillow explicitly.

## P351-1 — Font asset contract and packaged default

Add v0.13 Context schema/contract parsing, font-pair resolver, generator axis
support, Noto font/NOTICE/metrics assets, and package-data inventory checks.
Migrate every public Theme and Context atomically.

**Acceptance:** metrics identity is bound to the actual font, packaged and
snapshot paths resolve identically, missing glyph/file/identity cases diagnose,
and existing Latin contexts retain valid closures.

## P351-2 — Text and output adapter closure

Implement CJK breaking, strict glyph measurement, font-aware PNG/PDF factories
and identities, materializer copying, plus Japanese SVG/PNG/PDF evidence and
documentation.

**Acceptance:** Japanese text measures/wraps without overlap; PNG excludes
system fonts and is byte-pinned; PDF embeds/uses the declared CJK font; every
output failure is pre-emission and diagnostic.

## P358-1 — Layout token interface

Add v0.4 Layout schema/resolver validation and migrate public Layouts/Themes.
Add a fixed-appearance composition pair and negative contract fixtures.

**Acceptance:** declaration/use equality and Theme type/value are enforced;
portable Layout pairing does not change Theme/Scheme; overflow remains its own
diagnostic.

## P-Release — Publication gate

Run focused tests per slice, full pytest, all declared materializers, Japanese
SVG/PNG/PDF evidence checks, generated-output audit, conformance/structural
gates, wheel smoke, and GitHub CI.  Publish a release review, comment evidence
on all four Issues, and close them serially only after remote verification.
