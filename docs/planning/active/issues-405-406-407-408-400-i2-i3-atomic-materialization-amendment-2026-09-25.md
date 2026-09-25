# I2/I3 Atomic Materialization Amendment (#405, #406, #407, #408, #400)

**Status:** Accepted sequencing correction before implementation resumes.

## Trigger

When I2 stopped silently omitting a measured non-fitting axis label, the
public corpus exposed existing `overflow: diagnose` tiers which had relied on
the old omission.  A standalone I2 publication would therefore either make a
materializable public Context fail or restore an unrecorded omission.  Neither
is an acceptable intermediate public state.

## Decision

I2's axis placement closure and I3's axis-label branch of the finite failure
registry are one atomic implementation and publication unit.  This does not
move row-density policy into I2, and it does not change the accepted failure
taxonomy.

The atomic unit must:

1. retain I2's typed interval, selected-candidate, and measured label outcome
   closure;
2. apply `diagnose` and `thin-with-record` to every non-fitting label through
   the Layout-owned registry, never through Scene or an adapter;
3. preserve the full omitted candidate identifier and reason for every
   thinned label, and emit a reader-visible density record;
4. make all affected public corpus Contexts materializable, with regenerated
   evidence; and
5. leave I3's row-density/draft-versus-immutable policy as its subsequent,
   independently reviewable unit because it does not affect axis
   materializability.

This is an atomicity correction, not a compatibility layer.  The positional
axis reader remains removed and there is no legacy fallback.
