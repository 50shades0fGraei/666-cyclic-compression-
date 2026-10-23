"""Unit tests for Oscillating Chain Engine and 6-Junction Mapping."""

import unittest
from cycle_compressor import CYCLIC
from oscillating_chain import OscillatingChainEngine
from junction_6_map import (
    get_6_junction_catalog,
    consolidate_7_digit_string,
    PatternChangeMap6,
)


class OscillatingJunctionChainTests(unittest.TestCase):
    def setUp(self):
        self.engine = OscillatingChainEngine()

    def test_6_junction_catalog_definitions(self):
        catalog = get_6_junction_catalog()
        # Equal spread raw 6: (1, 4, 1) and (2, 2, 2)
        self.assertEqual(catalog["raw_6_equal_spread"], [(1, 4, 1), (2, 2, 2)])
        # Directional steps: (1, 1, 4) and (4, 1, 1)
        self.assertEqual(catalog["raw_6_directional"], [(1, 1, 4), (4, 1, 1)])
        # Collapse == 6 counts
        self.assertEqual(len(catalog["collapse_6_equal_spread"]), 7)
        self.assertEqual(len(catalog["collapse_6_directional"]), 20)

    def test_consolidate_7_digit_string_user_example(self):
        # User example: 2414187
        res = consolidate_7_digit_string((2, 4, 1, 4, 1, 8, 7))
        self.assertEqual(res["total_sum"], 27)
        self.assertEqual(res["total_collapse"], 9)
        self.assertEqual(res["left_addition"], 6)
        self.assertEqual(res["middle_triplet"], (1, 4, 1))
        self.assertEqual(res["middle_sum"], 6)
        self.assertEqual(res["right_addition"], 15)
        self.assertEqual(res["right_collapse"], 6)
        self.assertTrue(res["is_6_junction"])
        self.assertTrue(res["is_equal_spread"])
        self.assertEqual(res["tri_sums"], [7, 6, 16])
        self.assertEqual(res["tri_collapses"], [7, 6, 8])

    def test_oscillating_difference_round_trip(self):
        # User example: 2 4 5 8 6 7 2 8 4
        seq = [2, 4, 5, 8, 6, 7, 2, 8, 4]
        enc = self.engine.encode_seed_and_differences(seq)
        rebuilt = self.engine.unfold_seed(enc["seed"], enc["differences"])
        self.assertEqual(rebuilt, seq)

    def test_pattern_change_map_6(self):
        seq_10 = (2, 4, 1, 4, 1, 8, 7, 2, 8, 4)
        chunks = [seq_10[:6], seq_10[4:]]
        transitions = PatternChangeMap6.map_pattern_changes(chunks)
        self.assertEqual(len(transitions), 2)
        self.assertIsNone(transitions[0]["transition"])
        self.assertEqual(transitions[0]["triplet_1"]["triplet"], (1, 4, 1))
        self.assertTrue(transitions[0]["triplet_1"]["is_6_junction"])
        self.assertEqual(transitions[1]["transition"]["shared_bridge"], (1, 8))

    def test_folding_script_engine_100_digits(self):
        import random
        from junction_6_map import FoldingScriptEngine
        random.seed(42)
        chain_100 = [random.choice(CYCLIC) for _ in range(100)]
        script = FoldingScriptEngine.compile_script(chain_100)
        self.assertEqual(len(script["seed"]), 3)
        self.assertEqual(script["length"], 100)
        self.assertGreater(len(script["pre_mapped_junctions"]), 0)
    def test_checkpoint_6_code_engine(self):
        from checkpoint_6_code import Checkpoint6CodeEngine
        import random
        random.seed(42)
        chain_100 = [random.choice(CYCLIC) for _ in range(100)]
        code = Checkpoint6CodeEngine.encode_as_6_code(chain_100)
        self.assertEqual(code["max_folds"], 4)
        self.assertEqual(len(code["terminal_code"]), 5)
        self.assertEqual(code["original_length"], 100)
        self.assertEqual(code["checkpoint_count"], 15)


if __name__ == "__main__":
    unittest.main()

