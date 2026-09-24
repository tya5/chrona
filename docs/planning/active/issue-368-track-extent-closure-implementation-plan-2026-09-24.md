# Issue 368 implementation plan

1. Extract planner-owned minimum row extent and test shared, stacked,
   planned/actual, and multi-lane point-milestone families.
2. Replace duplicated multiplier/sum logic with uniform-row maximum extent in
   Draft auto and fixed overflow calculations.
3. Add a public synthetic multi-lane/multi-milestone Draft fixture and prove
   auto succeeds while one-pixel-less fixed viewport rejects.
4. Run focused/full/materializer checks, architecture release review, CI, and
   close #368 after public verification.
