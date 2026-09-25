# Design Correction Plan: Reference observations in the capability matrix (#390)

## Trigger

The generated matrix has #391 capability rows and a list of reference links,
but it does not have a column for each reference implementation.  It therefore
cannot distinguish a reviewed external observation from an unreviewed source
link, contrary to the accepted #390 matrix boundary.

## Questions

1. What finite observation vocabulary can state evidence without turning the
   matrix into a feature-ranking claim?
2. Which source owns each observation and how is `unknown` made explicit?
3. How can the generator reject incomplete rows while remaining separate from
   runtime capability resolution?

## Required outputs

1. A correction design defining source-owned, per-capability observations.
2. A whole-architecture review of the generator, #391 registry, and external
   research boundary.
3. An implementation amendment with deterministic-generation and negative
   coverage requirements.
