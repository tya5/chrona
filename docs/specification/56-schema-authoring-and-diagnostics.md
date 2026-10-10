# Schema Authoring and Diagnostics

**Status:** Accepted (amended 2026-09-23; annotation-applicator correction; shared schema parts 2026-10-01)
**Depends on:** [05 Project Format](05-project-format.md), [09 Application
Architecture](09-application-architecture.md), [13 Presentation Format](13-presentation-format.md),
and [32 Repository Layout](32-repository-layout-and-packaging.md).
**Owns:** author-facing schema annotations, structural-validation explanations,
the live-schema documentation-reference gate, the shared schema parts (§7), and
the Project schedule union's discriminated successor.  It does not own semantic scheduling rules or a
renderer diagnostic surface.

## 1. Decision

Schemas are an author-facing reference surface.  Every live authorable shape
MUST have concise schema-owned descriptions and, when the shape is non-obvious,
an example.  Structural validation MUST return one deterministic explanation
with the resource identity, RFC 6901 instance pointer, failed rule, and useful
expected values.  It MUST NOT return a Python traceback, a flat schema error
list, or recover by choosing another syntax.

The Project schedule union moves from the ambiguous v0.5 `mode: fixed` pair to
the fully tagged v0.6 vocabulary: `fixed-point`, `fixed-span`, `scheduled`, and
`rollup`.  This is a clean contract migration: no parser accepts v0.5 fixed
syntax after first-party migration.

## 2. Schema annotation profile

An **author-facing node** is a reachable schema node that an author can select,
write, omit, or violate: a document/root definition, object property,
array item, branch, enum/const, pattern/range constraint, or required
combination.  Pure reuse plumbing (`$ref` wrapper with no local assertion) and
implementation-only inventory/example schemas are not author-facing.

Every author-facing node MUST have a `description` that states its intent and
constraints in author language.  A node with an awkward shape, a branch choice,
or a non-obvious format MUST additionally have at least one valid `examples`
value.  Descriptions do not restate JSON Schema keywords mechanically and do
not promise semantic behavior owned by a later validation stage.

The repository supplies a schema-annotation lint over all `live` entries in the
schema inventory. It traverses every reachable schema applicator, including
every `allOf` branch and nested `if`, `then`, `else`, and `not`; it never treats
an implementation container such as `properties` as a schema node. A pattern,
format, conditional form, or `allOf` wrapper with a local assertion is
non-obvious and MUST carry a valid example. A pure `$ref` reuse branch remains
exempt; a `$ref` combined with a local constraint is not pure reuse. The lint
validates every example in its enclosing schema context and reports a
schema-location pointer for defects.

An `allOf` branch that only carries a structural composition into its parent is
traversed but is not a second author-facing node: its ordinary property prose
belongs to the owner schema rather than being duplicated under the composition
carrier. This exemption never suppresses a nested applicator or a local
reference constraint; those are discovered and checked at their own branch.
It is run in conformance and before generated reference publication. Generated
reference may consume this metadata, but tutorials remain independently
authored.

## 3. Structured validation explanation

All schema ingress boundaries use the same immutable internal value before
mapping to their existing public error types. An ingress supplies its known
resource kind and identity; identity is absent when malformed input cannot
safely establish one:

```text
SchemaViolation {
  resourceKind: string | absent
  resourceIdentity: ClosureIdentity | absent
  instancePointer: RFC6901 pointer
  rule: enum | const | required | additionalProperties | type | range | pattern | format | union
  expected: ordered, JSON-safe values or form descriptions
  actualKind: string | absent
  message: deterministic author-facing explanation
}
```

`instancePointer` identifies the failing input value.  For a missing required
member it identifies the containing object; the message names the missing
member.  For an unexpected member it identifies the containing object and
names the member, including one deterministic near-name suggestion when the
Levenshtein-free `difflib` similarity threshold is met.  Enum/const messages
show the allowed literal values in schema order.  Numeric, length, and pattern
messages name the declared bound or format.  A `format` failure (for example
`date`) reports `expected` as a description of the format, such as
`YYYY-MM-DD calendar date`, and never the offending value.  No raw value is echoed when it may
contain large or sensitive user content.

The selection algorithm is deterministic:

1. collect JSON Schema errors;
2. recursively reduce branch contexts;
3. if an input has a declared discriminator, select its matching branch and
   report that branch's most specific violation; an unknown tag reports the
   allowed tags once;
4. for key-shape unions, report the most-specific matching form or a compact
   ordered list of valid forms; do not invent a tag. A union branch that only
   references a shared schema part (`urn:chrona:` `$ref`) is described by the
   part's definition, so moving a form into a part does not change the message;
5. rank remaining errors by deepest instance pointer, keyword specificity,
   schema order, then message; and
6. construct `SchemaViolation` from the selected error.

Presentation contract parsing maps this value to `SchemaContractError` and
then the existing `E_<KIND>_SCHEMA` / `sourceRef` CLI surface.  Core Project
validation maps it to `Diagnostic("E_SCHEMA", message, pointer)`.  Both retain
their existing semantic validation phase; this shared helper performs no
semantic normalization and is not imported by View, Layout, Scene, or renderer
code.

Operational resource, command, and authoring ingress boundaries use the same
reducer before mapping to their stable existing error codes. They may retain a
smaller public error record, but must not expose raw `jsonschema` wording.

### 3.1 Unsupported presentation resource versions (#489)

For any resource kind registered by the presentation contract schema registry whose declared string `version` is not
registered, ingress MUST refuse the resource with `E_RESOURCE_VERSION_UNSUPPORTED`,
resource-local `sourceRef: /version`, and an author-facing message naming the
resource kind, established id when available, found complete version, and all currently supported complete
versions in stable order. The supported set comes from the contract schema
registry. Missing and non-string versions retain their existing malformed-envelope
diagnostic; they are not labeled as unsupported historical versions in this
change. Unsupported kinds and supported-version body schema faults also keep
their separate diagnostics. No stale version is silently
upgraded or rendered with a fallback contract.

For a declared member of a locally copied builtin preset, the CLI additionally
names the catalogue preset id and instructs a new `chrona preset copy <id>` into
a new directory followed by re-applying edits. This command-specific remedy
belongs to the CLI and only applies when member provenance is established; a
stale explicit override or standalone resource does not inherit it. The
contract and closure layers preserve typed version evidence and the pointer,
including in multi-resource ingress findings, without carrying command text.

### 3.2 Schema version evolution (#591)

For View, Layout Profile, and Project schemas, an additive optional property
MUST be added to the current schema version in place, without a version bump,
when omitting it preserves the resource's prior behavior. A schema-level
`default` annotation does not set a runtime value; the owning consumer MUST
provide and test the behavior that omission requires. Theme schema additions
follow the same rule. Adding a tagged branch to an existing discriminated union
is a widening and is treated like an optional property: it is made in place,
with one L1 delta entry in the expected-deltas file, when no existing
document's verdict or behavior changes (precedent: the View `end` anchor
endpoint in v0.28; the Project `scheduled-point` schedule mode in v0.7).

A version bump is reserved for an incompatible contract change: removing,
renaming, or retyping an existing field; changing an existing field's default
behavior; adding a required field; or another change that makes an existing
resource invalid or changes its behavior. When a bump is required, batch the
pending incompatible changes into that version. Do not silently upgrade a
stale resource; the unsupported-version behavior in §3.1 remains in force.

Theme v0.15/v0.16 (#1088) retires the content-box `edge` token and role member.
v0.15 is the complete authored contract; v0.16 resolves a pinned v0.15 base
and validates the effective body against v0.15. First-party Themes, derived
pins and fixtures migrate atomically before v0.11/v0.12/v0.13/v0.14 readers
are retired and their schemas archived. Old versions are unsupported, not
silently converted. Kind-painted box borders retain `annotation-kind-accent`
ink; migrate `{side, size}` to `annotationContainer.border.<side>` with
`{width: size, paint: kind}`, removing unused edge values too. This knowingly
moves the strip from the inset content box to the full outer border.

Conformance compares newly introduced schema-inventory predecessor/successor
pairs for View, Layout Profile, and Project. Transitions already published when
this rule was adopted (through View v0.28, Layout Profile v0.9, and Project
v0.7) are historical and are not retroactively rejected; Project v0.6→v0.7,
for example, contains optional additions. It MUST fail a new version bump
when, after normalizing the corresponding version strings at `$id`,
versioned `title`, version `const`, and only the root schema
`examples[*].version` values equal to those version strings, the entire schema change consists
of one or more insertions of optional property declarations under object
`properties` maps, with no other example, title, or identity
change is normalized. Each inserted property name MUST be absent from the
containing object's `required` list; that list and all existing schema nodes
must remain unchanged. Each new property subtree may define its own
constraints, but no existing assertion may change. The comparison is structural,
not a proof of runtime behavior; omission behavior remains the responsibility
of focused consumer tests. If a composition or conditional requirement makes
optional status ambiguous, conformance MUST report the comparison as
unsupported or fail closed rather than classify the change as additive. A
version bump containing an incompatible schema change is outside this
additive-only failure rule.

Schemas check the shape of a date, not the calendar. Every ISO date field is
declared with a pattern (`^\d{4}-\d{2}-\d{2}$`, the `isoDate` definition of the
common schema part) and no schema asserts `format: date`; the validator factory
installs no format checker. A string of the right shape that is not a calendar
date (for example `2026-02-30`) is refused later by the consumer that reads it (Project
reports `E_SCHEMA` "Expected ISO Date"), not by the schema. The `format` rule in
§3 stays implemented for a schema that asserts a format. Making a schema refuse
impossible dates, or narrowing the pattern (ASCII digits, no trailing newline), changes
which inputs a schema accepts and moves a code, a stage and a message, so it follows the version bump
rule above. The decision and its revisit condition are recorded in the #662 design (D2, D3).

A refactor that leaves every schema's dereferenced form unchanged (a literal replaced by a `$ref` to an identical shared
definition, §7) needs no bump and is proven by the equivalence gate's structural layer. A change that refuses earlier an
input the consumer already refused later, such as a path guard in a command schema, may be made in place when every
working input stays accepted; the moved diagnostics are listed in the gate's `expected-deltas` with a test each, and
any input that worked and is now refused is named in the change as a narrowing.

**Store addresses (#710, owner decision 2026-10-01).** Every live Store address site references the strict
`storeAddress` definition of the common part: segments of `[A-Za-z0-9._-]` joined by single `/`, no
empty or all-dot segment (`.`, `..`, `...`), no leading `/`, `:`, backslash, NUL, control character, space or
non-ASCII character, and no trailing newline. The definition refuses inputs the loose `relativeAddress` family
accepted, so it is a bump, not an in-place change, for each kind that adopts it, even though the code guard
(`chrona.core.store_address`) already refuses the unsafe ones at every reader: the schema also closes the
character set and moves the refusal to the earliest stage. Layout Profile v0.9 becomes v0.10 (`extends.address`) and
Render Context v0.16 becomes v0.17 (every pinned `reference.address`, which had no guard at all, and the font
locators), Command Request v0.2 becomes v0.3 (its Store references, and `snapshotId` as one segment), Automation
Result v0.1 becomes v0.2 and Snapshot Reference v0.2 becomes v0.3 (both through `revision-store-resource-ref-v0.2`);
the predecessors were `transitioning` (all but Snapshot Reference v0.2 are retired, below), new Contexts and every Draft closure are v0.17, and each committed or packaged Context and Layout Profile was re-pointed by a version-string edit that the gate's L2
layer proves changes no verdict. Snapshot Reference v0.2 cannot be retired the way the others can: its instances are
immutable, content-pinned and already in operators' Stores, so the predecessor stays readable for as long as such a
baseline can exist, and the bump only changes what new writes emit (the writer emits v0.3 only; its fallback to v0.2 for
a loose legacy address was removed by #731). The inputs each site now refuses are listed as L3 `expected-deltas`.

*Tightening a further site (#731).* A later address site may move to `storeAddress` in place, without a bump, under the
clause above for a refusal the consumer already makes, only when the consumer refuses every value the stricter definition
refuses at every use of the field, including a document that carries such a value and never has it opened (an icon no view
selects, a reference that is only validated, a packaged entry): the guard that protects the file-opening adapters
does not, by itself, show that. The check is made per site and per refused input against the consumer's own code, and each moved verdict is
an `expected-deltas` line with a test; where it fails, the change narrows what a valid document may contain and takes the
version bump (or is named as a narrowing in the change). The verification for the sites left by #710 is in the #731 design. Two of them moved under this clause once their consumers were made to
refuse the same values: `preset-library` v0.2 `address` and `icon-catalog` v0.4 `source.address` (every declared raster address is checked when the catalog is parsed). Moving a
site from a letter-or-digit-first pattern to `storeAddress` also newly accepts a leading `.`, `_` or `-`, which the shared guard already accepts. Project evidence references stay on the loose
`revision-store-resource-ref-v0.1`: nothing opens them, so tightening them takes a Project version bump.

*Retirement of the #710 predecessors.* A predecessor was `transitioning` with a named `removalSlice`, and its schema
file (archived with `git mv`), its reader registration and its version string are deleted only in that slice, once no
committed, packaged or test document names it; the project has one user and no external Store, so no release of dual
support is required beyond that, and a document that still declares the retired version is an unsupported version (§3.1).
#731 retired `layout-profile-v0.9`, `render-context-v0.16`, `command-request-v0.2` and `automation-result-v0.1` this way.
`snapshot-ref-v0.2` is the exception and stays `transitioning` as a retained read format (its recorded slice is
`issue-731-snapshot-ref-v0.2-retained-for-reads`): only its authoring side was removed, because immutable baselines
already in Stores can never be rewritten. The loose `relativeAddress` and `relativeAddressDotTolerant` definitions are
now unreferenced and may be dropped with a new `common` part version; they are frozen until then and no schema
references them. `revision-store-resource-ref-v0.1` is not retired either: `snapshot-ref-v0.2` still references it, and
`extensions/profiles.py` still uses it to check the `resourceReference` fields (evidence and artifact references) of a Project's profile objects; nothing
opens such a reference afterwards, so moving the check to v0.2 would refuse a document accepted today, which is an owner decision
(the `extensions[].resource` object of Project v0.7 is unconstrained and has no address pattern to tighten). A guard test (`tests/unit/tools/test_store_address_retirement.py`) fails when the set of
predecessors, their removal slices, their reader registrations or the remaining users of the loose forms change
without this record changing.

*A `transitioning` entry kept on purpose (#715).* `icon-catalog-v0.3` stays `transitioning` for the bundled Material catalog, which is vector-only (no raster `address` exists for its loose
pattern to check), trusted packaged data, and covered for v0.4 catalogs by the parse-time `storeAddress` check; the owner decided on 2026-10-01 not to migrate that catalog. An inventory entry
may carry an optional non-empty `reason` string, and this entry does: the reason a predecessor is kept is stated where the next reader of the inventory looks, not only in an issue.

Adding a value to an existing `enum` is an in-place widening when every existing resource
stays valid and behaves the same and the consuming code handles the new value. It is not an
optional-property insertion, so the mechanical predecessor/successor check above does not apply; the equivalence gate
lists it as a deliberate delta. View v0.28's annotation anchor `endpoint` gained `end` this way: `end` is the
canonical spelling of a span's end (as in a Project `endpointRef`) and `finish` its alias, and Layout normalises `end`
to `finish` before any identifier is built, so the two spellings produce the same Scene.

### 3.3 Project validation reports every independent mistake (#1303)

Project validation does not stop at the first error. A schema error is one `E_SCHEMA` diagnostic per independent
mistake, in JSON Pointer order, and a `oneOf` over `mode` is reported as the one branch the object's `mode` selects (the
wrapper stays only when no branch is selected). A message for a value that fails a `pattern`, `format` or `enum` ends with
`, got '<value>'` for a short string, and the date pattern reads `expected a YYYY-MM-DD calendar date`. When every error
lies inside `/objects/<id>` or `/relations/<n>`, the Core rules (references, parents, cycles, endpoints, lag calendars)
still run for the objects and relations that passed, a failed object staying a known id; an error elsewhere ends the run.
An unknown id in a relation or a `parent` names the nearest known id by the rule of the terse compiler
(`; did you mean 'build'?`). For a Project read from a YAML file, `chrona validate` and `chrona schedule` add `sourceRange`
(`{line, column, endLine, endColumn}`, 1-based, one line) to every Core validation finding: the key of
an unexpected or misplaced member, else the deepest node of the pointer that exists. Scheduler findings and the agent
tool rows keep their shape.

## 4. Union policy and Project v0.6

Use a discriminator only where a stable author-owned tag already expresses a
real semantic form.  A union whose alternatives are selected by key shape,
literal scalar type, or conditional constraints remains a documented union;
its diagnostic reports the legal forms rather than fake metadata.

Project v0.6 schedule forms are:

| `mode` | Required members | Completed placement |
| --- | --- | --- |
| `fixed-point` | `at` | point at `at` |
| `fixed-span` | `start`, `end` | span `[start, end)` |
| `scheduled` | `amount` | derived span under existing anchors/constraints |
| `rollup` | none | derived envelope of children |

The v0.6 scheduler maps both fixed tags to the existing authoritative fixed
placement operation.  Endpoint availability, fixed-target constraints,
calendar interpretation, rollup derivation, and all semantic dates are
unchanged.  First-party Project documents, snapshot/context fixtures, profiles
that name the project format, commands, public examples, and conformance
evidence migrate atomically.  The v0.5 schema is removed from the live
inventory and parser mapping at that point; a converter, compatibility branch,
or silent rewrite is out of scope.

## 5. Live documentation references

The schema inventory and each live schema's `$id` are the only source of truth
for authorable identifiers.  A documentation gate scans normative
`docs/specification` files for YAML `version:` declarations and contract
literals.  Each occurrence is explicitly classified as one of:

* **current** — it MUST resolve to a live schema identifier/version; or
* **historical** — it MUST state its successor or archival status and cannot be
  presented as authorable input.

The gate rejects an unclassified occurrence and a current reference that has
no live schema.  `docs/archive` is excluded because it is historical by path;
current specifications are not exempted merely because they describe an older
decision.  This removes drift without pretending historical design records are
current contracts.

## 6. Evidence and migration gates

Implementation requires:

1. annotation-lint failures for missing description/example and an all-live
   positive run;
2. focused invalid Project, View, Theme, Layout, and nested union fixtures
   proving pointer, expected values/forms, and stable one-error selection;
3. Project v0.6 point/span/scheduled/rollup fixtures proving schedule and
   public CLI JSON equivalence in semantic content after migration;
4. negative v0.5 fixture proving no compatibility acceptance;
5. documentation-gate tests for current, historical, missing, and stale
   contract references; and
6. full tests, public materializers, generated SVG diff review, and installed
   package checks.

The schema and prose changes are accepted only together.  Passing a schema
lint while an author receives a generic error, or adding a helpful error while
leaving a live unannotated schema, is incomplete.

## 7. Shared schema parts (#662)

A schema part is a schema file whose `$defs` other live schemas reference by URN, for
example `urn:chrona:common-v0.1#/$defs/isoDate`. There are five: `common` (scalars and
small objects: content identity, date, paths, names, revision, license), `vocabulary`
(finite enums that more than one schema declares, with named subsets), `graphics` (the
bounded drawing vocabulary of the asset schemas), and the two older parts
`presentation-resource` and `revision-store-resource-ref`. A part asserts nothing at its
root, and only a file listed in `chrona.resources.SCHEMA_PARTS` can be a reference
target, so a stray or archived schema file can never become one.

* **Loading.** `chrona.resources.schema_registry()` builds one `referencing` registry from
  `SCHEMA_PARTS`; `schema_validator` (a packaged schema, cached by name) and
  `validator_for_schema` (a caller-supplied schema) are the only places a validator is
  constructed, and a guard test enforces that. An unresolvable `$ref` is a gate failure
  (`E_SCHEMA_REF_UNRESOLVED`), never a runtime fallback.
* **Frozen definitions.** The inventory records a digest per definition (`frozenDefs`,
  annotation-insensitive). Adding a definition to a part is allowed. Changing or removing
  one fails `E_SCHEMA_PART_FROZEN`; it is a new part version, or, for a definition with one
  consumer that is itself being changed in the same PR, a digest update the PR states
  (precedent: `anchorEndpoint`, which gained `end`).
* **A reference keeps the dereferenced form.** A site is its own description plus the
  `$ref`, and the structure it accepts is unchanged: an enum definition has no `type`, a
  nullable form is its own definition, and a context that accepts part of a vocabulary
  names a subset beside the full enum with a test that the subset is contained in it (an
  `allOf` intersection would produce two enum errors). A union branch that is only a `$ref`
  to a part is described through the part's definition (§3, step 4), and each adoption at
  a union is proven by a message-parity test against the inlined twin.
* **Siblings stay separate.** A shape that differs on purpose is not forced onto a
  definition: Scene's circle, rectangle, viewport and tile carry Layout-completed geometry
  without the asset bounds, the loose Store address family keeps today's accepted
  characters, and existing ids keep `minLength: 1`. Each is recorded, with its reason, in
  the copy tests and the #662 design.
* **A part has versions too (#710).** A part is frozen, so a change to a frozen definition is a new
  part file (`revision-store-resource-ref-v0.2`, `urn:chrona:revision-store-resource-ref-v0.2`),
  published beside its predecessor; both are listed in `SCHEMA_PARTS` and stay `live`, because the
  transitioning predecessor schemas that reference the old URN stay readable and a reader still validates against it. The inventory allows two live entries of one kind only
  when every one of them is a part. Adding a definition to a part is not a new version:
  `storeAddress` (strict Store-relative address, owner decision 2026-10-01) was added to `common-v0.1`
  in place; it rejects what the loose `relativeAddress` family accepts, so a kind that adopts it
  takes the version bump of §3.2 (a site never changes to it inside a published version).
* **No inline copy in a live schema.** Each part has a test that no live schema outside
  the parts repeats a pattern, shape or enum the part defines, with an explicit allowlist
  of documented exceptions. Historical (`transitioning`) schemas keep their own copies and
  are never re-pointed, because that would change what an accepted historical version
  accepts. Live inventory entries list `consumers` that name the schema
  (`E_SCHEMA_INVENTORY_CONSUMER_STALE`).
* **Validation equivalence.** `python -m tools.schema_equivalence --base-rev <rev>` compares
  the dereferenced form of every schema (L1), the verdict of every committed document (L2)
  and the diagnostic of every probe (L3) with a base revision; a deliberate change is a
  line in `conformance/schema-equivalence/expected-deltas-v0.1.yaml` with its reason and
  test. A schema change that touches a part or a site pastes this output into its PR.
  An L1 entry is meaningful only against the base that predates its PR. Once its PR is merged the entry is stale
  (the base file holds it and the base already moved past `before`): a `--base-rev` run reports it, and fails when it
  outlives its landing commit by more than one later merge that touches `schemas/`. `--prune-stale` retires stale
  entries, each only after proving it against the base it was recorded for (the landing commit's first parent). An
  L2 or L3 entry compares with the recorded baseline, not a base revision, and stays until the baseline is re-recorded.
