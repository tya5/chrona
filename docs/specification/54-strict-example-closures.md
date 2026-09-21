# Opt-in example closure behavior for Issue #54

## Supersession

This specification supersedes the previous strict-example proposal. It preserves the
authoritative #44 contract: `contentIdentity` is optional for normal immutable resource
references, including canonical example contexts.

## Materializer policy

The public example materializer copies every authored context and referenced resource
byte-for-byte. It verifies a `contentIdentity` only when the author supplied one. It does
not add or rewrite identities, and it does not unconditionally invoke the public CLI with
`--require-content-identity`.

The materializer may expose an explicit strict verification option in a future release, but
strictness is not inferred from an example manifest and is not part of the current public
example command.

## Font assets

A font asset without a `contentIdentity` remains a valid optional-pin declaration. A font
asset with a supplied identity is verified against the packaged bytes before render and a
mismatch raises `E_MATERIALIZER_FONT_IDENTITY`. The materializer does not manufacture a
font identity or alter the authored context.

## Evidence

Canonical generated SVGs are verified by materializing their unmodified authored contexts
through the public CLI and comparing bytes in check mode. Pinning is additionally tested
with disposable fixtures: an incorrect supplied resource pin yields `E_CONTENT_IDENTITY`;
an incorrect supplied font pin yields `E_MATERIALIZER_FONT_IDENTITY`. Check and
`--write` share the same validation path, so either failure leaves the expected SVG
untouched.
