"""6-Junctions and 6-6 Pattern Change Mapping for Cyclic Compression.

Copyright (c) 2026 Randall Lujan. All rights reserved.
Patent pending for the cyclic compression and rotor-folding system described herein.
"""

from __future__ import annotations

from typing import Dict, List, Tuple, Any, Optional
from cycle_compressor import CYCLIC, collapse

ANCHORS = {3, 6, 9}

# ---------------------------------------------------------------------------
# 1. THE 6-JUNCTION CATALOG
# ---------------------------------------------------------------------------
# Define all tri-sums from CYCLIC = (1, 4, 2, 8, 5, 7) that create 6.

def get_6_junction_catalog() -> Dict[str, Any]:
    """
    Catalog all triplets from the cyclic alphabet that create 6.
    Categorized into:
    - Raw Sum == 6 (Fundamental Junctions: Equal Spread vs Directional Step)
    - Collapsed Sum == 6 (Harmonic / Rotor Junctions: Sums 12, 15, 24)
    """
    raw_6_equal_spread = []
    raw_6_directional = []
    
    collapse_6_equal_spread = []
    collapse_6_directional = []
    
    for a in CYCLIC:
        for b in CYCLIC:
            for c in CYCLIC:
                t = (a, b, c)
                raw_sum = a + b + c
                c_val = collapse(raw_sum)
                is_equal_spread = (a == c)
                
                if raw_sum == 6:
                    if is_equal_spread:
                        raw_6_equal_spread.append(t)
                    else:
                        raw_6_directional.append(t)
                elif c_val == 6:
                    if is_equal_spread:
                        collapse_6_equal_spread.append((t, raw_sum))
                    else:
                        collapse_6_directional.append((t, raw_sum))
                        
    return {
        "raw_6_equal_spread": raw_6_equal_spread,
        "raw_6_directional": raw_6_directional,
        "collapse_6_equal_spread": collapse_6_equal_spread,
        "collapse_6_directional": collapse_6_directional,
    }


# ---------------------------------------------------------------------------
# 2. 6-6 MAP BY PATTERN CHANGES
# ---------------------------------------------------------------------------
class PatternChangeMap6:
    """
    Tracks and classifies 6-digit chunk patterns and transitions (pattern changes).
    Each chunk of 6 is characterized by:
    - Left pair sum (c0 + c1)
    - Center tri-sum (c2 + c3 + c4) or junction anchor
    - Right pair sum (c4 + c5)
    - Total chunk sum and collapse
    - Junction anchor type (whether it forms a 6-junction)
    """

    @staticmethod
    def analyze_chunk6(chunk: Tuple[int, ...]) -> Dict[str, Any]:
        if len(chunk) != 6:
            raise ValueError("Chunk must be exactly 6 digits")
        
        c0, c1, c2, c3, c4, c5 = chunk
        left_pair_sum = c0 + c1
        right_pair_sum = c4 + c5
        
        # Triplets with stride 2:
        t0 = (c0, c1, c2)
        t1 = (c2, c3, c4)
        
        t0_sum = sum(t0)
        t1_sum = sum(t1)
        
        total_sum = sum(chunk)
        total_collapse = collapse(total_sum)
        
        # Check if t0 or t1 is a 6-junction:
        t0_is_6 = (t0_sum == 6 or collapse(t0_sum) == 6)
        t1_is_6 = (t1_sum == 6 or collapse(t1_sum) == 6)
        
        return {
            "chunk": chunk,
            "total_sum": total_sum,
            "total_collapse": total_collapse,
            "left_pair_sum": left_pair_sum,
            "right_pair_sum": right_pair_sum,
            "triplet_0": {"triplet": t0, "sum": t0_sum, "is_6_junction": t0_is_6},
            "triplet_1": {"triplet": t1, "sum": t1_sum, "is_6_junction": t1_is_6},
            "pattern_signature": (left_pair_sum, t0_sum, t1_sum, right_pair_sum),
        }

    @staticmethod
    def map_pattern_changes(chunks: List[Tuple[int, ...]]) -> List[Dict[str, Any]]:
        """Map transition deltas between consecutive 6-chunks."""
        records = []
        for i in range(len(chunks)):
            analysis = PatternChangeMap6.analyze_chunk6(chunks[i])
            if i > 0:
                prev = records[i - 1]
                delta_sum = analysis["total_sum"] - prev["total_sum"]
                delta_collapse = analysis["total_collapse"] - prev["total_collapse"]
                analysis["transition"] = {
                    "delta_sum": delta_sum,
                    "delta_collapse": delta_collapse,
                    "shared_bridge": (prev["chunk"][4], prev["chunk"][5]),
                }
            else:
                analysis["transition"] = None
            records.append(analysis)
        return records


# ---------------------------------------------------------------------------
# 3. 7-DIGIT CONSOLIDATION WITH EQUAL-SPREAD 6-JUNCTION (e.g. 2414187)
# ---------------------------------------------------------------------------
def consolidate_7_digit_string(seq: Tuple[int, ...]) -> Dict[str, Any]:
    """
    Consolidate a 7-digit string using:
    - Total sum value
    - Left addition (x0 + x1)
    - Middle tri-sum (x2, x3, x4)
    - Right addition (x5 + x6)
    - Overlapping tri-sums (T0, T1, T2)
    - Equal spread detection (e.g. x2 == x4)
    """
    if len(seq) != 7:
        raise ValueError("Sequence must be exactly 7 digits")
        
    x0, x1, x2, x3, x4, x5, x6 = seq
    left_add = x0 + x1
    middle_triplet = (x2, x3, x4)
    middle_sum = sum(middle_triplet)
    right_add = x5 + x6
    
    t0 = (x0, x1, x2)
    t1 = (x2, x3, x4)
    t2 = (x4, x5, x6)
    
    total_sum = sum(seq)
    
    is_6_junction = (middle_sum == 6 or collapse(middle_sum) == 6)
    is_equal_spread = (x2 == x4)
    
    return {
        "sequence": seq,
        "total_sum": total_sum,
        "total_collapse": collapse(total_sum),
        "left_addition": left_add,
        "middle_triplet": middle_triplet,
        "middle_sum": middle_sum,
        "right_addition": right_add,
        "right_collapse": collapse(right_add),
        "is_6_junction": is_6_junction,
        "is_equal_spread": is_equal_spread,
        "tri_sums": [sum(t0), sum(t1), sum(t2)],
        "tri_collapses": [collapse(sum(t0)), collapse(sum(t1)), collapse(sum(t2))],
    }


# ---------------------------------------------------------------------------
# 4. FOLDING PATTERN SCRIPT COMPILER & INTERPRETER
# ---------------------------------------------------------------------------
class FoldingScriptEngine:
    """
    Implements Randall's pre-identified folding pattern script architecture:
    - Scans string ahead of time to identify 6-junctions and equal-spread placements
    - Defines the entire sequence by its folding pattern script and transitions
    - Unfolds the sequence deterministically from the seed guided by the pattern blueprint
    """

    @staticmethod
    def compile_script(seq: List[int]) -> Dict[str, Any]:
        """Compile a sequence into its compact folding pattern script."""
        from oscillating_chain import OscillatingChainEngine

        engine = OscillatingChainEngine()
        enc = engine.encode_seed_and_differences(seq)

        junctions = []
        for i in range(len(seq) - 2):
            t = (seq[i], seq[i + 1], seq[i + 2])
            raw_s = sum(t)
            c_s = collapse(raw_s)
            if raw_s == 6:
                junctions.append({
                    "pos": i,
                    "kind": "RAW_6",
                    "triplet": t,
                    "equal_spread": (t[0] == t[2]),
                })
            elif c_s == 6:
                junctions.append({
                    "pos": i,
                    "kind": "COLLAPSE_6",
                    "triplet": t,
                    "equal_spread": (t[0] == t[2]),
                })

        chunks = [tuple(seq[i : i + 6]) for i in range(0, len(seq) - 5, 4)]
        chunk_map = PatternChangeMap6.map_pattern_changes(chunks) if chunks else []

        return {
            "seed": enc["seed"],
            "length": len(seq),
            "differences": enc["differences"],
            "pre_mapped_junctions": junctions,
            "chunk_transitions": [
                {
                    "idx": i,
                    "sig": item["pattern_signature"],
                    "has_6_junction": item["triplet_0"]["is_6_junction"]
                    or item["triplet_1"]["is_6_junction"],
                }
                for i, item in enumerate(chunk_map)
            ],
        }

    @staticmethod
    def execute_script(script: Dict[str, Any]) -> List[int]:
        """Execute the folding script to deterministically unfold the entire sequence."""
        from oscillating_chain import OscillatingChainEngine

        engine = OscillatingChainEngine()
        rebuilt = engine.unfold_seed(script["seed"], script["differences"])

        for j in script["pre_mapped_junctions"]:
            pos = j["pos"]
            actual_t = tuple(rebuilt[pos : pos + 3])
            if actual_t != j["triplet"]:
                raise ValueError(f"Pattern script mismatch at junction position {pos}")

        return rebuilt

