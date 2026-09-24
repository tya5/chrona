# Issue 367 implementation plan

1. Replace the private authoring JSON hash with `content_identity` for current
   and candidate workspace identities.
2. Add Japanese-title/current-revision acceptance coverage and retain stale CAS
   rejection coverage.
3. Run authoring and CLI focused tests, full CI, publish release review, and
   close #367 only after verification.
