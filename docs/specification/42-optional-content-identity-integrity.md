# Optional Content Identity Integrity Policy

**Status:** Design complete (Issue 44); default revised by Issue 1567

## Policy

A resource reference MUST identify a Store, immutable revision, and address. `contentIdentity` is an optional exact-byte pin everywhere a reference carries one: a Render Context and its inner references (Layout Profile, icon raster sources, font metrics and font assets, previous-Scene artifact pins), a Theme `extends` declaration, a snapshot, a baseline, and an extension package reference. An absent `contentIdentity` is accepted with no error, no flag and no Store setting; the reader computes the identity of the bytes it read and carries it in the resolved closure and result. When a pin is supplied it MUST match, or the read fails with `E_CONTENT_IDENTITY` (or the resource-specific identity diagnostic, for example `E_ICON_ASSET_IDENTITY`, `E_MATERIALIZER_FONT_IDENTITY`). A supplied pin is never replaced, normalized or backfilled.

Reproducibility is not a goal of the format: the immutable revision token and the version control history say which version is meant, and a hand-maintained hash only adds a step to every edit. Authors and guides therefore MUST NOT tell a user to compute a hash. A user who wants a pin may keep one.

## Store read path (Issue 1567, supersedes Issue 723)

`LocalSnapshotReader`, `LocalBaselineRegistry` and a Store config that omits `integrity` accept an omitted identity. `E_CONTENT_IDENTITY_REQUIRED` is raised only by a Store that explicitly declares `integrity: required`, an opt-in strict mode for a team that wants every reference pinned; `--allow-missing-content-identity` lowers that explicit setting for one call and is otherwise accepted with no effect. `chrona init --example` writes no `integrity` entry.

## Optimistic locking

Commands and baseline operations keep `expectedContentIdentity` as an optional optimistic lock: a supplied value is verified; an omitted one relies on the immutable revision token. Result references always include the computed identity, as information.

## Boundaries

Schemas permit omission. Readers compute identity. Closure and result artifacts expose computed identity. No latest lookup or mutable tip is introduced. The derived-evidence byte comparison in CI is a regression oracle and is unchanged. The identities inside generated Scene and metadata documents, and the self-identity framing of a profile package document (Specification 62), are computed outputs, not authored pins.
