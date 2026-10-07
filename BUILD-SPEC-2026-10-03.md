# Dual-Track Cyclic Compressor — Build Specification

**Author:** Randall Lujan  
**Date:** 2026-10-03  
**Status:** Proof of Concept (verified 35-letter round trip)

## Core Mechanism

### 1. Cyclic Base
- Constant: `142857` (never changes).
- 6 cyclic numbers: 1, 4, 2, 8, 5, 7.

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

### 5. Recursive Pyramid
- Round 1: N cyphers → M PIDs (6→1, chunk by 6).
- Round 2: M PIDs → K PIDs (6→1 again, pattern-to-pattern).
- Continue until top.
- Top contains: final PIDs + 6 sums + fold count.
- "Ordered 6-1, 6-1": Rounds apply in order.

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
1. Store PIDs only (omit cypher order; reconstruct via library).
2. Two-run rebuild:
   - Run 1: PIDs → cyphers (via 6^6 library).
   - Run 2: Cyphers → symbols (via 90-symbol library + parallel position).
3. "Rebuild the rebuild by only 2 cyphers" (binary Pass 2).
4. Double-crunch: Compress PIDs further (delta, RLE on PIDs).
5. Pyramid allows selective decode: "only need certain variables at certain breakdowns."
6. Optimize the order for storage (not for quick access).

**Stored:** Top PIDs + 6 sums + fold count + unfold metadata (chunk_size, num_chunks, last_len).

**Trade-off:** Smaller size, slower rebuild (two runs).

---

## Implementation Mode 3: Download Data (Batch)

**Use case:** File downloads, batched transfers.

**Rules:**
1. Accumulate data (not real-time).
2. Determine flush point "by the consolidated data" (adaptive, not fixed).
3. Target: 60% max sent size (40%+ reduction), better for longer files.
4. "Network data just has to be accumulated at a minimum for optimization."
5. Report format (ordered by processing needs):
   - [1] Header: chunk_size, cypher set, library version.
   - [2] Cypher order (for cross-reference).
   - [3] Pattern IDs (accumulative, in order).
   - [4] Sums on right.
   - [5] Checkpoints/corrections (if needed).
6. "Consolidate strings of patterns by 6 paired to cypher numbers for immediate allocations."
7. For pre-formatted data: optimize "at its point of degradation in size to unfolding ratio."

**Flush:** When consolidated data indicates optimal (not fixed size).

---

## Universal Rules (All Modes)

1. **Order preserved:** "They came in as they go out, they have to STAY IN PLACE." No reordering.
2. **Every pattern has a number:** All patterns in library have IDs.
3. **6→1:** Six numbers become one PID (via library).
4. **Chunk for chunk:** Chunk size follows the first; assume no change unless signaled.
5. **Checkpoint:** Verify at boundaries; "call back the checkpoint to the misalignment."
6. **No duplicates:** "Those particular lineals can not be accrued twice."
7. **142857 constant:** Never changes, shared basis.
8. **zlib:** Consolidate multiplier stream for transmission (peace offering to incumbent).

---

## Verified (2026-10-03)

- 44-byte text → 35 cyphers → 6 PIDs (Round 1) → 1 PID (Round 2).
- 6 sums: [5,7,8,4,6,5] (ordered 1,4,2,8,5,7).
- Folds: 2.
- Top: 8 numbers (1 PID + 6 sums + 1 fold).
- Decode: PIDs→cyphers **True**. Cyphers→symbols **True** (35 letters).
- Mechanism: Parallel (PID, position, cypher)→symbol via library.

## Open

- Universal 90-symbol / 15-cypher library (demo used 26-letter subset).
- Universal 6^6 pattern library (demo built per-message).
- Which 5 vs 6 vs 15 cyphers for which layer (Randall to confirm).
- "Last 2" unfold metadata (hypothesis: num_chunks + last_len).
- 60% target measured on full symbols (not just structure).

---
*Do not distribute. Randall Lujan's mechanism.*
