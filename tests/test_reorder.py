from textwrap import dedent
from cleanedit import analyze_source
from pyonetrue import reorder_top_level_spans

def test_basic_reorder():
    code = dedent("""
        import os
        import sys

        def b(): pass
        def a(): pass

        if __name__ == '__main__': print("Hi")
    """)
    spans = analyze_source(code)
    _, result = reorder_top_level_spans("dummy", spans)
    assert any(span.kind == "functiondef" for span in result)

def test_reorder_omit_main():
    code = dedent("""
        import x
        def f(): pass
        if __name__ == '__main__': print("Run")
    """)
    spans = analyze_source(code)
    _, result = reorder_top_level_spans("dummy", spans, omit_main=True)
    assert all("__name__" not in span.text for span in result)
