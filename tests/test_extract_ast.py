import ast
import pytest

from pyonetrue import extract_spans, Span
from pyonetrue import FlatteningContext

# Edge and stress case sources
EDGE_SOURCES = {
    "module_docstring_and_comments": (
        '"""Module doc."""\n'# module docstring
        '# License header comment\n'
        'import os, sys\n'
        'from collections import defaultdict\n'
        '"""A multi-line\nstring literal"""\n'
        'class A:\n    pass\n'
        'def foo():\n    pass\n'
        'if __name__ == "__main__":\n    foo()\n'
    ),
    "try_except_finally": (
        'try:\n'
        '    x = 1/0\n'
        'except ZeroDivisionError as e:\n'
        '    print(e)\n'
        'finally:\n'
        '    print("done")\n'
    ),
    "with_statement_and_nested_def": (
        'with open("file.txt") as f:\n'
        '    data = f.read()\n'
        '    def inner():\n'
        '        return data.lower()\n'
    ),
    "decorated_function": (
        '@decorator(arg=1)\n'
        'def decorated():\n'
        '    pass\n'
    ),
}

@pytest.mark.parametrize("name, source", list(EDGE_SOURCES.items()))
def test_extract_spans_kinds(name, source):
    spans = extract_spans(source, filename=name)
    kinds = [s.kind for s in spans]
    # Basic assertions: all spans are instances of Span and have expected kinds
    assert all(isinstance(s, Span) for s in spans)
    # Check that import lines are captured
    if 'import' in name:
        assert 'import' in kinds
    if name == 'module_docstring_and_comments':
        # Expect order: module docstring (logic), import, import, multi-line literal (logic), class, function, main_guard
        assert kinds == ['logic', 'import', 'import', 'logic', 'class', 'function', 'main_guard']
    else:
        assert any(k in kinds for k in ['logic', 'function'])



@pytest.mark.parametrize("structure", [10, 100])
def test_performance_on_many_defs(tmp_path, structure):
    # Generate a module with many function definitions
    lines = [f'def f{i}():\n    return {i}\n' for i in range(structure)]
    source = "".join(lines)
    spans = extract_spans(source, filename='many_defs')
    # Should extract exactly 'structure' function spans
    fn_spans = [s for s in spans if s.kind == 'function']
    assert len(fn_spans) == structure

# Ensure nested definitions are not extracted at top level

def test_nested_definitions_not_extracted():
    source = (
        'def outer():\n'
        '    def inner():\n'
        '        pass\n'
        '    return inner\n'
        'class C:\n'
        '    def method(self):\n'
        '        pass\n'
    )
    spans = extract_spans(source, filename='nested')
    kinds = [s.kind for s in spans]
    # Should only have one function (outer) and one class
    assert kinds.count('function') == 1
    assert kinds.count('class') == 1

# Test that code with no main guard skips main_guard kind

def test_no_main_guard_yields_no_main_guard():
    source = 'import os\n'
    spans = extract_spans(source, filename='no_main')
    assert all(s.kind != 'main_guard' for s in spans)

def test_extract_ast_alias_imports():
    src = "import os as o\nfrom . import x\nfrom ..pkg import y"
    spans = extract_spans(src, filename="f.py")
    kinds = [s.kind for s in spans]
    assert kinds.count('import') == 3

def test_extract_ast_decorators_and_async():
    src = "@dec\ndef foo(): pass\nasync def bar(): pass"
    spans = extract_spans(src, filename="f.py")
    kinds = [s.kind for s in spans]
    assert '@dec' in spans[0].text
    assert 'function' in kinds

def test_extract_ast_comments_and_docstrings():
    src = '"""doc"""\n# comment\nimport os'
    spans = extract_spans(src, filename="f.py")
    assert any(s.kind=='import' and 'import os' in s.text for s in spans)

def test_extract_ast_syntax_error():
    with pytest.raises(SyntaxError):
        extract_spans("def x(: pass", filename="f.py")

