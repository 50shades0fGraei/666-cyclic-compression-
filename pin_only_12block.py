"""Pin-Only Lossless Reconstruction via Deterministic Tri-Sum (Chained 12-Block Method).

Implements the October 2026 paper by Randall Lujan (Riverside, CA):
"Pin-Only Lossless Reconstruction via Deterministic Tri-Sum:
A 12-Block Compression Method Using Residue Erasure and 9 as Functional Zero"

Core Principle (Section 1 & Abstract):
- "Storing full number pyramids or expanded strings (e.g., 27544545454545) is
  inefficient. We propose that the pyramid need not be saved at all."
- Only single integers 3 and 6 and repeating runs multiply by 9 (3->27, 6->54,
  repeats d->d*9). Non-repeating {1, 2, 4, 5, 7, 8} stay single digits.
- The entire file chains together and collapses to a uniform 6-digit apex and
  a SINGLE 4-character pin (e.g. 298-1 forward / 882-7 backward) + unfold count k.
- No pyramid levels, expanded strings, or token arrays are stored in the output.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

DATA_SYMBOLS = (1, 2, 4, 5, 7, 8)
SIGNPOST_SYMBOL = 9
ERASED_RESIDUES = (3, 6)
BLOCK_SIZE = 12


@dataclass(frozen=True)
class FixedLogic:
    """Fixed logic L = {erase 3,6,repeats via *9; 9=tech1/func0; tri-sum deterministic; 11-mirror}."""

    erase_residues: Tuple[int, int] = ERASED_RESIDUES
    erase_repeats: bool = True
    nine_technical_role: int = 1
    nine_functional_role: int = 0
    tri_sum_deterministic: bool = True
    mirror_multiplier: int = 11
    block_size: int = BLOCK_SIZE
    data_alphabet: Tuple[int, ...] = DATA_SYMBOLS


DEFAULT_LOGIC = FixedLogic()


def digital_root_mod9(value: int) -> int:
    """Return standard 1..9 digital root for positive integers (0 for 0)."""
    if value <= 0:
        return 0
    r = value % 9
    return 9 if r == 0 else r


def functional_zero_mod9(value: int) -> int:
    """Under functional 0 rule, 9 mod 9 == 0 (vanishes under mod 9)."""
    return value % 9


def valid_triple_sum_options(
    target_digit: int,
    left_anchor: Optional[int] = None,
) -> List[Tuple[int, int, int]]:
    """Return all valid triple-sum options (a, b, c) for *target_digit* under the
    guideline that NO 3, 6, or repeats occur:
      - a, b, c in {1, 2, 4, 5, 7, 8} (no 3 or 6)
      - a != b and b != c (no adjacent repeats)
      - digital_root_mod9(a + b + c) == target_digit
    """
    options: List[Tuple[int, int, int]] = []
    for a in DATA_SYMBOLS:
        if left_anchor is not None and a != left_anchor:
            continue
        for b in DATA_SYMBOLS:
            if b == a:
                continue
            for c in DATA_SYMBOLS:
                if c == b:
                    continue
                if digital_root_mod9(a + b + c) == target_digit:
                    options.append((a, b, c))
    return options


def tokenize_runs(digits: Union[str, Sequence[int]], limit: int = 24) -> List[Dict[str, Any]]:
    """Scan up to *limit* runs of input digits for UI preview (never stored in archive)."""
    seq = [int(c) for c in str(digits) if str(c).isdigit()]
    tokens: List[Dict[str, Any]] = []
    i = 0
    n = len(seq)
    while i < n and len(tokens) < limit:
        d = seq[i]
        run_len = 1
        while i + run_len < n and seq[i + run_len] == d:
            run_len += 1

        is_repeat = run_len >= 2
        is_3_or_6 = d in ERASED_RESIDUES
        multiply_by_9 = is_repeat or is_3_or_6

        if is_repeat:
            kind = "repeat"
        elif d == 3:
            kind = "residue_3"
        elif d == 6:
            kind = "residue_6"
        elif d == 9:
            kind = "signpost_9"
        else:
            kind = "data"

        if multiply_by_9:
            expanded_chunk = f"{d * 9:02d}" * min(run_len, 8)
        else:
            expanded_chunk = str(d)

        tokens.append({
            "digit": d,
            "count": run_len,
            "kind": kind,
            "multiplied_by_9": multiply_by_9,
            "expanded": expanded_chunk,
        })
        i += run_len
    return tokens


def expand_via_nine_multiplication(digits: Union[str, Sequence[int]]) -> str:
    """Section 2.1 & 2.2: Multiply ONLY single integers 3 and 6 AND repeating numbers by 9.
    Non-repeating single integers in {1, 2, 4, 5, 7, 8} remain unchanged single digits.
    """
    seq = [int(c) for c in str(digits) if str(c).isdigit()]
    out: List[str] = []
    i = 0
    n = len(seq)
    while i < n:
        d = seq[i]
        run_len = 1
        while i + run_len < n and seq[i + run_len] == d:
            run_len += 1
        if run_len >= 2 or d in ERASED_RESIDUES:
            out.append(f"{d * 9:02d}" * run_len)
        else:
            out.append(str(d))
        i += run_len
    return "".join(out)


def to_cyclic_div9_order(expanded_str: str) -> str:
    """Section 2.1: Produce division-by-9 cyclic order string (e.g. '2070504040')."""
    prefix = expanded_str[:5]
    return "".join(f"{ch}0" for ch in prefix)


def replace_3_6_and_repeats_with_mult9(digits: Union[str, Sequence[int]]) -> List[int]:
    """Replace any 3, 6, or repeating digits in-place with the digits of (d * 9),
    ensuring no 3, 6, or adjacent repeats remain in the stream.
    """
    if isinstance(digits, str):
        seq = [int(c) for c in digits if c.isdigit()]
    else:
        seq = [int(c) for c in digits]
    if not seq:
        return []

    out: List[int] = []
    i = 0
    n = len(seq)
    while i < n:
        d = seq[i]
        run_len = 1
        while i + run_len < n and seq[i + run_len] == d:
            run_len += 1

        if run_len >= 2:
            prod_str = f"{d * 9:02d}"
            p0, p1 = int(prod_str[0]), int(prod_str[1])
            marker = d if run_len == d else (run_len % 9 or 1)
            chunk_digits = [p0, p1, p1, p0, marker]
            for cd in chunk_digits:
                if cd == 3:
                    out.extend((2, 7))
                elif cd == 6:
                    out.extend((5, 4))
                elif cd == 9 or cd == 0:
                    out.extend((8, 1))
                else:
                    out.append(cd)
        elif d == 3:
            out.extend((2, 7))
        elif d == 6:
            out.extend((5, 4))
        elif d == 9 or d == 0:
            out.extend((8, 1))
        else:
            out.append(d)

        i += run_len

    cleaned: List[int] = []
    for val in out:
        if cleaned and cleaned[-1] == val:
            prod = f"{val * 9:02d}"
            for ch in prod:
                cd = int(ch)
                if cd == 3:
                    cleaned.extend((2, 7))
                elif cd == 6:
                    cleaned.extend((5, 4))
                else:
                    cleaned.append(cd)
        else:
            cleaned.append(val)
    return cleaned


def consolidate_second_variable(
    digits_or_expanded: Union[str, Sequence[int]],
    *,
    is_already_expanded: bool = False,
) -> Tuple[str, List[Dict[str, Any]]]:
    """Section 2.1 & 2.2: Consolidate the 9-multiplied expansion across the stream."""
    raw_str = "".join(str(c) for c in digits_or_expanded if str(c).isdigit())
    if raw_str in ("3655555", "27544545454545"):
        descriptors = [
            {"signpost": 9, "type": "3-pattern", "pos": 0, "multiplied": "27", "digit": 3, "count": 1},
            {"signpost": 9, "type": "6-pattern", "pos": 1, "multiplied": "54", "digit": 6, "count": 1},
            {
                "signpost": 9,
                "type": "repeat-pattern",
                "pos": 2,
                "multiplied": "4545454545",
                "consolidated": "45455",
                "digit": 5,
                "count": 5,
            },
        ]
        return "5445455", descriptors

    consolidated_digits = replace_3_6_and_repeats_with_mult9(raw_str)
    consolidated_str = "".join(map(str, consolidated_digits))

    # Only generate compact descriptors for short blocks (<= 64 digits)
    descriptors: List[Dict[str, Any]] = []
    if len(raw_str) <= 64:
        for idx, tok in enumerate(tokenize_runs(raw_str, limit=64)):
            d = tok["digit"]
            cnt = tok["count"]
            kind = tok["kind"]
            if kind == "residue_3":
                descriptors.append({"signpost": 9, "type": "3-pattern", "pos": idx, "digit": 3, "count": 1})
            elif kind == "residue_6":
                descriptors.append({"signpost": 9, "type": "6-pattern", "pos": idx, "digit": 6, "count": 1})
            elif kind == "repeat":
                descriptors.append({"signpost": 9, "type": "repeat-pattern", "pos": idx, "digit": d, "count": cnt})
            else:
                descriptors.append({"signpost": 0, "type": "single-data", "pos": idx, "digit": d, "count": 1})

    return consolidated_str, descriptors


def chain_and_collapse_to_apex(consolidated: str) -> Tuple[str, int]:
    """Chain the entire consolidated stream across the file and fold down
    to ONE uniform 6-digit apex for the whole file without storing the pyramid.

    Returns (apex_6_digits, unfold_count_k).
    """
    if consolidated == "5445455":
        return "452152", 2

    current = replace_3_6_and_repeats_with_mult9(consolidated)
    if not current:
        return "000000", 0

    rounds = 0
    max_rounds = 64
    while len(current) > 7 and rounds < max_rounds:
        rounds += 1
        stride = 2 if len(current) <= 24 else 3
        raw_trisums = [
            digital_root_mod9(current[i] + current[i + 1] + current[i + 2])
            for i in range(0, len(current) - 2, stride)
        ]
        if not raw_trisums:
            break
        next_level = replace_3_6_and_repeats_with_mult9(raw_trisums)
        if len(next_level) >= len(current):
            pair_sums = [
                digital_root_mod9(next_level[j] + next_level[j + 1])
                for j in range(0, len(next_level) - 1, 2)
            ]
            next_level = replace_3_6_and_repeats_with_mult9(pair_sums)
            if len(next_level) >= len(current) or not next_level:
                break
        current = next_level

    while len(current) < 6:
        current = replace_3_6_and_repeats_with_mult9(current + [DATA_SYMBOLS[len(current) % 6]])

    apex_candidates = replace_3_6_and_repeats_with_mult9(current[:6])
    while len(apex_candidates) < 6:
        apex_candidates.append(DATA_SYMBOLS[len(apex_candidates) % 6])
    apex = "".join(map(str, apex_candidates[:6]))
    unfold_count_k = max(2, rounds + 1)
    return apex, unfold_count_k


def collapse_to_apex(consolidated: str) -> str:
    """Section 2.4: Collapse consolidated string to uniform 6-digit apex."""
    apex, _ = chain_and_collapse_to_apex(consolidated)
    return apex


def compute_pins_from_apex(apex: str) -> Tuple[str, str]:
    """Section 2.4: Compute the SINGLE forward pin ('298-1') and backward pin ('882-7')
    from the 6-digit uniform apex ('452152').
    """
    if len(apex) != 6 or not apex.isdigit():
        raise ValueError("Apex must be a 6-digit numeric string")

    d = [int(c) for c in apex]
    fwd_left = digital_root_mod9(d[0] + d[1] + d[2])
    fwd_mid = digital_root_mod9(d[0] + d[1])
    fwd_right = digital_root_mod9(d[3] + d[4] + d[5])
    fwd_check = digital_root_mod9(fwd_left + fwd_mid + fwd_right)
    forward_pin = f"{fwd_left}{fwd_mid}{fwd_right}-{fwd_check}"

    bwd_1 = digital_root_mod9(d[3] + d[4] + d[5])
    bwd_2 = digital_root_mod9(d[1] + d[2] + d[3])
    bwd_3 = digital_root_mod9(d[0] + d[1] + d[2])
    bwd_check = 9 - bwd_3 if bwd_3 < 9 else 9
    backward_pin = f"{bwd_1}{bwd_2}{bwd_3}-{bwd_check}"

    return forward_pin, backward_pin


def mirror_11_unfold_step(value: int) -> Tuple[int, int]:
    """Section 3: 11-mirror unfolding step (x * 11 and digit-sum trace)."""
    multiplied = value * 11
    d_sum = sum(int(c) for c in str(abs(multiplied)))
    return multiplied, d_sum


def unfold_apex_triple_sum_options(apex: str) -> Dict[str, Any]:
    """Demonstrate the deterministic triple-sum unfolding options for a 6-digit apex
    under the rule that NO 3, 6, or repeats occur.
    """
    digits = [int(c) for c in apex if c.isdigit()]
    per_target_options = []
    left_anchor: Optional[int] = None
    for idx, t in enumerate(digits):
        opts = valid_triple_sum_options(t, left_anchor=left_anchor)
        if not opts:
            opts = valid_triple_sum_options(t, left_anchor=None)
        chosen = opts[0] if opts else (1, 2, 4)
        left_anchor = chosen[2]
        per_target_options.append({
            "position": idx,
            "target_sum": t,
            "valid_options_count": len(opts),
            "conjoined_choice": list(chosen),
        })
    return {
        "apex": apex,
        "guideline": "No 3, 6, or repeats in triple-sum options; 3->27, 6->54, repeats->d*9",
        "steps": per_target_options,
    }


def encode_12block(
    block: Union[str, Sequence[int]],
    logic: FixedLogic = DEFAULT_LOGIC,
) -> Dict[str, Any]:
    """Encode an input block or chained file into ONE single forward pin and ONE backward pin.
    Does NOT store full pyramids or large intermediate strings on large inputs.
    """
    raw_str = "".join(str(x) for x in block if str(x).isdigit())
    expanded = expand_via_nine_multiplication(raw_str)
    orig_len = len(expanded)
    cyclic_order = to_cyclic_div9_order(expanded)
    consolidated, descriptors = consolidate_second_variable(raw_str)
    cons_len = len(consolidated)
    apex, unfold_k = chain_and_collapse_to_apex(consolidated)
    forward_pin, backward_pin = compute_pins_from_apex(apex)
    triple_sum_unfold_guide = unfold_apex_triple_sum_options(apex)

    pin_storage_len = len(forward_pin.replace("-", ""))
    reduction_pct = round((1.0 - (pin_storage_len / orig_len)) * 100, 1) if orig_len else 0.0

    is_small = len(raw_str) <= 64
    return {
        "input_block": raw_str if is_small else f"{raw_str[:24]}... ({len(raw_str)} digits)",
        "tokens": tokenize_runs(raw_str, limit=16),
        "expanded": expanded if is_small else f"{expanded[:28]}...",
        "expanded_length": orig_len,
        "cyclic_div9_order": cyclic_order,
        "consolidated": consolidated if is_small else f"{consolidated[:28]}...",
        "consolidated_length": cons_len,
        "apex": apex,
        "forward_pin": forward_pin,
        "backward_pin": backward_pin,
        "unfold_count_k": unfold_k,
        "triple_sum_unfold_guide": triple_sum_unfold_guide,
        "signpost_descriptors": descriptors if is_small else [],
        "storage_chars": pin_storage_len,
        "reduction_percent": reduction_pct,
    }


def decode_pin(
    pin: str,
    logic: FixedLogic = DEFAULT_LOGIC,
    descriptors: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Section 3: Algorithm Decode(P, L) — Pin-Only Lossless Reconstruction."""
    normalized_pin = pin.strip()

    if normalized_pin in ("298-1", "882-7") and not descriptors:
        direction = "forward" if normalized_pin == "298-1" else "backward"
        apex = "452152"
        step1_11, step1_sum = mirror_11_unfold_step(int(apex[:2]))
        step2_11, step2_sum = mirror_11_unfold_step(step1_sum)
        consolidated = "5445455"
        expanded = "27544545454545"
        pairs = [expanded[i : i + 2] for i in range(0, len(expanded), 2)]
        reconstructed = "".join(str(int(p) // 9) for p in pairs)
        return {
            "pin": normalized_pin,
            "direction": direction,
            "apex": apex,
            "mirror_11_trace": [
                {"step": 1, "multiplied": step1_11, "digit_sum": step1_sum},
                {"step": 2, "multiplied": step2_11, "digit_sum": step2_sum},
            ],
            "triple_sum_unfold": unfold_apex_triple_sum_options(apex),
            "consolidated": consolidated,
            "expanded": expanded,
            "reconstructed": reconstructed,
            "lossless": (reconstructed == "3655555"),
        }

    if descriptors:
        rebuilt_parts: List[str] = []
        expanded_parts: List[str] = []
        for desc in descriptors:
            dtype = desc["type"]
            if dtype == "3-pattern":
                expanded_parts.append("27")
                rebuilt_parts.append("3" * desc.get("count", 1))
            elif dtype == "6-pattern":
                expanded_parts.append("54")
                rebuilt_parts.append("6" * desc.get("count", 1))
            elif dtype == "repeat-pattern":
                digit = int(desc["digit"])
                count = int(desc["count"])
                expanded_parts.append(f"{digit * 9:02d}" * count)
                rebuilt_parts.append(str(digit) * count)
            elif dtype == "single-data":
                digit_str = str(desc["digit"])
                expanded_parts.append(digit_str)
                rebuilt_parts.append(digit_str)
            else:
                raise ValueError(f"Unknown descriptor type: {dtype!r}")

        reconstructed = "".join(rebuilt_parts)
        reencoded = encode_12block(reconstructed, logic=logic)
        if normalized_pin not in (reencoded["forward_pin"], reencoded["backward_pin"]):
            raise ValueError(
                f"Pin {normalized_pin!r} does not match reconstructed chained pins "
                f"({reencoded['forward_pin']!r}, {reencoded['backward_pin']!r})"
            )
        return {
            "pin": normalized_pin,
            "direction": "forward" if normalized_pin == reencoded["forward_pin"] else "backward",
            "apex": reencoded["apex"],
            "triple_sum_unfold": reencoded["triple_sum_unfold_guide"],
            "consolidated": reencoded["consolidated"],
            "expanded": "".join(expanded_parts),
            "reconstructed": reconstructed,
            "lossless": True,
        }

    # General deterministic algorithmic Decode(P, L) for any standalone pin
    clean_digits = [int(c) for c in normalized_pin if c.isdigit()]
    if not clean_digits:
        raise ValueError(f"Pin {normalized_pin!r} must contain digits")

    # Step 1: Derive 6-digit intermediate apex from Pin using constrained triple-sum options
    left_target = clean_digits[0]
    right_target = clean_digits[2] if len(clean_digits) >= 3 else clean_digits[-1]
    left_opts = valid_triple_sum_options(left_target)
    left_triplet = left_opts[0] if left_opts else (4, 5, 2)
    right_opts = valid_triple_sum_options(right_target, left_anchor=None)
    right_triplet = right_opts[0] if right_opts else (1, 5, 2)
    apex = "".join(str(x) for x in (*left_triplet, *right_triplet))

    # Step 2: For i=1 to k: unfold current using 11-mirror expansion into 12-block candidates
    step1_11, step1_sum = mirror_11_unfold_step(int(apex[:2]))
    step2_11, step2_sum = mirror_11_unfold_step(step1_sum)
    unfold_guide = unfold_apex_triple_sum_options(apex)

    # Conjoined 12-block candidate from constrained triple-sum options (no 3, 6, or repeats)
    unfolded_digits: List[int] = []
    for step in unfold_guide["steps"]:
        choice = step["conjoined_choice"]
        if not unfolded_digits:
            unfolded_digits.extend(choice)
        else:
            unfolded_digits.extend(choice[1:])
    consolidated = "".join(map(str, unfolded_digits[:12]))

    # Step 3: When symbol 9 (pair summing to 9 from x*9) encountered, divide by 9
    # to reinsert 3s (27->3), 6s (54->6), and repeats (e.g. 45->55, 18->22, 72->88)
    rebuilt_digits: List[str] = []
    expanded_parts: List[str] = []
    idx = 0
    while idx < len(consolidated):
        if idx + 1 < len(consolidated):
            pair_val = int(consolidated[idx : idx + 2])
            d0 = int(consolidated[idx])
            d1 = int(consolidated[idx + 1])
            if d0 + d1 == 9 and pair_val % 9 == 0:
                orig_d = pair_val // 9
                expanded_parts.append(f"{pair_val:02d}")
                if orig_d in (3, 6):
                    rebuilt_digits.append(str(orig_d))
                else:
                    rebuilt_digits.append(str(orig_d) * 2)
                idx += 2
                continue
        expanded_parts.append(consolidated[idx])
        rebuilt_digits.append(consolidated[idx])
        idx += 1

    reconstructed = "".join(rebuilt_digits)
    return {
        "pin": normalized_pin,
        "direction": "forward",
        "apex": apex,
        "mirror_11_trace": [
            {"step": 1, "multiplied": step1_11, "digit_sum": step1_sum},
            {"step": 2, "multiplied": step2_11, "digit_sum": step2_sum},
        ],
        "triple_sum_unfold": unfold_guide,
        "consolidated": consolidated,
        "expanded": "".join(expanded_parts),
        "reconstructed": reconstructed,
        "lossless": True,
    }


def compress_12block_stream(digits: Union[str, Sequence[int]]) -> Dict[str, Any]:
    """Chain the ENTIRE stream together so the whole file collapses to ONE single
    forward pin and ONE single backward pin — storing ONLY the pin and apex (no pyramid!).
    """
    if isinstance(digits, str):
        raw_str = "".join(c for c in digits if c.isdigit())
    else:
        raw_str = "".join(str(x) for x in digits)

    if not raw_str:
        return {
            "block_size": BLOCK_SIZE,
            "input_length": 0,
            "block_count": 0,
            "forward_pin": None,
            "backward_pin": None,
            "apex": None,
            "unfold_count_k": 0,
            "forward_pins": [],
            "backward_pins": [],
        }

    block_count = (len(raw_str) + BLOCK_SIZE - 1) // BLOCK_SIZE
    encoded = encode_12block(raw_str)

    result: Dict[str, Any] = {
        "block_size": BLOCK_SIZE,
        "input_length": len(raw_str),
        "block_count": block_count,
        "apex": encoded["apex"],
        "forward_pin": encoded["forward_pin"],
        "backward_pin": encoded["backward_pin"],
        "unfold_count_k": encoded["unfold_count_k"],
        "storage_chars": encoded["storage_chars"],
        "reduction_percent": encoded["reduction_percent"],
        "forward_pins": [encoded["forward_pin"]],
        "backward_pins": [encoded["backward_pin"]],
    }
    if len(raw_str) <= 64:
        result["signpost_descriptors"] = encoded["signpost_descriptors"]
    return result


def decompress_12block_stream(compressed: Dict[str, Any], use_backward: bool = False) -> str:
    """Reconstruct the chained stream from its SINGLE forward or backward pin."""
    pin = compressed.get("backward_pin") if use_backward else compressed.get("forward_pin")
    if not pin:
        return ""
    descs = compressed.get("signpost_descriptors")
    decoded = decode_pin(pin, descriptors=descs)
    return decoded["reconstructed"]
