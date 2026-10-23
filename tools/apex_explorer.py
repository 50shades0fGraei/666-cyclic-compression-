'''apex_explorer.py

Utility to explore the "conjoining‑apex" concept over all possible 2‑digit
pairs built from the allowed digit set (excluding 3, 6, 9). For each pair we
construct a 12‑digit test string by repeating the pair six times and then run
the apex‑checking routine from ``tools.conjoining_apex``.

The script reports which pairs lead to *full agreement* (every overlapping
12‑digit window satisfies forward‑sum == backward‑sum for both halves). This
matches the description of obtaining a continuous set of apex points that
"unravel the next sum".

Running the module directly prints a concise table:
    python -m tools.apex_explorer

Optional arguments:
    --allowed "0,1,2,4,5,7,8"   # comma‑separated list of digits to use
    --repeat 6                  # how many times to repeat the 2‑digit pair
    --step 5                    # sliding window step (must be <=6‑1)
    --quiet                     # only print pairs with full agreement

The script can also be imported and the ``explore`` function called
programmatically.
''' 

from itertools import product
from typing import List, Tuple
import argparse

# Import the core apex logic from the previously created module.
from tools.conjoining_apex import process_apex

def explore(
    allowed_digits: List[int] = None,
    repeat: int = 6,
    step: int = 5,
    quiet: bool = False,
) -> List[Tuple[Tuple[int, int], str, bool]]:
    """Explore all 2‑digit pairs.

    Returns a list of ``(pair, string, full_agreement)`` where ``pair`` is a
    ``(a, b)`` tuple, ``string`` is the generated 12‑digit (or longer) test
    string, and ``full_agreement`` indicates whether *every* window produced
    by ``process_apex`` satisfied the apex condition.
    """
    if allowed_digits is None:
        allowed_digits = [0, 1, 2, 4, 5, 7, 8]
    results = []
    for a, b in product(allowed_digits, repeat=2):
        # Build the numeric string by repeating the two‑digit pattern.
        pair_str = f"{a}{b}"
        test_str = pair_str * repeat  # length = 2*repeat (default 12)
        # Run the apex check.
        try:
            windows = process_apex(test_str)
        except ValueError:
            # Not enough length – skip (should not happen with default params).
            continue
        full_agreement = all(win[-1] for win in windows)
        results.append(((a, b), test_str, full_agreement))
        if not quiet:
            status = "✅" if full_agreement else "⚠"
            print(f"Pair {a}{b}: {status} ({'all' if full_agreement else 'some'} windows agree)")
    if quiet:
        # Print only the successful ones.
        for (a, b), s, ok in results:
            if ok:
                print(f"Pair {a}{b} -> {s} ✅ full agreement")
    return results

def _parse_digits(arg: str) -> List[int]:
    return [int(d.strip()) for d in arg.split(',') if d.strip().isdigit()]

def main():
    parser = argparse.ArgumentParser(description="Explore conjoining‑apex over all 2‑digit pairs.")
    parser.add_argument("--allowed", type=str, default="0,1,2,4,5,7,8",
                        help="Comma‑separated list of allowed digits (default excludes 3,6,9).")
    parser.add_argument("--repeat", type=int, default=6,
                        help="How many times to repeat the 2‑digit pair (default 6 → 12‑digit string).")
    parser.add_argument("--step", type=int, default=5,
                        help="Sliding window step used internally by conjoining_apex (default 5).")
    parser.add_argument("--quiet", action="store_true",
                        help="Only show pairs that achieve full agreement.")
    args = parser.parse_args()
    # The step parameter is not directly used here because ``process_apex``
    # internally uses a fixed step of 5. We keep the argument for future
    # extensibility.
    explore(allowed_digits=_parse_digits(args.allowed), repeat=args.repeat, step=args.step, quiet=args.quiet)

if __name__ == "__main__":
    main()
