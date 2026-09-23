# Issue 314 Declared Colour Scales Acceptance Review

## Result

Accepted.  The release replaces hash-selected category paint with explicit
named Scheme slots and provides one field-driven planned-mark scale with a
derived, provenance-bearing legend.

## Delivered contract

| Boundary | Delivered evidence |
| --- | --- |
| View v0.9 | closed `colorEncoding` with tagged field source, eligible `planned` target, unique ordered domain |
| Theme v0.4 | ordinary direct `category:<slot>` role binding and exact named scale slot map |
| Scheme v0.2 | named `categories` literals; no array/hash selector |
| normalization | total object field-to-colour lookup and used-domain legend derivation |
| Scene | applies completed fill overrides only; does not parse a View, Theme, Scheme, or field |
| adapters | serialize completed `ScenePaint` only |

HALCYON programme board is the public non-default fixture.  Its owner values
paint planned marks through the declared map and produce six matching scale
swatches/labels, while its existing semantic legend remains present.

## Verification

* focused contract/normalization/Scene/materializer checks: 65 passed, then 16
  post-cleanup checks passed;
* full suite: 449 passed, 7 skipped;
* conformance: passed;
* all eight public materializers: passed with an empty generated-SVG diff;
* wheel build and isolated installed-wheel smoke: passed.

## Architecture review

`category_index`, role-key hashing, positional palette selection, and default
category fallback are absent.  Static group paint remains a direct Theme role
binding, data-driven paint is a resolved scale, and semantic legend entries
remain independent from scale-derived entries.  Layout does not consume scale
data; Scene consumes completed object/legend paint only.  This maintains the
View → normalization → Layout/Scene → adapter ownership direction established
by Specification 60.
