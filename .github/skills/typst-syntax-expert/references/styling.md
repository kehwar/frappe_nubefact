# Typst Styling Reference

## Table of Contents
- [Set rules](#set-rules)
- [Show rules](#show-rules)
- [Common styling patterns](#patterns)
- [Page layout](#page)
- [Templates](#templates)

## Set Rules { #set-rules }

Set rules configure default properties of elements:

```typst
// Syntax: #set element(param: value)
#set text(font: "Libertinus Serif", size: 11pt, lang: "en")
#set page(paper: "us-letter", margin: (x: 2.5cm, y: 3cm))
#set par(justify: true, leading: 0.65em, first-line-indent: 1em)
#set heading(numbering: "1.1.")
#set list(marker: ([•], [–], [◦]))
#set enum(numbering: "1.a.i.")
```

Scope a set rule to a block:

```typst
#[
  #set text(red)
  This text is red.
]
This text is not red.
```

Conditional set rule:

```typst
#let task(body, critical: false) = {
  set text(red) if critical
  [- #body]
}
```

## Show Rules { #show-rules }

### Show-Set Rule (most composable)

```typst
// Apply set rule only to matched elements
#show heading: set text(navy)
#show heading.where(level: 1): set align(center)
#show heading.where(level: 2): set text(style: "italic")
```

### Transformational Show Rule

```typst
// Custom function — receives element as `it`
#show heading: it => block[
  #text(weight: "bold", it.body)
  #v(0.3em)
]

// Access element fields
#show figure: it => {
  it.body
  if it.caption != none [
    #line(length: 100%)
    #it.caption
  ]
}
```

### Selectors

```typst
// All elements of a type
#show heading: ...

// Filtered by field
#show heading.where(level: 1): ...
#show figure.where(kind: table): ...

// Text matching
#show "TypeScript": "Typst"

// Regex
#show regex("\d{4}"): it => text(blue, it)

// Label
#show <important>: it => highlight(it)

// Everything (wrap whole document)
#show: body => template(body)
```

### Show Rule with `.with()`

```typst
// Pre-populate named arguments in a template
#show: conf.with(
  title: "My Paper",
  authors: ("Alice", "Bob"),
)
```

## Common Styling Patterns { #patterns }

### Custom heading style

```typst
#show heading.where(level: 1): it => {
  set align(center)
  set text(size: 14pt)
  smallcaps(it.body)
  v(0.5em)
}
```

### Run-in subheading (no block)

```typst
#show heading.where(level: 2): it => {
  text(style: "italic", it.body) + [. ]
}
```

### Numbered headings

```typst
#set heading(numbering: "1.1")
// or Roman numerals:
#set heading(numbering: "I.A")
```

### Document title and metadata

```typst
#set document(title: "My Paper", author: "Alice")
```

### Headers and footers

```typst
#set page(
  header: align(right, context document.title),
  footer: align(center, context counter(page).display("1 / 1", both: true)),
  numbering: "1",
)
```

## Page Layout { #page }

```typst
#set page(
  paper: "a4",          // or "us-letter", "a5", etc.
  margin: (
    left: 3cm,
    right: 2cm,
    top: 2.5cm,
    bottom: 2.5cm,
  ),
  columns: 2,           // two-column layout
  flipped: true,        // landscape
)

// Two-column with single-column float (title/abstract)
#place(
  top + center,
  float: true,
  scope: "parent",      // float spans both columns
  clearance: 2em,
)[
  // title/abstract content
]
```

## Templates { #templates }

### Minimal template file (`conf.typ`)

```typst
#let conf(
  title: "",
  authors: (),
  abstract: [],
  doc,
) = {
  set page("us-letter", numbering: "1", columns: 2)
  set text(font: "Libertinus Serif", 11pt)
  set par(justify: true)

  show heading.where(level: 1): set align(center)

  // Title block floating above columns
  place(top + center, float: true, scope: "parent", clearance: 2em, {
    align(center, text(17pt, weight: "bold", title))
    v(1em)
    par(justify: false)[*Abstract* \ #abstract]
  })

  doc
}
```

### Using the template (`main.typ`)

```typst
#import "conf.typ": conf

#set document(title: "My Paper")

#show: conf.with(
  title: "My Paper",
  abstract: [This paper presents...],
)

= Introduction
...
```
