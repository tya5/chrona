# Issue 222 Stage-3 Workspace Shape Correction

## Trigger

The initial workspace schema admitted only `presentation.mode: guided`, while the
approved Stage-3 transition requires the workspace to persistently change to `explicit`.
Without an explicit-mode source shape, materialization would either leave a stale
inheritance edge or invent an unreviewable side channel.

## Corrected v0.1 shape

`presentation` is a closed discriminated union:

* `guided`: the existing binding-only member;
* `explicit`: one `resources` map containing exact local references for `view`, `theme`,
  `colorScheme`, `layout`, and `renderContext`, plus one exact `receipt` reference.

An explicit workspace has no `binding`, preset selector, or overrides. Its references
are ordinary local canonical files created in the same aggregate transaction. The
receipt records the former preset/binding/normalizer identities and generated resource
identities, but neither evaluation nor resolution reads it as an inheritance input.

The normalizer accepts guided mode only. Explicit mode is resolved exclusively through
the ordinary explicit resource closure. This makes the one-way transition structural,
keeps the source of truth singular, and lets a reviewer see every Stage-3 ownership
edge in the workspace diff.
