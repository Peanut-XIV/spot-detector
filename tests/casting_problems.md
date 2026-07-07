# handling bit overflow while negating signed integers:

> Note: It works for any signed integer type *less* than the largest signed
  integer allowed but we use an 8 bits signed int here for the example:

## Introduction

In mathematics, integer numbers can be represented in a range of ways, allowing
the reader to better intuit abstract theories. The one we use in our day to day
life is base ten representation of numbers with arabic numerals. With the
digits 0, 1, 2, 3, 4, 5, 6, 7, 8 and 9 and enough space, we can represent any
finite positive integer. Their representation allow us to add, subtract and
multiply them following simple rules. With the help of a negative sign, we can
represent the negatives too. And with a decimal point, any real number within
finite precision. Yet, using our intuition, we can understand that using ten
different digits is a sensible but arbitrary choice.

Computers are machines initially designed to execute operations on such
numbers. Old mechanical computers even represented them in base ten.
However, when electronics started to become viable, representing numbers with
different tensions...



In this explanation, we will assume you already understand the binary
representation of positive integers. Also, this is in the concept of
manipulating integers with the numpy library.

## Representing negative integers

Assuming we are working with 2's complement for signed integers, negating a
number goes like so: the negative of a number is the 1's complement (1 becomes
0 and 0 becomes 1) then add one like a normal positive number. For a number
like 3 it works like so:

     - (3)
   = - (0b0000.0011)
   = (¬ 0b0000.0011) + 0b0000.0001
   = 0b1111.1100 + 0b1
   = 0b1111.1101
   = -3

We know that this is negative 3 because if we add it to 3, the carry propagates
and we end up with 0b0000.0000, or simply 0:

    carry ->     1111 1111
                  \\\\ \\\\
      (-3)      0b1111.1101
    + (+3)      0b0000.0011
   ------------------------
              0b1.0000.0000

We end up with a number coded in 9 bits... But since we are working with only
8, we ignore the last one and end up with 0.

Now let's say that we are working with an 8 bit signed int. If mini the minimum
value contained in our array is the minimum representable (-128), then negating
would not be possible while staying with the same type.

  - (-128)                        # -128 in base ten

= - (0b1000.0000)                 # -128 in base two with
                                  # two's complement for
                                  # negative numbers

=   (¬ 0b1000.0000) + 0b0000.0001 # ¬ means 1's complement

=   0b0111.1111                   # the carry propagates
  + 0b0000.0001
----------------
=   0b1000.0000                   # we get -128 again
=   -128                          # now in base ten

Turns out the maximum signed 8 bits integer is only 127, one less than needed
and would lead to an overflow. (Don't know how Numpy handles it) For that
reason we can't negate every signed int safely without casting it first to a
larger type, and have to be somewhat careful.

That's what we are doing here: if we detect this kind of edge case, we cast it
to the largest possible signed int (int64), make it positive and then convert
it back to unsigned afterwards.
