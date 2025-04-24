from pyonetrue import gather_imported_names, gather_class_and_func_names
from cleanedit import analyze_source
from textwrap import dedent


def test_gather_imported_names():
    code = dedent("""
        import os
        from sys import path
        import math as m
    """)
    spans = analyze_source(code)
    names = gather_imported_names(spans)
    assert set(names) >= {"os", "path", "m"}


def test_gather_class_and_func_names():
    code = dedent("""
        def foo(): pass
        class Bar: pass
    """)
    spans = analyze_source(code)
    names = gather_class_and_func_names(spans)
    assert set(names) >= {"foo", "Bar"}