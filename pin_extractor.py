"""Utility to obtain the 6‑digit PIN from the cyclic compression engine.

The existing :func:`compress_text` in ``cycle_compressor.py`` returns a detailed
JSON structure containing many diagnostic fields (cipher order, fold log, etc.).
For scenarios where only the final compressed identifier is required – e.g.
storing a minimal reference or transmitting a compact payload – the extra
metadata inflates the output size.

This module provides a thin wrapper that calls ``compress_text`` and returns
**only** the ``pin`` field.  The function is lightweight, has no side‑effects,
and produces a deterministic six‑integer list.

Example
-------
```python
from pin_extractor import get_pin

pin = get_pin("hello world")
print(pin)  # -> [3, 6, 9, 1, 5, 2]  (example values)
```
"""

from __future__ import annotations

from typing import Any, Dict, List

# Import the main compressor implementation.
from cycle_compressor import compress_text


def get_pin(text: str) -> List[int]:
    """Compress *text* and return only the 6‑digit PIN.

    Parameters
    ----------
    text:
        The input string to be compressed.

    Returns
    -------
    List[int]
        A list of six integers representing the compressed PIN.
    """
    result = compress_text(text)
    return result["pin"]


def get_pin_with_folds(text: str) -> Dict[str, Any]:
    """Compress *text* and return the PIN Set along with the fold amounts
    (how many unfolds to complete).
    """
    result = compress_text(text)
    pin12 = result.get("pin_only_12block", {})
    folds = int(result.get("fold_amount") or pin12.get("folds_to_7") or len(result.get("fold_log", [])))
    cypher_folds = int(result.get("cypher_fold_amount") or pin12.get("cypher_folds_to_7") or folds)
    return {
        "pin": result["pin"],
        "forward_pin": pin12.get("forward_pin"),
        "backward_pin": pin12.get("backward_pin"),
        "cypher_forward_pin": pin12.get("cypher_forward_pin"),
        "cypher_backward_pin": pin12.get("cypher_backward_pin"),
        "fold_amount": folds,
        "unfolds_to_complete": folds,
        "cypher_fold_amount": cypher_folds,
        "cypher_unfolds_to_complete": cypher_folds,
        "compact_pin_code": pin12.get("compact_pin_code"),
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python pin_extractor.py <text>")
        sys.exit(1)
    input_text = " ".join(sys.argv[1:])
    print(get_pin_with_folds(input_text))
