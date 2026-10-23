"""6-Checkpoint Code and Maximum Fold Depth Calculator.

Copyright (c) 2026 Randall Lujan. All rights reserved.
Patent pending for the cyclic compression and rotor-folding system described herein.
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple, Any
from cycle_compressor import CYCLIC, collapse, fold_triplets

class Checkpoint6CodeEngine:
    """
    Implements Randall's 6-Spine Code Architecture:
    - Identifies all checkpoint 6s (raw and collapse-6) across the stream
    - Determines the maximum fold depth (F_max) from the 6-intervals
    - Encodes the sequence as a compact 6-spine code
    """

    @staticmethod
    def extract_6_checkpoints(seq: List[int]) -> List[Dict[str, Any]]:
        """Find all 6-checkpoints in the sequence."""
        checkpoints = []
        for i in range(len(seq) - 2):
            t = (seq[i], seq[i + 1], seq[i + 2])
            raw_s = sum(t)
            c_s = collapse(raw_s)
            if raw_s == 6:
                checkpoints.append({
                    "pos": i,
                    "type": "RAW_6",
                    "triplet": t,
                    "equal_spread": (t[0] == t[2]),
                })
            elif c_s == 6:
                checkpoints.append({
                    "pos": i,
                    "type": "COLLAPSE_6",
                    "triplet": t,
                    "equal_spread": (t[0] == t[2]),
                })
        return checkpoints

    @staticmethod
    def calculate_max_folds(seq_length: int, checkpoints: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Determine maximum folds (F_max) based on sequence length and checkpoint intervals.
        Each fold roughly halves the span. Folding terminates when the span reaches terminal size (<= 6-7).
        """
        if seq_length <= 6:
            return {"max_folds": 0, "reason": "Already at or below terminal chunk size (6)"}

        # Theoretical geometric fold count to reach 6:
        # N * (0.5)^F <= 6 => F = ceil(log2(N / 6))
        theoretical_folds = math.ceil(math.log2(seq_length / 6.0))

        # Checkpoint-bounded intervals:
        positions = [cp["pos"] for cp in checkpoints]
        intervals = [positions[i + 1] - positions[i] for i in range(len(positions) - 1)] if len(positions) > 1 else [seq_length]
        max_interval = max(intervals) if intervals else seq_length
        interval_folds = math.ceil(math.log2(max_interval / 2.0)) if max_interval > 2 else 1

        # Real fold progression:
        actual_folds = 0
        current_len = seq_length
        while current_len > 7:
            current_len = (current_len - 3) // 2 + 1
            actual_folds += 1

        return {
            "max_folds": actual_folds,
            "theoretical_folds": theoretical_folds,
            "interval_folds": interval_folds,
            "checkpoint_count": len(checkpoints),
            "max_interval_between_6s": max_interval,
            "terminal_length": current_len,
        }

    @staticmethod
    def encode_as_6_code(seq: List[int]) -> Dict[str, Any]:
        """
        Define the 6s as the code:
        Returns the terminal PIN, maximum fold count, and the 6-checkpoint spine.
        """
        checkpoints = Checkpoint6CodeEngine.extract_6_checkpoints(seq)
        fold_analysis = Checkpoint6CodeEngine.calculate_max_folds(len(seq), checkpoints)

        # Run folds to terminal code:
        current = list(seq)
        for _ in range(fold_analysis["max_folds"]):
            current = fold_triplets(current)

        return {
            "terminal_code": current,
            "max_folds": fold_analysis["max_folds"],
            "original_length": len(seq),
            "checkpoints_6": [
                (cp["pos"], cp["type"], cp["triplet"][0], cp["triplet"][1], cp["triplet"][2])
                for cp in checkpoints
            ],
            "checkpoint_count": len(checkpoints),
        }
