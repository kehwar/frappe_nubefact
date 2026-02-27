# Typst Tables Reference

## Table of Contents
- [Basic structure](#basic)
- [Column sizes](#columns)
- [Headers and footers](#headers)
- [Cell merging (colspan/rowspan)](#merging)
- [Alignment](#alignment)
- [Fills and zebra stripes](#fills)
- [Strokes](#strokes)
- [Individual lines (hline/vline)](#lines)
- [Cell-level overrides](#cell-overrides)
- [Captions and cross-references](#captions)
- [Multi-page tables](#multipage)
- [Rotating tables](#rotate)
- [table vs grid](#grid)

## Basic Structure { #basic }

```typst
#table(
  columns: 3,
  [*Name*], [*Score*], [*Grade*],
  [Alice],  [95],      [A],
  [Bob],    [82],      [B],
  [Carol],  [78],      [C+],
)
```

Cells are placed left-to-right, top-to-bottom. Typst adds rows automatically.

Always wrap the header row in `table.header` for accessibility:

```typst
#table(
  columns: 3,
  table.header[Name][Score][Grade],
  [Alice], [95], [A],
  [Bob],   [82], [B],
)
```

Auto-style header cells with a show rule:

```typst
#show table.cell.where(y: 0): strong

#table(
  columns: 3,
  table.header[Name][Score][Grade],
  [Alice], [95], [A],
)
```

## Column Sizes { #columns }

```typst
// Fixed number → auto-sized columns
#table(columns: 3, ...)

// Mixed sizing
#table(
  columns: (auto, 1fr, 2fr, 6cm),
  ...
)
```

Column size options:
- `auto` — fit content
- `1fr`, `2fr` — fractional share of remaining space (`2fr` = twice as wide as `1fr`)
- `6cm`, `1in`, `1.5em` — absolute/relative length
- `40%` — percentage of available width

Common pattern — first column auto, rest fill page equally:

```typst
#table(
  columns: (auto, 1fr, 1fr, 1fr),
  ...
)
```

## Headers and Footers { #headers }

```typst
#table(
  columns: 3,
  table.header[Date][Event][Location],
  table.footer[—][End of schedule][—],
  [2024-01], [Conference], [Berlin],
  [2024-03], [Workshop],   [Vienna],
)
```

Headers and footers repeat on each page automatically. Disable with `repeat: false`:

```typst
table.header(repeat: false)[Date][Event][Location]
```

## Cell Merging (colspan / rowspan) { #merging }

```typst
#table(
  columns: 4,
  table.header[Name][Mon][Tue][Wed],
  [Alice],
    table.cell(colspan: 2)[Office],
    [Remote],
  [Bob],
    table.cell(colspan: 3)[On leave],
  [Carol],
    [Remote],
    table.cell(rowspan: 2)[Training],
    [Office],
  [Dave],
    [Office],
    // rowspan cell above covers this column
    [Remote],
)
```

## Alignment { #alignment }

```typst
// Single alignment for all cells
#table(columns: 3, align: center + horizon, ...)

// Array — cycled per column
#table(
  columns: 4,
  align: (right, left, left, left),
  ...
)

// Function — full control per cell
#table(
  columns: 4,
  align: (x, y) =>
    if x == 0 { right } else { left } +
    if y == 0 { bottom } else { top },
  ...
)
```

Override a single cell:

```typst
table.cell(align: center)[Centered content]
```

## Fills and Zebra Stripes { #fills }

```typst
// Solid fill for all cells
#table(columns: 2, fill: luma(230), ...)

// Alternating column stripes (cycle through array)
#set table(fill: (rgb("EAF2F5"), none))

// Horizontal zebra stripes (function)
#set table(
  fill: (_, y) => if calc.odd(y) { rgb("EAF2F5") },
)

// Three-tone row cycle
#set table(
  fill: (_, y) => (none, rgb("EAF2F5"), rgb("DDEAEF")).at(calc.rem(y, 3)),
)
```

Override a single cell's fill:

```typst
table.cell(fill: orange)[Special cell]
```

## Strokes { #strokes }

```typst
// Uniform stroke
#table(stroke: 0.5pt + gray, ...)

// Remove all strokes
#table(stroke: none, ...)

// Only horizontal strokes
#table(stroke: (x: none), ...)

// Only vertical strokes
#table(stroke: (y: none), ...)
```

Stroke dictionary keys: `top`, `bottom`, `left`, `right`, `x` (vertical lines), `y` (horizontal lines), `rest`.

### Stroke functions for document-wide patterns

```typst
// Only inner lines (no outer border)
#set table(stroke: (x, y) => (
  left: if x > 0 { 0.8pt },
  top:  if y > 0 { 0.8pt },
))

// Only underline the header row
#set table(stroke: (_, y) => if y == 0 { (bottom: 1pt) })

// No lines in header row, normal elsewhere
#set table(stroke: (x, y) => (
  left: if x == 0 or y > 0 { 1pt } else { 0pt },
  right: 1pt,
  top:  if y <= 1 { 1pt } else { 0pt },
  bottom: 1pt,
))
```

### Double lines via gutter

```typst
#table(
  columns: 3,
  stroke: (x: none),
  row-gutter: (2.2pt, auto),  // double line after row 0
  table.header[Date][Exercise][Calories],
  [2024-01], [Swimming], [400],
  [2024-02], [Yoga],     [200],
)
```

## Individual Lines (hline / vline) { #lines }

```typst
#table(
  stroke: none,
  columns: 2,
  [14:00], [Talk],
  [15:00], [Workshop],
  table.hline(),           // placed after row 1
  [19:00], [Mixer],
)
```

Position explicitly with `y:` (hline) or `x:` (vline):

```typst
table.hline(y: 2, stroke: 1pt + red)
table.vline(x: 1)
```

Start/end a line partway through the table:

```typst
table.vline(x: 1, start: 1)  // skip header row
table.hline(y: 3, end: 2)    // only span first two columns
```

## Cell-Level Overrides { #cell-overrides }

Wrap any cell in `table.cell` to override its properties:

```typst
#table(
  columns: 3,
  [Normal], [Normal],
  table.cell(
    fill: orange,
    stroke: 2pt + red,
    align: center,
    colspan: 2,
  )[Highlighted merged cell],
  [Normal], [Normal], [Normal],
)
```

Useful show-rule pattern — style by position:

```typst
// Bold first row
#show table.cell.where(y: 0): strong

// Italic first column (skip header)
#show table.cell: it => {
  if it.x == 0 and it.y > 0 { emph(it) } else { it }
}

// Small-caps first column
#show table.cell.where(x: 0): smallcaps
```

## Captions and Cross-References { #captions }

Wrap a table in `figure` for a caption and label:

```typst
#figure(
  table(
    columns: 3,
    stroke: none,
    table.header[Item][Spec][Result],
    [Voltage], [220V], [218V],
    [Current], [5A],   [4.2A],
  ),
  caption: [Test results for design A],
) <test-results>

See @test-results for the full data.
```

Use `placement: auto` on the figure to float it to the top or bottom of the page.

## Multi-Page Tables { #multipage }

Tables break across pages automatically. `table.header` and `table.footer` repeat on each page by default.

Tables inside `figure` don't break by default — enable it:

```typst
#show figure: set block(breakable: true)

#figure(
  table(...),
  caption: [Long dataset],
)
```

## Rotating Tables { #rotate }

```typst
// Rotate only the table (keeps page orientation)
#rotate(-90deg, reflow: true,
  table(columns: (1fr,) + 5 * (auto,), ...)
)

// Rotate the entire page
#page(flipped: true)[
  #table(...)
]
```

## table vs grid { #grid }

`table` — for tabular data (semantic, styled by templates, accessible).  
`grid` — for layout/presentational purposes (no strokes or inset by default).

Both have the same API; use `grid.cell`, `grid.hline`, `grid.vline` instead of `table.*` counterparts.

```typst
// Layout with grid
#grid(
  columns: (1fr, 2fr),
  gutter: 1em,
  [Sidebar content],
  [Main content],
)
```
