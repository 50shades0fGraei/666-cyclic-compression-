"""Fixed six-symbol pattern library for the cyclic compressor prototype.

The PID assignment is the lexicographic base-6 index using CYCLIC order. This
implements one confirmed 6-to-1 layer. A separate lossless mixed-radix codec
folds ordered cyclic/cypher pairs; it is not a size-compression algorithm.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from cycle_compressor import build_rotor_matrix, collapse

CYCLIC = (1, 4, 2, 8, 5, 7)
BASE_NUMBER = 142_857
MULTIPLIERS = (1, 2, 3, 4, 5, 6)
MULTIPLIER_ROWS = {
    multiplier: tuple(int(digit) for digit in str(multiplier * BASE_NUMBER))
    for multiplier in MULTIPLIERS
}
PATTERN_WIDTH = 6
PATTERN_COUNT = len(CYCLIC) ** PATTERN_WIDTH
ANCHOR_VALUES = (3, 6, 9)
PAIR_ALPHABET_SIZE = len(CYCLIC) * 15
PAIR_FOLD_FORMAT = "cyclic-pair-fold-v1"


def encode_pattern(cyphers: Sequence[int]) -> int:
    """Return the stable PID for exactly six values from the cyclic set."""
    if len(cyphers) != PATTERN_WIDTH:
        raise ValueError(f"a pattern must contain exactly {PATTERN_WIDTH} cyphers")

    pid = 0
    for cypher in cyphers:
        if isinstance(cypher, bool) or cypher not in CYCLIC:
            raise ValueError(f"unsupported cyclic cypher: {cypher!r}")
        pid = pid * len(CYCLIC) + CYCLIC.index(cypher)
    return pid


def decode_pattern(pid: int) -> tuple[int, ...]:
    """Expand a PID into its six cyclic values."""
    if isinstance(pid, bool) or not isinstance(pid, int) or not 0 <= pid < PATTERN_COUNT:
        raise ValueError(f"PID must be an integer from 0 to {PATTERN_COUNT - 1}")

    digits = [0] * PATTERN_WIDTH
    remainder = pid
    for position in range(PATTERN_WIDTH - 1, -1, -1):
        remainder, digits[position] = divmod(remainder, len(CYCLIC))
    return tuple(CYCLIC[digit] for digit in digits)


def fold_cypher_stream(cyphers: Iterable[int]) -> list[int]:
    """Fold a cypher stream into PIDs without padding partial patterns."""
    values = list(cyphers)
    if len(values) % PATTERN_WIDTH:
        raise ValueError(
            "cypher stream length must be a multiple of six; "
            "partial-pattern handling is not specified"
        )
    return [
        encode_pattern(values[offset:offset + PATTERN_WIDTH])
        for offset in range(0, len(values), PATTERN_WIDTH)
    ]


def unfold_pattern_ids(pattern_ids: Iterable[int]) -> list[int]:
    """Expand PIDs in order back into the original cyclic-value stream."""
    return [
        cypher
        for pid in pattern_ids
        for cypher in decode_pattern(pid)
    ]


def _encode_pair(pair: tuple[int, int]) -> int:
    if len(pair) != 2:
        raise ValueError("each item must be a (cyclic_value, cypher_id) pair")
    cyclic_value, cypher_id = pair
    if (
        isinstance(cyclic_value, bool)
        or not isinstance(cyclic_value, int)
        or cyclic_value not in CYCLIC
    ):
        raise ValueError(f"unsupported cyclic value: {cyclic_value!r}")
    if (
        isinstance(cypher_id, bool)
        or not isinstance(cypher_id, int)
        or not 1 <= cypher_id <= 15
    ):
        raise ValueError(f"cypher ID must be an integer from 1 to 15: {cypher_id!r}")
    return CYCLIC.index(cyclic_value) * 15 + cypher_id - 1


def _decode_pair(token: int) -> tuple[int, int]:
    cyclic_index, cypher_offset = divmod(token, 15)
    return CYCLIC[cyclic_index], cypher_offset + 1


def _pack_digits(values: Sequence[int], radix: int) -> int:
    packed = 0
    for value in values:
        if not 0 <= value < radix:
            raise ValueError("fold item is outside the pattern alphabet")
        packed = packed * radix + value
    return packed


def _unpack_digits(value: int, radix: int, digit_count: int) -> list[int]:
    digits = [0] * digit_count
    remainder = value
    for index in range(digit_count - 1, -1, -1):
        remainder, digits[index] = divmod(remainder, radix)
    if remainder:
        raise ValueError("fold value does not fit its recorded pattern width")
    return digits


def fold_pair_stream(
    paired_stream: Iterable[tuple[int, int]],
) -> dict[str, object]:
    """Recursively fold ordered cyclic/cypher pairs into a lossless root code.

    The integer code for each six-item group uses a mixed-radix alphabet, with
    each fold level's alphabet sized to hold one complete child pattern. The
    root is serialized as hexadecimal so it can be persisted without decimal
    integer conversion limits. This preserves the input exactly but does not
    promise a smaller encoding.
    """
    current = [_encode_pair(pair) for pair in paired_stream]
    original_count = len(current)
    fold_rounds = 0

    while len(current) > 1:
        radix = PAIR_ALPHABET_SIZE ** (PATTERN_WIDTH ** fold_rounds)
        current = [
            _pack_digits(current[offset:offset + PATTERN_WIDTH], radix)
            for offset in range(0, len(current), PATTERN_WIDTH)
        ]
        fold_rounds += 1

    return {
        "format": PAIR_FOLD_FORMAT,
        "base_number": BASE_NUMBER,
        "pattern_width": PATTERN_WIDTH,
        "original_count": original_count,
        "fold_rounds": fold_rounds,
        "root_code_hex": format(current[0], "x") if current else None,
    }


def unfold_pair_stream(folded: dict[str, object]) -> list[tuple[int, int]]:
    """Restore and validate the ordered pair stream from a recursive fold."""
    if folded.get("format") != PAIR_FOLD_FORMAT:
        raise ValueError("unsupported pair-fold format")
    if folded.get("base_number") != BASE_NUMBER or folded.get("pattern_width") != PATTERN_WIDTH:
        raise ValueError("pair-fold basis metadata does not match this decoder")

    original_count = folded.get("original_count")
    fold_rounds = folded.get("fold_rounds")
    root_code_hex = folded.get("root_code_hex")
    if (
        isinstance(original_count, bool)
        or not isinstance(original_count, int)
        or original_count < 0
    ):
        raise ValueError("original_count must be a non-negative integer")
    if isinstance(fold_rounds, bool) or not isinstance(fold_rounds, int) or fold_rounds < 0:
        raise ValueError("fold_rounds must be a non-negative integer")

    lengths = [original_count]
    while lengths[-1] > 1:
        lengths.append((lengths[-1] + PATTERN_WIDTH - 1) // PATTERN_WIDTH)
    expected_rounds = len(lengths) - 1
    if fold_rounds != expected_rounds:
        raise ValueError("fold_rounds does not match original_count")

    if original_count == 0:
        if root_code_hex is not None:
            raise ValueError("empty pair stream must not have a root code")
        return []
    if (
        not isinstance(root_code_hex, str)
        or not root_code_hex
        or any(char not in "0123456789abcdef" for char in root_code_hex)
    ):
        raise ValueError("root_code_hex must be a non-empty lowercase hexadecimal string")

    current = [int(root_code_hex, 16)]
    for level in range(fold_rounds - 1, -1, -1):
        child_count = lengths[level]
        radix = PAIR_ALPHABET_SIZE ** (PATTERN_WIDTH ** level)
        expanded: list[int] = []
        for node_index, pid in enumerate(current):
            group_count = min(PATTERN_WIDTH, child_count - node_index * PATTERN_WIDTH)
            expanded.extend(_unpack_digits(pid, radix, group_count))
        current = expanded

    if len(current) != original_count or any(
        token < 0 or token >= PAIR_ALPHABET_SIZE for token in current
    ):
        raise ValueError("decoded pair stream is inconsistent with its metadata")
    return [_decode_pair(token) for token in current]


def count_alignments(
    pairs: Iterable[tuple[int, int]],
) -> dict[str, object]:
    """Count (cyclic cypher, multiplier) alignments in one fixed-base matrix.

    Each pair increments the left-to-right slot where its cyclic cypher appears
    in the selected ``multiplier * 142857`` row. This aggregates counts without
    retaining the per-occurrence input stream.
    """
    slot_counts = {
        multiplier: [0] * len(CYCLIC)
        for multiplier in MULTIPLIERS
    }
    alignment_count = 0

    for pair in pairs:
        if len(pair) != 2:
            raise ValueError("each alignment must be a (cyclic_cypher, multiplier) pair")
        cyclic_cypher, multiplier = pair
        if isinstance(cyclic_cypher, bool) or cyclic_cypher not in CYCLIC:
            raise ValueError(f"unsupported cyclic cypher: {cyclic_cypher!r}")
        if (
            isinstance(multiplier, bool)
            or not isinstance(multiplier, int)
            or multiplier not in MULTIPLIER_ROWS
        ):
            raise ValueError(f"multiplier must be an integer from 1 to 6: {multiplier!r}")

        row = MULTIPLIER_ROWS[multiplier]
        slot_counts[multiplier][row.index(cyclic_cypher)] += 1
        alignment_count += 1

    return {
        "base_number": BASE_NUMBER,
        "rows": [
            {
                "multiplier": multiplier,
                "cyclic_row": list(MULTIPLIER_ROWS[multiplier]),
                "slot_counts": slot_counts[multiplier],
            }
            for multiplier in MULTIPLIERS
        ],
        "alignment_count": alignment_count,
    }


def count_cyclic_stream_alignments(cyphers: Iterable[int]) -> dict[str, object]:
    """Count a cypher stream while advancing the multiplier once per occurrence.

    The first occurrence uses multiplier 1; subsequent occurrences cycle through
    2..6 and back to 1. Only aggregate slot totals are retained.
    """
    pairs = (
        (cypher, MULTIPLIERS[index % len(MULTIPLIERS)])
        for index, cypher in enumerate(cyphers)
    )
    result = count_alignments(pairs)
    result["multiplier_rule"] = "1..6 repeated in occurrence order"
    return result


def place_cypher_order(
    paired_stream: Iterable[tuple[int, int]],
) -> dict[str, object]:
    """Place cypher IDs into slots selected by cyclic values and multiplier rows.

    Each input item is ``(cyclic_value, cypher_id)``. The multiplier starts at
    1 and advances once per item through 1..6. Cypher IDs are kept in input order
    within each multiplier/slot sequence; interleaving between different slots
    is not represented.
    """
    slots = {
        multiplier: [[] for _ in CYCLIC]
        for multiplier in MULTIPLIERS
    }
    occurrence_count = 0

    for occurrence_count, pair in enumerate(paired_stream, start=1):
        if len(pair) != 2:
            raise ValueError("each item must be a (cyclic_value, cypher_id) pair")
        cyclic_value, cypher_id = pair
        if isinstance(cyclic_value, bool) or cyclic_value not in CYCLIC:
            raise ValueError(f"unsupported cyclic value: {cyclic_value!r}")
        if (
            isinstance(cypher_id, bool)
            or not isinstance(cypher_id, int)
            or not 1 <= cypher_id <= 15
        ):
            raise ValueError(f"cypher ID must be an integer from 1 to 15: {cypher_id!r}")

        multiplier = MULTIPLIERS[(occurrence_count - 1) % len(MULTIPLIERS)]
        slot_index = MULTIPLIER_ROWS[multiplier].index(cyclic_value)
        slots[multiplier][slot_index].append(cypher_id)

    return {
        "base_number": BASE_NUMBER,
        "multiplier_rule": "1..6 repeated in occurrence order",
        "occurrence_count": occurrence_count,
        "rows": [
            {
                "multiplier": multiplier,
                "cyclic_row": list(MULTIPLIER_ROWS[multiplier]),
                "slots": [
                    {
                        "slot": slot_index + 1,
                        "cyclic_value": cyclic_value,
                        "cypher_order": slots[multiplier][slot_index],
                    }
                    for slot_index, cyclic_value in enumerate(
                        MULTIPLIER_ROWS[multiplier]
                    )
                ],
            }
            for multiplier in MULTIPLIERS
        ],
    }


def evaluate_rotor_rows() -> list[dict[str, object]]:
    """Record each row's cumulative sums that reduce to a 3/6/9 anchor.

    The step count is one-based and includes the cyclic value that reaches the
    anchor. This evaluates anchor hits; it does not infer source-symbol placement.
    """
    rows: list[dict[str, object]] = []
    for row_number, rotation in enumerate(build_rotor_matrix(), start=1):
        running_sum = 0
        anchor_hits: list[dict[str, int]] = []
        for step_count, cyclic_value in enumerate(rotation, start=1):
            running_sum += cyclic_value
            anchor = collapse(running_sum)
            if anchor in ANCHOR_VALUES:
                anchor_hits.append(
                    {
                        "steps": step_count,
                        "sum": running_sum,
                        "anchor": anchor,
                    }
                )
        rows.append(
            {
                "row": row_number,
                "rotation": rotation,
                "anchor_hits": anchor_hits,
            }
        )
    return rows
