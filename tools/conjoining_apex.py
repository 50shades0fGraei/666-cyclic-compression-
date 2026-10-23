'''conjoining_apex.py

Utility script implementing the "conjoining apex" algorithm described by the user.
It works on a numeric string (e.g., the compressed PIN) and processes it in
pairs of overlapping 6‑digit chunks (total 12 digits). For each 12‑digit window
it computes four "lineal sum" values:

1. forward_sum_1   – sum of the first 6 digits (left‑to‑right)
2. forward_sum_2   – sum of the next 6 digits (left‑to‑right)
3. backward_sum_1  – sum of the first 6 digits read right‑to‑left
4. backward_sum_2  – sum of the next 6 digits read right‑to‑left

If the forward and backward sums for the same half agree (i.e. forward_sum_i ==
backward_sum_i) the algorithm considers that "apex" resolved. The script
outputs the positions where the agreement occurs and the corresponding sums.

The overlap rule is implemented by sliding the 12‑digit window forward by 5
positions (i.e., each new window shares 1 digit with the previous window),
which yields the two overlap points of "1" mentioned in the description.

Running the module directly prints a readable report:
    python -m tools.conjoining_apex 123456789012345678

The function ``process_apex`` can also be imported and used programmatically.
''' 

from typing import List, Tuple

def digit_sum(chunk: str) -> int:
    """Return the sum of decimal digits in *chunk* (expects only digits)."""
    return sum(int(d) for d in chunk)

def process_apex(num_str: str) -> List[Tuple[int, int, int, int, bool]]:
    """Process *num_str* according to the conjoining‑apex algorithm.

    Returns a list of tuples for each 12‑digit window:
        (start_index, fwd1, fwd2, bwd1, bwd2, agreement)
    where ``agreement`` is True when both halves have matching forward and
    backward sums.
    """
    results: List[Tuple[int, int, int, int, int, bool]] = []
    length = len(num_str)
    if length < 12:
        raise ValueError("Input string must contain at least 12 digits for a full window.")
    # slide with 5‑digit step to keep a 1‑digit overlap between consecutive windows
    step = 5
    for start in range(0, length - 12 + 1, step):
        window = num_str[start:start + 12]
        first_half = window[:6]
        second_half = window[6:]
        fwd1 = digit_sum(first_half)
        fwd2 = digit_sum(second_half)
        bwd1 = digit_sum(first_half[::-1])
        bwd2 = digit_sum(second_half[::-1])
        agreement = (fwd1 == bwd1) and (fwd2 == bwd2)
        results.append((start, fwd1, fwd2, bwd1, bwd2, agreement))
    return results

def main(argv: List[str] = None) -> None:
    import sys
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        print("Usage: python -m tools.conjoining_apex <numeric-string>")
        return
    num_str = argv[0]
    try:
        report = process_apex(num_str)
    except ValueError as e:
        print(f"Error: {e}")
        return
    print(f"Processing {len(num_str)}‑digit string in 12‑digit windows (step=5):")
    for start, fwd1, fwd2, bwd1, bwd2, ok in report:
        status = "✅ agree" if ok else "⚠ mismatch"
        print(f"Window [{start}:{start+12}] → fwd1={fwd1}, fwd2={fwd2}, bwd1={bwd1}, bwd2={bwd2} -> {status}")

if __name__ == "__main__":
    main()
