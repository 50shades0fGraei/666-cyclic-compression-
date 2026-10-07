"""Lossless six-wide dual-track folding using the fixed 142857 pattern basis."""

from __future__ import annotations

import struct
import zlib
from collections.abc import Iterable, Sequence
from typing import Any

from .library import CYCLIC, LIBRARY_VERSION, SymbolLibrary

CHUNK_SIZE = 6
PATTERN_COUNT = len(CYCLIC) ** CHUNK_SIZE
FORMAT_VERSION = "dual-track-fold-v1"
BINARY_MAGIC = b"DTC1"
CHECKSUM_SIZE = 4


def encode_pattern(values: Sequence[int]) -> int:
    """Encode exactly six cyclic values as a base-six Pattern ID."""
    if len(values) != CHUNK_SIZE:
        raise ValueError(f"a pattern must contain exactly {CHUNK_SIZE} cyclic values")
    pid = 0
    for value in values:
        if isinstance(value, bool) or not isinstance(value, int) or value not in CYCLIC:
            raise ValueError(f"unsupported cyclic value: {value!r}")
        pid = pid * len(CYCLIC) + CYCLIC.index(value)
    return pid


def decode_pattern(pid: int) -> tuple[int, ...]:
    """Decode a Pattern ID into six cyclic values."""
    if isinstance(pid, bool) or not isinstance(pid, int) or not 0 <= pid < PATTERN_COUNT:
        raise ValueError(f"PID must be an integer from 0 to {PATTERN_COUNT - 1}")
    indices = [0] * CHUNK_SIZE
    remainder = pid
    for index in range(CHUNK_SIZE - 1, -1, -1):
        remainder, indices[index] = divmod(remainder, len(CYCLIC))
    return tuple(CYCLIC[index] for index in indices)


def _validate_pair(pair: tuple[int, int]) -> tuple[int, int]:
    if len(pair) != 2:
        raise ValueError("each item must be a (cyclic value, cypher ID) pair")
    cyclic_value, cypher_id = pair
    if isinstance(cyclic_value, bool) or not isinstance(cyclic_value, int) or cyclic_value not in CYCLIC:
        raise ValueError(f"unsupported cyclic value: {cyclic_value!r}")
    if (
        isinstance(cypher_id, bool)
        or not isinstance(cypher_id, int)
        or not 1 <= cypher_id <= 15
    ):
        raise ValueError("cypher ID must be an integer from 1 to 15")
    return cyclic_value, cypher_id


def _leaf_node(pairs: Sequence[tuple[int, int]]) -> dict[str, Any]:
    cyclic_values = [pair[0] for pair in pairs]
    node: dict[str, Any] = {
        "kind": "leaf",
        "length": len(pairs),
        "cypher_ids": [pair[1] for pair in pairs],
    }
    if len(pairs) == CHUNK_SIZE:
        node["pid"] = encode_pattern(cyclic_values)
    else:
        node["cyclic_values"] = cyclic_values
    return node


def _fold_tree(nodes: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, int]:
    if not nodes:
        return None, 0
    rounds = 1
    current = nodes
    while len(current) > 1:
        current = [
            {
                "kind": "branch",
                "children": current[offset:offset + CHUNK_SIZE],
            }
            for offset in range(0, len(current), CHUNK_SIZE)
        ]
        rounds += 1
    return current[0], rounds


def _serialize_lineal(node: dict[str, Any], records: list[dict[str, Any]]) -> None:
    if node["kind"] == "branch":
        children = node["children"]
        records.append({"kind": "branch", "child_count": len(children)})
        for child in children:
            _serialize_lineal(child, records)
    else:
        records.append({key: value for key, value in node.items()})


def fold_pairs(pairs: Iterable[tuple[int, int]]) -> dict[str, Any]:
    """Fold ordered pairs into six-wide PID leaves and lineal fold records.

    Every leaf PID represents six cyclic values; the aligned cypher IDs are
    stored alongside it. Partial final leaves store their exact cyclic values.
    Higher levels group child nodes explicitly. The tree is serialized as a
    preorder lineal record list, with each branch's child count delimiting its
    ordered descendants. This is lossless without pretending a parent PID
    compresses its children.
    """
    values = [_validate_pair(pair) for pair in pairs]
    leaves = [
        _leaf_node(values[offset:offset + CHUNK_SIZE])
        for offset in range(0, len(values), CHUNK_SIZE)
    ]
    root, fold_count = _fold_tree(leaves)
    lineal_records: list[dict[str, Any]] = []
    if root is not None:
        _serialize_lineal(root, lineal_records)

    sums = {cyclic_value: 0 for cyclic_value in CYCLIC}
    for cyclic_value, cypher_id in values:
        sums[cyclic_value] += cypher_id

    return {
        "format": FORMAT_VERSION,
        "library_version": LIBRARY_VERSION,
        "cyclic": list(CYCLIC),
        "chunk_size": CHUNK_SIZE,
        "num_chunks": len(leaves),
        "last_len": len(values) % CHUNK_SIZE or (CHUNK_SIZE if values else 0),
        "input_count": len(values),
        "fold_count": fold_count,
        "sums": [sums[value] for value in CYCLIC],
        "lineal_records": lineal_records,
    }


def _decode_leaf(node: dict[str, Any]) -> list[tuple[int, int]]:
    kind = node.get("kind")
    if kind != "leaf":
        raise ValueError(f"unknown fold node kind: {kind!r}")
    length = node.get("length")
    cypher_ids = node.get("cypher_ids")
    if isinstance(length, bool) or not isinstance(length, int) or not 1 <= length <= CHUNK_SIZE:
        raise ValueError("leaf length must be from one to six")
    if not isinstance(cypher_ids, list) or len(cypher_ids) != length:
        raise ValueError("leaf cypher ID count does not match its length")

    if length == CHUNK_SIZE:
        if "cyclic_values" in node:
            raise ValueError("full leaf must use a PID, not raw cyclic values")
        cyclic_values = decode_pattern(node.get("pid"))
    else:
        if "pid" in node:
            raise ValueError("partial leaf must store exact cyclic values, not a PID")
        cyclic_values = node.get("cyclic_values")
        if not isinstance(cyclic_values, list) or len(cyclic_values) != length:
            raise ValueError("partial leaf cyclic values do not match its length")

    return [
        _validate_pair((cyclic_value, cypher_id))
        for cyclic_value, cypher_id in zip(cyclic_values, cypher_ids)
    ]


def _unfold_lineal(records: object) -> list[tuple[int, int]]:
    if not isinstance(records, list):
        raise ValueError("lineal_records must be a list")
    position = 0

    def read_node() -> list[tuple[int, int]]:
        nonlocal position
        if position >= len(records):
            raise ValueError("lineal fold record ended before its children")
        node = records[position]
        position += 1
        if not isinstance(node, dict):
            raise ValueError("lineal fold records must be objects")

        kind = node.get("kind")
        if kind == "leaf":
            return _decode_leaf(node)
        if kind != "branch":
            raise ValueError(f"unknown fold node kind: {kind!r}")

        child_count = node.get("child_count")
        if (
            isinstance(child_count, bool)
            or not isinstance(child_count, int)
            or not 1 <= child_count <= CHUNK_SIZE
        ):
            raise ValueError("branch child_count must be from one to six")
        children: list[tuple[int, int]] = []
        for _ in range(child_count):
            children.extend(read_node())
        return children

    if not records:
        return []
    pairs = read_node()
    if position != len(records):
        raise ValueError("lineal fold contains records outside the root node")
    return pairs


def unfold_pairs(folded: dict[str, Any]) -> list[tuple[int, int]]:
    """Validate fold metadata and restore the original ordered pair stream."""
    if folded.get("format") != FORMAT_VERSION:
        raise ValueError("unsupported fold format")
    if folded.get("library_version") != LIBRARY_VERSION or folded.get("cyclic") != list(CYCLIC):
        raise ValueError("folded data uses a different library")
    if folded.get("chunk_size") != CHUNK_SIZE:
        raise ValueError("invalid chunk size")

    count = folded.get("input_count")
    num_chunks = folded.get("num_chunks")
    last_len = folded.get("last_len")
    fold_count = folded.get("fold_count")
    for name, value in (
        ("input_count", count),
        ("num_chunks", num_chunks),
        ("last_len", last_len),
        ("fold_count", fold_count),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{name} must be a non-negative integer")

    expected_chunks = (count + CHUNK_SIZE - 1) // CHUNK_SIZE
    expected_last_len = count % CHUNK_SIZE or (CHUNK_SIZE if count else 0)
    expected_fold_count = 0 if count == 0 else 1
    nodes = expected_chunks
    while nodes > 1:
        nodes = (nodes + CHUNK_SIZE - 1) // CHUNK_SIZE
        expected_fold_count += 1
    if num_chunks != expected_chunks or last_len != expected_last_len:
        raise ValueError("chunk metadata does not match input_count")
    if fold_count != expected_fold_count:
        raise ValueError("fold_count does not match input_count")

    if count == 0:
        if folded.get("lineal_records") != []:
            raise ValueError("empty input must have no lineal fold records")
        pairs: list[tuple[int, int]] = []
    else:
        pairs = _unfold_lineal(folded.get("lineal_records"))

    if len(pairs) != count:
        raise ValueError("decoded input count does not match metadata")
    sums = {cyclic_value: 0 for cyclic_value in CYCLIC}
    for cyclic_value, cypher_id in pairs:
        sums[cyclic_value] += cypher_id
    if folded.get("sums") != [sums[value] for value in CYCLIC]:
        raise ValueError("cypher sums do not match the decoded stream")
    return pairs


def encode_text(text: str, library: SymbolLibrary) -> dict[str, Any]:
    """Encode text through the supplied symbol library and fold its paired tracks."""
    pairs = library.encode_text(text)
    return fold_pairs(pairs)


def decode_text(folded: dict[str, Any], library: SymbolLibrary) -> str:
    """Unfold paired tracks and map them back through the supplied library."""
    return library.decode_pairs(unfold_pairs(folded))


def pack_text(text: str, library: SymbolLibrary) -> bytes:
    """Serialize text as PIDs, packed cypher IDs, sums, and its symbol library.

    The format stores only first-round PIDs. Each PID represents six cyclic
    positions; cypher IDs are packed at four bits each. A partial final block
    is padded with the first cyclic value and decoded using the original length.
    """
    pairs = library.encode_text(text)
    count = len(pairs)
    if count > 0xFFFFFFFF:
        raise ValueError("text is too long for the binary format")

    header = bytearray(BINARY_MAGIC)
    header.extend(struct.pack(">I", count))
    for symbol in library.symbols:
        codepoint = ord(symbol)
        if 0xD800 <= codepoint <= 0xDFFF:
            raise ValueError("symbol library cannot contain surrogate code points")
        header.extend(struct.pack(">I", codepoint))

    sums = {value: 0 for value in CYCLIC}
    for cyclic_value, cypher_id in pairs:
        sums[cyclic_value] += cypher_id
    for value in CYCLIC:
        header.extend(struct.pack(">Q", sums[value]))

    for offset in range(0, count, CHUNK_SIZE):
        block = [pair[0] for pair in pairs[offset:offset + CHUNK_SIZE]]
        block.extend([CYCLIC[0]] * (CHUNK_SIZE - len(block)))
        header.extend(struct.pack(">H", encode_pattern(block)))

    for offset in range(0, count, 2):
        high = pairs[offset][1]
        low = pairs[offset + 1][1] if offset + 1 < count else 0
        header.append((high << 4) | low)

    header.extend(struct.pack(">I", zlib.crc32(header)))
    return bytes(header)


def unpack_text(payload: bytes) -> str:
    """Validate and restore a text archive produced by :func:`pack_text`."""
    minimum_size = 4 + 4 + 4 * 90 + 8 * 6 + CHECKSUM_SIZE
    if len(payload) < minimum_size:
        raise ValueError("binary archive is truncated")
    if payload[:4] != BINARY_MAGIC:
        raise ValueError("unsupported binary archive format")
    expected_crc = struct.unpack(">I", payload[-CHECKSUM_SIZE:])[0]
    actual_crc = zlib.crc32(payload[:-CHECKSUM_SIZE])
    if expected_crc != actual_crc:
        raise ValueError("binary archive checksum mismatch")

    count = struct.unpack(">I", payload[4:8])[0]
    offset = 8
    codepoints = [
        struct.unpack(">I", payload[position:position + 4])[0]
        for position in range(offset, offset + 4 * 90, 4)
    ]
    offset += 4 * 90
    try:
        symbols = tuple(chr(codepoint) for codepoint in codepoints)
        library = SymbolLibrary(symbols)
    except (ValueError, OverflowError) as error:
        raise ValueError("archive contains an invalid symbol library") from error

    expected_sums = [
        struct.unpack(">Q", payload[position:position + 8])[0]
        for position in range(offset, offset + 8 * 6, 8)
    ]
    offset += 8 * 6

    chunk_count = (count + CHUNK_SIZE - 1) // CHUNK_SIZE
    pid_end = offset + chunk_count * 2
    cypher_end = pid_end + (count + 1) // 2
    if cypher_end + CHECKSUM_SIZE != len(payload):
        raise ValueError("binary archive length does not match its input count")

    cyclic_values: list[int] = []
    for position in range(offset, pid_end, 2):
        pid = struct.unpack(">H", payload[position:position + 2])[0]
        block = decode_pattern(pid)
        chunk_index = (position - offset) // 2
        block_length = min(CHUNK_SIZE, count - chunk_index * CHUNK_SIZE)
        cyclic_values.extend(block[:block_length])

    cypher_ids: list[int] = []
    for value in payload[pid_end:cypher_end]:
        cypher_ids.extend((value >> 4, value & 0x0F))
    if count % 2 and cypher_ids[-1] != 0:
        raise ValueError("unused final cypher nibble must be zero")
    cypher_ids = cypher_ids[:count]
    if any(not 1 <= cypher_id <= 15 for cypher_id in cypher_ids):
        raise ValueError("archive contains an invalid cypher ID")

    pairs = list(zip(cyclic_values, cypher_ids))
    actual_sums = {value: 0 for value in CYCLIC}
    for cyclic_value, cypher_id in pairs:
        actual_sums[cyclic_value] += cypher_id
    if [actual_sums[value] for value in CYCLIC] != expected_sums:
        raise ValueError("archive sums do not match the decoded tracks")
    return library.decode_pairs(pairs)
