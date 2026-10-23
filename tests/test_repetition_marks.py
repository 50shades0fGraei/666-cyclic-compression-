import random
import unittest

from repetition_marks import RunMark, decode, encode, from_file_text, to_file_text


class RepetitionMarkTests(unittest.TestCase):
    def marks_text(self, digits):
        return [m.to_text() for m in encode(digits)[1]]

    def test_pair_leaves_count_blank(self):
        # chunk 1 = 1 2 8 5 7 1, chunk 2 = 4 4 2 ...  -> pair of 4s in chunk 2
        self.assertEqual(self.marks_text("128571442"), ["2.4"])

    def test_three_or_more_records_total(self):
        self.assertEqual(self.marks_text("128571444"), ["2.4.3"])

    def test_which_occurrence_when_chunk_has_several(self):
        # chunk 5 = 4 1 4 4 4 2 : run starts at the 2nd 4 in the chunk
        digits = "1" * 0 + "125871" "258714" "587142" "871425" "414442"
        self.assertIn("5(2).4.3", self.marks_text(digits))

    def test_run_crossing_chunk_boundary_uses_start_chunk(self):
        # chunk 1 = 1 2 8 5 7 4, run of 4s continues into chunk 2
        self.assertEqual(self.marks_text("12857444"), ["1.4.3"])

    def test_mark_text_round_trip(self):
        for text in ("5.4", "5.4.3", "5(2).4.3", "12(3).7"):
            self.assertEqual(RunMark.from_text(text).to_text(), text)

    def test_random_142857_round_trip(self):
        rng = random.Random(42)
        for length in (0, 1, 6, 100, 1000):
            digits = [rng.choice((1, 4, 2, 8, 5, 7)) for _ in range(length)]
            body, marks = encode(digits)
            self.assertEqual(decode(body, marks), digits)
            self.assertEqual(from_file_text(to_file_text(digits)), digits)

    def test_long_runs_round_trip(self):
        digits = [4] * 20 + [1, 1, 4, 4, 4, 1] + [7] * 3
        self.assertEqual(from_file_text(to_file_text(digits)), digits)

    def test_tampered_mark_is_rejected(self):
        text = to_file_text("128571444").replace("2.4.3", "3.4.3")
        with self.assertRaises(ValueError):
            from_file_text(text)


if __name__ == "__main__":
    unittest.main()
