# Controller Z example

`project.yaml` is the planning source of truth and `actual.yaml` contains observations.
Resources shared by presentation variants live in `shared/`. Each directory below
`variants/` owns only its additional inputs and deterministic derived artifacts.

| Variant | Contents |
|---|---|
| `baseline/` | Minimal schedule SVG. |
| `review/` | Original Plan/Actual review resources. |
| `executive/` | Executive table-timeline acceptance output and retained historical alternatives. |
| `editorial/` | Editorial presentation settings and SVG/PNG. |
| `signal/` | Dark high-signal direction. |
| `studio/` | Light studio direction. |
| `delivery-control/` | Delivery-control theme outputs. |
| `review-detail/` | M23 group detail, observations, and milestone digest. |

Example regeneration:

```sh
chrona render-review examples/controller-z/project.yaml \
  --actual examples/controller-z/actual.yaml \
  --view examples/controller-z/shared/view.yaml \
  --style examples/controller-z/shared/style.yaml \
  --theme examples/controller-z/shared/theme.yaml \
  --profile examples/controller-z/shared/layout.yaml \
  --presentation-settings examples/controller-z/variants/editorial/settings.yaml \
  --output examples/controller-z/variants/editorial/expected.svg
```

No variant is selected by product code. All appearance differences remain user-editable
resources.
