# I3 Implementation Amendment — Calendar-Closed Extent Orientation (#389, #409)

1. Change only the v0.6 `calendarClosed` mapping member to a `timeline` const.
2. Pass semantic identity to Layout's extent resolver and compose calendar
   rectangles from their measured day inline interval plus timeline block
   bounds; retain the existing row-oriented resolver for the other roles.
3. Characterize unequal calendar stripe and timeline widths, preserve Scene
   projection/paint assertions, and regenerate public scene/SVG evidence.
4. Run focused tests, the complete pytest suite, presentation and corpus
   coverage checks, schema-reference validation, materializer checks and a
   generated SVG review before one implementation publication.
