"""Serve the local C3 compression workbench over loopback."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from cycle_compressor import compress_text, fold_triplets

HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8765"))
APP_FILE = Path(__file__).with_name("mvp-trifold-app-2026-10-06.html")
MAX_REQUEST_BYTES = 8 * 1024 * 1024


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


def _build_trace_preview(compression: dict[str, Any]) -> dict[str, Any]:
    current = list(compression["ordered_cypher_values"])
    folds = []
    for fold in compression["fold_log"]:
        next_values = fold_triplets(current)
        if len(next_values) != fold["output_count"]:
            raise ValueError("fold preview does not match compressor fold log")
        preview_limit = 12
        folds.append(
            {
                "fold": fold["fold"],
                "input_count": fold["input_count"],
                "output_count": fold["output_count"],
                "duality_checks": fold["duality_checks"],
                "anchor_counts": fold["anchor_counts"],
                "preview_values": next_values[:preview_limit],
                "omitted_values": max(0, len(next_values) - preview_limit),
            }
        )
        current = next_values

    if current != compression["folded_values"]:
        raise ValueError("fold preview does not match the final compressor values")

    stream = compression["ordered_cypher_values"]
    stream_limit = 24
    return {
        "ordered_values": stream[:stream_limit],
        "ordered_omitted": max(0, len(stream) - stream_limit),
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
        if self.path != "/api/compress":
            self.send_error(404)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json(400, {"error": "Invalid Content-Length"})
            return
        if content_length < 0 or content_length > MAX_REQUEST_BYTES:
            self._send_json(413, {"error": "Text must be no larger than 8 MiB"})
            return

        try:
            request = json.loads(self.rfile.read(content_length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json(400, {"error": "Request body must be valid UTF-8 JSON"})
            return
        if not isinstance(request, dict) or not isinstance(request.get("text"), str):
            self._send_json(400, {"error": "Provide text as a string"})
            return

        text = request["text"]
        compression = compress_text(text)
        artifact = {
            "format": "c3-compression-workbench-v1",
            "source_text": text,
            "compression": compression,
        }
        mapped_count = len(compression["sequence"])
        metrics = {
            "source_characters": len(text),
            "mapped_characters": mapped_count,
            "fold_count": len(compression["fold_log"]),
            "pin_values": len(compression["pin"]),
            "duality_checks": compression["duality_checks"],
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
