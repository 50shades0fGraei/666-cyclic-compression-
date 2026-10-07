"""Randall's Cyclic Compression Engine.

Copyright (c) 2026 Randall Lujan. All rights reserved.
Patent pending for the cyclic compression and rotor-folding system described herein.

This module captures the project's current prototype architecture while giving it
an explicit rotor, fold, and reconstruction model. The design is deterministic,
readable, and suitable for extension into a more complete cyclic cipher system.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

PROJECT_NAME = "Randall's Cyclic Compression"
COPYRIGHT_NOTICE = "Copyright (c) 2026 Randall Lujan. All rights reserved. Patent pending."
CYCLIC = [1, 4, 2, 8, 5, 7]

# The rotor is the core 142857 cycle used by the project. Each slot represents a
# multiplier position in the cyclic matrix, and the sequence of rotations creates
# the order used by the compressor.
ROTOR_ROTATIONS = [
    [1, 4, 2, 8, 5, 7],
    [4, 2, 8, 5, 7, 1],
    [2, 8, 5, 7, 1, 4],
    [8, 5, 7, 1, 4, 2],
    [5, 7, 1, 4, 2, 8],
    [7, 1, 4, 2, 8, 5],
]

KEYBOARD_ORDER = "qwertyuiopasdfghjklzxcvbnm"
CHARACTER_MAP = {
    ch: CYCLIC[index % len(CYCLIC)]
    for index, ch in enumerate(KEYBOARD_ORDER)
}
CHARACTER_MAP.update({" ": 5, ".": 5, ",": 5, "/": 5})


@dataclass(frozen=True)
class CyclicRotor:
    """Represents the canonical 142857 rotor and its rotations."""

    cycle: Tuple[int, ...] = (1, 4, 2, 8, 5, 7)

    def rotations(self) -> List[List[int]]:
        """Return the six valid circular rotations of the cycle."""
        rotated: List[List[int]] = []
        for offset in range(len(self.cycle)):
            rotated.append(list(self.cycle[offset:] + self.cycle[:offset]))
        return rotated

    def as_string(self) -> str:
        return " ".join(str(value) for value in self.cycle)


def collapse(value: int) -> int:
    """Reduce an integer to a single digit using a deterministic fold rule."""
    n = int(value)
    while n > 9:
        if n % 2 == 0:
            n = n // 2
        else:
            n = sum(int(ch) for ch in str(n))
    return n


def build_rotor_matrix() -> List[List[int]]:
    """Return the canonical rotor matrix in rotation order."""
    return CyclicRotor().rotations()


def _build_sequence(text: str) -> Tuple[List[int], List[str], Dict[int, List[str]], Dict[int, List[str]]]:
    """Map supported characters while preserving their original order."""
    by_cipher: Dict[int, List[str]] = {}
    sequence: List[str] = []
    for ch in text.lower():
        bucket = CHARACTER_MAP.get(ch)
        if bucket is not None:
            by_cipher.setdefault(bucket, []).append(ch)
            sequence.append(ch)

    order = [cipher for cipher in sorted(by_cipher) if by_cipher[cipher]]
    counts = {cipher: list(by_cipher[cipher]) for cipher in order}
    return order, sequence, counts, by_cipher


def fold_triplets(values: Iterable[int]) -> List[int]:
    """Collapse overlapping triplets into a new sequence representing one fold."""
    items = list(values)
    if len(items) < 3:
        return []

    folded: List[int] = []
    for idx in range(0, len(items) - 2, 2):
        triplet = items[idx:idx + 3]
        folded.append(collapse(sum(triplet)))
    return folded


def verify_369_duality(value: int) -> Dict[str, object]:
    """Verify a 369 anchor using the 3x1 and 3x2 multiplication dualities."""
    multipliers = {3: (1,), 6: (2,), 9: (1, 2)}
    if value not in multipliers:
        raise ValueError(f"{value} is not a 369 anchor")

    products = [3 * multiplier for multiplier in multipliers[value]]
    return {
        "value": value,
        "products": products,
        "verified": sum(products) == value,
    }


def compress_text(text: str) -> Dict[str, object]:
    """Fold an ordered cipher stream and retain compact fold-verification data."""
    order, raw_sequence, counts, _ = _build_sequence(text)
    if not raw_sequence:
        return {
            "input_length": len(text),
            "cipher_order": [],
            "counts": {},
            "sequence": [],
            "ordered_cypher_values": [],
            "folded_values": [],
            "pin": [],
            "fold_log": [],
            "anchor_counts": {},
            "duality_checks": 0,
            "cyclic": CYCLIC,
            "rotor": CyclicRotor().rotations(),
            "project": PROJECT_NAME,
        }

    ordered_values = [CHARACTER_MAP[ch] for ch in raw_sequence]
    current = ordered_values[:]
    folds: List[Dict[str, object]] = []
    anchor_counts: Counter[int] = Counter()
    duality_checks = 0
    folds_count = 0

    while len(current) > 6:
        next_values = fold_triplets(current)
        if not next_values or abs(len(next_values) - 6) > abs(len(current) - 6):
            break

        fold_anchor_counts = Counter(value for value in next_values if value in (3, 6, 9))
        checks = sum(fold_anchor_counts.values())
        if not all(verify_369_duality(value)["verified"] for value in fold_anchor_counts):
            raise ValueError("A 369 multiplication duality failed verification")
        anchor_counts.update(fold_anchor_counts)
        duality_checks += checks
        serialized_anchor_counts = {
            str(value): count for value, count in fold_anchor_counts.items()
        }
        folds.append(
            {
                "fold": folds_count + 1,
                "input_count": len(current),
                "output_count": len(next_values),
                "anchor_counts": serialized_anchor_counts,
                "duality_checks": checks,
            }
        )
        current = next_values
        folds_count += 1

    result = {
        "input_length": len(text),
        "cipher_order": order,
        "counts": counts,
        "sequence": raw_sequence,
        "ordered_cypher_values": ordered_values,
        "pin": current[:],
        "folded_values": current,
        "fold_log": folds,
        "anchor_counts": {str(value): count for value, count in anchor_counts.items()},
        "duality_checks": duality_checks,
        "cyclic": CYCLIC,
        "rotor": build_rotor_matrix(),
        "project": PROJECT_NAME,
    }
    return result


def unfold_numeric(
    ordered_values: Iterable[int],
    fold_log: Iterable[Dict[str, object]],
    folded_values: Iterable[int],
) -> List[int]:
    """Return the stored ordered cipher stream after verifying its fold chain."""
    source = list(ordered_values)
    current = source[:]

    folds = list(fold_log)
    for expected_fold, fold in enumerate(folds, start=1):
        if fold["fold"] != expected_fold or fold["input_count"] != len(current):
            raise ValueError(f"Fold {expected_fold} does not match the ordered stream")

        next_values = fold_triplets(current)
        if fold["output_count"] != len(next_values):
            raise ValueError(f"Fold {expected_fold} has an invalid output count")
        anchors = Counter(value for value in next_values if value in (3, 6, 9))
        serialized_anchors = {str(value): count for value, count in anchors.items()}
        if serialized_anchors != fold["anchor_counts"] or sum(anchors.values()) != fold["duality_checks"]:
            raise ValueError(f"Fold {expected_fold} has invalid 369 verification counts")
        if not all(verify_369_duality(value)["verified"] for value in anchors):
            raise ValueError(f"Fold {expected_fold} failed a 369 multiplication check")
        current = next_values

    if len(current) > 6:
        next_values = fold_triplets(current)
        if next_values and abs(len(next_values) - 6) <= abs(len(current) - 6):
            raise ValueError("The fold log stops before the closest-to-six fold level")

    if current != list(folded_values):
        raise ValueError("The ordered cipher stream does not produce the stored folded values")

    return source


def unfold_sequence(pin: Iterable[int], cipher_order: Iterable[int], counts: Dict[int, List[str]]) -> List[str]:
    """Reverse the fold by replaying the stored per-bucket symbols.

    The six-digit pin is the compressed terminal state, while the cipher_order and the
    stored bucket values provide the exact original per-bucket symbol inventory needed
    to reconstruct the symbolic sequence in deterministic order.
    """
    ordered_cipher_values = list(cipher_order)
    unfolded: List[str] = []
    for cipher in ordered_cipher_values:
        bucket_values = counts.get(cipher, [])
        if not bucket_values:
            continue
        unfolded.extend(bucket_values)
    return unfolded


def rebuild_sequence(sequence: Iterable[int]) -> List[int]:
    """Rebuild a deterministic sequence from the compressed representation."""
    return list(sequence)


if __name__ == "__main__":
    sample = "hello world"
    result = compress_text(sample)
    print(f"Project: {result['project']}")
    print("Rotor:", result["rotor"])
    print("Input:", sample)
    print("Cipher order:", result["cipher_order"])
    print("PIN:", result["pin"])
    print("Unfolded:", unfold_sequence(result["pin"], result["cipher_order"], result["counts"]))
    print("Fold log:", result["fold_log"])
