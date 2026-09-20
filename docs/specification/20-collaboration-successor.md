# Collaboration and Hosted Synchronization Successor Design

**Status:** Proposed  
**Owns:** collaboration session, merge, authorization, approval, and audit provenance
at the Revision Store and Command boundaries.

## 1. Authority

A hosted service synchronizes immutable Store snapshots and Command records; it does
not become an alternate Project, schedule, or Scene authority. A client reads an
explicit snapshot and submits a typed Command with its base revision. The service
either persists one new snapshot, rejects it as stale, or returns a separately typed
merge proposal. It never silently chooses last writer wins.

## 2. Merge and conflicts

Merge is an explicit operation over identified parent snapshots. Structural conflicts
are represented by stable conflict objects that name both source values, their paths,
and provenance. Semantic conflicts—such as competing temporal placements or profile
changes—remain unresolved until a typed resolution Command selects an allowed value.
The merged result has a new Store-issued revision and records every parent revision.

Automated merge may normalize non-semantic formatting only when byte/content identity
and normalized semantic equivalence are demonstrated. It may not infer user intent,
discard a valid semantic change, alter a fixed placement, or merge derived schedule,
Scene, SVG, or canvas state.

## 3. Authorization, approvals, and audit

Authorization is evaluated at the application boundary before a Command persists. A
policy decision names the actor, authenticated principal, action, target, base
revision, rule/policy version, decision, and time source. A required approval binds the
exact Command fingerprint and expires or invalidates on any payload/base-revision
change. Audit records are append-only observations; they explain acceptance but do not
give an actor a semantic bypass.

## 4. Hosted synchronization

Replication transfers immutable snapshots, content identities, Command results,
conflict objects, and audit provenance. A replica may be behind but must label its
known revision; it cannot claim an unobserved remote tip. Offline commands preserve
their original base revision and undergo normal conflict/authorization checks when
submitted. Presence indicators and cursors are ephemeral collaboration state and are
not Project fields or scheduling inputs.

## 5. Required evidence before implementation

- a schema and fixture cases for stale write, explicit conflict, approved command,
  denied command, and causally-behind replica;
- Revision Store, Application Architecture, Command, Quality, and Federation boundary
  updates plus an ADR; and
- review proving no LWW, unpinned child mutation, or hidden merge of derived state.

## 6. M12 executable profile

A `submitCommand` carries one immutable base revision and canonical command fingerprint.
Policy returns `allow` or `deny` with principal, policy version, and trusted decision
time. An approval carries that fingerprint and an exclusive `expiresAt`; changed base,
payload, principal, or an expired approval rejects before persistence. A stale base
returns `E_COMMAND_STALE_BASE_REVISION` or a Conflict Object, never a write.

A Conflict Object has stable `id`, two parent revisions, `path`, `kind` (`structural`
or `semantic`), left/right values, and provenance. `resolveMergeConflict` names its ID
and one allowed value; it creates one new revision with both parents recorded. Audit
records append command fingerprint, decision, actor, base/result revisions and time.
Replicas retain `knownRevision`; an offline command retains its original base and is
submitted through the same policy/CAS path. No derived schedule, Scene, output, or
Federation child is a mergeable field.
