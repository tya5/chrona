# Issue 370 diagnostic actionability design correction

**Status:** Accepted correction before I370-1 implementation

## Finding

The initial Issue 370 design incorrectly required a separate allowlist record
for every bare diagnostic construction.  A trial AST extraction shows that one
stable code is intentionally raised at many source sites (notably closure and
contract validation).  This changes policy maintenance without adding a new
human decision, and conflicts with Issue 370's stated gate: an explicit
allowlist for **codes** whose identifier is genuinely the whole message.

## Corrected decision

The generated inventory continues to list every code, site, layer, and
detail-bearing status.  The ingress gate evaluates every site:

```text
ingress site has detail                         -> accepted
ingress site has no detail + code allowlisted   -> accepted
ingress site has no detail + code absent        -> rejected
```

The policy entry is exactly `{code, reason}`.  It is accepted only when the
same diagnostic identifier is a complete actionable message in every
user-facing context in which it is bare.  The report makes all such contexts
visible, so code-level classification is still reviewable.  A code whose
meaning varies by source must gain detail at those sources; it may not use a
generic allowlist reason.

Stale policy entries, duplicate codes, missing reasons, and allowlisted codes
without a currently bare ingress construction fail the gate.  New bare sites
with an already allowlisted code remain visible in the generated report and
require review in normal code review; a newly introduced code fails unless it
also receives an explicit policy classification.

## Architecture review

This correction restores the intended boundary: policy classifies a stable
diagnostic interface, while the inventory exposes source implementation.  It
neither hides source locations nor creates a second error-message layer.  The
production owner still decides whether a code needs contextual detail.

## Required implementation-plan change

I370-1 uses exact code classifications, not source-anchor classifications.
Its focused tests must prove both that a new bare code fails and that a bare
site with an existing allowlisted code remains in the report.
