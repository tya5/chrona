# Implementation Amendment — Onboarding Ingress Quality (#378)

**Design correction:**
`issue-378-onboarding-ingress-quality-correction-2026-09-26.md`.

## Q378-1 — Restore layer direction

Replace the preset copy use case's operational parser import with direct
validation against its packaged schema. Preserve the existing error code and
all five copied bundle results. Focused preset copy/render tests and
`tools/check_import_direction.py` must pass.

## Q378-2 — Complete contract and policy evidence

Annotate all live nodes of `preset-library-v0.1` and `theme-v0.12` schemas,
with valid examples for pattern nodes. Classify the derived Theme's canonical
identity comparison in the declared-value policy. Regenerate only the CLI
reference, diagnostic inventory, and declared-value inventory from their
tools. Run their `--check` modes and the complete conformance catalogue.

## Q378-3 — Publish and resume

Run focused preset, Theme, schema, and inventory tests plus the public
materializer byte check. Publish the correction as one coherent code/evidence
unit; review the CI outcome once it completes. Resume I378-2 only from the
corrected public commit. This amendment does not close #378 or substitute for
the later literal onboarding acceptance review.
