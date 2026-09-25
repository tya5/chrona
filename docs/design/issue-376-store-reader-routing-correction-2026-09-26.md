# Design Correction — Store Routing for Initialized Context Snapshots (#376)

**Status:** Proposed for architecture review.

## Discovery

The first #376 implementation test resolved every initialized HALCYON Context,
not only the first slide.  The baseline comparison Context exposed an existing
adapter mismatch: `ConfiguredStoreReader` sent every `snapshot-ref` to
`LocalBaselineRegistry`, while `copy_context_closure` correctly stores a
Context-declared reference with revision `example-v1` below the ordinary
revision-store namespace.  A registry-published baseline instead has the
distinct `baseline:<sha256>` revision token and its resource belongs below the
registry `snapshots/` namespace.

Moving the full Store root to `.chrona/store` makes the mismatch observable;
copying untyped source snapshots beside the registry would duplicate the
closure and still fail the reference's revision/identity contract.

## Correction

`ConfiguredStoreReader` dispatches a local `snapshot-ref` by its typed revision
form:

```text
revision token begins `baseline:` → LocalBaselineRegistry
all other immutable revision tokens → LocalSnapshotReader
```

The registry remains the sole reader for resources published by
`capture_baseline_v02`, whose identity is derived from its baseline bytes.  An
immutable Context snapshot reference is read from the ordinary revision
closure, just like the nested Project it identifies.  Missing/invalid tokens
continue to be rejected by the chosen reader; this correction adds no mutable
source fallback and no dual write.

## Consequence for #376

The explicit HALCYON initializer continues to copy exactly one typed closure
under `.chrona/store/revision-*`.  No root `snapshots/` copy is made.  The
all-Context resolution test is retained as the regression proof, alongside the
existing registry baseline tests.  This is a Store-adapter correction, not a
Context, schema, materializer, or presentation change.
