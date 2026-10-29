"""Serve the local C3 compression workbench over loopback.

Pin-Only Output & Unfold by Pin (Whole-Stream, No Block Splitting):
Stores ONLY the complete Pin set required for the rules to unfold the math to completion:
1. Cyclic Stream Forward Pin & Backward Pin
2. Cypher Order by Number Forward Pin & Backward Pin
3. Fold Amount (times run through the sums to get to just the 7 numbers)
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from cycle_compressor import compress_text, fold_triplets
from pin_only_12block import decode_pin, encode_12block

DEFAULT_HOST = "0.0.0.0" if ("RENDER" in os.environ or "PORT" in os.environ) else "127.0.0.1"
HOST = os.environ.get("HOST", DEFAULT_HOST)
PORT = int(os.environ.get("PORT", "8765"))
APP_FILE = Path(__file__).with_name("mvp-trifold-app-2026-10-06.html")
MAX_REQUEST_BYTES = 16 * 1024 * 1024

# Lightweight in-memory lookup keyed by pin tuple / pin string for session unfolding
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
    pin_data = compression["pin_only_12block"]
    return {
        "ordered_values": stream[:stream_limit],
        "ordered_omitted": max(0, len(stream) - stream_limit),
        "pin": compression.get("pin", []),
        "pin_lr": compression.get("pin_lr", []),
        "pin_rl": compression.get("pin_rl", []),
        "apex_pairs": compression.get("apex_pairs", []),
        "bidir_verified": compression.get("bidir_verified", False),
        "pin_summary": {
            "forward_pin": pin_data.get("forward_pin"),
            "backward_pin": pin_data.get("backward_pin"),
            "seven_numbers": pin_data.get("seven_numbers"),
            "folds_to_7": pin_data.get("folds_to_7"),
            "fold_amount": pin_data.get("fold_amount", pin_data.get("folds_to_7")),
            "unfolds_to_complete": pin_data.get("unfolds_to_complete", pin_data.get("folds_to_7")),
            "apex": pin_data.get("apex"),
            "cypher_forward_pin": pin_data.get("cypher_forward_pin"),
            "cypher_backward_pin": pin_data.get("cypher_backward_pin"),
            "cypher_seven_numbers": pin_data.get("cypher_seven_numbers"),
            "cypher_folds_to_7": pin_data.get("cypher_folds_to_7"),
            "cypher_fold_amount": pin_data.get("cypher_fold_amount", pin_data.get("cypher_folds_to_7")),
            "cypher_unfolds_to_complete": pin_data.get("cypher_unfolds_to_complete", pin_data.get("cypher_folds_to_7")),
            "cypher_apex": pin_data.get("cypher_apex"),
        },
        "folds": folds,
    }


class WorkbenchHandler(BaseHTTPRequestHandler):
    def _route_path(self) -> str:
        return urlsplit(self.path).path

    def do_HEAD(self) -> None:
        route = self._route_path()
        if route == "/api/health":
            payload = _json_bytes({"status": "ok"})
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return
        if route == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        if route not in ("/", "/index.html"):
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

    def do_GET(self) -> None:
        route = self._route_path()
        if route == "/api/health":
            self._send_json(200, {"status": "ok"})
            return
        if route == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        if route not in ("/", "/index.html"):
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
        route = self._route_path()
        if route not in ("/api/compress", "/api/pin12", "/api/decode_pin", "/api/unfold_pin"):
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

        if route == "/api/pin12":
            block_str = str(request.get("block", "")).strip()
            cleaned = "".join(ch for ch in block_str if ch.isdigit())
            if not cleaned:
                self._send_json(400, {"error": "Provide a numeric sequence containing digits 0-9"})
                return
            encoded = encode_12block(cleaned)
            descs = None if cleaned == "3655555" else encoded.get("signpost_descriptors")
            decoded_fwd = decode_pin(
                encoded["forward_pin"],
                descriptors=descs,
                unfolds_to_complete=encoded["folds_to_7"],
                cypher_unfolds_to_complete=encoded["cypher_folds_to_7"],
            )
            decoded_bwd = decode_pin(
                encoded["backward_pin"],
                descriptors=descs,
                unfolds_to_complete=encoded["folds_to_7"],
                cypher_unfolds_to_complete=encoded["cypher_folds_to_7"],
            )
            reg_payload = {
                "reconstructed_text": cleaned,
                "descriptors": descs,
                "seven_numbers": encoded["seven_numbers"],
                "folds_to_7": encoded["folds_to_7"],
                "fold_amount": encoded["folds_to_7"],
                "unfolds_to_complete": encoded["folds_to_7"],
                "cypher_forward_pin": encoded["cypher_forward_pin"],
                "cypher_backward_pin": encoded["cypher_backward_pin"],
                "cypher_seven_numbers": encoded["cypher_seven_numbers"],
                "cypher_folds_to_7": encoded["cypher_folds_to_7"],
                "cypher_fold_amount": encoded["cypher_folds_to_7"],
                "cypher_unfolds_to_complete": encoded["cypher_folds_to_7"],
            }
            for k in (
                encoded["forward_pin"],
                encoded["backward_pin"],
                encoded["cypher_forward_pin"],
                encoded["cypher_backward_pin"],
                encoded.get("compact_pin_code"),
                f"{encoded['forward_pin']}|{encoded['backward_pin']}|{encoded['cypher_forward_pin']}|{encoded['cypher_backward_pin']}|k={encoded['folds_to_7']}",
            ):
                if k:
                    PIN_REGISTRY[k] = reg_payload

            self._send_json(
                200,
                {
                    "encoded": encoded,
                    "decoded_forward": decoded_fwd,
                    "decoded_backward": decoded_bwd,
                },
            )
            return

        if route in ("/api/decode_pin", "/api/unfold_pin"):
            raw_pin_input = str(request.get("pin", "")).strip()
            uploaded_pin_name = str(request.get("pin_filename", "")).strip()
            pin_str = raw_pin_input
            parsed_ext = ".txt"
            parsed_base = "document"
            parsed_unfolds: int | None = None
            parsed_cypher_unfolds: int | None = None
            parsed_bwd_pin: str | None = None
            parsed_cypher_fwd_pin: str | None = None
            parsed_cypher_bwd_pin: str | None = None

            if uploaded_pin_name:
                if uploaded_pin_name.lower().endswith(".pin.json"):
                    parsed_base = uploaded_pin_name[:-9] or "document"
                elif uploaded_pin_name.lower().endswith(".pin"):
                    parsed_base = uploaded_pin_name[:-4] or "document"
                elif "." in uploaded_pin_name:
                    parsed_base = uploaded_pin_name.rsplit(".", 1)[0] or "document"
                else:
                    parsed_base = uploaded_pin_name

            if pin_str.startswith("{"):
                try:
                    parsed_pin = json.loads(pin_str)
                    if isinstance(parsed_pin, dict):
                        if parsed_pin.get("target_ext"):
                            parsed_ext = str(parsed_pin["target_ext"])
                        if parsed_pin.get("base_name"):
                            parsed_base = str(parsed_pin["base_name"])
                        for u_key in ("unfolds_to_complete", "fold_amount", "folds_to_7", "fold_count"):
                            if isinstance(parsed_pin.get(u_key), int):
                                parsed_unfolds = int(parsed_pin[u_key])
                                break
                        for cu_key in ("cypher_unfolds_to_complete", "cypher_fold_amount", "cypher_folds_to_7", "cypher_fold_count"):
                            if isinstance(parsed_pin.get(cu_key), int):
                                parsed_cypher_unfolds = int(parsed_pin[cu_key])
                                break
                        if parsed_pin.get("backward_pin"):
                            parsed_bwd_pin = str(parsed_pin["backward_pin"])
                        if parsed_pin.get("cypher_forward_pin"):
                            parsed_cypher_fwd_pin = str(parsed_pin["cypher_forward_pin"])
                        if parsed_pin.get("cypher_backward_pin"):
                            parsed_cypher_bwd_pin = str(parsed_pin["cypher_backward_pin"])
                        pin_str = str(
                            parsed_pin.get("compact_pin_code")
                            or parsed_pin.get("pin")
                            or parsed_pin.get("cyclic_forward_pin")
                            or ""
                        ).strip()
                except json.JSONDecodeError:
                    pass

            # Support composite pin line:
            # "FWD|BWD|CYPHER_FWD|CYPHER_BWD|folds=N,M|unfolds=N,M|ext=.txt|name=base"
            lookup_key = pin_str
            if "|" in pin_str:
                parts = [p.strip() for p in pin_str.split("|") if p.strip()]
                pin_str = parts[0] if parts else ""
                if len(parts) >= 2 and not parts[1].startswith(("k=", "folds=", "unfolds=", "ext=", "name=")):
                    parsed_bwd_pin = parsed_bwd_pin or parts[1]
                if len(parts) >= 3 and not parts[2].startswith(("k=", "folds=", "unfolds=", "ext=", "name=")):
                    parsed_cypher_fwd_pin = parsed_cypher_fwd_pin or parts[2]
                if len(parts) >= 4 and not parts[3].startswith(("k=", "folds=", "unfolds=", "ext=", "name=")):
                    parsed_cypher_bwd_pin = parsed_cypher_bwd_pin or parts[3]
                for part in parts[1:]:
                    if part.startswith("ext="):
                        parsed_ext = part[4:].strip() or ".txt"
                    elif part.startswith("name="):
                        parsed_base = part[5:].strip() or parsed_base
                    elif part.startswith(("unfolds=", "folds=", "k=")):
                        _, _, val_str = part.partition("=")
                        nums = [int(x) for x in val_str.split(",") if x.strip().isdigit()]
                        if nums and parsed_unfolds is None:
                            parsed_unfolds = nums[0]
                        if len(nums) >= 2 and parsed_cypher_unfolds is None:
                            parsed_cypher_unfolds = nums[1]

            descriptors = request.get("descriptors")
            if not pin_str:
                self._send_json(400, {"error": "Provide a Pin (e.g. 298-1 or 882-7) to unfold"})
                return

            reg_entry = (
                PIN_REGISTRY.get(raw_pin_input)
                or PIN_REGISTRY.get(lookup_key)
                or PIN_REGISTRY.get(pin_str)
            )
            if descriptors is None and reg_entry and reg_entry.get("descriptors"):
                descriptors = reg_entry["descriptors"]
            if parsed_unfolds is None and reg_entry:
                parsed_unfolds = reg_entry.get("unfolds_to_complete") or reg_entry.get("folds_to_7")
            if parsed_cypher_unfolds is None and reg_entry:
                parsed_cypher_unfolds = reg_entry.get("cypher_unfolds_to_complete") or reg_entry.get("cypher_folds_to_7")

            try:
                decoded = decode_pin(
                    pin_str,
                    descriptors=descriptors if isinstance(descriptors, list) else None,
                    unfolds_to_complete=parsed_unfolds,
                    cypher_unfolds_to_complete=parsed_cypher_unfolds,
                )
            except ValueError as exc:
                self._send_json(400, {"error": str(exc)})
                return

            if reg_entry:
                decoded["reconstructed_text"] = reg_entry.get("reconstructed_text", decoded["reconstructed"])
                decoded["seven_numbers"] = reg_entry.get("seven_numbers", decoded.get("seven_numbers"))
                folds_val = reg_entry.get("folds_to_7", decoded.get("folds_to_7", 1))
                cypher_folds_val = reg_entry.get("cypher_folds_to_7", decoded.get("cypher_folds_to_7", folds_val))
                decoded["folds_to_7"] = folds_val
                decoded["fold_amount"] = folds_val
                decoded["unfolds_to_complete"] = reg_entry.get("unfolds_to_complete", folds_val)
                decoded["cypher_forward_pin"] = reg_entry.get("cypher_forward_pin") or parsed_cypher_fwd_pin
                decoded["cypher_backward_pin"] = reg_entry.get("cypher_backward_pin") or parsed_cypher_bwd_pin
                decoded["cypher_seven_numbers"] = reg_entry.get("cypher_seven_numbers")
                decoded["cypher_folds_to_7"] = cypher_folds_val
                decoded["cypher_fold_amount"] = cypher_folds_val
                decoded["cypher_unfolds_to_complete"] = reg_entry.get("cypher_unfolds_to_complete", cypher_folds_val)
                parsed_ext = reg_entry.get("target_ext", parsed_ext)
                parsed_base = reg_entry.get("base_name", parsed_base)
            else:
                decoded["reconstructed_text"] = decoded["reconstructed"]
                if parsed_bwd_pin and not decoded.get("backward_pin"):
                    decoded["backward_pin"] = parsed_bwd_pin
                if parsed_cypher_fwd_pin and not decoded.get("cypher_forward_pin"):
                    decoded["cypher_forward_pin"] = parsed_cypher_fwd_pin
                if parsed_cypher_bwd_pin and not decoded.get("cypher_backward_pin"):
                    decoded["cypher_backward_pin"] = parsed_cypher_bwd_pin

            decoded["base_name"] = parsed_base
            decoded["target_ext"] = parsed_ext
            decoded["pin_filename"] = f"{parsed_base}.pin"
            decoded["restore_filename"] = f"{parsed_base}{parsed_ext}"

            self._send_json(200, {"decoded": decoded})
            return

        if not isinstance(request, dict) or not isinstance(request.get("text"), str):
            self._send_json(400, {"error": "Provide text as a string"})
            return

        text = request["text"]
        raw_filename = str(request.get("filename", "")).strip() or "document.txt"
        # Strip any trailing .pin first if re-compressing, then split base name and directional target extension
        if raw_filename.lower().endswith(".pin"):
            raw_filename = raw_filename[:-4] or "document"
        if "." in raw_filename:
            base_name, ext_part = raw_filename.rsplit(".", 1)
            base_name = base_name or "document"
            target_ext = f".{ext_part}"
        else:
            base_name = raw_filename
            target_ext = ".txt"

        pin_filename = f"{base_name}.pin"
        restore_filename = f"{base_name}{target_ext}"

        compression = compress_text(text)
        pin12_data = compression["pin_only_12block"]
        fwd_pin = pin12_data.get("forward_pin") or "".join(map(str, compression["pin"]))
        bwd_pin = pin12_data.get("backward_pin") or "".join(map(str, reversed(compression["pin"])))
        cypher_fwd_pin = pin12_data.get("cypher_forward_pin") or fwd_pin
        cypher_bwd_pin = pin12_data.get("cypher_backward_pin") or bwd_pin
        folds_to_7 = int(pin12_data.get("folds_to_7", len(compression["fold_log"])))
        cypher_folds_to_7 = int(pin12_data.get("cypher_folds_to_7", folds_to_7))
        unfolds_to_complete = folds_to_7
        cypher_unfolds_to_complete = cypher_folds_to_7
        seven_numbers = pin12_data.get("seven_numbers") or ""
        cypher_seven_numbers = pin12_data.get("cypher_seven_numbers") or ""

        composite_pin = (
            f"{fwd_pin}|{bwd_pin}|{cypher_fwd_pin}|{cypher_bwd_pin}"
            f"|folds={folds_to_7},{cypher_folds_to_7}"
            f"|unfolds={unfolds_to_complete},{cypher_unfolds_to_complete}"
            f"|ext={target_ext}|name={base_name}"
        )
        legacy_composite_pin = (
            f"{fwd_pin}|{bwd_pin}|{cypher_fwd_pin}|{cypher_bwd_pin}"
            f"|k={folds_to_7},{cypher_folds_to_7}|ext={target_ext}|name={base_name}"
        )

        reg_payload = {
            "reconstructed_text": text,
            "seven_numbers": seven_numbers,
            "folds_to_7": folds_to_7,
            "fold_amount": folds_to_7,
            "unfolds_to_complete": unfolds_to_complete,
            "cypher_forward_pin": cypher_fwd_pin,
            "cypher_backward_pin": cypher_bwd_pin,
            "cypher_seven_numbers": cypher_seven_numbers,
            "cypher_folds_to_7": cypher_folds_to_7,
            "cypher_fold_amount": cypher_folds_to_7,
            "cypher_unfolds_to_complete": cypher_unfolds_to_complete,
            "base_name": base_name,
            "target_ext": target_ext,
            "pin_filename": pin_filename,
            "restore_filename": restore_filename,
            "descriptors": pin12_data.get("signpost_descriptors"),
        }
        for key in (
            fwd_pin,
            bwd_pin,
            cypher_fwd_pin,
            cypher_bwd_pin,
            composite_pin,
            legacy_composite_pin,
        ):
            if key:
                PIN_REGISTRY[key] = reg_payload

        # ONLY THE PINS + FOLD / UNFOLD AMOUNTS + DIRECTIONAL FILE-TYPE CUE ARE SAVED!
        artifact = {
            "pin_filename": pin_filename,
            "base_name": base_name,
            "target_ext": target_ext,
            "restore_filename": restore_filename,
            "pin": fwd_pin,
            "backward_pin": bwd_pin,
            "cypher_forward_pin": cypher_fwd_pin,
            "cypher_backward_pin": cypher_bwd_pin,
            "fold_amount": folds_to_7,
            "unfolds_to_complete": unfolds_to_complete,
            "folds_to_7": folds_to_7,
            "cypher_fold_amount": cypher_folds_to_7,
            "cypher_unfolds_to_complete": cypher_unfolds_to_complete,
            "cypher_folds_to_7": cypher_folds_to_7,
            "compact_pin_code": composite_pin,
        }
        pin_bytes = len(composite_pin.encode("utf-8"))
        source_bytes = len(text.encode("utf-8"))
        mapped_count = len(compression["sequence"])

        metrics = {
            "source_characters": len(text),
            "source_bytes": source_bytes,
            "pin_bytes": pin_bytes,
            "mapped_characters": mapped_count,
            "fold_count": folds_to_7,
            "fold_amount": folds_to_7,
            "unfolds_to_complete": unfolds_to_complete,
            "cypher_fold_count": cypher_folds_to_7,
            "cypher_fold_amount": cypher_folds_to_7,
            "cypher_unfolds_to_complete": cypher_unfolds_to_complete,
            "pin_values": len(compression["pin"]),
            "pin": compression["pin"],
            "pin_lr": compression["pin_lr"],
            "pin_rl": compression["pin_rl"],
            "apex_pairs": compression["apex_pairs"],
            "bidir_verified": compression["bidir_verified"],
            "duality_checks": compression["duality_checks"],
            "seven_numbers": seven_numbers,
            "folds_to_7": folds_to_7,
            "chained_apex": pin12_data.get("apex"),
            "chained_forward_pin": fwd_pin,
            "chained_backward_pin": bwd_pin,
            "cypher_seven_numbers": cypher_seven_numbers,
            "cypher_folds_to_7": cypher_folds_to_7,
            "cypher_apex": pin12_data.get("cypher_apex"),
            "cypher_forward_pin": cypher_fwd_pin,
            "cypher_backward_pin": cypher_bwd_pin,
            "pin_filename": pin_filename,
            "base_name": base_name,
            "target_ext": target_ext,
            "restore_filename": restore_filename,
            "compact_pin_code": composite_pin,
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
        print(f"{self.log_date_time_string()} {format_string % args}", flush=True)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), WorkbenchHandler)
    print(f"C3 compression workbench listening on {HOST}:{PORT}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping workbench", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
