# Implementation Plan — Footer Side-Content Geometry Closure (#455)

**Design:** `issue-455-footer-side-content-geometry-design-2026-09-26.md`.
**Architecture review:**
`issue-455-footer-side-content-geometry-review-2026-09-26.md`.

## I455-1 — Footer-band completion seam

**Files:** `src/chrona/presentation/layout/surface_composer.py`, focused Layout
tests if a private helper needs direct coverage.

1. Extract the #445 inline downstream allocation into a private footer-band
   coordinator accepting provisional slots and final replacement slots.
2. Preserve the finite footer source set and its provisional/completed union
   calculation.  Translate only the physical downstream annotations slot when
   the completed union grows and its inline interval physically overlaps a
   footer panel.
3. Make the coordinator available to the group-detail/milestone, notes, and
   legend completion paths without changing their source selection or Scene
   composition.

**Acceptance:** the existing group-detail expansion fixture is unchanged;
zero-growth layouts retain byte-stable slots; no Scene module imports a footer
helper or computes a successor coordinate.

## I455-2 — Measured notes completion

**Files:** `surface_composer.py`, `tests/integration/test_render.py`, affected
public source/evidence.

1. Replace the notes font-size step with a completed placement cursor.  Build
   final notes slot extent from the measured cursor while retaining stable
   source order, selected text typography, source content, and slot identity.
2. Route required visible overflow through existing `FitWarning`/canvas
   completion; retain current optional suppression behavior where declared.
3. Feed the final notes slot replacement to the footer-band coordinator before
   annotation text/box/leader composition.

**Acceptance:** adjacent notes have no positive-area overlap; a notes-driven
footer growth preserves the manifest annotations gap; no normal notes output
changes source ordering or typography facts.

## I455-3 — Swatch-reserved legend completion

**Files:** `surface_composer.py`, focused materializer/layout tests,
HALCYON programme-board evidence.

1. Define the text available interval after the existing swatch reservation.
2. For `ellipsize-with-source`, ellipsize the source against that interval
   before placement and retain the unabridged `source_content`.  Validate text
   containment through the final parent slot.
3. For visible overflow, preserve natural text, complete one structured
   warning with the reserved interval facts, and include final extent in the
   completed canvas/footer band.

**Acceptance:** every programme-board ellipsized legend run is contained;
the swatch stays inside its slot; explicit visible-overflow fixture remains a
successful warned result rather than a hidden ellipse.

## I455-4 — Corpus evidence and release gate

**Files:** changed public Scenes/SVGs, diagnostic inventory only if source
literal sites change, and acceptance-review evidence.

1. Regenerate all public materializers once after I455-1 through I455-3 are
   complete.  Review only intended output changes and raster-inspect the
   notes/legend contexts.
2. Run focused Layout/Scene/materializer tests, public byte reproduction,
   schema/inventory and import/delivery gates when affected, and the
   tolerance-aware completed-Scene audit.
3. Publish one atomic implementation commit.  Use the three-OS CI and newest
   Python materializer jobs for the full-suite release gate; do not duplicate
   full local pytest or poll CI repeatedly.

**Release acceptance:** P0 has zero unpermitted project-note overlaps and zero
`ellipsize-with-source` slot escapes.  #446 resumes only after this evidence
and a P0 baseline review record the findings as fixed, never as exemptions.

## Stop conditions

Return to design before implementation if notes/legend completion needs a new
resource syntax, an adapter clip, a Scene layout branch, an unbounded generic
footer rule, or a changed #449 disposition meaning.
