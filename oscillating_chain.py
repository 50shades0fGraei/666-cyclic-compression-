"""Oscillating Dual-Stream Cyclic Engine with Stream Switchout and Seed Unfolding.

Copyright (c) 2026 Randall Lujan. All rights reserved.
Patent pending for the cyclic compression and rotor-folding system described herein.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Sequence
from cycle_compressor import CYCLIC, collapse, CHARACTER_MAP

ANCHORS = {3, 6, 9}
FAM_A = {1, 4, 7}
FAM_B = {2, 5, 8}


class OscillatingChainEngine:
    """
    Implements Randall's parallel oscillating stream architecture:
    - Primary line: unshifted tri-sums, e.g. (2 4 (5) 8 6) 7 2 8 4 centered on junction (5)
    - Secondary line (echo): phase-shifted by 1, e.g. 2 (4 5 (8) 6 7) 2 8 4 centered on junction (8)
    - Difference recurrence: T[k+1] - T[k] = x[k+3] - x[k]
    - Stream switchout: when an anchor (3, 6, 9) or '0' is encountered, switch fold streams
    - Seed unfolding: reconstructs the entire sequence from a 3-to-7 digit seed using oscillating differences
    """

    def __init__(self, cyclic_set: Sequence[int] = (1, 4, 2, 8, 5, 7)) -> None:
        self.cyclic_set = tuple(cyclic_set)

    def compute_parallel_streams(self, seq: Sequence[int]) -> Dict[str, Any]:
        """Generate the primary stream and the parallel secondary echo stream."""
        primary_triplets = []
        for i in range(0, len(seq) - 2, 2):
            t = (seq[i], seq[i + 1], seq[i + 2])
            raw_sum = sum(t)
            c = collapse(raw_sum)
            primary_triplets.append({
                "index": i,
                "triplet": t,
                "raw_sum": raw_sum,
                "collapse": c,
                "is_anchor": c in ANCHORS,
            })

        secondary_triplets = []
        for i in range(1, len(seq) - 2, 2):
            t = (seq[i], seq[i + 1], seq[i + 2])
            raw_sum = sum(t)
            c = collapse(raw_sum)
            secondary_triplets.append({
                "index": i,
                "triplet": t,
                "raw_sum": raw_sum,
                "collapse": c,
                "is_anchor": c in ANCHORS,
            })

        continuous_tri_sums = [
            sum(seq[i : i + 3]) for i in range(len(seq) - 2)
        ]

        return {
            "primary": primary_triplets,
            "secondary": secondary_triplets,
            "continuous_sums": continuous_tri_sums,
        }

    def encode_seed_and_differences(self, seq: Sequence[int]) -> Dict[str, Any]:
        """
        Encode sequence into:
        - Seed: first 3 integers (or 6-7 digit boundary block)
        - Oscillating difference echo: Delta[k] = T[k+1] - T[k] = x[k+3] - x[k]
        - Parallel stream collapse values (with 369 anchors 0-ed out)
        """
        if len(seq) < 3:
            return {"seed": list(seq), "differences": [], "length": len(seq)}

        seed = list(seq[:3])
        differences = [seq[i + 3] - seq[i] for i in range(len(seq) - 3)]
        
        p_stream, s_stream = [], []
        for i in range(0, len(seq) - 2, 2):
            c = collapse(seq[i] + seq[i+1] + seq[i+2])
            p_stream.append(0 if c in ANCHORS else c)
        for i in range(1, len(seq) - 2, 2):
            c = collapse(seq[i] + seq[i+1] + seq[i+2])
            s_stream.append(0 if c in ANCHORS else c)

        return {
            "seed": seed,
            "differences": differences,
            "length": len(seq),
            "primary_stream": p_stream,
            "secondary_stream": s_stream,
        }

    def unfold_seed(
        self,
        seed: Sequence[int],
        differences: Sequence[int],
    ) -> List[int]:
        """
        Reconstruct the full sequence from the seed and the oscillating differences.
        Direct mathematical recurrence: x[k+3] = x[k] + Delta[k].
        """
        rebuilt = list(seed)
        for k, diff in enumerate(differences):
            next_val = rebuilt[k] + diff
            rebuilt.append(next_val)
        return rebuilt

    def unfold_with_dual_streams(
        self,
        seed: Sequence[int],
        primary_stream: Sequence[int],
        secondary_stream: Sequence[int],
        target_length: int,
    ) -> List[int]:
        """
        Reconstruct sequence by solving joint constraints across both oscillating streams.
        When a stream hits 0 (an anchor 3, 6, 9), the other stream cross-validates the transition.
        """
        p_map = {i * 2: val for i, val in enumerate(primary_stream)}
        s_map = {1 + i * 2: val for i, val in enumerate(secondary_stream)}

        solutions: List[List[int]] = []

        def solve_step(current: List[int]) -> None:
            if len(current) == target_length:
                solutions.append(list(current))
                return

            idx = len(current)  # index we are trying to determine
            # Check constraints on current + [cand]
            for cand in self.cyclic_set:
                candidate_seq = current + [cand]
                valid = True

                # Check any fully formed triplets:
                # 1. Even triplet ending at idx: indices (idx-2, idx-1, idx)
                if (idx - 2) in p_map:
                    t_sum = candidate_seq[idx - 2] + candidate_seq[idx - 1] + cand
                    c = collapse(t_sum)
                    expected = p_map[idx - 2]
                    if expected == 0:
                        if c not in ANCHORS:
                            valid = False
                    else:
                        if c != expected:
                            valid = False

                # 2. Odd triplet ending at idx: indices (idx-2, idx-1, idx)
                if valid and (idx - 2) in s_map:
                    t_sum = candidate_seq[idx - 2] + candidate_seq[idx - 1] + cand
                    c = collapse(t_sum)
                    expected = s_map[idx - 2]
                    if expected == 0:
                        if c not in ANCHORS:
                            valid = False
                    else:
                        if c != expected:
                            valid = False

                if valid:
                    solve_step(candidate_seq)
                    if solutions:
                        return

        solve_step(list(seed))
        return solutions[0] if solutions else list(seed)
