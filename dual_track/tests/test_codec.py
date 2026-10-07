import json
import unittest

from dual_track import (
    CYCLIC,
    PATTERN_COUNT,
    SymbolLibrary,
    decode_pattern,
    decode_text,
    encode_pattern,
    encode_text,
    fold_pairs,
    pack_text,
    unpack_text,
    unfold_pairs,
)


TEST_LIBRARY = SymbolLibrary(tuple(chr(code) for code in range(0x1000, 0x1000 + 90)))


class DualTrackCodecTests(unittest.TestCase):
    def test_pattern_library_is_a_bijection(self):
        self.assertEqual(PATTERN_COUNT, 46_656)
        for pid in range(PATTERN_COUNT):
            self.assertEqual(encode_pattern(decode_pattern(pid)), pid)

    def test_symbol_library_maps_and_restores_all_symbols(self):
        for symbol in TEST_LIBRARY.symbols:
            self.assertEqual(TEST_LIBRARY.decode_pair(*TEST_LIBRARY.encode_symbol(symbol)), symbol)

    def test_text_round_trip_for_empty_partial_and_multiple_round_sizes(self):
        for length in (0, 1, 6, 7, 36, 37, 217):
            text = "".join(TEST_LIBRARY.symbols[index % 90] for index in range(length))
            with self.subTest(length=length):
                folded = encode_text(text, TEST_LIBRARY)
                self.assertEqual(decode_text(folded, TEST_LIBRARY), text)
                self.assertEqual(folded["input_count"], length)
                self.assertEqual(folded["last_len"], length % 6 or (6 if length else 0))

    def test_pair_fold_preserves_order_and_six_verification_sums(self):
        source = [(CYCLIC[index % 6], index % 15 + 1) for index in range(101)]
        folded = fold_pairs(source)
        self.assertEqual(unfold_pairs(folded), source)
        self.assertEqual(sum(folded["sums"]), sum(cypher for _, cypher in source))
        self.assertEqual(folded["fold_count"], 3)
        self.assertIsInstance(folded["lineal_records"], list)
        self.assertNotIn("root", folded)

    def test_fold_round_trip_after_json_persistence(self):
        text = "".join(TEST_LIBRARY.symbols[index % 90] for index in range(300))
        persisted = json.loads(json.dumps(encode_text(text, TEST_LIBRARY)))
        self.assertEqual(decode_text(persisted, TEST_LIBRARY), text)

    def test_symbol_library_rejects_invalid_order(self):
        with self.assertRaises(ValueError):
            SymbolLibrary(("a", "b"))
        with self.assertRaises(ValueError):
            SymbolLibrary(("a",) * 90)
        with self.assertRaises(ValueError):
            SymbolLibrary(tuple("a" for _ in range(90)))

    def test_fold_validation_rejects_tampering(self):
        folded = fold_pairs([(1, 1), (4, 2), (2, 3)])
        folded["sums"][0] += 1
        with self.assertRaises(ValueError):
            unfold_pairs(folded)

        folded = fold_pairs([(1, 1), (4, 2), (2, 3)])
        folded["last_len"] = 6
        with self.assertRaises(ValueError):
            unfold_pairs(folded)

        folded = fold_pairs([(1, 1), (4, 2), (2, 3)])
        folded["lineal_records"].append({"kind": "leaf"})
        with self.assertRaises(ValueError):
            unfold_pairs(folded)

    def test_input_pair_validation(self):
        for source in ([(3, 1)], [(1, 0)], [(1, 16)], [(1, True)]):
            with self.subTest(source=source), self.assertRaises(ValueError):
                fold_pairs(source)

    def test_binary_archive_round_trip_and_corruption_detection(self):
        text = "".join(TEST_LIBRARY.symbols[index % 90] for index in range(103))
        payload = pack_text(text, TEST_LIBRARY)
        self.assertEqual(unpack_text(payload), text)
        corrupted = bytearray(payload)
        corrupted[20] ^= 1
        with self.assertRaisesRegex(ValueError, "checksum"):
            unpack_text(bytes(corrupted))


if __name__ == "__main__":
    unittest.main()
