"""Compact store that saves only the data required to fully reconstruct the original text.

Required elements for reconstruction (see `cycle_compressor.unfold_sequence`):
* **pin** – six‑digit list (identifies the final folded state).
* **cipher_order** – ordered list of cipher values used during compression.
* **counts** – a mapping from each cipher value to the list of characters that fell
  into that bucket.  This is the only non‑deterministic piece; the CYCLIC list is
  a constant defined in the library and does not need to be stored.

The JSON payload is written with the most compact separators, making the file
typically a few hundred bytes even for moderate‑length inputs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Optional

# Import the core compressor utilities.
from cycle_compressor import compress_text, unfold_sequence

# Directory where the tiny JSON files will live.
STORE_DIR = Path(__file__).with_name("compact_pin_data")
STORE_DIR.mkdir(exist_ok=True)

def _pin_key(pin: List[int]) -> str:
    """Create a deterministic filename key from a PIN list."""
    return ",".join(map(str, pin))

def store_compact(text: str) -> Path:
    """Compress *text* and write a minimal JSON file.

    The stored JSON contains exactly three keys:
    * ``pin`` – the six‑digit identifier.
    * ``cipher_order`` – the ordered list of cipher values.
    * ``counts`` – the per‑cipher bucket character lists needed for reconstruction.
    """
    result = compress_text(text)
    payload = {
        "pin": result["pin"],
        "cipher_order": result["cipher_order"],
        "counts": result["counts"],
    }
    pin_str = _pin_key(payload["pin"])  # e.g. "3,6,9,1,5,2"
    file_path = STORE_DIR / f"compact_{pin_str.replace(',', '_')}.json"
    # Compact JSON: no whitespace, ':' and ',' only.
    file_path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    return file_path

def reconstruct(text_pin: List[int]) -> Optional[str]:
    """Rebuild the original text from a stored compact file.

    Returns ``None`` if no matching file exists for the given PIN.
    """
    pin_str = _pin_key(text_pin)
    file_path = STORE_DIR / f"compact_{pin_str.replace(',', '_')}.json"
    if not file_path.exists():
        return None
    data = json.loads(file_path.read_text(encoding="utf-8"))
    # Use the library's unfold_sequence to get the original character list.
    rebuilt_chars = unfold_sequence(data["pin"], data["cipher_order"], data["counts"])
    return "".join(rebuilt_chars)

# Simple CLI for quick manual tests.
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Compact PIN storage and reconstruction")
    sub = parser.add_subparsers(dest="cmd", required=True)
    store = sub.add_parser("store")
    store.add_argument("text", nargs="+", help="Text to compress and store")
    get = sub.add_parser("get")
    get.add_argument("pin", nargs=6, type=int, help="Six integer PIN values")
    args = parser.parse_args()
    if args.cmd == "store":
        txt = " ".join(args.text)
        path = store_compact(txt)
        print(f"Stored compact data at {path}")
    else:
        pin = list(args.pin)
        original = reconstruct(pin)
        if original is None:
            print("No entry found for the given PIN.")
        else:
            print("Reconstructed text:\n" + original)
