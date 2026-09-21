# Materializer closure integrity for Issue #50

## Decision

An example context is an authored immutable closure. The materializer MUST validate and
copy it without changing any authored byte or identity. Generated SVG evidence is valid only
when it derives from that validated closure.

## 1. Authored closure

The authored render-context file, every direct or nested resource reference, and every
declared font asset are authoritative inputs.

For each referenced resource, the materializer MUST:

1. locate the resource only through its declared address and revision token;
2. copy its exact bytes to the temporary local snapshot at the same address;
3. compute the SHA-256 of those copied bytes; and
4. verify any authored `contentIdentity` against that digest.

An absent identity remains absent when opt-in pinning permits it. A present identity MUST NOT
be replaced, normalized, or backfilled. A mismatch fails before rendering with the
resource-reader identity diagnostic. The same rule applies recursively to a snapshot
reference's embedded project reference.

The materializer MUST copy the authored context file byte-for-byte and construct the
top-level local `render-context` reference from the digest of those unchanged bytes.
It MUST NOT serialize the parsed YAML back to the copied context path.

For each declared font asset, the materializer MUST copy the packaged asset bytes and verify
the authored identity when present. It MUST NOT mutate the parsed context's font metadata.

## 2. Derived execution closure

The materializer may emit a separate `closure.yaml` beside its transient render output.
That file is provenance only: it identifies the unchanged authored context reference and
the resolved resource digests observed during validation. It is not a replacement context,
is not fed to the renderer as the authored context, and cannot repair an invalid authored
pin.

## 3. Failure semantics

- stale or incorrect resource pin: `E_CONTENT_IDENTITY`;
- missing resource, unsafe address, or invalid revision: the existing Revision Store
  diagnostic;
- invalid context or manifest shape: the existing materializer diagnostic;
- declared font asset unavailable or identity mismatch: a stable materializer closure
  diagnostic.

Check and `--write` modes share this validation path. `--write` may replace only the
declared generated SVG after successful closure validation and rendering.

## 4. Scene measurements

Scene composition requires every measurement it reads, including `title`. Missing values
MUST fail with `E_PRESENTATION_MEASUREMENTS_REQUIRED`; raw map subscripting is not an
allowed diagnostic surface. Scene fixtures must provide the declared title measurement when
they intend to compose a title.

## 5. Snapshot result contracts

`capture_snapshot` returns a snapshot document, whose project reference is found under
`body.project`. `capture_baseline_v02` returns a flat snapshot resource reference:
`{id, kind, store, address, revision, contentIdentity}`. Consumers and tests MUST use the
contract returned by the selected operation; neither result is a compatibility alias for the
other.

## 6. Evidence gate

The gate covers every manifest context. It first validates original closure pins, then
renders through the public CLI, then compares generated SVG bytes. Re-running the same
validated input must be byte-identical. Tests include positive reproduction and negative
stale-pin cases, so a regenerated SVG alone can never mask invalid authored evidence.
