# Implementation Plan Amendment — I3 Completed Backgrounds (#389, #409)

1. Normalize `rowDecoration` into surface content and add finite row/group
   decoration semantic bindings.
2. Add ThemeTokenView access to typed background treatment/order; reject
   missing or invalid background role closure.
3. Complete row/group/header/calendar shapes in Layout with cross-slot bounds,
   semantic identity, slot, and paint order; remove Scene group reconstruction.
4. Validate intersecting translucent fills before Scene. Migrate shipped
   calendar closure treatment coherently so all public contexts materialize.
5. Add focused geometry/projection/overlap tests, regenerate public evidence,
   run full pytest and materializer checks, then publish serially.
