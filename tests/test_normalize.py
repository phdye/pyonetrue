from pyonetrue import normalize_import_spans, is_import_span
from cleanedit import analyze_source, rebuild_source_from_spans
from textwrap import dedent


def test_normalize_import_spans():
    code = dedent("""
        import os, sys
        from math import pi
        import re
    """)
    spans = analyze_source(code)
    import_spans = [s for s in spans if is_import_span(s)]
    normalized = normalize_import_spans(import_spans)
    text = rebuild_source_from_spans(normalized)
    assert "os" in text and ("math" in text or "pi" in text)
