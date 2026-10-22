# Fit a fixed slide or page

You have a slide (1280x720) or a sheet of paper (A4) and want one picture that fills it. This guide
says what Chrona does for that, what it does not, and what to change when
`W_LAYOUT_CANVAS_EXCEEDS_VIEWPORT` appears.

## What the size means

`--viewport WIDTHxHEIGHT` is a **minimum**, not a fit. Chrona lays out the rows the View selects at the
size the design gives them, then stretches the picture up to the viewport if it is smaller. If the content is
taller (or wider) than the viewport, the picture grows past it and `render` reports
`W_LAYOUT_CANVAS_EXCEEDS_VIEWPORT`. Nothing is clipped, shrunk or paginated, and the status stays `ok`.

Not supported, by design:

- **No fit-to-page.** Chrona does not shrink text, compact rows or pick a smaller size for you
  (Spec 33, "Named page defaults").
- **No pagination.** A plan taller than one page is one tall picture, never several pages. Make one View
  per slide instead (below).
- **No scaling of the finished picture.** Shrinking an SVG or PNG to a page is the job of the program that
  places it; the text shrinks with it.

## Choose a page size without copying a preset

A Layout Profile can declare `pageSize`, but you do not need a Layout file for that: pass the pixel size.
`pageSize` is only a name for these numbers (96 CSS pixels per inch):

| Page | `--viewport` |
| --- | --- |
| slide 16:9 | `1280x720` |
| A4 landscape / portrait | `1123x794` / `794x1123` |
| A3 landscape / portrait | `1587x1123` / `1123x1587` |
| A5 landscape / portrait | `794x559` / `559x794` |
| Letter landscape / portrait | `1056x816` / `816x1056` |
| Legal landscape / portrait | `1344x816` / `816x1344` |

```bash
chrona init my-fixed-project
chrona render my-fixed-project/project.yaml --actual my-fixed-project/actual.yaml \
  --viewport 1123x794 --output my-fixed-project/a4.svg
```

Chrona has no separate `--page-size` option, because it would only repeat the table above; a profile's
`pageSize` stays the way to give a shared design its own default.

## Make the content fit

The height comes from the number of rows and the design's row height, so change those. In the order
that usually matters:

1. **Show fewer rows.** Filter the View, not the Project: `selection.include` (`ids`, `types`,
   `objectTypes`), `selection.exclude` (`state: [finished]`, `objectTypes`) and a relative `window` drop
   rows from the picture and keep them in the schedule. The
   [focus a slide](update-a-plan.md#focus-a-slide-hide-finished-work-show-the-next-n-weeks) section has a
   working View. For a long plan, write one View per slide and render each.
2. **Choose a denser design.** Rows differ a lot by design. Rendering the 30-row Controller Z
   curriculum plan with its Executive View at `--viewport 1280x720`, about 12 rows fit `executive-light`,
   about 16 fit `mission-light` and 18 or more fit `print-mono`; all 30 rows need 1375 px with
   `executive-light` but 2593 px with `technical-print` and 2258 px with `wallboard-dark`.
   `chrona preset list` names the designs.
3. **Leave out what you do not need.** A summary, a legend, the title, annotations and relations each take
   space; drop them from the View.
4. **Mind the width as well.** A design can be wider than a portrait page: with the weekly plan of
   [Update a plan](update-a-plan.md), all five approved designs (`target-b`, `yuya`, `titlecard`,
   `marquee`, `sunday`) fit 1280x720 and A4 landscape, but `titlecard` (about 1048 px) and `sunday`
   (about 1000 px) are wider than A4 portrait (794 px), so the warning names the inline edge.

Row height, fonts and spacing belong to the design's Theme and Layout Profile. Changing them means writing
your own Layout or Theme files, which is a larger step than the rows above; do it only if you cannot show
fewer rows.

## Read the warning

The warning lists the slots that stick out and by how much (`block-end N` means the bottom is N px past the
declared height, `inline-end N` the right edge). If the biggest contributor is the table, show fewer rows; if it is the timeline or the
title, the width is the problem. Render again with the same `--viewport` until the warning is gone: a fitting
picture produces none.
