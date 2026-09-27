# Implementation Plan Amendment — Reuse the Icon Catalogue (#465)

**Corrects:** the [implementation plan](issue-465-image-annotation-container-implementation-plan-2026-09-27.md)'s
I465-1, and the Coordination note's "one decision needed" paragraph.
**Resolves against:** the
[design amendment](../../design/issue-465-image-annotation-container-design-amendment-2026-09-27.md)
and the
[architecture review amendment](../../reviews/current/issue-465-image-annotation-container-architecture-review-amendment-2026-09-27.md).
**Rebase:** `origin/main` at `3aa616c3` (contains #488, `bac5a6c7`, which
kept member labels inside their own row band and changed 7 slides).

## Coordination note

"One decision needed before I465-1 starts" is resolved: reuse
`chrona/icon-catalog/v0.3`. Both remaining coordination risks stand
unchanged (avoid the shared `02-programme-board` Theme/View #466/#467 are
patching; use a new gallery document instead). Add one more: **#488
changed 7 committed slides' member-label geometry.** Before I465-6 bumps
any corpus count, re-read the count's current value on this rebased base,
not the value recorded in the original implementation plan or review —
both were written before #488 landed.

## I465-1 (replaces the original slice)

## I465-1: container artwork as an icon-catalog PNG entry

**Owners/files:**
- `tools/generate_container_image_placeholder.py` (new): a small
  deterministic script that emits one repository-owned nine-slice PNG (a
  bordered panel, no photographic content) and normalizes it into a
  `chrona/icon-catalog/v0.3` PNG entry document (reusing whatever helper
  `src/chrona/presentation/icons.py`'s importer already exposes for
  writing a normalized entry, so the entry's shape is provably identical
  to an ordinary imported icon's).
- No new schema file. No `contracts/resources.py` registration change. No
  `render-context` version change.
- The generated catalog document lives under a location consistent with
  existing example/packaged catalogs (confirmed against repository
  convention — e.g. alongside the HALCYON gallery example's own pinned
  `iconCatalogs` input — before creating it, since it is pinned by a
  Context exactly like any other icon catalog).

**Focused tests:**
- the placeholder-generation script is deterministic (byte-identical PNG
  and catalog document across two runs);
- the generated document round-trips as an ordinary `chrona/icon-catalog/v0.3`
  document through existing icon-catalog parsing/closure code, with no
  code path change required to accept it (this is the direct evidence that
  no new resource kind was needed);
- a Context pinning this catalog resolves `set:name` for the new entry
  through the existing `iconCatalogs` closure.

**Public evidence:** none yet (no Theme/View consumes this entry until
I465-2/5).

**Gate:** focused tests only.

## I465-2 through I465-6

Unchanged from the original implementation plan, with one substitution
throughout: wherever the original plan says "resolves the `image`
reference against the pinned `containerImageCatalogs` closure," read
"resolves the `image` reference against the pinned `iconCatalogs` closure"
(the same closure `theme_tokens.py` and Layout already consult for icon
requests). No other file, test, or gate changes.
