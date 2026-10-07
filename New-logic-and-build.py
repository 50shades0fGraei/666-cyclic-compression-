"""Compatibility entry point for the cyclic compression system.

This script preserves the original project name while delegating the actual
logic to the structured compressor implementation in cycle_compressor.py.
"""

from cycle_compressor import compress_text, rebuild_sequence


def main() -> None:
    sample = "hello world"
    compressed = compress_text(sample)
    print("INPUT:", sample)
    print("CIPHER ORDER:", compressed["cipher_order"])
    print("PIN:", compressed["pin"])
    print("FOLD LOG:", compressed["fold_log"])
    print("REBUILD:", rebuild_sequence(compressed["pin"]))


if __name__ == "__main__":
    main()
