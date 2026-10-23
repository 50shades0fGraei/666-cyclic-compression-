"""Repetition-mark consolidation format.

Copyright (c) 2026 Randall Lujan. All rights reserved.
Patent pending for the cyclic compression and rotor-folding system described herein.

A digit stream is read in chunks (default 6). Every run of two or more identical
digits is collapsed to a single digit in the body, and one mark records the run:

    C.D        run of exactly 2 of digit D starting in chunk C
    C.D.N      run of N (3 or more) of digit D starting in chunk C
    C(K).D...  same, when chunk C holds more than one D; K says which D it is

Chunks are numbered from 1 by position in the ORIGINAL stream. K counts the
appearances of D in that chunk from the left, where a run of repeated Ds counts
as one appearance, up to and including the run being marked. Runs may continue
past the end of their chunk; the mark always uses the chunk where the run starts.

Example: chunk 5 = 4 1 4 4 4 2  ->  the run starts at the 2nd 4 in chunk 5 and
is 3 long, so the mark is 5(2).4.3.

File layout (plain text, three lines):

    RPM1 chunk=6 length=<original digit count>
    <body: original digits with each run collapsed to one digit>
    <marks separated by spaces, or "-" when there are none>
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

FORMAT_TAG = "RPM1"
DEFAULT_CHUNK = 6
_MARK_RE = re.compile(r"^(\d+)(?:\((\d+)\))?\.(\d)(?:\.(\d+))?$")


@dataclass(frozen=True)
class RunMark:
    chunk: int              # 1-based chunk where the run starts
    which: Optional[int]    # K: which D in the chunk (None when the chunk holds one D)
    digit: int
    count: int              # total run length, >= 2

    def to_text(self) -> str:
        text = str(self.chunk)
        if self.which is not None:
            text += f"({self.which})"
        text += f".{self.digit}"
        if self.count >= 3:
            text += f".{self.count}"
        return text

    @classmethod
    def from_text(cls, text: str) -> "RunMark":
        match = _MARK_RE.match(text)
        if not match:
            raise ValueError(f"malformed mark: {text!r}")
        chunk, which, digit, count = match.groups()
        count_value = int(count) if count else 2
        if count_value < 2:
            raise ValueError(f"run count must be at least 2: {text!r}")
        return cls(int(chunk), int(which) if which else None, int(digit), count_value)


def _parse_digits(digits: Sequence[int] | str) -> List[int]:
    if isinstance(digits, str):
        cleaned = "".join(digits.split())
        if not cleaned.isdigit() and cleaned:
            raise ValueError("input must contain only digits 0-9 (whitespace is ignored)")
        return [int(ch) for ch in cleaned]
    values = list(digits)
    for value in values:
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 9:
            raise ValueError(f"each value must be a single digit 0-9: {value!r}")
    return values


def _appearances(values: Sequence[int], digit: int, start: int, stop: int) -> int:
    """Count appearances of digit in values[start:stop]; a run of repeats counts once."""
    total = 0
    for p in range(start, min(stop, len(values))):
        if values[p] == digit and (p == start or values[p - 1] != digit):
            total += 1
    return total


def encode(digits: Sequence[int] | str, chunk_size: int = DEFAULT_CHUNK) -> Tuple[List[int], List[RunMark]]:
    """Collapse runs and return (body, marks)."""
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    seq = _parse_digits(digits)
    body: List[int] = []
    marks: List[RunMark] = []

    i = 0
    while i < len(seq):
        digit = seq[i]
        j = i
        while j < len(seq) and seq[j] == digit:
            j += 1
        run_length = j - i
        body.append(digit)

        if run_length >= 2:
            chunk_index = i // chunk_size
            start = chunk_index * chunk_size
            which = _appearances(seq, digit, start, i + 1)
            several = _appearances(seq, digit, start, start + chunk_size) > 1
            marks.append(
                RunMark(
                    chunk=chunk_index + 1,
                    which=which if several else None,
                    digit=digit,
                    count=run_length,
                )
            )
        i = j

    return body, marks


def decode(body: Sequence[int], marks: Sequence[RunMark], chunk_size: int = DEFAULT_CHUNK) -> List[int]:
    """Rebuild the original stream from the body and the run marks."""
    lookup: Dict[Tuple[int, int, int], int] = {}
    for mark in marks:
        key = (mark.chunk, mark.which or 1, mark.digit)
        if key in lookup:
            raise ValueError(f"duplicate mark: {mark.to_text()}")
        lookup[key] = mark.count

    out: List[int] = []
    for digit in body:
        position = len(out)
        chunk_index = position // chunk_size
        start = chunk_index * chunk_size
        which = _appearances(out + [digit], digit, start, position + 1)
        out.extend([digit] * lookup.pop((chunk_index + 1, which, digit), 1))

    if lookup:
        unused = ", ".join(f"{c}({k}).{d}" for c, k, d in lookup)
        raise ValueError(f"marks did not match the body: {unused}")
    return out


def to_file_text(digits: Sequence[int] | str, chunk_size: int = DEFAULT_CHUNK) -> str:
    seq = _parse_digits(digits)
    body, marks = encode(seq, chunk_size)
    mark_line = " ".join(mark.to_text() for mark in marks) or "-"
    return (
        f"{FORMAT_TAG} chunk={chunk_size} length={len(seq)}\n"
        f"{''.join(map(str, body))}\n"
        f"{mark_line}\n"
    )


def from_file_text(text: str) -> List[int]:
    lines = text.splitlines()
    if len(lines) < 3:
        raise ValueError("expected 3 lines: header, body, marks")
    header = lines[0].split()
    if not header or header[0] != FORMAT_TAG:
        raise ValueError(f"not an {FORMAT_TAG} file")
    fields = dict(part.split("=", 1) for part in header[1:])
    chunk_size = int(fields["chunk"])
    length = int(fields["length"])

    body = _parse_digits(lines[1])
    marks = [] if lines[2].strip() == "-" else [RunMark.from_text(t) for t in lines[2].split()]
    restored = decode(body, marks, chunk_size)
    if len(restored) != length:
        raise ValueError(f"restored {len(restored)} digits, header says {length}")
    return restored


def _main(argv: List[str]) -> int:
    if len(argv) != 4 or argv[1] not in ("encode", "decode"):
        print("usage: python repetition_marks.py encode <digits.txt> <out.rpm>")
        print("       python repetition_marks.py decode <in.rpm> <digits.txt>")
        return 2
    mode, source, target = argv[1], Path(argv[2]), Path(argv[3])
    text = source.read_text(encoding="utf-8")
    if mode == "encode":
        output = to_file_text(text)
        target.write_text(output, encoding="utf-8")
        original = len("".join(text.split()))
        print(f"{original} digits -> {len(output.encode('utf-8'))} bytes written to {target}")
    else:
        digits = "".join(map(str, from_file_text(text)))
        target.write_text(digits + "\n", encoding="utf-8")
        print(f"restored {len(digits)} digits to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
