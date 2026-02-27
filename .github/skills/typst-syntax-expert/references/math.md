# Typst Math Reference

## Table of Contents
- [Inline vs Block equations](#inline-vs-block)
- [Symbols and Greek letters](#symbols)
- [Subscripts, superscripts, and fractions](#attachments)
- [Math functions](#functions)
- [Matrices and vectors](#matrices)
- [Math fonts](#fonts)

## Inline vs Block Equations { #inline-vs-block }

```typst
// Inline: no surrounding spaces
The formula $E = m c^2$ appears inline.

// Block: spaces inside delimiters
The formula is:
$ E = m c^2 $
```

## Symbols { #symbols }

Greek letters are spelled by name: `alpha`, `beta`, `gamma`, `delta`, `epsilon`, `zeta`, `eta`, `theta`, `iota`, `kappa`, `lambda`, `mu`, `nu`, `xi`, `pi`, `rho`, `sigma`, `tau`, `upsilon`, `phi`, `chi`, `psi`, `omega` (uppercase: `Alpha`, `Beta`, etc.)

Common symbols:
- `nabla`, `partial`, `infinity` (∞)
- `RR` (ℝ), `ZZ` (ℤ), `NN` (ℕ), `QQ` (ℚ), `CC` (ℂ)
- `sum`, `product`, `integral`, `union`, `inter`
- `forall`, `exists`, `in`, `not`, `and`, `or`
- Arrows: `arrow.r`, `arrow.l`, `arrow.r.long`, `arrow.double.r`
- Relations: `gt.eq` (≥), `lt.eq` (≤), `approx`, `equiv`, `tilde`
- `dot`, `times`, `div`, `plus.minus`

Symbol variants use dot notation: `arrow.squiggly`, `gt.eq.not`

Shorthand sequences: `=>` (⇒), `->` (→), `!=` (≠), `<=` (≤), `>=` (≥)

## Subscripts, Superscripts, and Fractions { #attachments }

```typst
// Subscript and superscript
$x_1$, $x^2$, $x_i^n$

// Grouping with parentheses for multi-char scripts
$x_(i+1)$, $e^(2 pi i)$

// Fractions
$a / b$
$(a + b) / (c + d)$
$frac(a, b)$  // explicit fraction function

// Roots
$sqrt(x)$, $root(3, x)$  // cube root
```

## Math Functions { #functions }

Functions in math mode don't need `#` prefix:

```typst
$abs(x)$, $norm(x)$
$floor(x)$, $ceil(x)$, $round(x)$
$sin(x)$, $cos(x)$, $tan(x)$, $exp(x)$, $ln(x)$, $log(x)$
$max(a, b)$, $min(a, b)$
$gcd(a, b)$, $lcm(a, b)$

// Limits with custom operator
$op("lim", limits: #true)_(x -> 0) f(x)$

// Sum and product with limits
$sum_(i=0)^n a_i$
$product_(i=1)^n i$
$integral_0^1 f(x) dif x$

// Calligraphic letters
$cal(A)$, $cal(F)$, $cal(L)$

// Binom
$binom(n, k)$
```

## Matrices and Vectors { #matrices }

```typst
// Vector (column by default)
$vec(a, b, c)$
$vec(a, b, delim: "[")$  // square bracket delimiters

// Matrix (rows separated by ; )
$mat(1, 2; 3, 4)$
$mat(1, 0, 0; 0, 1, 0; 0, 0, 1, delim: "[")$

// Spread from array
$mat(..#range(1, 5).chunks(2))$

// Cases
$f(x) = cases(
  1 "if" x > 0,
  0 "if" x = 0,
  -1 "if" x < 0,
)$
```

## Line Breaks and Alignment { #alignment }

```typst
// Line breaks in equation
$ a + b \
  + c + d $

// Alignment with &
$ a &= b + c \
    &= d + e $

// Multiple alignment columns (alternates right/left)
$ (3x + y) / 7 &= 9 && "given" \
  3x + y &= 63 & "multiply by 7" $
```

## Math Fonts { #fonts }

```typst
// Change math font (must be OpenType math font)
#show math.equation: set text(font: "Fira Math")
$ sum_(i in NN) 1 + i $
```

## Accessibility

```typst
// Provide alt text for equations
#math.equation(
  alt: "sum from i equals 0 to n of i",
  block: true,
  $ sum_(i=0)^n i $,
)
```
