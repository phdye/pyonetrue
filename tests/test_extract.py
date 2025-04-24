from pyonetrue import extract_defined_names, extract_used_names, extract_main_guard_span
from cleanedit import analyze_source
from textwrap import dedent


def test_extract_defined_names():
    code = """
def foo(): pass
class Bar: pass
x = 1
    """
    spans = analyze_source(code)
    names = set()
    for s in spans:
        names.update(extract_defined_names(s))
    assert set(names) >= {"foo", "Bar", "x"}


def test_extract_used_names():
    code = """
print(x)
os.path.join("a", "b")
    """
    spans = analyze_source(code)
    names = set()
    for s in spans:
        names.update(extract_used_names(s))
    assert "x" in names
    assert "os" in names


def test_extract_main_guard_span():
    code = """
if __name__ == '__main__':
    run()
    """
    spans = analyze_source(code)
    span, _ = extract_main_guard_span(spans)
    assert span is not None
    assert "__main__" in span.text

