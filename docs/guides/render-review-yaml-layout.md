# Render-review YAML organization

Users author reusable resources separately. The immutable Render Context is generated
when a revision is materialized; users do not guess hashes.

| Path | Authority | Reuse boundary |
|---|---|---|
| `project.yaml` | planned facts and relations | project |
| `actual.yaml` | independent observations | project/revision |
| `views/<name>.yaml` | selection, grouping, ordering and window | matching data vocabulary |
| `themes/<name>.yaml` | paint, typography and concrete number tokens | organization/audience |
| `layouts/<name>.yaml` | composition, sizing, alignment and bounded anchors | medium/use case |
| `profiles/<name>.yaml` | optional summary/detail wording | matching profile IDs |
| `contexts/<name>.yaml` | generated immutable binding and environment | one evaluation |

Layout Profiles contain no Project facts and use Theme number tokens for routine
spacing. A derived Layout may override stable node IDs, never array positions. Theme
`metrics` bind source-internal semantic quantities to number tokens; exact glyph widths
and baselines come from the Font Metrics assets pinned by the Context.

The only review context is `chrona/presentation/v0.5`. It references Theme, Color Scheme and Layout
independently and declares viewport, locale, Font Metrics, Scene precision and output
capabilities. `chrona render-review` accepts its immutable resource reference:

<!-- chrona:doc-check skip: requires an author-created immutable Render Context reference and local store -->
```sh
chrona render-review \
  --context-reference context-reference.yaml \
  --snapshot-root .chrona/snapshots \
  --store-identity local-workspace \
  --output review.svg
```

All referenced resources use one snapshot token. Their `contentIdentity` values are
SHA-256 evidence generated from the exact stored bytes. There is no Presentation
Settings/Preset file, compatibility adapter, raw coordinate offset, or renderer default
table in this path.
