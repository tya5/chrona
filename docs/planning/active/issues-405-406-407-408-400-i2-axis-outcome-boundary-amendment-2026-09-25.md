# I2 Amendment — Axis Outcome Boundary (#405, #406, #407, #408, #400)

**Status:** Accepted clarification before completing I2.

The accepted axis-and-visible-failure design assigns two distinct concerns to
different implementation slices.  I2 closes axis geometry: it selects a
declared auto candidate, creates fiscal/calendar intervals, measures formatted
labels, and returns a typed outcome for every consumed tier.  I3 owns failure
policy: it interprets a label non-fit under `diagnose|thin-with-record`,
constructs a deterministic thinning schedule where allowed, and publishes the
visible warning or diagnostic through the finite Layout registry.

The phrase "thinning-record production" in the I2 implementation amendment
could incorrectly move I3 policy into I2.  It is corrected as follows:

1. I2 records each tier's declared candidate units, selected unit, form,
   interval identities, and measured label-fit outcomes in `SurfacePlacement`.
2. I2 does not silently suppress a non-fitting label.  Before I3 exists, a
   non-fitting concrete tier keeps the existing explicit
   `E_PRESENTATION_AXIS_OVERFLOW` result.
3. I3 consumes those typed outcomes to apply `diagnose` or
   `thin-with-record`, preserve every omitted interval identity and reason,
   and emit the required reader-visible record.

This preserves the architecture boundary: View declares policy; Layout is the
single owner of measurement and policy execution; Scene and adapters project
the completed result without inferring ticks, labels, or warnings.
