# Issue #354 — Environment Equality and Coverage Label Release Review

**Decision:** Accepted

## Delivered

- Gallery peers now require byte-identical declared `environment`; a mismatch
  raises `E_DESIGN_GALLERY_ENVIRONMENT_MISMATCH:<set>`.
- The network surface evidence is regenerated at the programme board's 1920 ×
  1080 environment.  The set keeps fixed Theme/Scheme and declares only its
  Layout support.
- The gallery index now calls #355's link **Semantic corpus coverage** and
  explicitly states that it is neither presentation-vocabulary coverage nor a
  renderer gate.

## Verification

- Focused gallery validator/generator tests: `7 passed`.
- Corpus coverage, gallery inventory, and gallery generation `--check` all
  passed after regeneration.
- Conformance and module reachability, Scene primitive delivery, View dispatch
  reachability, and import-direction gates passed.
- GitHub Actions run 35944862051 passed on Ubuntu and macOS for `14a9571`.

## Architecture review

The correction constrains only declared documentation evidence.  It does not
introduce viewport policy into Layout or Scene, widen semantic corpus coverage
into presentation-schema ownership, or add a runtime dependency from gallery
tools into materialization.
