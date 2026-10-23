# Dual-Track Cyclic Compressor — Build Specification

**Author:** Randall Lujan  
**Date:** 2026-10-03 (Updated 2026-10-23)  
**Status:** Proof of Concept (verified 35-letter round trip + 12-block Pin-Only Lossless Reconstruction)

## Core Mechanism

### 1. Cyclic Base
- Constant: `142857` (never changes).
- 6 cyclic numbers: 1, 4, 2, 8, 5, 7.
- Signpost marker: `9` (Technical `1` in multiplication: $x \times 9$ retains trace; Functional `0` in digital root / mod 9: $9 \bmod 9 = 0$).
- Residue erasure: Single integers `3` and `6` AND repeating numbers multiply by `9` (e.g., `3` $\to$ `27`, `6` $\to$ `54`, `55555` $\to$ `4545454545`), while non-repeating single data digits in `{1, 2, 4, 5, 7, 8}` remain untouched single digits.

### 2. Symbol Library (Track 1)
- 90 symbols (full keyboard, ordered by keystrokes).
- 15 cyphers, 6 symbols per cypher (90/6=15).
- Each symbol maps to one cypher.
- Library is universal and fixed.

### 3. Pattern Library (Track 2)
- 6^6 = 46,656 patterns (6-length sequences over 6 cyphers).
- Each pattern has a unique Pattern ID (PID).
- 6→1: Six cyphers become one PID.
- Library is universal and fixed.

### 4. Dual Tracks (Parallel)
- Track 1: Symbols → 15 cyphers (symbol encoding).
- Track 2: Cyphers → PIDs via 6→1 (pattern consolidation).
- Tracks run symbol-for-symbol parallel, synchronized by position.
- Neither outruns the other.

### 5. Recursive Pyramid & 12-Block Pin-Only Collapse
- 12-Block Processing (`12 = 4 x 3`, optimal for threesome tri-sum):
  - Input block (e.g., `3655555`) expands only single `3`, `6`, and `repeats` via $\times 9$ $\to$ `27544545454545` (14 digits)
  - Consolidates via second-variable chunk marker $\to$ `5445455` (7 digits)
  - Collapses to uniform 6-digit apex `452152` and final forward pin `298-1` / backward pin `882-7`
  - Reconstructs losslessly from pin `P` + fixed logic `L` using `11-mirror` unfolding and `9` signpost descriptors.

### 6. Sums and Verification
- 6 sums: one per cyclic number (1,4,2,8,5,7), ordered.
- Sums recorded per cypher per placement.
- "Sums on right": Stored after PIDs for verification.
- Checkpoint: Verifies no double-count ("not accrued twice").
- Correction: If sums off track, emit `(multiplier, cypher, slot, sum)`.

### 7. Binary Pass 2 (Optimization)
- 2-cypher system (not 6).
- Tracks multiplier order (multiplier values vs cyclic numbers order).
- Change marking: `-` for 1→2, `+` for 2→1.
- Optimization: Only mark one direction; absence + state implies the other.
- "When it's not 1 it's the other."

### 8. Variable = Cypher × Cyclic
- For disambiguation: variable = cypher_number × cyclic_number.
- Cypher first, then cyclic "constitutes the change."
- Used in multiplier rule (only on changes).

### 9. Delta on Changes
- "You only need the multiplier rule on changes."
- When cypher changes, write multiplied variable.
- Otherwise, "back to singular representation until change."
- Decoder tracks state.

---

## Implementation Mode 1: Traffic Data (Streaming)

**Use case:** Real-time network traffic, low latency.

**Rules:**
1. Send variables immediate (don't wait for batch).
2. Each immediate variable = `(cypher, accumulative_PID)` pair.
3. PID is accumulative (also the sequence order).
4. Receiver unfolds 1→6 in real time, places immediately.
5. "Placing patterns as real time unfolding."
6. Latency: 6 symbols (one chunk), not large buffer.
7. Binary change marks for efficiency (only mark 1→2).
8. Format includes "prefolded allocation" (compressed) alongside real-time unfolded.

**Packet:** `(cypher, PID)` — PID does double duty (consolidation + ordering).

**Ordering:** "Which 3s after which 7s" — compare PIDs (lineal).

---

## Implementation Mode 2: Storage Data (Long-term)

**Use case:** Archival, optimize for size not speed.

**Rules:**
1. Store PIDs / Pins only (omit cypher order; reconstruct via fixed logic & library).
2. Pin-Only 12-Block rebuild via `Decode(P, L)`:
   - Unfold pin (`298-1` or `882-7`) via `11-mirror` expansion to uniform apex (`452152`)
   - Expand `9` signpost descriptors (`3-pattern`, `6-pattern`, `repeat-pattern`) to recover original 12-block (`3655555`).

---

## Implementation Mode 3: Download Data (Batch)

**Use case:** File downloads, batched transfers.

**Rules:**
1. Accumulate data (not real-time).
2. Determine flush point "by the consolidated data" (adaptive, not fixed).
3. Target: 60% max sent size (40%+ reduction), up to ~90% on 12-block files with overlap removal.

---

## Universal Rules (All Modes)

1. **Order preserved:** "They came in as they go out, they have to STAY IN PLACE." No reordering.
2. **Every pattern has a number:** All patterns in library have IDs.
3. **6→1 / 12-Block Pin-Only:** Six numbers become one PID; 12-number blocks collapse to a single pin (`298-1` / `882-7`).
4. **Chunk for chunk:** Chunk size follows the first; assume no change unless signaled.
5. **Checkpoint:** Verify at boundaries; "call back the checkpoint to the misalignment."
6. **No duplicates:** "Those particular lineals can not be accrued twice."
7. **142857 constant:** Never changes, shared basis.
8. **No external compressors (no zlib):** Consolidation is 100% native cyclic / tri-sum / 9-signpost arithmetic.

---
*Do not distribute. Randall Lujan's mechanism.*
