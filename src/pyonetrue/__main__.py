#!/usr/bin/env python3
"""
Usage:
  pyonetrue <input.py> (--stdout | -o <output>) [--no-main] [--trace]
  pyonetrue (-h | --help)

Options:
  -h --help       Show this help message
  -o <output>     Write output to file
  --stdout        Output to STDOUT (required if -o is not given)
  --no-main       Omit __main__ block even if present
  --trace         Emit trace output to stderr and show warnings in STDOUT
"""

import sys
from pathlib import Path

from cleanedit import analyze_source, rebuild_source_from_spans

from pyonetrue import (
    normalize_import_spans,
    reorder_top_level_spans,
    extract_main_guard_span,
    is_import_span,
)

def run(filename: str, omit_main: bool = False, trace: bool = False, output: str = None):
    source = Path(filename).read_text(encoding="utf-8")
    spans = analyze_source(source)

    import_spans = [s for s in spans if is_import_span(s)]
    non_import_spans = [s for s in spans if not is_import_span(s)]

    normalized_imports = normalize_import_spans(import_spans, trace=trace)
    main_guard, remaining = extract_main_guard_span(non_import_spans)
    ordered = reorder_top_level_spans(remaining, trace=trace)

    new_spans = normalized_imports + ordered
    if main_guard and not omit_main:
        new_spans.append(main_guard)

    result = rebuild_source_from_spans(new_spans)

    if output:
        Path(output).write_text(result, encoding="utf-8")
    else:
        if trace:
            for line in result.splitlines():
                if line.startswith("# [WARNING]") or line.startswith("# missing:"):
                    print(line, file=sys.stdout)
        print(result, end="")

if __name__ == "__main__":
    if "-h" in sys.argv or "--help" in sys.argv or len(sys.argv) < 2:
        print(__doc__.strip())
        sys.exit(0)

    omit_main = "--no-main" in sys.argv
    trace = "--trace" in sys.argv
    output = None
    use_stdout = "--stdout" in sys.argv
    args = []

    skip_next = False
    for i, arg in enumerate(sys.argv[1:]):
        if skip_next:
            skip_next = False
            continue
        if arg == "-o" and i + 2 <= len(sys.argv):
            output = sys.argv[i + 2]
            skip_next = True
        elif arg.startswith("-"):
            continue
        else:
            args.append(arg)

    if not args:
        sys.exit("Error: missing input file.\n\n" + __doc__)

    if not output and not use_stdout:
        sys.exit("Error: either --stdout or -o <file> must be specified.\n\n" + __doc__)

    run(args[0], omit_main=omit_main, trace=trace, output=output if not use_stdout else None)
