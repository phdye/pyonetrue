from pyonetrue import is_classdef_span, is_functiondef_span, is_main_guard_span
from cleanedit import analyze_source


def test_is_classdef_span():
    source = """
class Foo:
    pass
    """
    spans = analyze_source(source)
    assert any(is_classdef_span(s) for s in spans)


def test_is_functiondef_span():
    source = """
def foo():
    pass
    """
    spans = analyze_source(source)
    assert any(is_functiondef_span(s) for s in spans)


def test_is_main_guard_span():
    source = """
if __name__ == '__main__':
    print("hi")
    """
    spans = analyze_source(source)
    assert any(is_main_guard_span(s) for s in spans)
