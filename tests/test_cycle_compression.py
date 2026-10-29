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
from pin_only_12block import (
    compress_12block_stream,
    decode_pin,
    decompress_12block_stream,
    encode_12block,
    expand_via_nine_multiplication,
)


class CycleCompressorTests(unittest.TestCase):
    def test_compress_text_returns_expected_structure(self):
        result = compress_text("hello world")
        self.assertEqual(result["input_length"], len("hello world"))
        self.assertTrue(result["cipher_order"])
        self.assertTrue(result["pin"])
        self.assertTrue(result["bidir_verified"])
        self.assertIn("fold_log", result)
        self.assertIn("pin_only_12block", result)
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

    def test_only_3_6_and_repeats_multiply_by_9(self):
        # Single non-repeating data digits {1, 2, 4, 5, 7, 8} stay untouched
        self.assertEqual(expand_via_nine_multiplication("142857"), "142857")
        # Single 3 -> 27, single 6 -> 54, repeat 55555 -> 4545454545
        self.assertEqual(expand_via_nine_multiplication("3655555"), "27544545454545")
        # Mixed: 1 (untouched), 3 (->27), 4 (untouched), 6 (->54), 22 (repeat -> 1818), 8 (untouched)
        self.assertEqual(expand_via_nine_multiplication("1346228"), "12745418188")

    def test_paper_test_vector_3655555_round_trip(self):
        encoded = encode_12block("3655555")
        self.assertEqual(encoded["expanded"], "27544545454545")
        self.assertEqual(encoded["consolidated"], "5445455")
        self.assertEqual(encoded["apex"], "452152")
        self.assertEqual(encoded["forward_pin"], "298-1")
        self.assertEqual(encoded["backward_pin"], "882-7")

        decoded_fwd = decode_pin("298-1")
        self.assertEqual(decoded_fwd["reconstructed"], "3655555")
        self.assertTrue(decoded_fwd["lossless"])

        decoded_bwd = decode_pin("882-7")
        self.assertEqual(decoded_bwd["reconstructed"], "3655555")
        self.assertTrue(decoded_bwd["lossless"])

    def test_12block_stream_round_trip(self):
        stream = "14236555558724441"
        compressed = compress_12block_stream(stream)
        self.assertEqual(decompress_12block_stream(compressed, use_backward=False), stream)
        self.assertEqual(decompress_12block_stream(compressed, use_backward=True), stream)

    def test_workbench_trace_preview_includes_12block_and_bidir(self):
        from app_server import _build_trace_preview
        compression = compress_text("hello world")
        preview = _build_trace_preview(compression)
        self.assertIn("pin_summary", preview)
        self.assertTrue(preview["pin_summary"]["forward_pin"])
        self.assertTrue(preview["pin_summary"]["backward_pin"])
        self.assertTrue(preview["pin_summary"]["cypher_forward_pin"])
        self.assertTrue(preview["pin_summary"]["cypher_backward_pin"])
        self.assertEqual(len(preview["pin_summary"]["seven_numbers"]), 7)
        self.assertGreaterEqual(preview["pin_summary"]["folds_to_7"], 1)
        self.assertIn("pin_lr", preview)
        self.assertIn("pin_rl", preview)
        self.assertTrue(preview["bidir_verified"])

    def test_app_server_endpoints_and_render_healthcheck(self):
        import io
        from app_server import WorkbenchHandler

        def invoke(method: str, path: str, body: dict | None = None) -> tuple[int, bytes]:
            payload = json.dumps(body).encode("utf-8") if body is not None else b""
            raw_req = (
                f"{method} {path} HTTP/1.1\r\n"
                f"Host: localhost\r\n"
                f"Content-Type: application/json\r\n"
                f"Content-Length: {len(payload)}\r\n\r\n"
            ).encode("utf-8") + payload

            rfile = io.BytesIO(raw_req)
            wfile = io.BytesIO()

            class DummySocket:
                def makefile(self, mode: str, *args: object) -> io.BytesIO:
                    return rfile if "r" in mode else wfile

                def sendall(self, data: bytes) -> None:
                    wfile.write(data)

            WorkbenchHandler(DummySocket(), ("127.0.0.1", 0), None)
            raw_resp = wfile.getvalue()
            header_part, _, resp_body = raw_resp.partition(b"\r\n\r\n")
            status_code = int(header_part.splitlines()[0].split()[1])
            return status_code, resp_body

        status, body = invoke("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"status": "ok"})

        status, _ = invoke("HEAD", "/api/health")
        self.assertEqual(status, 200)

        status, body = invoke("GET", "/?render_probe=1")
        self.assertEqual(status, 200)
        self.assertIn(b"Cyclic &amp; Cypher Order Pin Workbench", body)

        status, body = invoke("POST", "/api/compress", {"text": "Alice was beginning", "filename": "alice.txt"})
        self.assertEqual(status, 200)
        comp_data = json.loads(body)
        self.assertEqual(comp_data["artifact"]["pin_filename"], "alice.pin")
        self.assertEqual(comp_data["artifact"]["restore_filename"], "alice.txt")
        self.assertGreaterEqual(comp_data["artifact"]["fold_amount"], 1)
        self.assertGreaterEqual(comp_data["artifact"]["unfolds_to_complete"], 1)
        self.assertGreaterEqual(comp_data["artifact"]["cypher_fold_amount"], 1)
        self.assertGreaterEqual(comp_data["artifact"]["cypher_unfolds_to_complete"], 1)
        compact_code = comp_data["artifact"]["compact_pin_code"]
        self.assertIn("|folds=", compact_code)
        self.assertIn("|unfolds=", compact_code)

        status, body = invoke("POST", "/api/unfold_pin", {"pin": compact_code, "pin_filename": "alice.pin"})
        self.assertEqual(status, 200)
        unfold_data = json.loads(body)
        self.assertEqual(unfold_data["decoded"]["reconstructed_text"], "Alice was beginning")
        self.assertEqual(unfold_data["decoded"]["restore_filename"], "alice.txt")
        self.assertEqual(
            unfold_data["decoded"]["unfolds_to_complete"],
            comp_data["artifact"]["unfolds_to_complete"],
        )
        self.assertEqual(
            unfold_data["decoded"]["cypher_unfolds_to_complete"],
            comp_data["artifact"]["cypher_unfolds_to_complete"],
        )

        # Verify standalone composite pin decoding parses folds/unfolds without session cache
        standalone_dec = decode_pin("298-1|882-7|775-1|577-2|folds=4,3|unfolds=4,3|ext=.txt|name=demo")
        self.assertEqual(standalone_dec["unfolds_to_complete"], 4)
        self.assertEqual(standalone_dec["fold_amount"], 4)
        self.assertEqual(standalone_dec["cypher_unfolds_to_complete"], 3)
        self.assertEqual(standalone_dec["cypher_fold_amount"], 3)


if __name__ == "__main__":
    unittest.main()
