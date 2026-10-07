import json
import unittest

from cycle_compressor import (
    CHARACTER_MAP,
    CYCLIC,
    PROJECT_NAME,
    compress_text,
    rebuild_sequence,
    unfold_numeric,
    unfold_sequence,
    verify_369_duality,
)


class CycleCompressorTests(unittest.TestCase):
    def test_compress_text_returns_expected_structure(self):
        result = compress_text("hello world")
        self.assertEqual(result["input_length"], len("hello world"))
        self.assertTrue(result["cipher_order"])
        self.assertTrue(result["pin"])
        self.assertIn("fold_log", result)
        self.assertEqual(result["cyclic"], CYCLIC)
        self.assertEqual(result["project"], PROJECT_NAME)

    def test_rebuild_sequence_round_trip(self):
        original = [1, 4, 2, 8, 5, 7, 1, 4, 2]
        rebuilt = rebuild_sequence(original)
        self.assertEqual(rebuilt, original)

    def test_rotor_is_canonical_cycle(self):
        result = compress_text("qwerty")
        self.assertEqual(result["cyclic"], [1, 4, 2, 8, 5, 7])
        self.assertTrue(result["rotor"])
        self.assertEqual(result["ordered_cypher_values"], [1, 4, 2, 8, 5, 7])

    def test_stops_at_fold_level_closest_to_six_values(self):
        result = compress_text("hello world")
        self.assertEqual(len(result["pin"]), 5)

    def test_empty_input_does_not_add_synthetic_pin_values(self):
        result = compress_text("!@#$")
        self.assertEqual(result["pin"], [])

    def test_pin_can_unfold_back_to_sequence(self):
        original_text = "hello world"
        result = compress_text(original_text)
        reconstructed = unfold_sequence(result["pin"], result["cipher_order"], result["counts"])
        self.assertIn("h", reconstructed)
        self.assertIn("o", reconstructed)
        self.assertIn(" ", reconstructed)

    def test_369_dualities_are_verified_by_multiplication(self):
        self.assertEqual(verify_369_duality(3), {
            "value": 3,
            "products": [3],
            "verified": True,
        })
        self.assertEqual(verify_369_duality(6), {
            "value": 6,
            "products": [6],
            "verified": True,
        })
        self.assertEqual(verify_369_duality(9), {
            "value": 9,
            "products": [3, 6],
            "verified": True,
        })

    def test_compression_records_duality_checks_for_369_anchors(self):
        result = compress_text("qwertyuiopasdfghjklzxcvbnm")
        self.assertEqual(sum(result["anchor_counts"].values()), result["duality_checks"])
        self.assertEqual(
            sum(fold["duality_checks"] for fold in result["fold_log"]),
            result["duality_checks"],
        )
        self.assertTrue(all("input_values" not in fold for fold in result["fold_log"]))
        self.assertTrue(all("output_values" not in fold for fold in result["fold_log"]))

    def test_numeric_unfold_restores_original_sequence_and_verifies_anchors(self):
        result = compress_text("qwertyuiopasdfghjklzxcvbnm")
        restored = unfold_numeric(
            result["ordered_cypher_values"],
            result["fold_log"],
            result["folded_values"],
        )
        self.assertEqual(
            restored,
            [CHARACTER_MAP[ch] for ch in result["sequence"]],
        )

    def test_numeric_unfold_rejects_mismatched_fold_state(self):
        result = compress_text("qwertyuiopasdfghjklzxcvbnm")
        folded_values = result["folded_values"][:]
        folded_values[0] += 1
        with self.assertRaises(ValueError):
            unfold_numeric(result["ordered_cypher_values"], result["fold_log"], folded_values)

    def test_numeric_unfold_rejects_tampered_anchor_context(self):
        result = compress_text("qwertyuiopasdfghjklzxcvbnm")
        fold_log = [dict(fold) for fold in result["fold_log"]]
        fold_with_anchor = next(fold for fold in fold_log if fold["duality_checks"])
        fold_with_anchor["anchor_counts"] = dict(fold_with_anchor["anchor_counts"])
        fold_with_anchor["anchor_counts"]["3"] = fold_with_anchor["anchor_counts"].get("3", 0) + 1
        with self.assertRaises(ValueError):
            unfold_numeric(result["ordered_cypher_values"], fold_log, result["folded_values"])

    def test_numeric_unfold_works_after_json_persistence(self):
        result = compress_text("qwertyuiopasdfghjklzxcvbnm")
        persisted = json.loads(json.dumps(result))
        restored = unfold_numeric(
            persisted["ordered_cypher_values"],
            persisted["fold_log"],
            persisted["folded_values"],
        )
        self.assertEqual(restored, result["ordered_cypher_values"])


if __name__ == "__main__":
    unittest.main()
