# Issue #46 row-index design micro-amendment

`tableColumns[].source: rowIndex` is a View-owned, one-based display ordinal. It is resolved after View ordering/explicit-row selection, has `text` formatting only, and does not alter Project identity or row mapping. Existing sources remain unchanged.
