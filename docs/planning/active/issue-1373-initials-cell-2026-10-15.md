# #1373 row 2: the `initials` cell transform

Status: design and implementation record, 2026-10-15. Base: `origin/main` a0bfb32ab. Refs #1373.
Normative text: [Spec 46 "Cell transform"](../../specification/46-halcyon-resource-authoring.md). Slice origin:
[backlog slices](backlog-slices-1397-1373-1047-2026-10-14.md) row 2.

## Baseline and acceptance

Issue row 2 (literal): "A `source: {field: owner}` column shows the raw field value; the reference shows initials.
Needs: a closed set of cell transforms in the View column grammar (initials first), applied by Layout, so Scene stays
completed text." Gap report row 2 says the same. Not covered by the issue: the initials rule itself (the slice note
proposes "split on whitespace and hyphen, first letter of each word, upper-cased"); this note fixes the edge cases.

## Grammar

`tableColumns[].transform`: optional, `enum: [initials]`, declared in `view-v0.28` in place (Spec 56 section 3.2:
behavior-preserving optional member, no version bump). Absent: the code path is not entered, so output is byte-identical.
It is declared on the View column only: `common-v0.1` is a frozen part (`E_SCHEMA_PART_FROZEN`), as `zero` was when
added (#1289), so a Layout `columnStyles` entry cannot carry it. Closed set: a second transform is a new enum value.

## Rule (deterministic, locale-independent)

| Input | Result | Basis |
| --- | --- | --- |
| `Ana Maria Lopez` | `AML` | issue/slice rule: first letter of each word |
| `fw-team` | `FT` | hyphen is a word break (slice rule); also U+2010, U+2011 |
| single word `alice` | `A` | the rule applied to one word; no special case, no second letter |
| `Ken (Ito)`, leading punctuation | `KI` | a word's initial is its first letter or digit; punctuation is not an initial |
| digits `3rd floor` | `3F` | letters and digits are the identity-bearing characters of an id-like field |
| CJK with a space, `<family> <given>` | one character per word | same word rule |
| CJK without a break | its first character | no dictionary-free word boundary exists; one word gives one initial |
| empty, blank, punctuation only | reads as absent: `missing` text and `missing` affix | there is nothing to abbreviate; the existing absent-value contract applies |
| non-text value (number, bool, list) | `E_VIEW_COLUMN_TRANSFORM` | an initial of a non-name is a source mistake; fail visibly, as `E_VIEW_BOOLEAN_PRESENTATION` does |

Whitespace is Unicode whitespace (includes U+3000). Combining marks following an initial stay with it; the result is
NFC. Case is `str.upper` (Unicode default mapping, never locale-tailored: Turkish `i` gives `I`; a script without case is
unchanged). No length cap: a many-word value yields many letters and Layout measures the result like any cell text.
No owner decision is needed: every choice above follows the slice rule or is the single deterministic reading of it; the
only judgement calls (unspaced CJK gives one character; empty is absent) are stated and can be changed by an enum
value or a later optional member without breaking this one.

## Layers

View declares; the table normalizer (`review/v05_content.py` with `surface_content.initials`) applies it before
measurement, like `format` and `zero`, so Layout measures and Scene carries completed text and no layer downstream sees a
transform. The affix state of an emptied cell is `missing`.

## Diagnostics

`E_VIEW_SCHEMA` for an unknown value (schema). New `E_VIEW_COLUMN_TRANSFORM` (ingress `ContractError`): source not a
`field` or `title`, format not `text`; runtime (`_diagnostic_error`): non-text value. The generated inventory
(`docs/diagnostics/inventory.md`) is bot-owned and not edited here.

## Files and tests

`schemas/view-v0.28.schema.yaml`; `contracts/resources.py` (`TableColumn.transform`, validation);
`model/surface_content.py` (`initials`, `display_value`); `review/v05_content.py`; Spec 46; one L1 line in
`conformance/schema-equivalence/expected-deltas-v0.1.yaml`. Tests: `tests/integration/test_initials_cell_transform.py`
(each rule row, locale independence, absent-is-identical, affix, diagnostics; all literals ASCII or `\u` escapes so
Windows console output is safe). Evidence: schema-equivalence PASS; `regenerate_public_examples.py --check --jobs 4`
shows byte identity because no example declares `transform`. The Editorial gap report row 2 stays open until a
bundle uses the member (a Theme/preset change is separate).
