# Implementation Plan: Draft preset ingress and default (#377)

**Status:** Accepted.

**Implements:** [#377 draft-preset design](../../design/issue-377-draft-preset-ingress-design-2026-09-25.md)

## I377-1 — Typed preset resolver and CLI precedence

Extract one preset-root resolver in `presentation.model.closure` and route
draft `chrona render --preset` through the existing ordinary draft closure
constructor.  Make the four presentation flags optional only after resolver
precedence is complete; retain explicit paths as higher-precedence member
overrides.  Add stable errors for incomplete effective input and invalid
packaged/preset members.

**Acceptance:** equivalent explicit and preset invocations produce identical
Scene/SVG bytes; path traversal and incomplete bundles reject; immutable Context
and guided workspace behavior are unchanged.

## I377-2 — Package the baseline default

Author a small ordinary baseline View/Theme/Scheme/Layout/preset closure below
`src/chrona/resources/presets/default/`, force-include it in the wheel, and
resolve it with `importlib.resources`.  Make a no-preset draft invocation use
that resource only for omitted presentation members.  Add a small Project /
Actual guide and generated CLI reference.

**Acceptance:** a wheel installed outside the checkout renders a no-preset
draft; help names the default and precedence; no repository-relative runtime
lookup or package acquisition exists.

## I377-3 — Verification and release

Add CLI, resolver, package-resource, byte-characterization, and guide-command
tests.  Run full pytest, conformance, structural/documented-command checks,
wheel build/size/install smoke, generated output review, and three-platform CI.
Publish acceptance evidence and close #377 after CI passes.
