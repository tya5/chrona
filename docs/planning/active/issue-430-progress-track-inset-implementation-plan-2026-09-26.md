# Implementation Plan — Progress Track Inset (#430)

## I430-1

**Files:**
- `schemas/theme-v0.11.schema.yaml` (`progressInset`);
- `model/theme_tokens.py` (`progress_track`);
- `layout/surface_composer.py` (`progress_fill_bounds`, radius);
- `layout/surface_quality.py` (`ShapePlacement.corner_radius`);
- `scene/v05_builder.py`;
- the Controller Z Theme, context and manifest, plus generated evidence;
- Specification 61.

**Tests:**
- fraction 0, fraction 1 and ½ at several bar lengths, including a bar shorter than `8b`;
- zero inset equals the old formula;
- an out-of-range ratio is diagnosed;
- the new slide's fills lie inside the host, with a radius and different lengths;
- the 21 existing slides are unchanged (`--check`).

## I430-2: acceptance review
