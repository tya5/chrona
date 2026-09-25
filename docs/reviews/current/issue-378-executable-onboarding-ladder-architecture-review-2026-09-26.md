# Architecture Review — Executable Onboarding Ladder (#378)

**Decision:** Accepted for implementation planning.

The design preserves the existing authority chain.  A builtin catalogue is a
package-resource distribution boundary; its copy command produces ordinary
Draft source, and the existing draft-preset resolver remains the sole render
ingress.  Gallery pages remain evidence consumers, Context/materializer
semantics remain immutable, and no registry acquisition is implied.

The review rejects two tempting boundary breaches: treating guided workspace
overrides as design inheritance, and applying a generic YAML merge at either
the CLI or renderer.  Theme/View inheritance must first close to an effective
ordinary resource with exact bases before the existing Theme → Layout → Scene
chain starts.  The progressive tutorial is documentation/fixture evidence and
does not acquire a new project grammar.

The designer supplier track is correctly separated.  Its semantic-vocabulary
and contract-reliability work is neither silently solved by a builtin preset
nor required to make the user onboarding commands truthful.
