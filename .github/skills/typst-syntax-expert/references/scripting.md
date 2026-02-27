# Typst Scripting Reference

## Table of Contents
- [Data types](#types)
- [Operators](#operators)
- [Destructuring](#destructuring)
- [Functions](#functions)
- [Control flow](#control-flow)
- [Methods](#methods)
- [Modules and packages](#modules)
- [Context](#context)
- [Counters and state](#counters)

## Data Types { #types }

```typst
// Content (markup as a value)
#let body = [*Hello* world]

// String
#let name = "Alice"
#let greeting = "Hello, " + name + "!"

// Integer
#let n = 42
// Float
#let pi = 3.14159
// Boolean
#let flag = true

// Length values
#let w = 5cm
#let h = 2in
#let size = 1.5em  // relative to font size
#let pct = 50%     // relative to container

// Array
#let items = (1, "two", [three])
#items.at(0)        // → 1
#items.len()        // → 3
#items.push(4)

// Dictionary
#let person = (name: "Bob", age: 30)
#person.name        // → "Bob"
#person.at("age")   // → 30
```

## Operators { #operators }

| Operator | Effect              | Precedence |
|----------|---------------------|------------|
| `-`      | Negation (unary)    | 7          |
| `*`, `/` | Multiply, divide    | 6          |
| `+`, `-` | Add, subtract       | 5          |
| `==`, `!=`, `<`, `<=`, `>`, `>=` | Comparison | 4 |
| `in`, `not in` | Collection membership | 4 |
| `not`    | Logical NOT         | 3          |
| `and`    | Logical AND         | 3          |
| `or`     | Logical OR          | 2          |
| `=`, `+=`, `-=`, `*=`, `/=` | Assignment | 1 |

Content concatenation: `[Hello] + [ world]`

## Destructuring { #destructuring }

```typst
// Array destructuring
#let (x, y) = (1, 2)
#let (a, .., z) = (1, 2, 3, 4)  // a=1, z=4

// Dictionary destructuring
#let books = (Shakespeare: "Hamlet", Austen: "Persuasion")
#let (Austen,) = books          // Austen = "Persuasion"
#let (Shakespeare: s) = books   // s = "Hamlet"

// Discard with underscore
#let (_, y, _) = (1, 2, 3)
```

## Functions { #functions }

```typst
// Named function
#let double(x) = x * 2

// Named function with default argument
#let greet(name, greeting: "Hello") = [#greeting, #name!]
#greet("Alice")
#greet("Bob", greeting: "Hi")

// Unnamed (lambda) function
#let add = (x, y) => x + y
#(x => x * 2)(5)  // → 10

// Function with content argument (trailing block syntax)
#let framed(body) = box(stroke: 1pt, inset: 4pt, body)
#framed[Important text]

// Multiple content arguments
#let two-col(left, right) = grid(columns: 2, left, right)
#two-col[Left][Right]

// Spreading arguments
#let nums = (1, 2, 3)
#calc.min(..nums)

// .with() for partial application
#let red-text = text.with(fill: red)
#red-text[danger!]
```

## Control Flow { #control-flow }

```typst
// If / else if / else
#if x > 0 [
  positive
] else if x < 0 [
  negative
] else [
  zero
]

// For loop over array
#for item in ("a", "b", "c") [
  - #item
]

// For loop over dictionary
#for (key, val) in (a: 1, b: 2) [
  #key: #val \
]

// For loop with index
#for (i, item) in ("a", "b", "c").enumerate() [
  #(i + 1). #item \
]

// While loop
#let count = 0
#while count < 5 {
  count += 1
  [#count ]
}

// Break and continue
#for i in range(10) {
  if i == 3 { continue }
  if i == 7 { break }
  [#i ]
}
```

## Array and Dictionary Methods { #methods }

```typst
// Array methods
#let a = (3, 1, 4, 1, 5)
#a.len()              // 5
#a.first()            // 3
#a.last()             // 5
#a.at(2)              // 4
#a.slice(1, 3)        // (1, 4)
#a.contains(4)        // true
#a.filter(x => x > 2) // (3, 4, 5)
#a.map(x => x * 2)    // (6, 2, 8, 2, 10)
#a.fold(0, (acc, x) => acc + x)  // 14
#a.sorted()           // (1, 1, 3, 4, 5)
#a.rev()              // (5, 1, 4, 1, 3)
#a.join([, ])         // content joined with separator
#a.chunks(2)          // ((3,1), (4,1), (5,))
#a.zip((10,20,30,40,50))  // pairs

// String methods
#let s = "Hello, World"
#s.len()              // 12
#s.contains("World")  // true
#s.starts-with("Hello")
#s.ends-with("World")
#s.split(", ")        // ("Hello", "World")
#s.trim()
#s.replace("World", "Typst")
#upper(s)             // "HELLO, WORLD"
#lower(s)             // "hello, world"
```

## Modules and Packages { #modules }

```typst
// Import specific items from file
#import "utils.typ": fn1, fn2

// Import and rename
#import "utils.typ": fn1 as helper

// Import everything
#import "utils.typ": *

// Import as module (access with dot notation)
#import "utils.typ"
#utils.fn1()

// Community packages from Typst Universe
#import "@preview/cetz:0.3.0": canvas, draw
```

## Context { #context }

Context makes code aware of its document position:

```typst
// Access style properties
#context text.size
#context text.lang
#context text.font

// Heading counter
#set heading(numbering: "1.")
#context counter(heading).get()     // current value as array
#context counter(heading).display() // formatted string

// Counter at a label
#context counter(heading).at(<intro>)

// Physical position
#context locate(<figure-1>).position()  // returns (page, x, y)

// Query elements
#context query(heading)  // all headings up to this point
```

## Counters and State { #counters }

```typst
// Named counter
#let c = counter("mycounter")
#c.step()           // increment
#c.update(5)        // set value
#context c.display()

// Page counter
#context counter(page).display("1 of 1", both: true)

// Figure counter
#context counter(figure).display()

// Mutable state (caution: can cause convergence issues)
#let total = state("total", 0)
#total.update(t => t + 1)
#context total.get()
```
