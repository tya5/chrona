# Issues #379 and #381 — Template Sentinel Design Correction Review

**Decision:** Accept correction before implementation resumes

## Finding

Removing tracked files does not guarantee that an empty development
`chrona/resources/examples/` directory disappears immediately.  A resolver
that treats any directory at the installed location as a valid template can
therefore select an empty placeholder instead of the authored source tree.

## Correction

Template selection requires the contract-defining `manifest.yaml` child, not
only `is_dir()`.  The same validation applies to the force-included wheel
resource and the development source alternative.  This is a bounded template
identity check, not content discovery or a compatibility path: only the known
requested template and its required root document are considered.

The correction preserves the resource/use-case boundary and makes the
source-mode test represent the post-deletion tree honestly.
