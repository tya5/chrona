# Design: Draft preset ingress and packaged default (#377)

**Status:** Accepted for implementation planning.

## Decision

`chrona render` gains a single optional `--preset PATH` input and a packaged,
explicit default preset.  Both inputs resolve through one draft-preset closure
resolver.  The resolver loads the preset and every member only relative to the
preset root, validates the existing `presentation-preset/v0.1` contract, and
then calls the existing ordinary draft-closure constructor.  It is not a guided
workspace, package resolver, Context producer, or second render pipeline.

## CLI precedence

```text
explicit --view/--theme/--scheme/--layout
    > explicit --preset member
    > packaged default preset member
```

The command requires a complete effective four-resource bundle.  With
`--preset`, any named explicit resource flag replaces only that preset member;
without `--preset`, each omitted member comes from the packaged default.  An
explicit resource is never silently replaced.  `--actual`, summary/detail,
icon catalogs, font metrics, locale, viewport, and target remain independently
explicit command inputs.

This makes the old four-flag invocation still valid while admitting one-preset
and no-preset forms.  It does not make draft rendering reproducible evidence:
only an immutable Render Context/materializer remains that boundary.

## Packaged resource topology

The default lives beneath `src/chrona/resources/presets/default/` with ordinary
View, Theme, Color Scheme, Layout, and preset documents.  Hatch force-includes
that source tree in the installed wheel.  Runtime lookup uses
`importlib.resources`, never a repository-relative path.  The preset uses only
the existing baseline visual profile and bundled font descriptor, so a fresh
wheel can render it without a user-installed font or catalog.

The preset's resource references are explicit relative paths.  Its Color
Scheme list remains the existing finite `compatibleColorSchemes` contract.  It
is not a Presentation Package; #348's acquisition/lock/cache deferral remains
unchanged.

## Diagnostics and help

The resolver distinguishes missing packaged default, invalid preset, unsafe
member path, absent member, and incomplete effective resource bundle with
stable draft-ingress diagnostics.  CLI help names the default preset and states
that explicit resource flags override its members.  No implicit file discovery
is introduced.

## Evidence

I377 must prove byte equality for equivalent explicit and `--preset` commands,
and successful rendering for the packaged no-preset command.  It adds a small,
readable Project/Actual guide and a public wheel-installed invocation outside a
checkout.  The guide uses the default to explain first render, while advanced
users retain the explicit ordinary-resource form.

## Non-goals

Theme/View inheritance, a library picker, minimal `init`, guided override
expansion, presentation package acquisition, and terse Project syntax remain
separate work.  The default preset uses no #383 editorial capability.
