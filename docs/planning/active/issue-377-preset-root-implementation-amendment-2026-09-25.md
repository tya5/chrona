# Implementation Amendment: Self-contained preset roots (#377)

Before I377-1 resumes:

1. migrate both Controller Z preset fixtures into self-contained roots;
2. replace the misleading public-preset evidence test with actual closure and
   byte-equivalence evidence; and
3. make the CLI resolver reject missing/unsafe preset members as a public
   diagnostic rather than leaking filesystem errors.

The packaged default is then authored under the same root layout.  No parent
path compatibility behavior is permitted.
