# Issue344 Level 1 — typed Project fields

Status: design record for reviewer review; no product implementation authorized
before review. Baseline: published `main` `690f3549f`. Scope:
[reviewer comment](https://github.com/tya5/chrona/issues/344#issuecomment-6234966270)
(Level 1 only, after #1660). This record changes no schema, code, example or
generated file. It plugs into the field accessor named by the #419 design
([PR #1664](https://github.com/tya5/chrona/pull/1664): "Issue344 plugs into this
same field accessor"); if that PR is not yet merged, this record depends on it
only for that sentence, not for any mechanism.

## 1. Baseline (what exists today)

- **Object fields are free-form.** `schemas/project-v0.7.schema.yaml` gives
  `object.fields` and `entity.fields` as `type: object` with no property
  schema, so any key and any JSON value pass schema validation. Project
  `additionalProperties: false` rejects unknown *top-level* keys and unknown
  *object members*, but never an unknown key *inside* `fields`.
- **The only typed fields today are the profile-package ones.**
  `schemas/profile-v0.3.schema.yaml` defines `fieldDefinition` (`type` in
  string, boolean, integer, number, date, enum, objectReference,
  resourceReference; `cardinality`; `required`; `enumValues`) with
  `profiles.<id>.extends`. `src/chrona/extensions/profiles.py`
  `validate_profiles` applies them only when the pinned
  `implementation-delivery` package is declared and only to objects whose
  `type` is a delivery profile. It reports "Unknown delivery profile field"
  (`IDP-PROFILE-006`), `IDP-PROFILE-001` (required), `IDP-STATE-001` (enum) and
  `IDP-PROFILE-003`; enum is the only scalar type it actually value-checks.
  Pointers are `/objects/<id>/fields[/<name>]`.
- **`fieldRole` is a Project-owned alias.** Project `fieldRoles` maps the
  closed roles `responsible` and `phase` (`vocabulary-v0.1#projectFieldRole`)
  to a field name. `FieldRoleBindings.read` in
  `src/chrona/presentation/model/field_roles.py` resolves either
  `{field: name}` or `{fieldRole: role}` to a key and then does
  `fields.get(key)`; it reads, never rewrites.
- **`colorEncoding` accessor.** View `body.colorEncoding.source` is
  `common-v0.1#projectFieldReference` (`{field}` or `{fieldRole}`). In
  `presentation/model/color_scale.py`, `ResolvedColorScale` stores the resolved
  `source_field` and reads `fields.get(source_field)` per selected object.
  Today it accepts only `str` values inside the declared domain, otherwise
  `E_PRESENTATION_SCALE_VALUE`; a `firstAppearance` domain skips objects whose
  value is `None`. `projection.py` copies `project["objects"][id]["fields"]`
  into the projected item; there is no type information on that path.
- **Where rejection happens today.** Unknown View/Project members: JSON Schema
  (`additionalProperties: false`, Spec 56 pointed diagnostics). Unknown or
  mistyped field *values*: nowhere for plain Projects; only the delivery
  profile above. So a typo in a field name silently yields "absent".

## 2. Literal acceptance (verbatim from the scope comment)

1. A Project declares a typed field and a value on an object without Python; an
   unknown field, a wrong type and an out-of-enum value each fail with a pointer.
2. A View colours planned marks by that declared field through `colorEncoding`
   with no code change, shown on a synthetic fixture and its PNG.
3. Existing Projects without declarations render unchanged (count table).

## 3. Proposed schema shape (for review; not yet written)

**Declaration site.** One optional Project member, `fieldDefinitions`, a map
from namespaced field ID to a definition. It reuses the existing
`profile-v0.3` `fieldDefinition` vocabulary rather than inventing a second one,
restricted in Level 1 to the scalar subset and extended with the applicable
kinds:

| Member | Meaning |
| --- | --- |
| key | Namespaced ID, `<namespace>.<name>` (lowercase `[a-z][a-z0-9_-]*` segments, at least one dot), e.g. `acme.risk`. The ID is the key used in `objects.<id>.fields`. |
| `type` | `string`, `number`, `boolean`, `date` (ISO date via the shared `isoDate`), or `enum`. |
| `enumValues` | Required iff `type: enum`; non-empty, unique, non-empty strings. Forbidden otherwise. |
| `appliesTo` | Non-empty unique list of object kinds (the object `type` identifier). Absent means every object. |
| `cardinality` | Not in Level 1: always one value. |
| `required` | Not in Level 1 (see section 9). |

Values live where they live now: `objects.<id>.fields.<namespaced id>`. No new
object member. `integer` is not added: `number` covers it, and the profile
vocabulary keeps its own `integer`.

**Absent vs null.** Absent key: the object has no value; always valid; the
accessor reports "absent". `null`: an explicit empty value; valid for every
declared type in Level 1, and the accessor reports it as "null", distinct from
absent in diagnostics and in the report counts. Both are "no colour from this
encoding" for a `firstAppearance` domain (existing behaviour: `None` is
skipped) and the existing `E_PRESENTATION_SCALE_VALUE` for a closed domain
(unchanged). Neither is coerced to an empty string, `0` or `false`.

**Pointed errors** (stable codes assigned in slice 1, Spec 56 style, pointer is
the instance location):

- Unknown field: `/objects/<id>/fields/<key>` where `<key>` is
  namespaced-shaped but not declared, naming the nearest declared ID (the
  existing nearest-known-id rule in Spec 56).
- Field not applicable: the key is declared but the object's `type` is not in
  `appliesTo`; same pointer, lists the allowed kinds.
- Wrong type: `/objects/<id>/fields/<key>` with expected type and the JSON type
  found (a string for `number`, `"2026-13-01"` for `date`, `"yes"` for
  `boolean`).
- Out-of-enum: same pointer; lists the allowed values and the nearest one.
- Malformed declaration (non-namespaced ID, `enumValues` on a non-enum, empty
  `enumValues`): `/fieldDefinitions/<id>[/...]`.

**Legacy keys stay free-form.** A `fields` key that is *not* namespaced-shaped
(no dot) keeps today's behaviour: any value, never an "unknown field" error.
Only dotted keys are claimed by the declaration mechanism. This is what keeps
existing Projects valid (section 7); it is a recommendation, see section 9.

## 4. View projection through the same accessor

There is one evaluator: the existing `{field: …}` read. A declared field is
selected by `colorEncoding.source: {field: "acme.risk"}` exactly as
`{field: "owner"}` is today; no View schema change, no new source form, no
profile-specific path. `fieldRole` still resolves a role to a field name through
`FieldRoleBindings`, which may now name a declared ID.

What changes is only what the accessor knows about the field it reads:

1. Project load validates `fieldDefinitions` and every dotted `fields` key
   (section 3) before projection, so the accessor never sees a mistyped
   declared value.
2. The projected item carries the field value as today. The accessor gains an
   optional declared-type lookup (the Project's `fieldDefinitions`, per source
   Project, like `FieldRoleBindings` is captured per source) so that:
   - an `enum` field supplies its `enumValues` as the default closed domain
     when the encoding says `firstAppearance` is not wanted and the View lists
     the domain explicitly, and a View domain value outside `enumValues` is a
     pointed View-to-Project mismatch error rather than a silent empty class;
   - `number`, `boolean` and `date` values are rendered to the domain's string
     form by one canonical rule (decimal `repr` without exponent for numbers,
     `true`/`false`, ISO date) so `color_for`'s `str` contract is kept and the
     same text is used in legends. Whether `colorEncoding` admits non-string
     types at all in this pass is open question 2.
3. Multi-source comparison reads the selected occurrence's own source Project
   declarations and values (per #1664: never an accidental primary-project
   lookup for a snapshot value). A snapshot source without the declaration
   yields "absent", not an error.

Semantics stay with the owners: Project owns declaration and value validity
(Spec 04/56), View owns the field reference (Spec 06/60), Style/Theme own
colours (Spec 49). Layout and Scene are untouched.

## 5. Migration

None expected; verified against the baseline:

- `fieldDefinitions` is an optional additive Project member and omission keeps
  prior behaviour, so Spec 56 section 3.2 requires an in-place addition to
  `project-v0.7` with no version bump and no migration tool. The "optional
  Project properties are backward compatible" owner statement matches.
- Existing Projects have no `fieldDefinitions`, so no dotted key is validated;
  a Project that already uses a dotted `fields` key with no declaration would
  stay valid (rule: no declarations means no claim). The slice 1 inventory must
  count dotted keys across `examples/**` and `tests/**` Projects to confirm zero
  conflicts; a non-zero count changes the rule, not the schema.
- `profile-v0.3` and the delivery validation are untouched. A delivery profile
  field and a `fieldDefinitions` ID may not collide; a collision is a pointed
  error at `/fieldDefinitions/<id>`.
- Expected L1 delta: one admission entry in the Spec 56 expected-deltas file for
  the new optional member. No existing document's verdict or behaviour changes.

## 6. Compatibility with Spec 56 section 3.2

Additive optional property on the current Project version (in place), omitted
means prior behaviour, the consumer (Project validator and accessor) provides
and tests that omission behaviour, `default` annotations are not used as runtime
values. No rename, retype, required member or default change. No new schema
version, no new discriminated-union tag.

## 7. Explicitly not in this pass

`extends` profiles and new object kinds, references between objects
(`objectReference`/`resourceReference`), `cardinality: many`, `required`,
Level 2 derived expressions, Level 3 code plugins, domain packages, a second
evaluator, any View schema change, changes to `fieldRole` vocabulary,
and any edit to `examples/**` (the corpus is not an oracle). The #419 Style
resource and predicates are separate work owned by that issue; this record
only guarantees the field they will reference.

## 8. Slices

Proposed, independently reviewable, not authorized until the record is accepted.

| Slice | Change | Acceptance evidence and side-effect expectation |
| --- | --- | --- |
| 1 | `fieldDefinitions` schema (in-place, `project-v0.7`), Project validator for declarations and dotted `fields` keys, pointed errors, Spec 04/56 text, expected-delta entry, wheel resource sync | Positive and four negative fixtures (unknown, not-applicable, wrong type for each of number/boolean/date, out-of-enum) with exact pointers; dotted-key inventory table over `examples/**` and `tests/**`; corpus render count table: every existing slide unchanged (0 route/label/primitive deltas, 0 new diagnostics). Derived evidence regenerates only for the schema inventory. Rows 1 and 3 |
| 2 | Accessor learns declared types: `enumValues` domain check, canonical string form for number/boolean/date, absent vs null distinction, per-source declarations | Synthetic fixture and PNG: planned marks coloured by an enum field through `colorEncoding` with no View code change; legend entries in domain order; absent and null marks keep role paint; multi-source fixture reading each source's own declaration. Existing `colorEncoding` tests and corpus unchanged (count table). Row 2 |
| 3 | Guide/tutorial line and conformance or gallery fixture, only if slices 1-2 show a usable path | Docs and new synthetic gallery entry; no change to existing outputs |

If #419 V1/S1/S2 change the accessor signature first, slice 2 rebases onto it;
coordinate with dev A before slice 2 starts, since dev A owns #419.

## 9. Open questions and recommendations (none blocks review)

1. **Unknown field rule.** Option A (recommended): only namespaced (dotted) keys
   are claimed; plain keys stay free-form, so existing Projects and typo-prone
   legacy keys behave as today. Option B: when any declaration exists, reject
   every undeclared key in `fields`. B catches typos but breaks the "unchanged"
   guarantee for mixed Projects and ties validity to whether a declaration is
   present. Recommend A; revisit B as an opt-in `strictFields` flag later.
2. **Non-string colorEncoding sources.** Recommend admitting `enum` and
   `boolean` in slice 2 (closed small domains) and deferring `number` and `date`
   colouring to a binning design (no binning evaluator in this pass); number and
   date declarations still validate and project, they just are not valid
   `colorEncoding` sources yet, with a pointed View error.
3. **Declaration site.** Recommend a Project member over a profile package
   because Level 1 must work without pinning an extension package. Later `extends`
   profiles can supply the same `fieldDefinition` shape; one vocabulary.
4. **Namespace policy.** Recommend only a syntactic rule now (dotted lowercase
   segments), with no registry and no reserved `chrona.` prefix enforcement
   beyond rejecting `chrona.` for author declarations to keep it host-owned.
5. **`required` and `cardinality`.** Recommend deferring both; `required` needs
   a story for existing objects and `many` needs list colouring semantics.
6. **Explicit null.** Recommend valid for all types, as above; the alternative
   (null only if `nullable: true`) adds a member for little value at Level 1.
