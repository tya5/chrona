<!-- chrona:literal-acceptance/v1 -->

# Release Review — Bundled Default Readability (#498)

**Status:** accepted; all four literal criteria and the planned release gate are met. **Observed:** 2026-09-27. **Published base:** `c06daa954b5a240e21343fc0705a4d4aaf7095eb` on `main`.

**Issue:** [#498](https://github.com/tya5/chrona/issues/498); [owner decision](https://github.com/tya5/chrona/issues/498#issuecomment-5852117933). **Published implementation:** `e732c1c1bd393b13ea739b89389799af38fe309e`; inventory/CI correction: `2031b3193522725560b4f7d4c0c83b29bf8b8b7e`; I2 rendered evidence: `1a6cca23f1f5f27db5c4ea5f294004e8edab03ec`; Windows path correction: `c06daa954b5a240e21343fc0705a4d4aaf7095eb`.

**Design record:** [selected design](../../design/issue-498-bundled-default-readability-design-2026-09-27.md), [design correction](../../design/issue-498-bundled-default-readability-design-correction-2026-09-27.md), [architecture review](issue-498-bundled-default-readability-architecture-review-2026-09-27.md), [architecture-review amendment](issue-498-bundled-default-readability-architecture-review-amendment-2026-09-27.md). **Plan:** [implementation plan](../../planning/active/issue-498-bundled-default-readability-implementation-plan-2026-09-27.md), [implementation amendment](../../planning/active/issue-498-bundled-default-readability-implementation-plan-amendment-2026-09-27.md). **Rendered evidence and hashes:** [I2 evidence README](../../research/presentation/issue-498-bundled-default-readability-evidence-2026-09-27/README.md).

## Literal issue acceptance

### Issue #498

- Source: [Issue #498](https://github.com/tya5/chrona/issues/498)
- Observed: 2026-09-27

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A bare `chrona render` of HALCYON-1 with no presentation flags gives every bar a row guide across the plot. It also names every bar at its end or start inside its own row, or reports the name suppressed. | met | [Bundled-default regression and Scene/SVG checks](#verification-and-rendered-output); [HALCYON Scene, SVG and PNG](../../research/presentation/issue-498-bundled-default-readability-evidence-2026-09-27/halcyon-1/); [side-by-side image](../../research/presentation/issue-498-bundled-default-readability-evidence-2026-09-27/comparison/halcyon-vs-editorial.png) | — |
| 2 | The readable-defaults test renders the **bundled default** (no `--view/--theme/--layout/--scheme`), so a future repoint cannot bypass it. The pinned `default-draft` check may stay as an additional test. | met | [Bundled-default regression test](#verification-and-rendered-output) asserts the bare CLI invocation; pinned `default-draft` remains a separate supplemental test. | — |
| 3 | The same holds for the `chrona init` starter. | met | [Init-starter regression and Scene/SVG checks](#verification-and-rendered-output); [captured initialized starter source and renders](../../research/presentation/issue-498-bundled-default-readability-evidence-2026-09-27/starter/) | — |
| 4 | The regenerated default for HALCYON-1 and the starter is committed as evidence. It is compared side by side with `13-gallery-editorial` in the acceptance review, and it keeps the same palette, type and axis. | met | [Published I2 evidence](../../research/presentation/issue-498-bundled-default-readability-evidence-2026-09-27/README.md), including committed HALCYON/starter Scene, SVG and PNG, full-figure and same-scale comparison boards, source hashes, palette/type/axis review, unchanged slide-13 hashes, and [green evidence CI](https://github.com/tya5/chrona/actions/runs/36294476924). | — |

## Programme-level criteria (optional)

## Verification and rendered output

The focused suite passed locally in the project `.venv`:

```text
.venv/bin/python -m pytest -q \
  tests/integration/test_readable_defaults.py \
  tests/integration/test_packaged_resources.py \
  tests/integration/test_public_preset_evidence.py
73 passed
```

The three directly affected acceptance tests also passed independently:

```text
.venv/bin/python -m pytest -q \
  tests/integration/test_readable_defaults.py::test_bundled_default_guides_every_bar_and_names_it_or_reports_suppression \
  tests/integration/test_readable_defaults.py::test_init_starter_bundled_default_guides_and_names_every_bar \
  tests/integration/test_public_preset_evidence.py::test_readable_default_resources_are_mirrored_and_selected_without_mutating_editorial
3 passed
```

The two bundled-default rendering tests use the public CLI path without View,
Theme, Layout, or Scheme overrides. The HALCYON test exercises actual SVG and
Scene output, complete member-label suppression accounting (including no
hidden primitive/text for suppressed members), own-row containment and
bar-end/start geometry, alternate band coverage through timeline end, and the
separate variance labels required by the approved title-only View contract.
The starter test invokes `chrona init`, then checks its bare-default output in
both Scene and SVG.

The captured bare HALCYON render has 26 rows and planned bars, 13
plot-end-reaching row bands, 23 visible member labels, three explicitly
suppressed member labels (`eps`, `detector`, `avionics`), and 12 independent
variance labels. Every visible member label is within its own row and anchored
at its own bar's start or end; suppression identities have no member-label
primitive/text. The 12 variance outputs remain distinct from names, with
existing ahead/on-track/behind treatment. The initialized starter has 3 rows
and bars, two plot-end-reaching bands, 3 visible member labels, zero
suppressed labels, and zero variance labels. SVG and Scene counts agree for
both outputs. Detailed counts, visible geometry findings, and artifact hashes
are in the [evidence README](../../research/presentation/issue-498-bundled-default-readability-evidence-2026-09-27/README.md).

The evidence set retains separate Scene JSON, SVG, and PNG for both actual
bare-default renders. I inspected the rendered images at useful scale: the
warm row tint is faint but discernible, the labels sit with their bars, and
the grid/axis remain legible. The HALCYON board compares complete same-size
figures; the starter board includes both complete figures and a native-scale
top-section crop to avoid interpreting the starter's shorter height as a
resizing difference. The candidate preserves the Editorial Scheme and Layout,
Noto Sans typography and type sizes, axis hierarchy, axis bounds/text/paint,
and all common Scene primitives. It adds only row guidance, member names, and
separately placed variance labels. The default uses the warm category fill
`#EFE7DE` at opacity `0.12`; its fill is visually subordinate to the retained
raised column ground `#E3E5E9` against paper `#F5F5F1`. This is visual review
of the final default, not a broader claim of warm-tint acceptance.

`tools/check_starter_perceptibility.py` passed with **0 errors**. The public
materializer check `.venv/bin/python tools/regenerate_public_examples.py
--check` passed for **28 slides**. No public materializer update was needed.

Resource identity is covered by the three-test focused run and the exact
package/corpus SHA-256 pairs recorded in the I2 README: default View
`9468d74b…` and Theme `3f9b865c…` match their HALCYON corpus mirrors byte for
byte. The default manifest switches only its View/Theme members; Scheme,
Layout and Detail remain Editorial. The named `editorial` library entry and
corpus resource identities are unchanged. `13-gallery-editorial` remains
byte-stable: committed SVG SHA-256
`026b124709cd2841172a6a58c7c2e6b7c017527cd4126d47bd76f0ba2953b313`, Scene
SHA-256 `959741a31ec450d926cc3c3497cbc1f5da1af916542b588674f0777ef4bc856a`;
the I2 reference Scene is the checked-in Scene byte-for-byte. The I1 diff
against the parent commit for those two slide-13 outputs was empty.

## CI and prior failure disposition

The first CI run on implementation commit `e732c1c1` was [run
36292902338](https://github.com/tya5/chrona/actions/runs/36292902338). Its
Ubuntu, macOS, and Windows conformance jobs failed on three introduced
inventory/test issues: a stale expected default View ID, newly authored Theme
resources missing from the role-admission closure enumeration, and the new
corpus mirrors missing from reachability enumeration. These were corrected in
`2031b319`; no product behavior or design was changed by that correction.
Replacement [run 36293139097](https://github.com/tya5/chrona/actions/runs/36293139097)
on `2031b319` passed on Ubuntu, macOS, and Windows: conformance, full pytest,
and wheel/smoke all succeeded, and newest-Python public-materializer
reproduction succeeded. Ubuntu pytest reported 1442 passed and 29 skipped.

The first evidence run
[36293605503](https://github.com/tya5/chrona/actions/runs/36293605503) for
`1a6cca23f1f5f27db5c4ea5f294004e8edab03ec` passed Ubuntu, macOS, and
newest-Python evidence, but Windows failed in
`test_default_autocrlf_clone_reproduces_every_declared_corpus_slide` before
rendering: the Windows checkout under pytest's temporary clone path exceeded
the file-name/path limit for three comparison PNGs. The rendered PNG bytes
were not defective. Commit `c06daa95` shortens only four comparison filenames
and updates their README/compositor references; all image bytes remain
identical. Replacement [run
36294476924](https://github.com/tya5/chrona/actions/runs/36294476924)
completed successfully on `c06daa95`: Ubuntu, macOS, and Windows
conformance/full-pytest/wheel-smoke jobs and newest-Python public-materializer
reproduction are all green. The Windows checkout-path failure is resolved
without changing any rendered bytes.

## Architecture conclusion

The implementation respects the published C-depth contract: the default-only
View declares plot names, fallback, and alternate rows; the Theme owns faint
row-band paint; existing Layout owns measurement, label/variance placement,
geometry, and suppression diagnostics; Scene carries completed geometry and
paint relations; SVG/PNG adapters serialize the result. No schema, Layout,
Scene, adapter, CLI, normative specification, or named-catalogue behavior was
changed. The published design correction explicitly preserves Layout's
independent variance-label behavior rather than hiding it in the View or
counting it as member-name handling.

This reconciles the actual default regression with the row-local placement
contract of adjacent [#483](https://github.com/tya5/chrona/issues/483) and
[#488](https://github.com/tya5/chrona/issues/488): the published default is
now the owner-requested Editorial-derived readable surface, while the named
Editorial gallery remains faithful to its no-row-ground reference. No
normative spec amendment was justified because the change composes existing
View and Layout semantics. **Review disposition:** all four literal
acceptance criteria and the three-OS/newest-Python release gate are met.
