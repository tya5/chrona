# Design plan — shipped preset starter renderability (#460)

## Published baseline and scope

At `8eedb89e`, four of the five packaged preset entries render the fresh
starter project with the default Draft target. `elevated-light` requires a
group-band gradient and shadow while the default target profile lacks them.
The existing CLI matrix passes only by adding an explicit rich profile for
that entry. The issue and #454 are the public work order.

## Literal issue acceptance

- `chrona render demo/project.yaml --preset <copy of each library entry>`
  succeeds for all five entries, on a fresh `chrona init demo`.
- A check fails if a library entry cannot render the starter project.

## Design questions and slices

1. Choose between a preset-selected target profile and a deliberately
   decorative-optional elevated treatment with a supported flat fallback.
   Review target ownership, explicit profile overrides, and non-SVG targets.
2. Specify the default output, any warning and rich-profile output, and how
   the library test discovers all entries instead of using a curated list.
3. Review against visual-capability specification 63, preset acquisition,
   Scheme/Theme ownership, #378 onboarding and current adapter behavior.
4. Publish design and architecture review, then implementation plan, before
   changing a Theme or CLI test.

## Evidence and migration

Exercise the actual copied preset and fresh starter for every library entry,
with no special-case profile. Check rich-profile appearance, generated public
evidence, package mirrors, conformance and CI. No broad capability fallback
or implicit adapter paint substitution is authorized by this plan.
