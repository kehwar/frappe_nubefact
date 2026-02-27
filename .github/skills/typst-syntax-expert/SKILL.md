---
name: typst-syntax-expert
description: Expert knowledge of Typst markup language syntax, scripting, and styling. Use when writing or editing .typ files, creating Typst documents, templates, or packages, setting up page layout, using math mode, applying set/show rules, writing Typst scripting (variables, functions, loops), or any task involving Typst typesetting.
---

# Typst Syntax Expert

> Based on Typst's official documentation. Typst is a modern markup-based typesetting system.

## Three Modes

Typst has three syntactical modes:

| Mode   | How to enter                        | Example                         |
|--------|-------------------------------------|---------------------------------|
| Markup | Default in `.typ` files             | `= Heading`, `*bold*`           |
| Math   | Surround with `$...$`               | `$x^2 + y^2 = z^2$`            |
| Code   | Prefix with `#` or inside `{...}`   | `#let x = 1`, `#if x > 0 {...}`|

Once in code mode with `#`, no further `#` is needed until returning to markup.

## Markup Quick Reference

| Element          | Syntax                        |
|------------------|-------------------------------|
| Heading (h1–h6)  | `= H1`, `== H2`, `=== H3`    |
| Bold             | `*bold*`                      |
| Italic           | `_italic_`                    |
| Raw/code inline  | `` `code` ``                  |
| Raw block        | ` ```lang ... ``` `           |
| Link             | `https://typst.app/`          |
| Label            | `<my-label>`                  |
| Reference        | `@my-label`                   |
| Bullet list      | `- item`                      |
| Numbered list    | `+ item`                      |
| Term list        | `/ Term: description`         |
| Line break       | `\` (backslash)               |
| Paragraph break  | Blank line                    |
| Comment          | `// line` or `/* block */`    |
| Escape           | `\#`, `\$`, `\*` etc.         |

## Styling System

### Set Rules — configure element defaults

```typst
#set text(font: "New Computer Modern", size: 11pt)
#set page(paper: "a4", margin: (x: 2cm, y: 2.5cm))
#set par(justify: true, leading: 0.65em)
#set heading(numbering: "1.1")
```

Set rules apply from that point to end of file (or enclosing block).

### Show Rules — redefine element appearance

```typst
// Show-set: apply set rule only to matched elements
#show heading: set text(navy)

// Transformational: custom rendering function
#show heading.where(level: 1): it => block[
  #upper(it.body)
]

// Show-everything: wrap whole document in template
#show: template

// Replace text
#show "TypeScript": "Typst"

// Regex
#show regex("\d+"): it => text(red, it)
```

## Math Mode

```typst
// Inline math (no surrounding spaces)
$x^2 + y^2 = z^2$

// Block math (spaces inside delimiters)
$ sum_(i=0)^n i = (n(n+1)) / 2 $

// Subscript / superscript
$x_1$, $x^2$, $x_(i+1)^(n-1)$

// Fractions
$a / b$, $(a + b) / (c + d)$

// Vectors and matrices
$vec(1, 2, 3)$
$mat(1, 2; 3, 4)$

// Alignment in multi-line equations
$ a &= b + c \
  &= d $

// Text inside math
$x "where" x > 0$

// Greek letters and symbols: just spell them out
$alpha, beta, gamma, pi, nabla, infinity, RR, ZZ, NN$

// Symbol variants via dot notation
$arrow.r.long$, $gt.eq$
```

See [references/math.md](references/math.md) for math functions and symbols.

## Scripting

### Variables and Functions

```typst
// Variable binding
#let name = "Alice"
#let data = (1, 2, 3)
#let info = (name: "Bob", age: 30)

// Function definition
#let greet(name) = [Hello, #name!]
#let box-it(body, color: red) = box(fill: color)[#body]

// Usage in markup
#greet("World")
#box-it(color: blue)[content]
```

### Control Flow

```typst
// Conditional
#if x > 0 [positive] else [non-positive]

// For loop
#for item in (1, 2, 3) [
  - Item #item
]

// While loop
#let i = 0
#while i < 3 {
  i = i + 1
  [Line #i\ ]
}
```

### Content and Code Blocks

```typst
// Content block: markup as a value
#let intro = [*Welcome* to Typst]

// Code block: multiple statements
#{
  let a = 1
  let b = 2
  str(a + b)
}
```

### Modules and Packages

```typst
// Import from file
#import "utils.typ": helper-fn, another-fn

// Import community package
#import "@preview/package-name:0.1.0": some-fn

// Include file (inserts its content)
#include "chapter1.typ"
```

## Context

Context lets code react to its location in the document (required for counters, positions, style properties):

```typst
// Access a style property
#context text.lang

// Access heading counter
#context counter(heading).get()

// Locate an element by label
#context locate(<intro>).position()
```

## Templates

A template is a function that wraps `doc` content:

```typst
// conf.typ
#let conf(title: "", doc) = {
  set page("a4", numbering: "1")
  set text(font: "Libertinus Serif", 11pt)
  // ... more styling
  doc
}

// main.typ
#import "conf.typ": conf
#show: conf.with(title: "My Paper")

= Introduction
...
```

## Common Functions

| Function     | Purpose                                      |
|--------------|----------------------------------------------|
| `text()`     | Font, size, color, style for text            |
| `page()`     | Paper size, margins, header, footer, columns |
| `par()`      | Justify, leading, spacing                    |
| `heading()`  | Numbering, appearance                        |
| `image()`    | Include image with optional width/height     |
| `figure()`   | Captioned figure with optional label         |
| `table()`    | Grid-based table with columns arg            |
| `grid()`     | Low-level grid layout                        |
| `align()`    | Horizontal/vertical alignment                |
| `box()`      | Inline container, prevents line breaks       |
| `block()`    | Block container with spacing                 |
| `columns()`  | Multi-column layout                          |
| `place()`    | Absolute placement on page                   |
| `bibliography()` | Insert bibliography from .bib file      |
| `cite()` / `@label` | Cite a bibliography entry           |
| `lorem(n)`   | Generate n words of Lorem Ipsum placeholder  |
| `counter()`  | Create/access named counter                  |
| `state()`    | Mutable document-wide state                  |
| `query()`    | Query elements by selector                   |
| `raw()`      | Verbatim code block with syntax highlighting |
| `link()`     | Hyperlink                                    |
| `ref()`      | Cross-reference to label                     |
| `footnote()` | Footnote                                     |
| `outline()`  | Table of contents                            |

## Reference Files

| Topic | When to read |
|-------|-------------|
| [references/math.md](references/math.md) | Math functions, symbols, and advanced math typesetting |
| [references/styling.md](references/styling.md) | Advanced set/show rule patterns and styling techniques |
| [references/scripting.md](references/scripting.md) | Data types, operators, destructuring, methods |
| [references/tables.md](references/tables.md) | Table structure, column sizing, headers, merging, strokes, fills, alignment |
