# Randall's Cyclic Compression

Copyright (c) 2026 Randall Lujan. All rights reserved.
Patent pending for the cyclic compression and rotor-folding system described herein.

Randall's Cyclic Compression is a deterministic rotor-based folding and 12-block pin-only reconstruction system built around the repeating `142857` cycle, residue erasure of `3`, `6`, and repeats via `9`-multiplication, and deterministic tri-sum unfolding (with **zero external compression libraries—no zlib**).

## Architecture Overview

### 1. Rotor Layer
The project uses the canonical 6-slot cycle:

`[1, 4, 2, 8, 5, 7]`

This is the design anchor for the full system and is exposed through the public rotor metadata in the compressor output.

### 2. 12-Block Pin-Only Lossless Reconstruction (`pin_only_12block.py`)
Implements the October 2026 paper, *"Pin-Only Lossless Reconstruction via Deterministic Tri-Sum: A 12-Block Compression Method Using Residue Erasure and 9 as Functional Zero"*:

- **Selective $\times 9$ Multiplication (`3`, `6`, and Repeats Only)**:
  - Non-repeating data digits in `{1, 2, 4, 5, 7, 8}` remain untouched single integers.
  - Only single integers `3` and `6` **and** repeating runs multiply by `9`:
    - `3` $\to 3 \times 9 = 27$
    - `6` $\to 6 \times 9 = 54$
    - Repeating runs (e.g., `55555`) $\to 5 \times 9 = 45$ repeated (`4545454545`)
  - Test vector: `3655555` $\to$ `27544545454545` (14 digits) $\to$ second-variable consolidated `5445455` (7 digits).
- **Dual Role of `9` (Technical `1` / Functional `0`)**:
  - Technical `1`: preserves the variable in multiplication ($x \times 9$ retains trace: pair digit-sum is `9`, and $\text{pair} \div 9 = x$).
  - Functional `0`: vanishes under digital root and division by 9 ($9 \bmod 9 = 0$).
  - In the compressed stream, `9` is never data; it serves as a self-describing signpost.
- **Tri-Sum Uniqueness & Uniform Apex**:
  - With repeats and residues $3, 6 \pmod 9$ erased, overlapping tri-sums collapse `5445455` to uniform apex `452152` and final forward pin `298-1` / backward pin `882-7`.
- **Pin-Only Decoding `Decode(P, L)`**:
  - `decode_pin("298-1")` or `decode_pin("882-7")` unfolds via `11-mirror` expansion and `9` signpost descriptors (`3-pattern`, `6-pattern`, `repeat-pattern`) to deterministically reconstruct `3655555`.

### 3. Bidirectional Tri-Sum Fold Engine (`cycle_compressor.py`)
The compressor collapses overlapping triplets at stride 2 in both left-to-right (`fold_trisums_lr`) and right-to-left (`fold_trisums_rl`) directions, verifying bidirectional consistency (`bidir_verified`) and 369 multiplication dualities ($3\times 1=3$, $3\times 2=6$, $3+6=9$).

## Public Entry Points

- `pin_only_12block.py` contains `encode_12block`, `decode_pin`, `compress_12block_stream`, and `decompress_12block_stream`.
- `cycle_compressor.py` contains the core engine, bidirectional tri-sum verification, and rotor metadata.
- `pattern_library.py` contains the fixed 46,656-entry pattern mapping and `6 -> 1` PID fold/unfold layer.
- `randall_cyclic_compressor.py` is the public branded entry point for the system.
- `app_server.py` and `mvp-trifold-app-2026-10-06.html` provide a local browser workbench backed by the Python compressor.

## Usage

```bash
python randall_cyclic_compressor.py
python pin_only_12block.py
```

### Local Workbench

```bash
python app_server.py
```

Then open <http://127.0.0.1:8765>.

## License

- Open-source use: [LICENSE](LICENSE) (MIT)
- Commercial use: [COMMERCIAL-LICENSE.md](COMMERCIAL-LICENSE.md)
