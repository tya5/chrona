# Issue #46 correction amendment: target-slide authoring shapes

## Supersession

This amendment supersedes the simplified View and summary shapes in the initial #46 specification where they differ from the accepted issue map.

## View labels

`visibility.labels` accepts the legacy boolean or `{placement, content, side}`. `placement` is `plot`, `table`, or `none`; `content` is an ordered subset of `title` and `finishDelta`; `side` is `auto`, `start`, or `end`. Plot labels choose start when it fits the viewport and otherwise end; table remains an explicit non-plot behavior.

## View temporal presentation

View uses the issue-level authoring keys:

```yaml
axis:
  levels: [{unit: quarter, format: year-quarter}, {unit: month, format: short-month}]
  ticks: week
markers: [{kind: asOf, source: actual, label: as of}]
shading: {nonWorking: true, exceptions: true}
```

Legacy automatic axis behavior remains the default. Project owns calendar facts. Reusable planned temporal ranges are Project annotations with `kind: range`, `start`, `end`, and label/text; View only selects their presentation.

## Summary figures

A v0.5 Summary Profile panel has `presentation: lines | figures`. `metrics` accepts legacy mapping entries and the target list form. A typed list metric has `id`, optional `label`, and one source: `{actual: asOf}`, `{object: ID, facet: planned}`, or `{counts: finishDelta}`. `figures` resolves value plus caption and Theme applies `metric` typography to values.

## Numbered annotations

`visibility.annotations` accepts the legacy enum or `{mode, marker}`. `marker: numbered` creates the deterministic circled index at the resolved anchor and the same prefix in the note slot; board rails retain leaders. Annotation semantics remain Project/View facts and never become renderer-specific text.

## Theme roles

HALCYON themes bind `baseline`, `groupHeader`, `metric`, `calendar-closed`, `calendar-exception`, `range`, `asOf`, and `note-index` to color-scheme intents. Existing role aliases may remain for compatibility, but generated primitives use these semantic names.

## Revised acceptance

Each of `board`, `sidebar`, and `dossier` is authored by the resources with these exact forms; no slide path, slide id, or proposal name reaches renderer control flow.