"""Public entry point for Randall's Cyclic Compression.

Copyright (c) 2026 Randall Lujan. All rights reserved.
Patent pending for the cyclic compression and rotor-folding system described herein.
"""

from cycle_compressor import (
    CYCLIC,
    COPYRIGHT_NOTICE,
    PROJECT_NAME,
    compress_text,
    rebuild_sequence,
    unfold_numeric,
    unfold_sequence,
)
from pattern_library import (
    count_alignments,
    count_cyclic_stream_alignments,
    fold_pair_stream,
    place_cypher_order,
    unfold_pair_stream,
)

__all__ = [
    "PROJECT_NAME",
    "COPYRIGHT_NOTICE",
    "CYCLIC",
    "compress_text",
    "rebuild_sequence",
    "unfold_numeric",
    "unfold_sequence",
    "count_alignments",
    "count_cyclic_stream_alignments",
    "place_cypher_order",
    "fold_pair_stream",
    "unfold_pair_stream",
]


def main() -> None:
    sample = "hello world"
    result = compress_text(sample)
    print(f"Project: {PROJECT_NAME}")
    print("Rotor:", result["rotor"])
    print("PIN:", result["pin"])
    print("UNFOLD:", unfold_sequence(result["pin"], result["cipher_order"], result["counts"]))
    print(
        "NUMERIC ORDER VERIFIED:",
        unfold_numeric(
            result["ordered_cypher_values"],
            result["fold_log"],
            result["folded_values"],
        ),
    )
    print("Fold log:", result["fold_log"])


if __name__ == "__main__":
    main()
