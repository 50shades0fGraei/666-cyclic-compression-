import unittest

from pattern_library import (
    BASE_NUMBER,
    CYCLIC,
    MULTIPLIER_ROWS,
    PATTERN_COUNT,
    count_alignments,
    count_cyclic_stream_alignments,
    decode_pattern,
    encode_pattern,
    evaluate_rotor_rows,
    fold_pair_stream,
    fold_cypher_stream,
    place_cypher_order,
    unfold_pattern_ids,
    unfold_pair_stream,
)


class PatternLibraryTests(unittest.TestCase):
    def test_library_is_a_bijection_over_all_patterns(self):
        self.assertEqual(PATTERN_COUNT, 46_656)
        self.assertEqual(
            [encode_pattern(decode_pattern(pid)) for pid in range(PATTERN_COUNT)],
            list(range(PATTERN_COUNT)),
        )

    def test_pid_order_is_stable_and_uses_cyclic_order(self):
        self.assertEqual(decode_pattern(0), (1, 1, 1, 1, 1, 1))
        self.assertEqual(encode_pattern(CYCLIC), 1_865)
        self.assertEqual(decode_pattern(1_865), CYCLIC)

    def test_fold_and_unfold_preserve_stream_order(self):
        source = [1, 4, 2, 8, 5, 7, 7, 5, 8, 2, 4, 1]
        self.assertEqual(unfold_pattern_ids(fold_cypher_stream(source)), source)

    def test_empty_stream_round_trips(self):
        self.assertEqual(fold_cypher_stream([]), [])
        self.assertEqual(unfold_pattern_ids([]), [])

    def test_partial_pattern_is_rejected_instead_of_padded(self):
        with self.assertRaisesRegex(ValueError, "multiple of six"):
            fold_cypher_stream([1, 4, 2, 8, 5])

    def test_invalid_pattern_values_and_pids_are_rejected(self):
        with self.assertRaises(ValueError):
            encode_pattern([1, 4, 2, 8, 5, 6])
        with self.assertRaises(ValueError):
            encode_pattern([1, 4, 2, 8, 5])
        for pid in (-1, PATTERN_COUNT, True, "1"):
            with self.subTest(pid=pid), self.assertRaises(ValueError):
                decode_pattern(pid)

    def test_rotor_row_evaluation_records_collapsed_anchor_hits(self):
        rows = evaluate_rotor_rows()
        self.assertEqual(
            [
                [(hit["steps"], hit["sum"], hit["anchor"]) for hit in row["anchor_hits"]]
                for row in rows
            ],
            [
                [(4, 15, 6), (6, 27, 9)],
                [(2, 6, 6), (6, 27, 9)],
                [(3, 15, 6), (6, 27, 9)],
                [(4, 21, 3), (6, 27, 9)],
                [(2, 12, 6), (6, 27, 9)],
                [(3, 12, 6), (6, 27, 9)],
            ],
        )

    def test_alignment_counts_use_fixed_base_and_left_to_right_slots(self):
        result = count_alignments([(1, 3), (4, 3), (1, 3), (7, 1)])
        self.assertEqual(BASE_NUMBER, 142_857)
        self.assertEqual(
            MULTIPLIER_ROWS,
            {
                1: (1, 4, 2, 8, 5, 7),
                2: (2, 8, 5, 7, 1, 4),
                3: (4, 2, 8, 5, 7, 1),
                4: (5, 7, 1, 4, 2, 8),
                5: (7, 1, 4, 2, 8, 5),
                6: (8, 5, 7, 1, 4, 2),
            },
        )
        self.assertEqual(result["alignment_count"], 4)
        rows = result["rows"]
        row_three = rows[2]
        self.assertEqual(row_three["cyclic_row"], [4, 2, 8, 5, 7, 1])
        self.assertEqual(row_three["slot_counts"], [1, 0, 0, 0, 0, 2])
        self.assertEqual(rows[0]["slot_counts"], [0, 0, 0, 0, 0, 1])
        self.assertEqual(sum(sum(row["slot_counts"]) for row in rows), 4)

    def test_alignment_counter_rejects_invalid_pairs(self):
        for pairs in (
            [(3, 3)],
            [(1, 0)],
            [(1, True)],
            [(1,)],
        ):
            with self.subTest(pairs=pairs), self.assertRaises(ValueError):
                count_alignments(pairs)

    def test_stream_alignment_advances_multiplier_once_per_occurrence(self):
        result = count_cyclic_stream_alignments(CYCLIC)
        self.assertEqual(result["alignment_count"], 6)
        self.assertEqual(result["multiplier_rule"], "1..6 repeated in occurrence order")
        self.assertEqual(
            [row["multiplier"] for row in result["rows"]],
            [1, 2, 3, 4, 5, 6],
        )
        self.assertEqual(
            [row["slot_counts"] for row in result["rows"]],
            [
                [1, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 1],
                [0, 1, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 1],
                [0, 0, 0, 0, 0, 1],
                [0, 0, 1, 0, 0, 0],
            ],
        )

    def test_cypher_order_is_placed_by_cyclic_slot(self):
        result = place_cypher_order(
            [
                (1, 7),
                (4, 2),
                (7, 15),
                (1, 3),
                (2, 4),
                (8, 9),
                (1, 12),
            ]
        )
        self.assertEqual(result["occurrence_count"], 7)
        rows = result["rows"]
        self.assertEqual(
            rows[1]["slots"][5]["cypher_order"],
            [2],
        )
        self.assertEqual(
            rows[2]["slots"][4]["cypher_order"],
            [15],
        )
        self.assertEqual(
            rows[0]["slots"][0]["cypher_order"],
            [7, 12],
        )
        self.assertEqual(
            sum(
                len(slot["cypher_order"])
                for row in rows
                for slot in row["slots"]
            ),
            7,
        )

    def test_cypher_placement_rejects_invalid_input(self):
        for paired_stream in (
            [(3, 1)],
            [(1, 0)],
            [(1, 16)],
            [(1, True)],
            [(1,)],
        ):
            with self.subTest(paired_stream=paired_stream), self.assertRaises(ValueError):
                place_cypher_order(paired_stream)

    def test_recursive_pair_fold_round_trips_across_boundaries(self):
        for length in (0, 1, 2, 6, 7, 36, 37, 217):
            source = [
                (CYCLIC[index % len(CYCLIC)], index % 15 + 1)
                for index in range(length)
            ]
            with self.subTest(length=length):
                folded = fold_pair_stream(source)
                self.assertEqual(folded["original_count"], length)
                self.assertEqual(unfold_pair_stream(folded), source)

    def test_recursive_pair_fold_survives_json_persistence(self):
        import json

        source = [(CYCLIC[index % 6], index % 15 + 1) for index in range(50)]
        folded = json.loads(json.dumps(fold_pair_stream(source)))
        self.assertEqual(unfold_pair_stream(folded), source)

    def test_pair_fold_rejects_invalid_input_and_tampered_metadata(self):
        with self.assertRaises(ValueError):
            fold_pair_stream([(3, 1)])
        with self.assertRaises(ValueError):
            fold_pair_stream([(1, 16)])

        folded = fold_pair_stream([(1, 1), (4, 2), (2, 3)])
        folded["fold_rounds"] = 2
        with self.assertRaises(ValueError):
            unfold_pair_stream(folded)

        folded = fold_pair_stream([(1, 1), (4, 2), (2, 3)])
        folded["root_code_hex"] = "zz"
        with self.assertRaises(ValueError):
            unfold_pair_stream(folded)


if __name__ == "__main__":
    unittest.main()
