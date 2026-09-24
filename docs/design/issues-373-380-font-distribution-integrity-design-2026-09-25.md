# Font Distribution Integrity Design (#373, #380)

**Decision:** Accepted.

## Scope

This design corrects four residual distribution defects without changing the
semantic-to-surface pipeline: remove a data-redundant fallback literal; gate
the primary wheel; make the optional CJK provider truthful in development; and
make draft substitution warnings report what a target actually drew.  It also
repairs the Japanese provider's legal notice and face metadata through a
reproducible build boundary.

No Project, Context, Layout, Scene, materializer, renderer capability, or
font-metric schema version changes.  Existing public artifacts will change
only because the JP font bytes and their pinned identities change once.

## 1. Data-owned fallback selection

`draft-substitute-font-metrics.yaml` remains the sole declaration of the
fallback face.  Font-metric resolution loads that descriptor, validates its
single selected same-weight asset through the ordinary descriptor path, and
uses its declared `family`.  It does not name a family, weight, resource file,
or provider in product code.

The fallback is still a metrics-only draft policy.  It is neither a host-font
lookup nor a renderer fallback, and immutable Context/materialization continue
to reject `missingFont: substitute`.

## 2. Measurement ledger versus target warning

`FontGlyphSubstitution` remains a target-neutral record made while Layout
measures text.  It cannot truthfully state whether any target drew a glyph.

`render_review` projects the completed metric ledger into a new output-warning
record after the artifact target is known.  The CLI serializes that record.
For PNG and PDF, every fallback-only glyph is reported with `drawn: false`:
Chrona gives those adapters only the declared primary font bytes, and the
metrics-only fallback supplies no outline.  SVG warnings omit `drawn`; Chrona
serializes text but does not rasterize it, so it must not claim browser display
behavior.

The stable warning payload retains `W_FONT_GLYPH_SUBSTITUTED`, requested and
fallback families, weight, code point, and source text.  It gains the optional
boolean `drawn` only where Chrona owns the rendered result.  The projection
lives in the RenderReview use case, not FontMetrics, Layout, Scene, or an
adapter; the adapter is not asked to reinterpret a warning.

## 3. Truthful package and test boundary

The root distribution must not advertise an extra whose dependency cannot be
resolved from a package index.  Remove `fonts-cjk` until the provider is
actually published.  The supported repository development setup installs the
provider explicitly from `packages/chrona-fonts-noto-cjk`; release automation
will restore a version-pinned public dependency only as part of a real provider
publication.

CJK-specific tests use an explicit optional-provider availability guard with a
stated skip reason.  The normal primary editable install therefore has a green
suite.  CI continues to install the local provider before conformance and the
CJK matrix, so provider/corpus evidence is not silently weakened.

## 4. Primary wheel guard

A small standalone wheel-size checker receives the built primary wheel and
fails when its compressed byte length is **5,000,000 bytes or more**.  It names
the actual size, threshold, and wheel path in its diagnostic.  The checker runs
after the existing wheel build locally and in each CI matrix job, before wheel
installation/smoke.  It selects exactly one primary `chrona-*.whl`; the CJK
provider has its own distribution and is deliberately excluded.

This is a release-policy guard, not a package loader or resource test.  The
installed-wheel CLI smoke remains the proof that the admitted resources work.

## 5. Japanese provider build and provenance

The provider's current static faces identify **Source Han Sans 2.004**:
their copyright record names Adobe and their original Reserved Font Name is
`Source`.  The authoritative notice is Adobe's Source Han Sans `2.004R`
`LICENSE.txt`, not Noto Sans Latin's notice.  The provider carries a byte-copy
of that supplied notice and a small provenance record naming the upstream
repository, tag, input paths/identities, selected weights, notice identity,
and generated artifact identities.

A provider-build tool is the only writer for the checked-in provider faces,
metrics, descriptor identities, notice, and provenance record.  It takes
explicit local source-face and notice inputs; it never fetches from the
network, reads the destination as an input, or borrows an unrelated license.
The release procedure obtains the pinned upstream inputs separately, verifies
their identities, and invokes the tool.

For each selected 400/700 static face the tool:

1. loads the declared input face with fontTools;
2. rewrites every platform/language name-table record for IDs 1, 2, 3, 4, and
   6 to the descriptor's `Noto Sans JP` family and its `Regular` or `Bold`
   subfamily, including a unique/PostScript name that contains no `Source`;
3. preserves copyright, licensing, manufacturer, and `OS/2.usWeightClass`;
4. writes the static output deterministically;
5. regenerates metrics from those exact output bytes; and
6. copies the supplied upstream notice and writes regenerated identities into
   the descriptor and provenance record.

This is a modified OFL font.  Removing the `Source` family/unique/PostScript
names is required by the upstream Reserved Font Name while retaining the
copyright and notice acknowledges the source.  The tool does not claim that
the faces are unmodified upstream Noto assets.

## 6. Japanese corpus migration

The provider descriptor identities are input to the Japanese Context.  Once
the provider build changes the two font and metric identities, regenerate the
affected `controller-z-ja` Context and committed SVG through the public
materializer in one atomic reviewed slice.  No hand edit of the SVG or Context
identity is allowed.  The result must reproduce byte-identically from the
new declared closure and continue to render SVG, PNG, and PDF with the local
provider installed.

## Rejected alternatives

- Retain the `fonts-cjk` extra and document that it currently fails: an
  installable contract cannot be conditional on a private checkout.
- Make all CJK tests unconditional: it makes optional provider absence look
  like a primary-product failure.
- Skip CJK tests in CI: it abandons public corpus/provider evidence.
- Put `drawn` on the metric substitution: metric resolution has no target and
  would make an untrue rendering claim.
- Let PNG/PDF use a system font for the fallback: it breaks the declared-byte,
  identity-pinned raster contract.
- Copy or edit a Latin Noto notice: it neither describes the source face nor
  preserves the Source Han Sans notice.
- Patch binaries or generated JSON by hand: it leaves no reproducible source
  for the next provider release.

## Acceptance

- Core product modules contain no font family, weight, or asset-name literals
  outside declared resource data.
- A primary wheel at or above 5,000,000 bytes fails locally and in CI.
- A plain primary editable install has a green suite; CI explicitly retains
  CJK provider and corpus coverage.
- PNG/PDF substitute warnings say `drawn: false`; SVG does not claim a browser
  drawing result.
- The provider notice, provenance, name tables, metrics, descriptor, Context,
  and generated Japanese evidence agree on the same new bytes.
