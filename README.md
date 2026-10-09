# Randall's Cyclic Compression

Copyright (c) 2026 Randall Lujan. All rights reserved.
Patent pending for the cyclic compression and rotor-folding system described herein.

Randall's Cyclic Compression is a deterministic rotor-based folding system built around the repeating 142857 cycle, a symbol cipher map, and a triplet reduction engine.

## Architecture overview

### 1. Rotor layer
The project uses the canonical 6-slot cycle:

[1, 4, 2, 8, 5, 7]

This is the design anchor for the full system and is exposed through the public rotor metadata in the compressor output. It is not appended to the folded result.

### 2. Input normalization
Text is normalized to lowercase and mapped in original character order. The keyboard sequence starts with the documented mapping `qwerty → 1, 4, 2, 8, 5, 7`, repeating the canonical cycle for remaining letters.

### 3. Fold engine
The compressor collapses adjacent triplets, sums their values, and reduces them using a deterministic single-digit collapse function. It stops at whichever fold level is closer to six values; it does not pad the result with synthetic cycle values. Values that resolve to 3, 6, or 9 are verified with multiplication dualities: 3×1=3, 3×2=6, and 3+6=9. The ordered cipher-number stream is retained as the numeric source, and each compact fold-log entry records input/output lengths and 369 check counts. No per-fold input or output copies are stored.

### 4. Reconstruction layer
`unfold_numeric(ordered_values, fold_log, folded_values)` recomputes the folds from the ordered cipher-number stream, validates the 369 duality counts at every level, and confirms that the final values match. This verifies the ordered numeric stream; it does not by itself restore original text characters.

## Public entry points

- `cycle_compressor.py` contains the core engine and rotor metadata.
- `pattern_library.py` contains the fixed 46,656-entry pattern mapping and one
  exact six-cypher-to-one-PID fold/unfold layer. PIDs use lexicographic base-6
  numbering over `[1, 4, 2, 8, 5, 7]`. Its `evaluate_rotor_rows()` helper
  records one-based steps and cumulative sums where each rotor row reduces to
  a 3/6/9 anchor using the existing `collapse` rule. `count_alignments()` keeps
  142857 fixed and counts each `(cyclic cypher, multiplier)` occurrence in the
  matching slot of the multiplier row, without retaining the source stream.
  `count_cyclic_stream_alignments()` assigns multipliers 1 through 6 repeatedly,
  advancing once per cypher occurrence, then returns aggregate slot totals.
  `place_cypher_order()` accepts `(cyclic value, cypher ID)` pairs and appends
  each cypher ID to the matching multiplier/slot sequence. `fold_pair_stream()`
  and `unfold_pair_stream()` recursively encode and restore an ordered pair
  stream, including partial final groups.
- `analyze_cyclic_stream()` preserves source order in six-pair chunks, applies
  each multiplier rotation to each complete chunk, and records the six circular
  overlapping tri-sum totals, digit-sum results, and ordered 3/6/9 checkpoints.
  An incomplete final chunk is retained unchanged. This is a derived analysis
  trace, not a compact archive; the ordered pair chunks are its source evidence.
- `randall_cyclic_compressor.py` is the public branded entry point for the system.
- `New-logic-and-build.py` remains as a compatibility runner.
- `app_server.py` and `mvp-trifold-app-2026-10-06.html` provide a local browser workbench backed by the Python compressor.

## Usage

```bash
python randall_cyclic_compressor.py
```

This prints the project identity, rotor matrix, and the folded pin for the sample string `hello world`.

### Local workbench

Start the local app with:

```bash
python app_server.py
```

Then open <http://127.0.0.1:8765>. Paste text or open a `.txt` file to inspect
the final pin, fold trace, 369 checks, and serialized size figures. The JSON
export retains both the source text and full verification state; the pin alone
is not a lossless compressed archive.

### Deploy to Render

The repository includes a `render.yaml` Blueprint for the browser workbench.
In the Render Dashboard, choose **New > Blueprint**, connect this repository,
and apply the Blueprint. Render will build and start the web service; when the
deployment finishes, open its `onrender.com` URL.

## License

This project is published under a dual-license model:

- Open-source use: [LICENSE](LICENSE) (MIT)
- Commercial use: [COMMERCIAL-LICENSE.md](COMMERCIAL-LICENSE.md)

Commercial deployment, resale, SaaS use, or product integration requires a separate commercial license from the copyright holder. The MIT license covers non-commercial and open-source use only.

The pattern-library module is intentionally separate from the existing triplet
prototype. Its cypher-only fold rejects incomplete six-cypher chunks rather than
inventing padding. The pair-stream fold is lossless and records the original
length, but it is a reversible mixed-radix encoding—not the 369 overlap/sum
algorithm and not a demonstrated size compression. Its `root_code_hex` is an
unbounded code, not a PID in the fixed 46,656-pattern library. The row evaluation
records anchor hits but does not infer source-symbol placement. Six-sum
verification, the universal 90-symbol/15-cypher mapping, and the streaming/batch
formats remain unimplemented until their rules are confirmed.
The alignment counter requires explicit `(cyclic cypher, multiplier)` pairs;
the stream counter provides the confirmed sequential multiplier schedule. These
aggregate counts do not preserve source order by themselves.
Cypher placement preserves order within each multiplier/slot, but not the
interleaving between slots; it is a placement representation, not a full decoder.
The recursive pair fold preserves the explicit input order, but still requires
an upstream symbol-to-pair mapping to operate on text.
