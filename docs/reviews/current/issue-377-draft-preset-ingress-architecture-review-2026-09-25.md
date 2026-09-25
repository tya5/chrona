# Architecture Review: Draft preset ingress and packaged default (#377)

**Decision:** Accepted for implementation planning.

The design keeps the existing authority chain intact: the preset is a typed
bundle of ordinary resources; the resolver validates it; ordinary draft closure
construction remains the only draft ingress; Layout/Scene/adapters are
unchanged.  Explicit CLI inputs win deterministically, while immutable Context
and materializer routes remain fully explicit.  Package acquisition is not
introduced, and installed-wheel resource lookup follows Specification 32.
