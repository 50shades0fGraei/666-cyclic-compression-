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
    analyze_cyclic_stream,
    count_alignments,
    count_cyclic_stream_alignments,
    fold_pair_stream,
    place_cypher_order,
    unfold_pair_stream,
)
from pin_only_12block import (
    DEFAULT_LOGIC,
    FixedLogic,
    compress_12block_stream,
    decode_pin,
    decompress_12block_stream,
    encode_12block,
)

__all__ = [
    "PROJECT_NAME",
    "COPYRIGHT_NOTICE",
    "CYCLIC",
    "compress_text",
    "rebuild_sequence",
    "unfold_numeric",
    "unfold_sequence",
    "analyze_cyclic_stream",
    "count_alignments",
    "count_cyclic_stream_alignments",
    "place_cypher_order",
    "fold_pair_stream",
    "unfold_pair_stream",
    "FixedLogic",
    "DEFAULT_LOGIC",
    "encode_12block",
    "decode_pin",
    "compress_12block_stream",
    "decompress_12block_stream",
]


def main() -> None:
    sample = "hello world"
    result = compress_text(sample)
    print(f"Project: {PROJECT_NAME}")
    print("Rotor:", result["rotor"])
    print("PIN:", result["pin"])
    print("PIN LR / RL:", result["pin_lr"], "/", result["pin_rl"], "Verified:", result["bidir_verified"])
    print("UNFOLD:", unfold_sequence(result["pin"], result["cipher_order"], result["counts"]))
    print(
        "NUMERIC ORDER VERIFIED:",
        unfold_numeric(
            result["ordered_cypher_values"],
            result["fold_log"],
            result["folded_values"],
        ),
    )

    # Demonstrate October 2026 Paper Test Vector (3655555 -> 298-1 / 882-7 -> 3655555)
    block_enc = encode_12block("3655555")
    block_dec = decode_pin(block_enc["forward_pin"])
    print(
        f"12-Block Pin-Only Test Vector: {block_enc['input_block']} -> "
        f"expanded {block_enc['expanded']} -> consolidated {block_enc['consolidated']} -> "
        f"apex {block_enc['apex']} -> pin {block_enc['forward_pin']} / {block_enc['backward_pin']} -> "
        f"decoded {block_dec['reconstructed']}"
    )


if __name__ == "__main__":
    main()
