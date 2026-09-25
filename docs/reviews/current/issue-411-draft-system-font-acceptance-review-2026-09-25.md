# Acceptance Review — Draft System-Font Provider (#411)

**Design:** `2ff688de`, `8cca9120`, `25a5612a`.
**Implementation:** `3207b73c`, `724d3206`.
**Decision:** accepted for release.

## Delivered behavior

`chrona render --system-fonts` is an explicit draft-only capability.  It
derives one uniform primary family/weight from Theme, resolves an exact local
OpenType face through the fontconfig port, verifies name-table metadata,
generates the existing v3 metrics document from those exact bytes, and gives
the resulting metrics to Layout.  Draft PNG receives only that resolved file
while retaining `skip_system_fonts=True`; SVG receives completed geometry.

The resolution is held only by `DraftRender`/`RenderRequest`.  Context
environment data and serialized Scene do not contain the process-local path.
Immutable Context rendering, materialization-shaped callers, and draft
PDF/Typst/TikZ reject it with `E_FONT_SYSTEM_IMMUTABLE`.  A missing bridge,
missing face, malformed face, bridge substitution, or heterogeneous Theme
diagnoses explicitly rather than falling back.  This is the #400-relevant
control: an observer cannot receive silently measured/painted different font
bytes.

The first release deliberately requires one face across typography roles.  A
role/face metric catalog is a separate #410 measurement-contract extension;
the system provider does not conceal that limitation by synthesizing a weight.

## Evidence

* Resolver tests use the repository Noto face through a fake bridge and cover
  exact identity/metrics, numeric feature metrics, substituted family,
  missing path, malformed bytes, and unavailable bridge.
* Draft closure and renderer tests prove opt-in runtime-only state, uniform
  Theme enforcement, target rejection, exact PNG handoff, no Scene host path,
  and immutable-call rejection.  The focused set passed **34 tests**.
* `pytest -q -n 4` passed: **859 passed, 19 skipped**.
* `python conformance/run_conformance.py` passed after adding the explicit
  `chrona render` provenance classification for the volatile byte-identity
  comparison.  Documented-command, reachability, Scene delivery, Layout sum,
  View dispatch, semantic registry, import-direction, encoding, and coverage
  checks passed.
* `pytest -q tests/integration/test_materialize_example.py::test_declared_examples_reproduce_by_public_cli` passed.  No public Context,
  Scene, or SVG was regenerated because host-font state is intentionally
  excluded from corpus evidence.
* A fresh primary wheel was **2,647,545 bytes** (under 5,000,000) and its
  installed-wheel smoke passed.  On this authoring host, real `fc-match`
  substituted Verdana for unavailable Noto Sans and the CLI correctly emitted
  `E_FONT_SYSTEM_MISMATCH`, confirming no silent fallback.

## Architecture result

The authority chain remains Theme → draft resolver/metrics → Layout → Scene →
adapter.  No Context schema provider, host path locator, adapter-local font
selection, or compatibility reader was added.  The declared-font guide and
CLI reference document the nonportable, SVG/PNG-only opt-in and its explicit
failure modes.
