# Dual-track cyclic compressor

This directory contains a separate implementation based on
[`../BUILD-SPEC-2026-10-03.md`](../BUILD-SPEC-2026-10-03.md). It does not replace
the existing prototype.

## Current implementation

- The cyclic basis is fixed at `[1, 4, 2, 8, 5, 7]`.
- A supplied 90-symbol library is grouped in order into fifteen six-symbol
  cyphers. Within each group, the cyclic value identifies the symbol position.
- Six cyclic values map to a stable PID in the 46,656-entry pattern library.
- Ordered `(cyclic value, cypher ID)` pairs are grouped in chunks of six. Full
  groups store the cyclic values as a PID and aligned cypher IDs; the partial
  final group stores its exact cyclic values and length.
- Recursive parent groups are recorded in one lineal preorder list. Branch
  records say how many ordered children follow; leaf records carry the PID and
  aligned cypher IDs (or exact cyclic values for the last partial chunk).
  This guarantees round-trip order, but parent groups are not misrepresented as
  single PIDs.
- Six verification sums are the sums of cypher IDs for each cyclic value, in
  cyclic order. They validate the stream; they do not independently encode it.

This is a lossless structural prototype, not yet a demonstrated compression
ratio. The lineal child records preserve the information required for
unfolding. Batch optimization, streaming packets, binary Pass 2, the specified
369 correction algorithm, and an agreed universal 90-character ordering remain
future work.

## API

```python
from dual_track import SymbolLibrary, encode_text, decode_text

symbols = tuple(chr(code) for code in range(0x1000, 0x1000 + 90))
library = SymbolLibrary(symbols)
folded = encode_text("example", library)
assert decode_text(folded, library) == "example"
```

Provide the actual agreed 90-symbol order to `SymbolLibrary`; the example uses
placeholder Unicode symbols only for demonstration.

For a compact binary archive, `pack_text(text, library)` stores the six-wide
cyclic PIDs, aligned four-bit cypher IDs, the six verification sums, and the
90-symbol library. `unpack_text(payload)` verifies the checksum and sums before
returning the text. This archive does not store recursive copies of child PIDs.

Run the isolated tests from the repository root:

```bash
python -m unittest discover -s dual_track/tests -v
```
