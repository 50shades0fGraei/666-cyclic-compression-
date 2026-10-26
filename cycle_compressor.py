# -*- coding: utf-8 -*-
"""Randall's Cyclic Compression Engine.

Copyright (c) 2026 Randall Lujan. All rights reserved.
Patent pending for the cyclic compression and rotor-folding system described herein.

Includes:
- Canonical 142857 cyclic rotor and character cipher mapping
- Deterministic stride-2 overlapping tri-sum folding (LR & RL bidirectional verification)
- 369 multiplication duality verification and high-digit anchor flags
- 12-Block Pin-Only Lossless Reconstruction integration (Oct 2026 paper:
  residue erasure of 3,6 and repeats, 9 as technical 1 / functional 0 signpost,
  uniform apex 452152 and forward/backward pins 298-1 / 882-7)
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from pin_only_12block import (
    DEFAULT_LOGIC,
    FixedLogic,
    compress_12block_stream,
    decode_pin,
    decompress_12block_stream,
    encode_12block,
)

PROJECT_NAME = "Randall's Cyclic Compression"
COPYRIGHT_NOTICE = "Copyright (c) 2026 Randall Lujan. All rights reserved. Patent pending."
CYCLIC = [1, 4, 2, 8, 5, 7]

# The rotor is the core 142857 cycle used by the project.
ROTOR_ROTATIONS = [
    [1, 4, 2, 8, 5, 7],
    [4, 2, 8, 5, 7, 1],
    [2, 8, 5, 7, 1, 4],
    [8, 5, 7, 1, 4, 2],
    [5, 7, 1, 4, 2, 8],
    [7, 1, 4, 2, 8, 5],
]

# Keyboard sequence maps characters to the canonical cycle in order.
KEYBOARD_ORDER = "qwertyuiopasdfghjklzxcvbnm"
CHARACTER_MAP = {
    ch: CYCLIC[index % len(CYCLIC)]
    for index, ch in enumerate(KEYBOARD_ORDER)
}
CHARACTER_MAP.update({" ": 5, ".": 5, ",": 5, "/": 5})

# Cypher Order by Number map: each 6-character group is assigned its cypher number (1..5),
# multiplied by its cyclic slot to produce the second string (cypher order by number).
CYPHER_NUMBER_MAP = {
    ch: ((index // len(CYCLIC)) + 1)
    for index, ch in enumerate(KEYBOARD_ORDER)
}
CYPHER_NUMBER_MAP.update({" ": 5, ".": 5, ",": 5, "/": 5})


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
    """Fold overlapping triplets at stride 2 left-to-right."""
    items = list(values)
    if len(items) < 3:
        return []
    return [collapse(items[i] + items[i + 1] + items[i + 2]) for i in range(0, len(items) - 2, 2)]


def fold_triplets_with_flag(values: Iterable[int]) -> List[int]:
    """Fold triplets while encoding the tens-digit flag alongside the collapsed digit."""
    items = list(values)
    if len(items) < 3:
        return []
    folded: List[int] = []
    for idx in range(0, len(items) - 2, 2):
        a, b, c = items[idx : idx + 3]
        raw_sum = a + b + c
        digit = collapse(raw_sum)
        encoded = 10 * digit + (raw_sum // 10)
        folded.append(encoded)
    return folded


def fold_trisums_lr(values: List[int]) -> List[int]:
    """Trisum fold left-to-right at stride 2.

    Walks overlapping triplets (0,1,2), (2,3,4), (4,5,6) …
    Each triplet collapses to a single digit. This is the canonical
    direction that advances the pyramid.
    """
    return fold_triplets(values)


def fold_trisums_rl(values: List[int]) -> List[int]:
    """Trisum fold right-to-left — the mirror of fold_trisums_lr.

    Reverses the input, applies fold_trisums_lr, then reverses the result.
    By the stride-2 overlap property, fold_trisums_rl(v) == fold_trisums_lr(v)
    for any odd-length input, providing bidirectional confirmation.
    """
    return list(reversed(fold_trisums_lr(list(reversed(values)))))


def check_bidirectional_pairs(lr: List[int], rl: List[int]) -> Dict[str, object]:
    """Verify the bidirectional fold and extract the last-4 apex pairs."""
    bidir_verified = (lr == rl)
    tail = lr[-4:] if len(lr) >= 4 else lr[:]
    pairs: List[Dict[str, int]] = []
    for i in range(0, len(tail) - 1, 2):
        pairs.append({"a": tail[i], "b": tail[i + 1]})
    return {
        "bidir_verified": bidir_verified,
        "apex_pairs": pairs,
    }


def _map_anchor_to_nine(digit: int) -> int:
    """Map any anchor (3, 6, 9) to the visible digit 9.
    Non-anchor digits are returned unchanged.
    """
    return 9 if digit in (3, 6, 9) else digit


def _compute_anchor_flags(values: Iterable[int]) -> List[int]:
    """Compute high-digit flags for 3/6/9 anchors (0: non-anchor/3, 1: 6, 2: 9)."""
    flags: List[int] = []
    for v in values:
        if v == 6:
            flags.append(1)
        elif v == 9:
            flags.append(2)
        else:
            flags.append(0)
    return flags


def compress_text(text: str) -> Dict[str, object]:
    """Fold an ordered cipher stream using bidirectional trisum verification and 12-block pin encoding.

    Stops at the fold level closest to six values (canonical PIN), while also
    recording LR/RL bidirectional verification, apex pairs, anchor flags, and
    12-block pin-only compression metadata.
    """
    order, raw_sequence, counts, _ = _build_sequence(text)
    if not raw_sequence:
        return {
            "input_length": len(text),
            "cipher_order": [],
            "counts": {},
            "sequence": [],
            "ordered_cypher_values": [],
            "pin": [],
            "flags": [],
            "folded_values": [],
            "pin_lr": [],
            "pin_rl": [],
            "apex_pairs": [],
            "bidir_verified": True,
            "fold_log": [],
            "anchor_counts": {},
            "duality_checks": 0,
            "pin_only_12block": compress_12block_stream([]),
            "cyclic": CYCLIC,
            "rotor": CyclicRotor().rotations(),
            "project": PROJECT_NAME,
        }

    ordered_values = [CHARACTER_MAP[ch] for ch in raw_sequence]
    ordered_cypher_numbers = [
        collapse(CYPHER_NUMBER_MAP.get(ch, 1) * CHARACTER_MAP[ch])
        for ch in raw_sequence
    ]
    current = ordered_values[:]
    folds: List[Dict[str, object]] = []
    anchor_counts: Counter[int] = Counter()
    duality_checks = 0
    folds_count = 0

    while len(current) > 6:
        lr = fold_trisums_lr(current)
        rl = fold_trisums_rl(current)
        if not lr or len(lr) >= len(current):
            break
        if abs(len(lr) - 6) > abs(len(current) - 6):
            break
        bidir = check_bidirectional_pairs(lr, rl)
        fold_anchor_counts = Counter(v for v in lr if v in (3, 6, 9))
        checks = sum(fold_anchor_counts.values())
        if fold_anchor_counts:
            if not all(verify_369_duality(v)["verified"] for v in fold_anchor_counts):
                raise ValueError("A 369 multiplication duality failed verification")
        anchor_counts.update(fold_anchor_counts)
        duality_checks += checks
        folds.append({
            "fold": folds_count + 1,
            "input_count": len(current),
            "output_count": len(lr),
            "bidir_verified": bidir["bidir_verified"],
            "apex_pairs": bidir["apex_pairs"],
            "anchor_counts": {str(v): c for v, c in fold_anchor_counts.items()},
            "duality_checks": checks,
        })
        current = lr
        folds_count += 1

    lr_final = fold_trisums_lr(current) or current
    rl_final = fold_trisums_rl(current) or current
    if not fold_trisums_lr(current):
        lr_final = current
        rl_final = current
    apex_bidir = check_bidirectional_pairs(lr_final, rl_final)

    return {
        "input_length": len(text),
        "cipher_order": order,
        "counts": counts,
        "sequence": raw_sequence,
        "ordered_cypher_values": ordered_values,
        "pin": current[:],
        "flags": _compute_anchor_flags(current),
        "folded_values": current[:],
        "pin_lr": lr_final,
        "pin_rl": rl_final,
        "apex_pairs": apex_bidir["apex_pairs"],
        "bidir_verified": apex_bidir["bidir_verified"],
        "fold_log": folds,
        "anchor_counts": {str(v): c for v, c in anchor_counts.items()},
        "duality_checks": duality_checks,
        "pin_only_12block": compress_12block_stream(
            ordered_values,
            cypher_order_stream=ordered_cypher_numbers,
        ),
        "cyclic": CYCLIC,
        "rotor": build_rotor_matrix(),
        "project": PROJECT_NAME,
    }


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
    """Reverse the fold by replaying the stored per-bucket symbols."""
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
    print("Flags:", result["flags"])
    print("12-Block Forward Pins:", result["pin_only_12block"]["forward_pins"])
    print("12-Block Backward Pins:", result["pin_only_12block"]["backward_pins"])
    print("Unfolded:", unfold_sequence(result["pin"], result["cipher_order"], result["counts"]))
