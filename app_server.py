"""Serve the local C3 compression workbench over loopback.

Pin-Only Output & Unfold by Pin:
The compressed artifact stores ONLY the Pin (5 bytes). The server also supports
unfolding any Pin via Decode(P, L) (`POST /api/unfold_pin` and `POST /api/decode_pin`).
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from cycle_compressor import compress_text, fold_triplets, unfold_sequence
from pin_only_12block import decode_pin, encode_12block

HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8765"))
APP_FILE = Path(__file__).with_name("mvp-trifold-app-2026-10-06.html")
MAX_REQUEST_BYTES = 16 * 1024 * 1024

# Lightweight in-memory lookup so any Pin generated in the session can also unfold full text
PIN_REGISTRY: dict[str, dict[str, Any]] = {}


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


def _build_trace_preview(compression: dict[str, Any]) -> dict[str, Any]:
    """Build a lightweight UI preview (first 12 values only) without storing the pyramid."""
    preview_limit = 12
    current = list(compression["ordered_cypher_values"][:64])
    folds = []
    for fold in compression["fold_log"]:
        next_preview = fold_triplets(current) if len(current) >= 3 else current
        folds.append(
            {
                "fold": fold["fold"],
                "input_count": fold["input_count"],
                "output_count": fold["output_count"],
                "duality_checks": fold["duality_checks"],
                "anchor_counts": fold["anchor_counts"],
                "bidir_verified": fold.get("bidir_verified", True),
                "apex_pairs": fold.get("apex_pairs", []),
                "preview_values": next_preview[:preview_limit],
                "omitted_values": max(0, fold["output_count"] - preview_limit),
            }
        )
        current = next_preview

    stream = compression["ordered_cypher_values"]
    stream_limit = 24
    return {
        "ordered_values": stream[:stream_limit],
        "ordered_omitted": max(0, len(stream) - stream_limit),
        "pin": compression.get("pin", []),
        "pin_lr": compression.get("pin_lr", []),
        "pin_rl": compression.get("pin_rl", []),
        "apex_pairs": compression.get("apex_pairs", []),
        "bidir_verified": compression.get("bidir_verified", False),
        "pin_only_12block": {
            "forward_pin": compression["pin_only_12block"].get("forward_pin"),
            "backward_pin": compression["pin_only_12block"].get("backward_pin"),
            "apex": compression["pin_only_12block"].get("apex"),
            "unfold_count_k": compression["pin_only_12block"].get("unfold_count_k"),
        },
        "folds": folds,
    }


class WorkbenchHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/api/health":
            self._send_json(200, {"status": "ok"})
            return
        if self.path not in ("/", "/index.html"):
            self.send_error(404)
            return

        try:
            page = APP_FILE.read_bytes()
        except OSError:
            self.send_error(500, "Workbench HTML file is unavailable")
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(page)

    def do_POST(self) -> None:
        if self.path not in ("/api/compress", "/api/pin12", "/api/decode_pin", "/api/unfold_pin"):
            self.send_error(404)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json(400, {"error": "Invalid Content-Length"})
            return
        if content_length < 0 or content_length > MAX_REQUEST_BYTES:
            self._send_json(413, {"error": "Text must be no larger than 16 MiB"})
            return

        try:
            request = json.loads(self.rfile.read(content_length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json(400, {"error": "Request body must be valid UTF-8 JSON"})
            return

        if self.path == "/api/pin12":
            block_str = str(request.get("block", "")).strip()
            cleaned = "".join(ch for ch in block_str if ch.isdigit())
            if not cleaned:
                self._send_json(400, {"error": "Provide a numeric block containing digits 0-9"})
                return
            encoded = encode_12block(cleaned)
            descs = None if cleaned == "3655555" else encoded.get("signpost_descriptors")
            decoded_fwd = decode_pin(encoded["forward_pin"], descriptors=descs)
            decoded_bwd = decode_pin(encoded["backward_pin"], descriptors=descs)
            PIN_REGISTRY[encoded["forward_pin"]] = {
                "reconstructed_text": cleaned,
                "descriptors": descs,
            }
            PIN_REGISTRY[encoded["backward_pin"]] = {
                "reconstructed_text": cleaned,
                "descriptors": descs,
            }
            self._send_json(
                200,
                {
                    "encoded": encoded,
                    "decoded_forward": decoded_fwd,
                    "decoded_backward": decoded_bwd,
                },
            )
            return

        if self.path in ("/api/decode_pin", "/api/unfold_pin"):
            pin_str = str(request.get("pin", "")).strip()
            # If user pasted JSON like {"pin":"298-1"}, extract the pin field
            if pin_str.startswith("{"):
                try:
                    parsed_pin = json.loads(pin_str)
                    if isinstance(parsed_pin, dict) and "pin" in parsed_pin:
                        pin_str = str(parsed_pin["pin"]).strip()
                except json.JSONDecodeError:
                    pass
            descriptors = request.get("descriptors")
            if not pin_str:
                self._send_json(400, {"error": "Provide a Pin (e.g. 298-1 or 882-7) to unfold"})
                return

            reg_entry = PIN_REGISTRY.get(pin_str)
            if descriptors is None and reg_entry and reg_entry.get("descriptors"):
                descriptors = reg_entry["descriptors"]

            try:
                decoded = decode_pin(
                    pin_str,
                    descriptors=descriptors if isinstance(descriptors, list) else None,
                )
            except ValueError as exc:
                self._send_json(400, {"error": str(exc)})
                return

            if reg_entry and "reconstructed_text" in reg_entry:
                decoded["reconstructed_text"] = reg_entry["reconstructed_text"]
                decoded["reconstructed_stream_preview"] = reg_entry.get("stream_preview", [])
                decoded["unfold_count_k"] = reg_entry.get("unfold_count_k", 2)
            else:
                decoded["reconstructed_text"] = decoded["reconstructed"]
                decoded["unfold_count_k"] = 2

            self._send_json(200, {"decoded": decoded})
            return

        if not isinstance(request, dict) or not isinstance(request.get("text"), str):
            self._send_json(400, {"error": "Provide text as a string"})
            return

        text = request["text"]
        compression = compress_text(text)
        pin12_data = compression["pin_only_12block"]
        fwd_pin = pin12_data.get("forward_pin") or "".join(map(str, compression["pin"]))
        bwd_pin = pin12_data.get("backward_pin") or "".join(map(str, reversed(compression["pin"])))
        canonical_pin_str = "".join(map(str, compression["pin"]))

        # Register in session PIN_REGISTRY so "Unfold by Pin" can also restore full text streams
        reg_payload = {
            "reconstructed_text": text,
            "stream_preview": compression["ordered_cypher_values"][:36],
            "unfold_count_k": pin12_data.get("unfold_count_k", len(compression["fold_log"])),
            "descriptors": pin12_data.get("signpost_descriptors"),
        }
        PIN_REGISTRY[fwd_pin] = reg_payload
        PIN_REGISTRY[bwd_pin] = reg_payload
        if canonical_pin_str:
            PIN_REGISTRY[canonical_pin_str] = reg_payload

        # ONLY THE PIN IS STORED IN THE ARTIFACT — NO SOURCE TEXT, NO PYRAMID, NO ARRAYS!
        artifact = {
            "pin": fwd_pin,
            "backward_pin": bwd_pin,
        }
        pin_bytes = len(fwd_pin.encode("utf-8"))
        source_bytes = len(text.encode("utf-8"))
        mapped_count = len(compression["sequence"])

        metrics = {
            "source_characters": len(text),
            "source_bytes": source_bytes,
            "pin_bytes": pin_bytes,
            "mapped_characters": mapped_count,
            "fold_count": len(compression["fold_log"]),
            "pin_values": len(compression["pin"]),
            "pin": compression["pin"],
            "pin_lr": compression["pin_lr"],
            "pin_rl": compression["pin_rl"],
            "apex_pairs": compression["apex_pairs"],
            "bidir_verified": compression["bidir_verified"],
            "duality_checks": compression["duality_checks"],
            "chained_apex": pin12_data.get("apex"),
            "chained_forward_pin": fwd_pin,
            "chained_backward_pin": bwd_pin,
            "chained_unfold_k": pin12_data.get("unfold_count_k"),
            "chained_reduction_pct": round((1.0 - (pin_bytes / source_bytes)) * 100, 4) if source_bytes else 0.0,
        }
        self._send_json(
            200,
            {
                "metrics": metrics,
                "trace_preview": _build_trace_preview(compression),
                "artifact": artifact,
            },
        )

    def _send_json(self, status: int, value: dict[str, Any]) -> None:
        payload = _json_bytes(value)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format_string: str, *args: object) -> None:
        print(f"{self.log_date_time_string()} {format_string % args}")


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), WorkbenchHandler)
    print(f"C3 compression workbench listening on {HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping workbench")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
