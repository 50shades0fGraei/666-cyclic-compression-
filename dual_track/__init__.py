"""Isolated dual-track cyclic compression implementation."""

from .codec import (
    CHUNK_SIZE,
    FORMAT_VERSION,
    PATTERN_COUNT,
    decode_pattern,
    decode_text,
    encode_pattern,
    encode_text,
    fold_pairs,
    pack_text,
    unpack_text,
    unfold_pairs,
)
from .library import CYCLIC, LIBRARY_VERSION, SymbolLibrary

__all__ = [
    "CHUNK_SIZE",
    "CYCLIC",
    "FORMAT_VERSION",
    "LIBRARY_VERSION",
    "PATTERN_COUNT",
    "SymbolLibrary",
    "decode_pattern",
    "decode_text",
    "encode_pattern",
    "encode_text",
    "fold_pairs",
    "pack_text",
    "unpack_text",
    "unfold_pairs",
]
