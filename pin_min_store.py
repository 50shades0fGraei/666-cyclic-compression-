"""Minimal PIN store that also retains just enough metadata to rebuild the original text.

Unlike the previous `pin_store.py`, this version saves the *pin*, the *cipher order*
and the *bucket counts* produced by `compress_text`.  Those three pieces are the
only data the `unfold_sequence` routine needs to reconstruct the original
character sequence (see `cycle_compressor.unfold_sequence`).  The on‑disk
payload is still tiny – typically a few hundred bytes for a short string – and
does not require a separate lookup table.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Optional

# Local import – the main compression engine.
from cycle_compressor import compress_text, unfold_sequence

# Directory for storing the minimal JSON files.
STORE_DIR = Path(__file__).with_name("pin_min_data")
STORE_DIR.mkdir(exist_ok=True)

def _pin_to_str(pin: List[int]) -> str:
    """Deterministic key for a PIN – comma‑separated integers."""
    return ",".join(map(str, pin))

def store_minimal(text: str) -> Path:
    """Compress *text* and write a minimal JSON file.

    The JSON contains:
    * ``pin`` – the six‑digit list (used as identifier).
    * ``cipher_order`` – the ordered list of cipher values.
    * ``counts`` – per‑bucket character lists required for reconstruction.
    """
    result = compress_text(text)
    payload = {
        "pin": result["pin"],
        "cipher_order": result["cipher_order"],
        "counts": result["counts"],
    }
    pin_str = _pin_to_str(payload["pin"])  # e.g. "3,6,9,1,5,2"
    file_path = STORE_DIR / f"min_{pin_str.replace(',', '_')}.json"
    file_path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    return file_path

def reconstruct_text(pin: List[int]) -> Optional[str]:
    """Rebuild the original text for *pin* if a matching minimal file exists.

    Returns ``None`` when the PIN has no stored entry.
    """
    pin_str = _pin_to_str(pin)
    file_path = STORE_DIR / f"min_{pin_str.replace(',', '_')}.json"
    if not file_path.exists():
        return None
    data = json.loads(file_path.read_text(encoding="utf-8"))
    # Use the library's unfold_sequence to rebuild the symbol list.
    rebuilt = unfold_sequence(data["pin"], data["cipher_order"], data["counts"])
    # ``unfold_sequence`` returns a list of characters; join them.
    return "".join(rebuilt)

# Simple CLI for manual testing.
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Store minimal PIN data and rebuild text")
    sub = parser.add_subparsers(dest="cmd", required=True)
    store = sub.add_parser("store")
    store.add_argument("text", nargs="+", help="Text to compress and store")
    get = sub.add_parser("get")
    get.add_argument("pin", nargs=6, type=int, help="Six integer PIN values")
    args = parser.parse_args()
    if args.cmd == "store":
        txt = " ".join(args.text)
        path = store_minimal(txt)
        print(f"Stored minimal data at {path}")
    else:
        pin = list(args.pin)
        original = reconstruct_text(pin)
        if original is None:
            print("PIN not found.")
        else:
            print("Reconstructed text:")
            print(original)
