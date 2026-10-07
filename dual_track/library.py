"""Symbol and pattern libraries for the isolated dual-track implementation."""

from __future__ import annotations

from collections.abc import Sequence

CYCLIC = (1, 4, 2, 8, 5, 7)
SYMBOL_COUNT = 90
SYMBOLS_PER_CYPHER = 6
CYPHER_COUNT = SYMBOL_COUNT // SYMBOLS_PER_CYPHER
LIBRARY_VERSION = "dual-track-v1"


class SymbolLibrary:
    """A supplied 90-symbol ordering split into fifteen six-symbol cyphers."""

    def __init__(self, symbols: Sequence[str]) -> None:
        values = tuple(symbols)
        if len(values) != SYMBOL_COUNT:
            raise ValueError(f"symbol library must contain exactly {SYMBOL_COUNT} symbols")
        if any(not isinstance(symbol, str) or len(symbol) != 1 for symbol in values):
            raise ValueError("each library entry must be exactly one character")
        if len(set(values)) != SYMBOL_COUNT:
            raise ValueError("symbol library entries must be unique")
        self.symbols = values
        self._symbol_to_index = {symbol: index for index, symbol in enumerate(values)}

    def encode_symbol(self, symbol: str) -> tuple[int, int]:
        """Map a symbol to its cyclic position and one-based cypher ID."""
        try:
            index = self._symbol_to_index[symbol]
        except KeyError as error:
            raise ValueError(f"symbol is not in the configured library: {symbol!r}") from error
        cypher_id, symbol_offset = divmod(index, SYMBOLS_PER_CYPHER)
        return CYCLIC[symbol_offset], cypher_id + 1

    def decode_pair(self, cyclic_value: int, cypher_id: int) -> str:
        """Restore a symbol from its cyclic position and cypher ID."""
        if isinstance(cyclic_value, bool) or not isinstance(cyclic_value, int):
            raise ValueError(f"invalid cyclic value: {cyclic_value!r}")
        if cyclic_value not in CYCLIC:
            raise ValueError(f"unsupported cyclic value: {cyclic_value!r}")
        if isinstance(cypher_id, bool) or not isinstance(cypher_id, int):
            raise ValueError(f"invalid cypher ID: {cypher_id!r}")
        if not 1 <= cypher_id <= CYPHER_COUNT:
            raise ValueError(f"cypher ID must be from 1 to {CYPHER_COUNT}")
        index = (cypher_id - 1) * SYMBOLS_PER_CYPHER + CYCLIC.index(cyclic_value)
        return self.symbols[index]

    def encode_text(self, text: str) -> list[tuple[int, int]]:
        """Convert text to its ordered parallel-track values."""
        return [self.encode_symbol(symbol) for symbol in text]

    def decode_pairs(self, pairs: Sequence[tuple[int, int]]) -> str:
        """Convert ordered parallel-track values back to text."""
        return "".join(self.decode_pair(cyclic_value, cypher_id) for cyclic_value, cypher_id in pairs)
