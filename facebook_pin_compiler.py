# -*- coding: utf-8 -*-
"""Facebook Profile Data -> 666 Cyclic PIN Code Compilation Tool.

For each section/file in the Facebook profile export (and for the entire profile
strung together), outputs ONLY the 4 PIN codes and the fold amounts required to
unfold the math to completion:
  1. Cyclic Stream Forward Pin (`forward_pin`)
  2. Cyclic Stream Backward Pin (`backward_pin`)
  3. Cypher Order by Number Forward Pin (`cypher_forward_pin`)
  4. Cypher Order by Number Backward Pin (`cypher_backward_pin`)
  + Fold Amounts (`fold_amount` / `folds_to_7` and `cypher_fold_amount` / `cypher_folds_to_7`)
"""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from cycle_compressor import compress_text
from pin_only_12block import encode_12block

TEXT_EXTENSIONS = {
    ".json",
    ".html",
    ".htm",
    ".txt",
    ".csv",
    ".md",
    ".xml",
    ".vcf",
    ".ics",
}


def _fix_fb_mojibake(text: str) -> str:
    """Fix Facebook JSON export UTF-8-as-Latin1 encoding artifacts when present."""
    try:
        return text.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def _extract_text_from_bytes(raw_bytes: bytes, rel_path: str) -> str:
    """Convert raw file bytes into a deterministic text representation for cyclic folding."""
    ext = Path(rel_path).suffix.lower()
    if ext in TEXT_EXTENSIONS or ext == "":
        try:
            decoded = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            decoded = raw_bytes.decode("latin1", errors="replace")

        if ext == ".json":
            try:
                parsed = json.loads(decoded)
                normalized = json.dumps(parsed, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                return _fix_fb_mojibake(normalized)
            except json.JSONDecodeError:
                return _fix_fb_mojibake(decoded)
        return decoded

    return raw_bytes.hex()


def iter_profile_entries(
    source_path: Path,
    include_media: bool = False,
) -> Iterable[Tuple[str, bytes]]:
    """Yield (relative_path, raw_bytes) in deterministic sorted order from a .zip, folder, or file."""
    if source_path.is_file():
        if zipfile.is_zipfile(source_path):
            with zipfile.ZipFile(source_path, "r") as zf:
                names = sorted(
                    info.filename
                    for info in zf.infolist()
                    if not info.is_dir()
                )
                for name in names:
                    ext = Path(name).suffix.lower()
                    if not include_media and ext not in TEXT_EXTENSIONS:
                        continue
                    yield name, zf.read(name)
        else:
            yield source_path.name, source_path.read_bytes()
        return

    if source_path.is_dir():
        files = sorted(p for p in source_path.rglob("*") if p.is_file())
        for file_path in files:
            rel_name = file_path.relative_to(source_path).as_posix()
            ext = file_path.suffix.lower()
            if not include_media and ext not in TEXT_EXTENSIONS:
                continue
            yield rel_name, file_path.read_bytes()
        return

    raise FileNotFoundError(f"Source path not found: {source_path}")


def _build_entry_pin_record(rel_path: str, text: str) -> Dict[str, Any]:
    """Compress a section/file and return ONLY its 4 PIN codes and fold amounts."""
    path_obj = Path(rel_path)
    base_name = path_obj.stem or "section"
    target_ext = path_obj.suffix or ".txt"

    comp = compress_text(text)
    pin12 = comp["pin_only_12block"]

    fwd_pin = pin12.get("forward_pin") or "".join(map(str, comp["pin"]))
    bwd_pin = pin12.get("backward_pin") or "".join(map(str, reversed(comp["pin"])))
    cypher_fwd_pin = pin12.get("cypher_forward_pin") or fwd_pin
    cypher_bwd_pin = pin12.get("cypher_backward_pin") or bwd_pin
    folds_to_7 = int(pin12.get("folds_to_7") or comp.get("fold_amount") or 0)
    cypher_folds_to_7 = int(pin12.get("cypher_folds_to_7") or comp.get("cypher_fold_amount") or folds_to_7)

    compact_pin_code = (
        f"{fwd_pin}|{bwd_pin}|{cypher_fwd_pin}|{cypher_bwd_pin}"
        f"|folds={folds_to_7},{cypher_folds_to_7}"
        f"|unfolds={folds_to_7},{cypher_folds_to_7}"
        f"|ext={target_ext}|name={base_name}"
    )

    return {
        "section": rel_path,
        "forward_pin": fwd_pin,
        "backward_pin": bwd_pin,
        "cypher_forward_pin": cypher_fwd_pin,
        "cypher_backward_pin": cypher_bwd_pin,
        "fold_amount": folds_to_7,
        "cypher_fold_amount": cypher_folds_to_7,
        "unfolds_to_complete": folds_to_7,
        "cypher_unfolds_to_complete": cypher_folds_to_7,
        "compact_pin_code": compact_pin_code,
    }


def compile_facebook_profile(
    source_path: Path,
    include_media: bool = False,
) -> Dict[str, Any]:
    """Compile each Facebook profile section into its 4 PIN codes + fold amounts,
    and string the entire profile together into the Master 4 PIN codes + fold amounts.
    """
    section_records: List[Dict[str, Any]] = []
    continuous_segments: List[str] = []

    for rel_path, raw_bytes in iter_profile_entries(source_path, include_media=include_media):
        text = _extract_text_from_bytes(raw_bytes, rel_path)
        if not text.strip():
            continue
        record = _build_entry_pin_record(rel_path, text)
        section_records.append(record)
        continuous_segments.append(f"section {rel_path} {text}")

    full_continuous_text = "\n".join(continuous_segments)
    master_record = _build_entry_pin_record(
        rel_path=f"{source_path.stem or 'facebook_profile'}.profile",
        text=full_continuous_text,
    )

    # Also fold the strung-together section PIN digits into a Chained 4-PIN + fold amounts
    chained_pin_digits = "".join(
        "".join(ch for ch in (rec["forward_pin"] or "") if ch.isdigit())
        + "".join(ch for ch in (rec["backward_pin"] or "") if ch.isdigit())
        + "".join(ch for ch in (rec["cypher_forward_pin"] or "") if ch.isdigit())
        + "".join(ch for ch in (rec["cypher_backward_pin"] or "") if ch.isdigit())
        for rec in section_records
    )
    chained_meta = encode_12block(chained_pin_digits) if chained_pin_digits else {}

    chained_4pin = {
        "forward_pin": chained_meta.get("forward_pin"),
        "backward_pin": chained_meta.get("backward_pin"),
        "cypher_forward_pin": chained_meta.get("cypher_forward_pin"),
        "cypher_backward_pin": chained_meta.get("cypher_backward_pin"),
        "fold_amount": chained_meta.get("folds_to_7", 0),
        "cypher_fold_amount": chained_meta.get("cypher_folds_to_7", 0),
        "unfolds_to_complete": chained_meta.get("folds_to_7", 0),
        "cypher_unfolds_to_complete": chained_meta.get("cypher_folds_to_7", 0),
        "compact_pin_code": chained_meta.get("compact_pin_code"),
    }

    # Continuous single-line compilation string of all section 4-PINs + fold amounts
    strung_together_compilation = " || ".join(rec["compact_pin_code"] for rec in section_records)

    return {
        "master_profile_pin": master_record,
        "chained_sections_pin": chained_4pin,
        "strung_together_pin_compilation": strung_together_compilation,
        "sections": section_records,
    }


def write_compilation_outputs(compilation: Dict[str, Any], output_prefix: Path) -> Tuple[Path, Path]:
    """Write both the compact JSON (.pin.json) and the line-by-line (.pin) compilation."""
    json_path = output_prefix.with_suffix(".pin.json")
    pin_path = output_prefix.with_suffix(".pin")

    json_path.write_text(
        json.dumps(compilation, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    master = compilation["master_profile_pin"]
    chained = compilation["chained_sections_pin"]
    lines = [
        f"MASTER_PROFILE|{master['compact_pin_code']}",
        f"CHAINED_PINS|{chained.get('compact_pin_code') or ''}",
        f"STRUNG_COMPILATION|{compilation['strung_together_pin_compilation']}",
    ]
    for sec in compilation["sections"]:
        lines.append(f"{sec['section']}|{sec['compact_pin_code']}")

    pin_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, pin_path


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compile a Facebook profile export into 4 PIN codes + fold amounts per section and master stream."
    )
    parser.add_argument(
        "source",
        type=Path,
        help="Path to the Facebook profile export folder, .zip file, or JSON/HTML file",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("facebook_profile_compilation"),
        help="Output filename prefix (produces <prefix>.pin and <prefix>.pin.json)",
    )
    parser.add_argument(
        "--include-media",
        action="store_true",
        help="Also include binary/media files (photos, videos, audio) as hex streams",
    )
    args = parser.parse_args(argv)

    compilation = compile_facebook_profile(args.source, include_media=args.include_media)
    json_path, pin_path = write_compilation_outputs(compilation, args.output)

    master = compilation["master_profile_pin"]
    chained = compilation["chained_sections_pin"]
    print("=" * 72)
    print("666 CYCLIC FACEBOOK PROFILE PIN COMPILATION (4 PINS + FOLD AMOUNTS)")
    print("=" * 72)
    print(f"Sections Compiled      : {len(compilation['sections'])}")
    print(f"Master Forward PIN     : {master['forward_pin']}")
    print(f"Master Backward PIN    : {master['backward_pin']}")
    print(f"Master Cypher Fwd PIN  : {master['cypher_forward_pin']}")
    print(f"Master Cypher Bwd PIN  : {master['cypher_backward_pin']}")
    print(f"Master Fold Amounts    : cyclic={master['fold_amount']}, cypher={master['cypher_fold_amount']}")
    print(f"Master Compact Line    : {master['compact_pin_code']}")
    print("-" * 72)
    print(f"Chained 4-PIN Line     : {chained.get('compact_pin_code')}")
    print(f"Saved .pin File        : {pin_path.resolve()}")
    print(f"Saved .pin.json File   : {json_path.resolve()}")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
