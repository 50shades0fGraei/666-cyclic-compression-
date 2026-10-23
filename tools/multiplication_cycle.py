'''multiplication_cycle.py

Utility script to explore the relationship described:
- Multiply a number by 11.
- Compute the digit‑sum (iterative, i.e., sum of digits, not reduced to a single digit unless desired).
- Repeat the process for a few steps.

The demo shows that starting from 15 we get:
    15 * 11 = 165  → digit sum = 1+6+5 = 12
    12 * 11 = 132  → digit sum = 1+3+2 = 6
    6  * 11 = 66   → digit sum = 6+6 = 12 (cycle continues)
Thus the series 15 → 12 → 6 ↔ 12 ↔ 6 repeats, illustrating the *6 ↔ 3* (via digital‑root equivalence) that you mentioned.

The script can be invoked as a module:
    python -m tools.multiplication_cycle [start] [steps] [--reduce]
where:
- *start* is the initial integer (default 15).
- *steps* is how many 11‑multiplication cycles to perform (default 5).
- *--reduce* will repeatedly collapse the digit sum to a single‑digit digital root (mod 9).

This helper is purely exploratory and does not affect the compression algorithm.
''' 

import sys
from typing import List

def digit_sum(n: int) -> int:
    """Return the sum of decimal digits of *n* (no reduction)."""
    return sum(int(d) for d in str(abs(n)))

def digital_root(n: int) -> int:
    """Return the digital root (1‑9, 0 for n==0). Equivalent to n % 9 with 0→9 handling."""
    if n == 0:
        return 0
    return 9 if n % 9 == 0 else n % 9

def cycle(start: int = 15, steps: int = 5, reduce_root: bool = False) -> List[int]:
    """Perform *steps* iterations of (x * 11) → digit‑sum.
    If *reduce_root* is True, the digit‑sum is further reduced to its digital root.
    Returns the list of intermediate sums (including the initial *start*).
    """
    values = [start]
    current = start
    for _ in range(steps):
        multiplied = current * 11
        summed = digit_sum(multiplied)
        if reduce_root:
            summed = digital_root(summed)
        values.append(summed)
        current = summed
    return values

def main(argv: List[str] = None):
    if argv is None:
        argv = sys.argv[1:]
    start = 15
    steps = 5
    reduce_root = False
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg.startswith("-"):
            if arg == "--reduce":
                reduce_root = True
                i += 1
            else:
                print(f"Unknown flag {arg}")
                return
        else:
            # positional arguments
            if start == 15:
                start = int(arg)
            else:
                steps = int(arg)
            i += 1
    seq = cycle(start, steps, reduce_root)
    header = "Digital‑root" if reduce_root else "Digit‑sum"
    print(f"Starting from {start}, {steps} cycles of '*11 → {header.lower()}'")
    for idx, val in enumerate(seq):
        print(f"Step {idx}: {val}")

if __name__ == "__main__":
    main()
