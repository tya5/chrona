# Issue #258 Honest Draft Typeset Targets Implementation Plan

**Design prerequisite:** [accepted #258 design](../../reviews/current/issue-258-honest-draft-typeset-targets-design-2026-09-23.md)

## I258-1 — Explicit descriptor ingress

Add the three conditional descriptor switches to both Draft CLI commands and a
single CLI helper that either returns a complete `TypesetterIdentity`, rejects
missing/partial typeset input with `E_RENDER_TYPESETTER_DESCRIPTOR`, or rejects
descriptor input for non-typeset targets.  Pass the typed value to both Draft
closure entry points.

**Files:** `src/chrona/app/cli.py`, CLI tests.  
**Acceptance:** `--help` exposes the conditional contract; both Draft routes
reject an absent or partial typeset descriptor before rendering; SVG rejects an
extraneous descriptor.

## I258-2 — Remove ambient identity inference

Change the common Draft closure factory to accept the optional typed identity,
include it only for typeset Contexts, and delete executable probing/version
parsing.  Retain target-to-engine/grammar validation in the existing Render
Context schema/parser path.

**Files:** `src/chrona/presentation/model/closure.py`, closure and target
registry tests.  
**Acceptance:** a complete explicit descriptor produces deterministic Typst and
TikZ Draft source without a host executable; wrong engine/grammar rejects via
Context validation; a structural test proves closure has no executable probe.

## I258-3 — Regression and publication gate

Test explicit and guided Draft success, diagnostics, immutable Context
independence, and existing positioned-source order/identity.  Run focused tests,
the complete suite, conformance, all public materializer byte checks, and an
installed-wheel CLI smoke.  Publish the acceptance review, then close #258.

**Acceptance:** no `E_RENDER_TYPESETTER_UNAVAILABLE` Draft route remains; all
advertised Draft targets have a declared invocation contract; immutable Context
behavior and public SVG bytes remain unchanged.
