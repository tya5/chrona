# Design Correction Plan: Self-contained preset roots (#377)

**Status:** Active correction.

## Trigger

The first #377 resolver implementation proved that the two current Controller
Z preset documents declare member paths relative to the project root while the
only safe resolver correctly interprets them relative to the preset document.
They are parseable evidence but not usable preset closures.

## Required correction

Do not permit `..`, repository-root lookup, or a fallback path interpretation.
Instead, define a presentation preset as a self-contained resource root and
migrate the public evidence atomically.  The default wheel preset follows the
same closure rule.  Re-evaluate gallery/public-preset evidence under that one
model before resuming CLI implementation.
